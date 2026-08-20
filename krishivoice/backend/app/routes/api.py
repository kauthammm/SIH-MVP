from fastapi import APIRouter, Depends, HTTPException, Query, Header, UploadFile, File
from typing import Optional

from app.db.database import get_db, USE_CSV
from app.models.schemas import (
    FarmerOut, ParcelOut, SoilOut, WeatherOut, IrrigationOut,
    CropObservationOut, RiskOut, AdvisoryOut, VoiceQueryIn, VoiceQueryOut,
    YieldPredictionIn, YieldPredictionOut, IrrigationPredictionOut,
    OpenMeteoHourlyOut, LoginIn, LoginOut, RegisterIn, GuestVoiceQueryIn,
    GuestSessionStartIn, GuestSessionOut, DailyBriefingOut, FarmReportOut, NotificationsOut,
    ParcelCustomIn, FarmerProfileOut,
    AlertsOut, WeatherAlertOut, CallBriefingIn, CallBriefingOut, CallQueryIn, CallQueryOut,
    FarmMapOut, SegmentsUpdateIn, FarmLandCreateIn, GeocodeOut,
    SpeakIn, ConversationOut, ConversationDetailOut, ConversationCreateIn, ChatMessageOut,
    SoilExtractOut, SoilAnalyzeIn, SoilRecommendOut, CropSuitabilityIn, CropSuitabilityOut,
)
from app.services.auth_deps import require_user, get_optional_user, assert_farmer_owner
from app.services.advisory_engine import assess_risks, generate_advisory, predict_irrigation
from app.services.voice_intent import process_voice_query
from app.services.agent_orchestrator import process_voice_with_agent
from fastapi.responses import Response

router = APIRouter()


def _persist_conversation_turn(
    user_id: Optional[str],
    conversation_id: Optional[str],
    query_text: str,
    response_text: str,
    meta: Optional[dict] = None,
) -> None:
    if not user_id or not conversation_id:
        return
    from app.services.conversation_store import add_message
    add_message(user_id, conversation_id, "user", query_text)
    add_message(user_id, conversation_id, "assistant", response_text, meta=meta or {})


def _ctx(db, parcel_id, farmer_id: str | None = None):
    from app.services import context_cache
    cache_key = f"{farmer_id}:{parcel_id}" if farmer_id else parcel_id
    cached = context_cache.get_cached(cache_key)
    if cached:
        return cached

    ctx = None
    if farmer_id and parcel_id:
        from app.services.profile_store import is_custom_land, build_context_from_custom_land
        if is_custom_land(farmer_id, parcel_id):
            ctx = build_context_from_custom_land(farmer_id, parcel_id)

    if ctx is None:
        if USE_CSV:
            from app.services import csv_store
            ctx = csv_store.get_parcel_context(parcel_id)
        else:
            from app.services.field_context import get_parcel_context
            ctx = get_parcel_context(db, parcel_id)

    if ctx:
        from app.services.openmeteo_weather import enrich_context_with_openmeteo
        ctx = enrich_context_with_openmeteo(ctx)
        if farmer_id:
            from app.services.profile_store import apply_custom_to_context
            ctx = apply_custom_to_context(ctx, farmer_id, parcel_id)
        context_cache.set_cached(cache_key, ctx)
    return ctx


@router.get("/health")
def health():
    from app.config import get_settings
    from app.services.openrouter_client import is_enabled as openrouter_ready
    from app.services.prediction_engine import model_status
    s = get_settings()
    ms = model_status()
    from app.services.advisory_search import advisory_index_stats
    from app.services.canonical_rag import index_stats as canonical_index_stats
    return {
        "status": "ok",
        "service": "KrishiVoice API",
        "storage": "csv" if USE_CSV else "postgresql",
        "weather": "open-meteo" if s.use_openmeteo else "synthetic",
        "openrouter": openrouter_ready(),
        "openrouter_vl_model": s.openrouter_vl_model if openrouter_ready() else None,
        "tavily": __import__("app.services.tavily_search", fromlist=["is_enabled"]).is_enabled(),
        "prediction_mode": ms.get("mode"),
        "soil_crop_model": ms.get("soil_crop_model"),
        "yield_model": ms.get("yield_model"),
        "data_source": "cleaned_csv_preferred",
        "indexes": advisory_index_stats(),
        "canonical_qa": canonical_index_stats(),
        "ml_metrics": ms.get("metrics", {}),
    }


@router.get("/predict/status")
def predict_status():
    from app.services.prediction_engine import model_status
    return model_status()


def _parcel_coords(parcel_id: str, db, farmer_id: Optional[str] = None) -> tuple[float, float]:
    if farmer_id:
        from app.services.profile_store import load_profile, custom_land_as_parcel
        prof = load_profile(farmer_id)
        custom = prof.get("parcels", {}).get(parcel_id, {})
        if custom.get("latitude") is not None and custom.get("longitude") is not None:
            return float(custom["latitude"]), float(custom["longitude"])
        cl = custom_land_as_parcel(farmer_id, parcel_id)
        if cl:
            return float(cl["latitude"]), float(cl["longitude"])

    if USE_CSV:
        from app.services import csv_store
        p = csv_store.get_parcel(parcel_id)
    else:
        from app.models.orm import LandParcel
        row = db.query(LandParcel).filter(LandParcel.parcel_id == parcel_id).first()
        p = row
    if not p:
        raise HTTPException(404, "Parcel not found")
    lat = float(p["latitude"] if isinstance(p, dict) else p.latitude)
    lon = float(p["longitude"] if isinstance(p, dict) else p.longitude)
    return lat, lon


@router.get("/farmers/{farmer_id}", response_model=FarmerOut)
def get_farmer(farmer_id: str, db=Depends(get_db)):
    if USE_CSV:
        from app.services import csv_store
        row = csv_store.get_farmer(farmer_id)
        if not row:
            raise HTTPException(404, "Farmer not found")
        return row
    from app.models.orm import Farmer
    farmer = db.query(Farmer).filter(Farmer.farmer_id == farmer_id).first()
    if not farmer:
        raise HTTPException(404, "Farmer not found")
    return farmer


@router.get("/farmers/{farmer_id}/parcels", response_model=list[ParcelOut])
def get_farmer_parcels(farmer_id: str, db=Depends(get_db)):
    _get_farmer_or_404(farmer_id, db)
    from app.services.profile_store import list_all_lands
    return list_all_lands(farmer_id)


@router.get("/parcels/{parcel_id}", response_model=ParcelOut)
def get_parcel_route(parcel_id: str, farmer_id: Optional[str] = None, db=Depends(get_db)):
    if farmer_id:
        from app.services.profile_store import get_merged_parcel
        merged = get_merged_parcel(farmer_id, parcel_id)
        if merged:
            return merged
    if USE_CSV:
        from app.services import csv_store
        p = csv_store.get_parcel(parcel_id)
        if not p:
            raise HTTPException(404, "Parcel not found")
        return p
    from app.models.orm import LandParcel
    p = db.query(LandParcel).filter(LandParcel.parcel_id == parcel_id).first()
    if not p:
        raise HTTPException(404, "Parcel not found")
    return p


@router.get("/parcels/{parcel_id}/soil", response_model=list[SoilOut])
def get_parcel_soil(parcel_id: str, limit: int = 5, db=Depends(get_db)):
    if USE_CSV:
        import pandas as pd
        from app.services.csv_store import _load
        df = _load("soil_data.csv")
        rows = df[df["parcel_id"] == parcel_id].sort_values("sample_date", ascending=False).head(limit)
        out = []
        for _, r in rows.iterrows():
            out.append({
                "sample_date": r["sample_date"].date() if hasattr(r["sample_date"], "date") else r["sample_date"],
                "ph": float(r["pH"]),
                "nitrogen": float(r["nitrogen"]),
                "phosphorus": float(r["phosphorus"]),
                "potassium": float(r["potassium"]),
                "organic_carbon": float(r["organic_carbon"]) if pd.notna(r.get("organic_carbon")) else None,
                "soil_type": r.get("soil_type"),
            })
        return out
    from sqlalchemy import desc
    from app.models.orm import SoilSample
    return (
        db.query(SoilSample).filter(SoilSample.parcel_id == parcel_id)
        .order_by(desc(SoilSample.sample_date)).limit(limit).all()
    )


@router.get("/parcels/{parcel_id}/crops")
def get_parcel_crops(parcel_id: str, db=Depends(get_db)):
    if USE_CSV:
        from app.services.csv_store import _load
        df = _load("crop_history.csv")
        rows = df[df["parcel_id"] == parcel_id].sort_values("year", ascending=False)
        return [{"year": int(r.year), "season": r.season, "crop": r.crop,
                 "yield_tph": float(r["yield"]) if r.get("yield") == r.get("yield") else None,
                 "area": float(r.area)} for _, r in rows.iterrows()]
    from sqlalchemy import desc
    from app.models.orm import CropHistory
    rows = db.query(CropHistory).filter(CropHistory.parcel_id == parcel_id).order_by(desc(CropHistory.year)).all()
    return [{"year": r.year, "season": r.season, "crop": r.crop,
             "yield_tph": float(r.yield_tph) if r.yield_tph else None, "area": float(r.area)} for r in rows]


@router.get("/parcels/{parcel_id}/weather", response_model=list[WeatherOut])
def get_parcel_weather(
    parcel_id: str,
    days: int = 7,
    source: str = Query("openmeteo", description="openmeteo | synthetic"),
    farmer_id: Optional[str] = None,
    db=Depends(get_db),
):
    if source == "openmeteo":
        try:
            from app.config import get_settings
            from app.services.openmeteo_weather import fetch_daily_weather
            if get_settings().use_openmeteo:
                lat, lon = _parcel_coords(parcel_id, db, farmer_id=farmer_id)
                records, _ = fetch_daily_weather(lat, lon, days=days)
                return records
        except HTTPException:
            raise
        except Exception:
            pass

    if USE_CSV:
        from app.services import csv_store
        from app.services.csv_store import _load
        parcel = csv_store.get_parcel(parcel_id)
        if not parcel:
            raise HTTPException(404, "Parcel not found")
        df = _load("weather_data.csv")
        rows = df[df["district"] == parcel["district"]].sort_values("date", ascending=False).head(days)
        return [{"date": r.date.date() if hasattr(r.date, "date") else r.date,
                 "rainfall": float(r.rainfall), "temperature": float(r.temperature),
                 "humidity": float(r.humidity), "wind_speed": float(r.wind_speed),
                 "source": "synthetic"} for _, r in rows.iterrows()]
    from sqlalchemy import desc
    from app.models.orm import LandParcel, Weather
    parcel = db.query(LandParcel).filter(LandParcel.parcel_id == parcel_id).first()
    if not parcel:
        raise HTTPException(404, "Parcel not found")
    rows = db.query(Weather).filter(Weather.district == parcel.district).order_by(desc(Weather.date)).limit(days).all()
    return [{"date": r.date, "rainfall": float(r.rainfall), "temperature": float(r.temperature),
             "humidity": float(r.humidity) if r.humidity else None,
             "wind_speed": float(r.wind_speed) if r.wind_speed else None,
             "source": "synthetic"} for r in rows]


@router.get("/parcels/{parcel_id}/weather/hourly", response_model=OpenMeteoHourlyOut)
def get_parcel_weather_hourly(parcel_id: str, days: int = 7, db=Depends(get_db)):
    """Full Open-Meteo hourly forecast with soil moisture layers (REAL DATA)."""
    from app.services.openmeteo_weather import fetch_hourly_forecast, aggregate_daily
    lat, lon = _parcel_coords(parcel_id, db)
    hourly_df, meta = fetch_hourly_forecast(lat, lon, forecast_days=days)
    daily_df = aggregate_daily(hourly_df)
    hourly_df["date"] = hourly_df["date"].astype(str)
    return OpenMeteoHourlyOut(
        latitude=meta["latitude"],
        longitude=meta["longitude"],
        elevation_m=meta["elevation_m"],
        rows=hourly_df.head(days * 24).to_dict(orient="records"),
        daily=daily_df.tail(days).to_dict(orient="records"),
    )


@router.get("/parcels/{parcel_id}/irrigation", response_model=list[IrrigationOut])
def get_parcel_irrigation(parcel_id: str, limit: int = 10, db=Depends(get_db)):
    if USE_CSV:
        from app.services.csv_store import _load
        df = _load("irrigation_data.csv")
        rows = df[df["parcel_id"] == parcel_id].sort_values("date", ascending=False).head(limit)
        return [{"event_date": r.date.date() if hasattr(r.date, "date") else r.date,
                 "method": r.get("method"),
                 "soil_moisture_before": float(r.soil_moisture_before) if r.get("soil_moisture_before") == r.get("soil_moisture_before") else None,
                 "soil_moisture_after": float(r.soil_moisture_after) if r.get("soil_moisture_after") == r.get("soil_moisture_after") else None,
                 "water_used": float(r.water_used) if r.get("water_used") == r.get("water_used") else None} for _, r in rows.iterrows()]
    from sqlalchemy import desc
    from app.models.orm import IrrigationEvent
    return db.query(IrrigationEvent).filter(IrrigationEvent.parcel_id == parcel_id).order_by(desc(IrrigationEvent.event_date)).limit(limit).all()


@router.get("/parcels/{parcel_id}/observations", response_model=list[CropObservationOut])
def get_observations(parcel_id: str, limit: int = 5, db=Depends(get_db)):
    if USE_CSV:
        from app.services.csv_store import _load
        df = _load("crop_observations.csv")
        rows = df[df["parcel_id"] == parcel_id].sort_values("date", ascending=False).head(limit)
        return [{"obs_date": r.date.date() if hasattr(r.date, "date") else r.date, "crop": r.crop,
                 "growth_stage": r.get("growth_stage"), "plant_height": float(r.plant_height) if r.get("plant_height") == r.get("plant_height") else None,
                 "leaf_condition": r.get("leaf_condition"), "pest": r.get("pest"), "disease": r.get("disease"),
                 "ndvi": float(r.NDVI) if r.get("NDVI") == r.get("NDVI") else None} for _, r in rows.iterrows()]
    from sqlalchemy import desc
    from app.models.orm import CropObservation
    return db.query(CropObservation).filter(CropObservation.parcel_id == parcel_id).order_by(desc(CropObservation.obs_date)).limit(limit).all()


@router.get("/parcels/{parcel_id}/risks", response_model=RiskOut)
def get_risks(parcel_id: str, db=Depends(get_db)):
    ctx = _ctx(db, parcel_id)
    if not ctx:
        raise HTTPException(404, "Parcel not found")
    return assess_risks(ctx)


@router.get("/parcels/{parcel_id}/advisory", response_model=AdvisoryOut)
def get_advisory(parcel_id: str, intent: str = "general_agriculture", db=Depends(get_db)):
    ctx = _ctx(db, parcel_id)
    if not ctx:
        raise HTTPException(404, "Parcel not found")
    return generate_advisory(ctx, intent)


@router.post("/advisory/generate", response_model=AdvisoryOut)
def post_advisory(parcel_id: str = Query(...), intent: str = Query("general_agriculture"), db=Depends(get_db)):
    ctx = _ctx(db, parcel_id)
    if not ctx:
        raise HTTPException(404, "Parcel not found")
    return generate_advisory(ctx, intent)


@router.post("/prediction/irrigation", response_model=IrrigationPredictionOut)
def post_irrigation_prediction(parcel_id: str = Query(...), db=Depends(get_db)):
    ctx = _ctx(db, parcel_id)
    if not ctx:
        raise HTTPException(404, "Parcel not found")
    return predict_irrigation(ctx)


@router.post("/prediction/yield", response_model=YieldPredictionOut)
def post_yield_prediction(body: YieldPredictionIn, db=Depends(get_db)):
    ctx = _ctx(db, body.parcel_id)
    if not ctx:
        raise HTTPException(404, "Parcel not found")
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
        from ml.train_models import predict_yield
        features = {"crop": ctx["crop"].crop if ctx.get("crop") else "Rice"}
        return YieldPredictionOut(**predict_yield(features))
    except FileNotFoundError:
        return YieldPredictionOut(predicted_yield_tph=4.2, confidence=0.65, model="rule_baseline",
                                  features_used={"note": "Run ml/train_models.py"})


@router.post("/auth/register", response_model=LoginOut)
def register(body: RegisterIn, db=Depends(get_db)):
    from app.services.user_auth import register_user, create_session, ensure_demo_user
    from app.services.profile_store import get_farmer_display_name

    ensure_demo_user()
    try:
        user = register_user(
            body.username,
            body.password,
            display_name=body.display_name,
            farmer_id=body.farmer_id,
            district=body.district,
            village=body.village,
            primary_crop=body.primary_crop,
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

    farmer_id = user["farmer_id"]
    _get_farmer_or_404(farmer_id, db)
    token = create_session(user["user_id"])
    meta = _login_meta_for_farmer(farmer_id)
    return LoginOut(
        token=token,
        farmer_id=farmer_id,
        display_name=user.get("display_name") or user["username"],
        message=f"Account created. Your farm record {farmer_id} is ready.",
        user_id=user["user_id"],
        username=user["username"],
        auth_mode="user",
        **meta,
    )


@router.post("/auth/login", response_model=LoginOut)
def login(body: LoginIn, db=Depends(get_db)):
    from app.services.profile_store import verify_login, get_farmer_display_name
    from app.services.user_auth import authenticate_user, create_session, ensure_demo_user

    ensure_demo_user()

    # Username + password (ChatGPT-style)
    if body.username and body.password:
        user = authenticate_user(body.username, body.password)
        if not user:
            raise HTTPException(401, detail="Invalid username or password")
        farmer_id = user["farmer_id"]
        _get_farmer_or_404(farmer_id, db)
        token = create_session(user["user_id"])
        meta = _login_meta_for_farmer(farmer_id)
        return LoginOut(
            token=token,
            farmer_id=farmer_id,
            display_name=user.get("display_name") or user["username"],
            message=f"Welcome back. Farm {farmer_id} loaded.",
            user_id=user["user_id"],
            username=user["username"],
            auth_mode="user",
            **meta,
        )

    # Legacy farmer ID + PIN
    if not body.farmer_id or not body.pin:
        raise HTTPException(400, detail="Use username/password or farmer ID + PIN")
    if not verify_login(body.farmer_id, body.pin):
        raise HTTPException(401, detail="Invalid farmer ID or PIN. Demo PIN: 1234")
    _get_farmer_or_404(body.farmer_id, db)
    return LoginOut(
        token=f"demo-{body.farmer_id}",
        farmer_id=body.farmer_id,
        display_name=get_farmer_display_name(body.farmer_id),
        message="Login successful. Sign up with username for saved chat history.",
        auth_mode="farmer",
    )


@router.get("/auth/me")
def auth_me(user=Depends(require_user)):
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "display_name": user.get("display_name"),
        "farmer_id": user.get("farmer_id"),
    }


@router.get("/conversations", response_model=list[ConversationOut])
def list_user_conversations(user=Depends(require_user)):
    from app.services.conversation_store import list_conversations
    return list_conversations(user["user_id"])


@router.post("/conversations", response_model=ConversationOut)
def create_user_conversation(body: ConversationCreateIn, user=Depends(require_user)):
    from app.services.conversation_store import create_conversation
    conv = create_conversation(user["user_id"], body.title)
    return ConversationOut(
        id=conv["id"],
        title=conv["title"],
        created_at=conv.get("created_at"),
        updated_at=conv.get("updated_at"),
        message_count=0,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
def get_user_conversation(conversation_id: str, user=Depends(require_user)):
    from app.services.conversation_store import get_conversation
    conv = get_conversation(user["user_id"], conversation_id)
    if not conv:
        raise HTTPException(404, detail="Conversation not found")
    return ConversationDetailOut(
        id=conv["id"],
        title=conv.get("title") or "New chat",
        created_at=conv.get("created_at"),
        updated_at=conv.get("updated_at"),
        messages=[ChatMessageOut(**m) for m in conv.get("messages") or []],
    )


@router.delete("/conversations/{conversation_id}")
def delete_user_conversation(conversation_id: str, user=Depends(require_user)):
    from app.services.conversation_store import delete_conversation
    if not delete_conversation(user["user_id"], conversation_id):
        raise HTTPException(404, detail="Conversation not found")
    return {"ok": True}


@router.get("/farmers/{farmer_id}/profile", response_model=FarmerProfileOut)
def get_profile(
    farmer_id: str,
    db=Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    from app.services.profile_store import load_profile, get_farmer_display_name, list_all_lands

    user = get_optional_user(authorization)
    if user:
        assert_farmer_owner(user, farmer_id)
    prof = load_profile(farmer_id)
    farmer = _get_farmer_or_404(farmer_id, db)
    parcels = list_all_lands(farmer_id)
    return FarmerProfileOut(
        farmer_id=farmer_id,
        display_name=get_farmer_display_name(farmer_id),
        active_parcel_id=prof.get("active_parcel_id"),
        parcels_custom=prof.get("parcels", {}),
        farmer=farmer,
        parcels=parcels,
    )


def _login_meta_for_farmer(farmer_id: str) -> dict:
    from app.services.profile_store import load_profile, get_merged_parcel
    from app.services import csv_store

    prof = load_profile(farmer_id)
    parcel_id = prof.get("active_parcel_id")
    district = village = None
    if parcel_id:
        merged = get_merged_parcel(farmer_id, parcel_id)
        if merged:
            district = merged.get("district")
            village = merged.get("village") or merged.get("land_name")
    if not district:
        farmer = csv_store.get_farmer(farmer_id)
        if farmer:
            district = farmer.get("district")
            village = village or farmer.get("village")
    return {
        "parcel_id": parcel_id,
        "district": district,
        "village": village,
    }


def _get_farmer_or_404(farmer_id: str, db):
    if USE_CSV:
        from app.services import csv_store
        row = csv_store.get_farmer(farmer_id)
        if not row:
            raise HTTPException(404, "Farmer not found")
        return row
    from app.models.orm import Farmer
    farmer = db.query(Farmer).filter(Farmer.farmer_id == farmer_id).first()
    if not farmer:
        raise HTTPException(404, "Farmer not found")
    return farmer


@router.put("/farmers/{farmer_id}/parcels/{parcel_id}/custom")
def save_parcel_custom(
    farmer_id: str,
    parcel_id: str,
    body: ParcelCustomIn,
    db=Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    from app.services import context_cache
    from app.services.profile_store import update_parcel_custom, is_custom_land, create_custom_land
    from app.services.geocode import reverse_geocode
    from app.services.geo_utils import polygon_area_ha

    user = get_optional_user(authorization)
    if user:
        assert_farmer_owner(user, farmer_id)
    _get_farmer_or_404(farmer_id, db)
    custom = body.model_dump(exclude_none=True)

    # Auto-fill place name from GPS / drawn boundary centroid
    lat = custom.get("latitude")
    lon = custom.get("longitude")
    if lat is not None and lon is not None:
        if not custom.get("land_name") or not custom.get("village"):
            geo = reverse_geocode(float(lat), float(lon))
            if not custom.get("land_name"):
                custom["land_name"] = geo.get("land_name") or geo.get("village") or ""
            if not custom.get("village"):
                custom["village"] = geo.get("village") or custom.get("land_name") or ""
            if not custom.get("taluk"):
                custom["taluk"] = geo.get("taluk") or ""
            if not custom.get("district"):
                custom["district"] = geo.get("district") or ""

    boundary = custom.get("boundary")
    if boundary and len(boundary) >= 3 and not custom.get("area"):
        custom["area"] = round(polygon_area_ha(boundary), 3)

    if parcel_id.startswith("FL") and not is_custom_land(farmer_id, parcel_id):
        create_custom_land(farmer_id, {**custom, "is_custom_land": True})
    else:
        update_parcel_custom(farmer_id, parcel_id, custom)
    context_cache.invalidate(f"{farmer_id}:{parcel_id}")
    context_cache.invalidate(parcel_id)
    return {"status": "saved", "parcel_id": parcel_id, "land_name": custom.get("land_name"), "village": custom.get("village")}


@router.post("/farmers/{farmer_id}/lands")
def create_farm_land(farmer_id: str, body: FarmLandCreateIn, db=Depends(get_db)):
    from app.services.profile_store import create_custom_land
    from app.services.geocode import reverse_geocode
    _get_farmer_or_404(farmer_id, db)
    initial = body.model_dump(exclude_none=True)
    if body.latitude is not None and body.longitude is not None:
        geo = reverse_geocode(body.latitude, body.longitude)
        initial.setdefault("village", geo.get("village"))
        initial.setdefault("taluk", geo.get("taluk"))
        initial.setdefault("district", geo.get("district"))
        if not initial.get("land_name") and geo.get("village"):
            initial["land_name"] = geo["village"]
    created = create_custom_land(farmer_id, initial)
    return {"status": "created", "land": created}


@router.delete("/farmers/{farmer_id}/lands/{land_id}")
def delete_farm_land(farmer_id: str, land_id: str, db=Depends(get_db)):
    from app.services.profile_store import delete_custom_land
    from app.services import context_cache
    _get_farmer_or_404(farmer_id, db)
    if not delete_custom_land(farmer_id, land_id):
        raise HTTPException(404, "Custom farm land not found")
    context_cache.invalidate(f"{farmer_id}:{land_id}")
    return {"status": "deleted", "land_id": land_id}


@router.get("/geo/reverse", response_model=GeocodeOut)
def reverse_geo(lat: float = Query(...), lon: float = Query(...)):
    from app.services.geocode import reverse_geocode
    data = reverse_geocode(lat, lon)
    return GeocodeOut(
        latitude=data["latitude"],
        longitude=data["longitude"],
        display_name=data.get("display_name") or "",
        land_name=data.get("land_name") or data.get("village") or "",
        village=data.get("village") or "",
        taluk=data.get("taluk") or "",
        district=data.get("district") or "",
        state=data.get("state") or "Tamil Nadu",
    )


@router.post("/voice/guest/session", response_model=GuestSessionOut)
def start_guest_session(body: GuestSessionStartIn):
    from app.services.voice_onboarding import start_session
    result = start_session(body.language)
    return GuestSessionOut(**result)


@router.post("/voice/guest/chat", response_model=GuestSessionOut)
def guest_chat(body: GuestVoiceQueryIn):
    from app.services.voice_onboarding import process_guest_message, start_session
    if not body.session_id:
        started = start_session(body.language if body.language != "Auto" else "Tamil")
        body.session_id = started["session_id"]
    result = process_guest_message(body.session_id, body.query_text)
    return GuestSessionOut(**result)


@router.get("/voice/daily-briefing", response_model=DailyBriefingOut)
def daily_briefing(
    farmer_id: Optional[str] = None,
    parcel_id: Optional[str] = None,
    session_id: Optional[str] = None,
    language: str = "Tamil",
    db=Depends(get_db),
):
    from app.services.daily_briefing import build_daily_briefing
    from app.services.guest_session import get_session, session_to_context
    from app.services.openmeteo_weather import enrich_context_with_openmeteo

    ctx = None
    is_guest = True
    if farmer_id and parcel_id:
        ctx = _ctx(db, parcel_id, farmer_id)
        is_guest = False
    elif session_id:
        session = get_session(session_id)
        if session:
            ctx = enrich_context_with_openmeteo(session_to_context(session))
    if not ctx:
        from app.services.weather_alerts import build_guest_weather_context
        ctx = build_guest_weather_context()
        ctx = enrich_context_with_openmeteo(ctx)

    briefing = build_daily_briefing(ctx, language, is_guest=is_guest)
    out = DailyBriefingOut(**briefing)
    out.weather_source = ctx.get("weather_source", "open-meteo")
    return out


@router.get("/voice/farm-report", response_model=FarmReportOut)
def voice_farm_report(
    period: str = Query("weekly", description="daily | weekly | monthly | yearly"),
    farmer_id: Optional[str] = None,
    parcel_id: Optional[str] = None,
    session_id: Optional[str] = None,
    language: str = "Tamil",
    db=Depends(get_db),
):
    from app.services.farm_reports import build_farm_report
    from app.services.guest_session import get_session, session_to_context
    from app.services.openmeteo_weather import enrich_context_with_openmeteo

    ctx = None
    if farmer_id and parcel_id:
        _get_farmer_or_404(farmer_id, db)
        ctx = _ctx(db, parcel_id, farmer_id)
    elif session_id:
        session = get_session(session_id)
        if session:
            ctx = enrich_context_with_openmeteo(session_to_context(session))
    if not ctx:
        from app.services.weather_alerts import build_guest_weather_context
        ctx = enrich_context_with_openmeteo(build_guest_weather_context())
    if not ctx:
        raise HTTPException(404, "Farm context not found")

    if period not in ("daily", "weekly", "monthly", "yearly"):
        raise HTTPException(400, detail="period must be daily, weekly, monthly, or yearly")

    return FarmReportOut(**build_farm_report(ctx, period=period, language=language))


@router.get("/farmers/{farmer_id}/parcels/{parcel_id}/farm-report", response_model=FarmReportOut)
def parcel_farm_report(
    farmer_id: str,
    parcel_id: str,
    period: str = Query("weekly"),
    language: str = "Tamil",
    db=Depends(get_db),
):
    from app.services.farm_reports import build_farm_report

    _get_farmer_or_404(farmer_id, db)
    ctx = _ctx(db, parcel_id, farmer_id)
    if not ctx:
        raise HTTPException(404, "Parcel not found")
    if period not in ("daily", "weekly", "monthly", "yearly"):
        raise HTTPException(400, detail="Invalid period")
    return FarmReportOut(**build_farm_report(ctx, period=period, language=language))


@router.get("/knowledge/convo-stats")
def convo_stats():
    from app.services.advisory_search import advisory_index_stats
    return advisory_index_stats()


@router.get("/knowledge/stats")
def knowledge_stats():
    from app.services.farmer_knowledge import build_knowledge_index
    return build_knowledge_index()


@router.get("/voice/demand-forecast")
def demand_forecast(crop: Optional[str] = None, land_type: str = "Wetland", district: Optional[str] = None, language: str = "Tamil"):
    from app.services.crop_recommendation import format_crop_recommendations, format_demand_forecast
    if crop:
        en, ta, ev, conf = format_demand_forecast(crop, language, district=district)
    else:
        en, ta, ev, conf = format_crop_recommendations(land_type, district, None, language)
    text = ta if language == "Tamil" else en
    return {"text": text, "english": en, "tamil": ta, "evidence": ev, "confidence": conf}


@router.get("/market/catalog")
def market_catalog():
    """Commodity categories: vegetables, pulses, cereals, fruits, spices, oilseeds."""
    from app.services.mandi_price_service import list_catalog
    return list_catalog()


@router.get("/market/prices")
def market_prices(
    commodity: Optional[str] = Query(None, description="e.g. Tomato, Black Gram, Paddy"),
    category: Optional[str] = Query(None, description="vegetables | pulses | cereals | fruits | spices | oilseeds"),
    district: Optional[str] = Query(None, description="Tamil Nadu district filter"),
    state: str = Query("Tamil Nadu"),
):
    """Live mandi modal/min/max from AGMARKNET (data.gov.in)."""
    from app.services.mandi_price_service import (
        format_category_speech,
        format_live_price_speech,
        get_category_prices,
        get_live_mandi_price,
        resolve_category,
        resolve_commodity,
    )

    if category or (commodity and resolve_category(commodity)):
        cat = resolve_category(category or commodity or "") or category
        snap = get_category_prices(cat or "vegetables", district=district, state=state)
        en, ta = format_category_speech(snap.get("prices", []), cat or "market", "English")
        return {
            "english": en,
            "tamil": ta,
            "category": cat,
            "prices": snap.get("prices", []),
            "source": "agmarknet",
            "state": state,
            "district": district,
            "ok": snap.get("ok", False),
        }

    name = resolve_commodity(commodity or "") or commodity
    if not name:
        from fastapi import HTTPException
        raise HTTPException(400, detail="Provide commodity or category")

    live = get_live_mandi_price(name, district=district, state=state)
    if not live.get("ok"):
        return {"ok": False, "commodity": name, "error": live.get("error"), "source": "agmarknet"}

    en, ta = format_live_price_speech(live["summary"], lang="English")
    return {
        "ok": True,
        "commodity": name,
        "summary": live["summary"],
        "records": live.get("records", []),
        "english": en,
        "tamil": ta,
        "source": "agmarknet",
    }


@router.post("/voice/query-guest", response_model=VoiceQueryOut)
def voice_query_guest(body: GuestVoiceQueryIn):
    from app.services.voice_onboarding import process_guest_message, start_session
    from app.services.agent_orchestrator import run_voice_agent
    from app.services.weather_alerts import build_guest_weather_context
    from app.models.schemas import AdvisoryOut

    if not body.session_id:
        started = start_session(body.language if body.language != "Auto" else "Tamil")
        sid = started["session_id"]
    else:
        sid = body.session_id

    if body.use_web_search:
        parsed = run_voice_agent(
            body.query_text,
            build_guest_weather_context(),
            guest_session_id=sid,
            language_preference=body.language,
            is_guest=True,
            use_web_search=True,
        )
        adv = parsed["advisory"]
        lang = parsed["detected_language"]
        return VoiceQueryOut(
            intent=parsed["intent"],
            entities={"mode": "guest", "session_id": sid, "web_search": True},
            advisory=adv,
            transcription_confidence=0.9,
            detected_language=lang,
            normalized_query=parsed.get("normalized_query"),
            nlp_confidence=parsed.get("nlp_confidence", 0.85),
            profile_updated=False,
            profile_fields={},
        )

    result = process_guest_message(sid, body.query_text)
    lang = result.get("language", "Tamil")
    adv = result.get("advisory")
    if not adv:
        adv = AdvisoryOut(
            recommendation=result["text"],
            reason="Personalized from your voice profile and farmer knowledge base.",
            evidence=result.get("evidence", {}),
            confidence=0.85,
            action_time="Today",
            risk_level="low",
            tamil_response=result["text"] if lang == "Tamil" else None,
            english_response=result["text"] if lang == "English" else result["text"],
        )
    return VoiceQueryOut(
        intent=result.get("intent", "general_agriculture"),
        entities={"mode": "guest", "session_id": sid, "profile": result.get("profile", {})},
        advisory=adv,
        transcription_confidence=0.9,
        detected_language=lang,
        normalized_query=body.query_text,
        nlp_confidence=0.85,
        profile_updated=result.get("profile_completeness", 0) > 0,
        profile_fields=result.get("profile", {}),
    )


@router.post("/voice/query", response_model=VoiceQueryOut)
def voice_query(
    body: VoiceQueryIn,
    db=Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    from app.services.language_utils import detect_language as detect_lang
    from app.services.auth_deps import get_optional_user
    from app.services.conversation_store import create_conversation, add_message, get_conversation

    if body.guest or not body.farmer_id:
        guest = GuestVoiceQueryIn(query_text=body.query_text, language=body.language)
        return voice_query_guest(guest)

    auth_user = get_optional_user(authorization)
    if auth_user:
        assert_farmer_owner(auth_user, body.farmer_id)
    user_id = body.user_id or (auth_user.get("user_id") if auth_user else None)
    conversation_id = body.conversation_id

    if user_id and not conversation_id:
        conv = create_conversation(user_id, "New chat")
        conversation_id = conv["id"]

    farmer = _get_farmer_or_404(body.farmer_id, db)

    parcel_id = body.parcel_id
    if not parcel_id:
        from app.services.profile_store import load_profile, list_all_lands
        prof = load_profile(body.farmer_id)
        parcel_id = prof.get("active_parcel_id")
        if not parcel_id:
            parcels = list_all_lands(body.farmer_id)
            if len(parcels) == 1:
                parcel_id = parcels[0]["parcel_id"] if isinstance(parcels[0], dict) else parcels[0].parcel_id
            elif len(parcels) > 1:
                ids = [p["parcel_id"] if isinstance(p, dict) else p.parcel_id for p in parcels]
                raise HTTPException(400, detail={"message": "Select a parcel in your profile", "tamil": "Profile-ல parcel select பண்ணுங்க", "parcels": ids})
            else:
                raise HTTPException(400, detail="No parcel found")

    from app.services.farmer_speech import extract_farmer_speech, speech_to_profile_patch, acknowledgment_for_updates
    from app.services.profile_store import update_parcel_custom
    from app.services import context_cache

    # Learn profile from speech before building farm context
    farmer_speech = extract_farmer_speech(body.query_text)
    profile_updated = False
    profile_fields: dict = {}
    patch = speech_to_profile_patch(farmer_speech)
    if patch:
        # Geocode spoken village/district → GPS for weather reports
        if patch.get("village") or patch.get("district"):
            from app.services.geocode import forward_geocode
            place = patch.get("village") or patch.get("district")
            if patch.get("district") and patch.get("village"):
                place = f"{patch['village']}, {patch['district']}"
            geo = forward_geocode(str(place))
            if geo.get("latitude") and geo.get("longitude") and not geo.get("error"):
                patch["latitude"] = geo["latitude"]
                patch["longitude"] = geo["longitude"]
                if not patch.get("village") and geo.get("village"):
                    patch["village"] = geo["village"]
                if not patch.get("district") and geo.get("district"):
                    patch["district"] = geo["district"]
                if not patch.get("taluk") and geo.get("taluk"):
                    patch["taluk"] = geo["taluk"]
                profile_fields["geocoded_from_voice"] = True
        update_parcel_custom(body.farmer_id, parcel_id, patch)
        context_cache.invalidate(f"{body.farmer_id}:{parcel_id}")
        profile_updated = True
        profile_fields.update(patch)

    ctx = _ctx(db, parcel_id, body.farmer_id)
    if not ctx:
        raise HTTPException(404, "Parcel not found")

    # Merge speech-extracted fields into context for this answer
    if farmer_speech.get("growth_stage") or farmer_speech.get("crop") or farmer_speech.get("soil_type"):
        class _Row:
            def __init__(self, d):
                self.__dict__.update(d)
        obs = ctx.get("observation")
        od = obs.__dict__.copy() if obs and hasattr(obs, "__dict__") else {}
        if farmer_speech.get("growth_stage"):
            od["growth_stage"] = farmer_speech["growth_stage"]
        if farmer_speech.get("crop"):
            od["crop"] = farmer_speech["crop"]
        ctx["observation"] = _Row(od)
        if farmer_speech.get("soil_type"):
            soil = ctx.get("soil")
            sd = soil.__dict__.copy() if soil and hasattr(soil, "__dict__") else {}
            sd["soil_type"] = farmer_speech["soil_type"]
            ctx["soil"] = _Row(sd)
            land = dict(ctx.get("land_nature") or {})
            land["soil_texture"] = farmer_speech["soil_type"]
            ctx["land_nature"] = land
        if farmer_speech.get("land_type"):
            land = dict(ctx.get("land_nature") or {})
            land["land_type"] = farmer_speech["land_type"]
            ctx["land_nature"] = land
        if farmer_speech.get("irrigation_source"):
            land = dict(ctx.get("land_nature") or {})
            land["irrigation_source"] = farmer_speech["irrigation_source"]
            ctx["land_nature"] = land
    if farmer_speech.get("soil_moisture") is not None:
        ctx["soil_moisture"] = float(farmer_speech["soil_moisture"])
        ctx["soil_moisture_source"] = "farmer_voice"

    from app.services.farm_reports import build_farm_report, detect_report_period
    report_period = detect_report_period(body.query_text)
    if report_period or any(w in body.query_text.lower() for w in ("farm report", "briefing", "அறிக்கை", "weekly report", "monthly report")):
        period = report_period or "daily"
        report = build_farm_report(ctx, period=period, language=body.language if body.language != "Auto" else "Tamil")
        adv = AdvisoryOut(
            recommendation=report["text"],
            reason=f"Live farm report ({period}) from Open-Meteo + field data.",
            evidence=report.get("evidence", {}),
            confidence=0.92,
            action_time="Today",
            risk_level="low",
            tamil_response=report.get("text_ta", report["text"]),
            english_response=report.get("text_en", report["text"]),
        )
        lang = report["language"]
        resp_text = report["text"]
        _persist_conversation_turn(
            user_id, conversation_id, body.query_text, resp_text,
            meta={"intent": "farm_report", "period": period},
        )
        return VoiceQueryOut(
            intent="farm_report",
            entities={"period": period, "weather_source": report.get("weather_source")},
            advisory=adv,
            transcription_confidence=0.9,
            detected_language=lang,
            normalized_query=body.query_text,
            nlp_confidence=0.92,
            profile_updated=profile_updated,
            profile_fields=profile_fields,
            conversation_id=conversation_id,
        )

    parsed = process_voice_with_agent(
        body.query_text, body.farmer_id, parcel_id,
        language_preference=body.language, context=ctx,
        conversation_id=conversation_id,
        user_id=user_id,
        use_web_search=body.use_web_search,
    )

    advisory = parsed["advisory"]
    lang = parsed["detected_language"]

    # Prepend acknowledgment when we learned from their speech
    ack = acknowledgment_for_updates(profile_fields, lang) if profile_updated else ""
    if ack:
        if lang == "Tamil" and advisory.tamil_response:
            advisory.tamil_response = ack + advisory.tamil_response
            advisory.recommendation = advisory.tamil_response
        elif advisory.english_response:
            advisory.english_response = ack + advisory.english_response
            advisory.recommendation = advisory.english_response

    if lang == "Tamil" and advisory.tamil_response:
        advisory.recommendation = advisory.tamil_response
    elif lang == "English" and advisory.english_response:
        advisory.recommendation = advisory.english_response

    if ctx.get("profile_customized") or profile_updated:
        advisory.evidence = {**(advisory.evidence or {}), "profile_customized": True}
    if profile_updated:
        advisory.evidence = {**(advisory.evidence or {}), "learned_from_voice": profile_fields}

    resp_text = advisory.recommendation or advisory.tamil_response or advisory.english_response or ""
    _persist_conversation_turn(
        user_id, conversation_id, body.query_text, resp_text,
        meta={"intent": parsed["intent"]},
    )

    return VoiceQueryOut(
        intent=parsed["intent"],
        entities=parsed["entities"],
        advisory=advisory,
        transcription_confidence=parsed.get("transcription_confidence", parsed.get("nlp_confidence", 0.85)),
        detected_language=lang,
        normalized_query=parsed.get("normalized_query"),
        nlp_confidence=parsed.get("nlp_confidence", parsed.get("confidence", 0.85)),
        profile_updated=profile_updated,
        profile_fields=profile_fields,
        conversation_id=conversation_id,
    )


def _resolve_parcel_id(farmer_id: str, parcel_id: Optional[str], db) -> str:
    if parcel_id:
        return parcel_id
    from app.services.profile_store import load_profile, list_all_lands
    prof = load_profile(farmer_id)
    pid = prof.get("active_parcel_id")
    if pid:
        return pid
    parcels = list_all_lands(farmer_id)
    if len(parcels) == 1:
        return parcels[0]["parcel_id"] if isinstance(parcels[0], dict) else parcels[0].parcel_id
    raise HTTPException(400, detail="Select a parcel in your profile")


@router.get("/notifications", response_model=NotificationsOut)
def get_notifications(
    farmer_id: Optional[str] = None,
    parcel_id: Optional[str] = None,
    session_id: Optional[str] = None,
    language: str = "Tamil",
    db=Depends(get_db),
):
    from app.services.notification_hub import generate_all_notifications, notifications_summary
    from app.services.guest_session import get_session, session_to_context
    from app.services.openmeteo_weather import enrich_context_with_openmeteo

    ctx = None
    if farmer_id and parcel_id:
        ctx = _ctx(db, parcel_id, farmer_id)
    elif session_id:
        session = get_session(session_id)
        if session:
            ctx = enrich_context_with_openmeteo(session_to_context(session))
    if not ctx:
        from app.services.weather_alerts import build_guest_weather_context
        ctx = enrich_context_with_openmeteo(build_guest_weather_context())

    raw = generate_all_notifications(ctx, language)
    summary = notifications_summary(raw)
    high = summary["high_count"]
    return NotificationsOut(
        parcel_id=parcel_id,
        session_id=session_id,
        notification_count=len(raw),
        high_count=high,
        medium_count=summary.get("medium_count", 0),
        notifications=[WeatherAlertOut(**a) for a in raw],
        summary=summary,
        weather_source=ctx.get("weather_source", "open-meteo"),
    )


@router.get("/parcels/{parcel_id}/alerts", response_model=AlertsOut)
def get_parcel_alerts(
    parcel_id: str,
    farmer_id: Optional[str] = None,
    db=Depends(get_db),
):
    from app.services.weather_alerts import generate_weather_alerts
    ctx = _ctx(db, parcel_id, farmer_id)
    if not ctx:
        raise HTTPException(404, "Parcel not found")
    raw = generate_weather_alerts(ctx)
    high = sum(1 for a in raw if a["severity"] == "high")
    return AlertsOut(
        parcel_id=parcel_id,
        alert_count=len(raw),
        high_count=high,
        alerts=[WeatherAlertOut(**a) for a in raw],
        weather_source=ctx.get("weather_source", "open-meteo"),
    )


@router.get("/voice/call/alerts", response_model=AlertsOut)
def get_guest_call_alerts():
    from app.services.weather_alerts import build_guest_weather_context, generate_weather_alerts
    ctx = build_guest_weather_context()
    raw = generate_weather_alerts(ctx)
    high = sum(1 for a in raw if a["severity"] == "high")
    return AlertsOut(
        alert_count=len(raw),
        high_count=high,
        alerts=[WeatherAlertOut(**a) for a in raw],
        weather_source=ctx.get("weather_source", "open-meteo"),
    )


@router.post("/voice/call/briefing", response_model=CallBriefingOut)
def call_briefing(body: CallBriefingIn, db=Depends(get_db)):
    from app.services.call_assistant import build_call_briefing
    from app.services.profile_store import get_farmer_display_name
    from app.services.weather_alerts import build_guest_weather_context

    name = body.farmer_name or "Farmer"
    if body.guest or not body.farmer_id:
        ctx = build_guest_weather_context()
        result = build_call_briefing(ctx, name, body.language, is_guest=True)
    else:
        _get_farmer_or_404(body.farmer_id, db)
        parcel_id = _resolve_parcel_id(body.farmer_id, body.parcel_id, db)
        ctx = _ctx(db, parcel_id, body.farmer_id)
        if not ctx:
            raise HTTPException(404, "Parcel not found")
        ctx["farmer_id"] = body.farmer_id
        ctx["parcel_id"] = parcel_id
        name = get_farmer_display_name(body.farmer_id).split("—")[0].strip() or name
        result = build_call_briefing(ctx, name, body.language, is_guest=False)

    return CallBriefingOut(
        text=result["text"],
        language=result["language"],
        alert_count=result.get("alert_count", 0),
        high_alert_count=result.get("high_alert_count", 0),
        mode=result.get("mode", "guest"),
        alerts=result.get("alerts", []),
    )


@router.post("/voice/call/query", response_model=CallQueryOut)
def call_query(body: CallQueryIn, db=Depends(get_db)):
    from app.services.call_assistant import process_call_query
    from app.services.weather_alerts import build_guest_weather_context

    if body.guest or not body.farmer_id:
        ctx = build_guest_weather_context()
        out = process_call_query(body.query_text, ctx, body.language, is_guest=True, use_web_search=body.use_web_search)
    else:
        _get_farmer_or_404(body.farmer_id, db)
        parcel_id = _resolve_parcel_id(body.farmer_id, body.parcel_id, db)
        ctx = _ctx(db, parcel_id, body.farmer_id)
        if not ctx:
            raise HTTPException(404, "Parcel not found")
        ctx["farmer_id"] = body.farmer_id
        ctx["parcel_id"] = parcel_id
        out = process_call_query(
            body.query_text, ctx, body.language, is_guest=False, use_web_search=body.use_web_search,
        )

    return CallQueryOut(
        text=out["text"],
        language=out["language"],
        intent=out["intent"],
        advisory=out["advisory"],
        entities=out.get("entities", {}),
        confidence=out.get("confidence", 0.0),
    )


@router.get("/parcels/{parcel_id}/farm-map", response_model=FarmMapOut)
def get_farm_map(parcel_id: str, farmer_id: str, db=Depends(get_db)):
    from app.services.farm_map import get_farm_map_data
    _get_farmer_or_404(farmer_id, db)
    data = get_farm_map_data(farmer_id, parcel_id)
    if not data:
        raise HTTPException(404, "Parcel not found")
    return FarmMapOut(**data)


@router.put("/farmers/{farmer_id}/parcels/{parcel_id}/segments")
def update_segments(farmer_id: str, parcel_id: str, body: SegmentsUpdateIn, db=Depends(get_db)):
    from app.services.farm_map import update_farm_segments
    from app.services import context_cache
    _get_farmer_or_404(farmer_id, db)
    segments = [s.model_dump() for s in body.segments]
    saved = update_farm_segments(farmer_id, parcel_id, segments)
    context_cache.invalidate(f"{farmer_id}:{parcel_id}")
    context_cache.invalidate(parcel_id)
    return {"status": "saved", "segments": saved.get("parcels", {}).get(parcel_id, {}).get("segments", segments)}


@router.post("/voice/speak")
def voice_speak(body: SpeakIn):
    if not body.text.strip():
        raise HTTPException(400, "Text is required")
    try:
        from app.services.tamil_tts import synthesize_speech
        audio = synthesize_speech(body.text, body.language)
        if not audio:
            raise HTTPException(500, "TTS produced empty audio")
        return Response(content=audio, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(500, f"TTS failed: {e}") from e


def _soil_dict_from_body(body: SoilAnalyzeIn | CropSuitabilityIn) -> dict:
    return {
        k: v for k, v in {
            "pH": body.pH,
            "N_kg_ha": body.nitrogen,
            "P_kg_ha": body.phosphorus,
            "K_kg_ha": body.potassium,
            "OC_percent": body.organic_carbon,
            "EC_dS_m": body.electrical_conductivity,
            "sand_percent": getattr(body, "sand_percent", None),
            "silt_percent": getattr(body, "silt_percent", None),
            "clay_percent": getattr(body, "clay_percent", None),
            "soil_type": body.soil_type,
            "drainage": body.drainage,
        }.items() if v is not None
    }


def _merge_parcel_soil(farmer_id: str, parcel_id: str, db, soil: dict) -> dict:
    from app.services.profile_store import load_profile
    ctx = _ctx(db, parcel_id, farmer_id)
    merged = dict(soil)
    if ctx:
        s = ctx.get("soil")
        if s:
            sd = s.__dict__ if hasattr(s, "__dict__") else dict(s)
            merged.setdefault("pH", sd.get("ph") or sd.get("pH"))
            merged.setdefault("N_kg_ha", sd.get("nitrogen"))
            merged.setdefault("P_kg_ha", sd.get("phosphorus"))
            merged.setdefault("K_kg_ha", sd.get("potassium"))
            merged.setdefault("OC_percent", sd.get("organic_carbon"))
        p = ctx.get("parcel")
        if p:
            pd_ = p.__dict__ if hasattr(p, "__dict__") else dict(p)
            merged.setdefault("district", pd_.get("district"))
            merged.setdefault("soil_type", pd_.get("soil_type"))
    prof = load_profile(farmer_id)
    custom = prof.get("parcels", {}).get(parcel_id, {})
    if custom.get("soil"):
        cs = custom["soil"]
        for k, v in cs.items():
            if v is not None:
                merged[k if k != "ph" else "pH"] = v
    return merged


@router.post("/soil/upload-report")
async def upload_soil_report(
    file: UploadFile = File(...),
    farmer_id: Optional[str] = None,
    parcel_id: Optional[str] = None,
    db=Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    from app.services.soil_report_ocr import extract_from_upload
    from app.services.soil_crop_advisor import recommend_crops
    from app.services.profile_store import update_parcel_custom
    from app.services import context_cache

    user = get_optional_user(authorization)
    if user and farmer_id:
        assert_farmer_owner(user, farmer_id)

    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 15 MB)")

    ocr = extract_from_upload(file.filename or "report.pdf", data)
    core_found = sum(
        1 for k in ("pH", "nitrogen", "phosphorus", "potassium", "N_kg_ha", "P_kg_ha", "K_kg_ha")
        if ocr.get(k) is not None
    )
    if not ocr.get("fields_found") or core_found < 1:
        raise HTTPException(
            422,
            detail="Could not read soil values from PDF. Try a clearer scan or enter values manually.",
        )

    district = ocr.get("district")
    if farmer_id and parcel_id:
        ctx = _ctx(db, parcel_id, farmer_id)
        if ctx and ctx.get("parcel"):
            p = ctx["parcel"]
            district = district or (p.__dict__.get("district") if hasattr(p, "__dict__") else p.get("district"))

    rec = recommend_crops(ocr, district=district)

    # Save extracted soil to farmer profile
    if farmer_id and parcel_id:
        patch = {
            "soil": {
                "ph": ocr.get("pH"),
                "nitrogen": ocr.get("N_kg_ha") or ocr.get("nitrogen"),
                "phosphorus": ocr.get("P_kg_ha") or ocr.get("phosphorus"),
                "potassium": ocr.get("K_kg_ha") or ocr.get("potassium"),
                "organic_carbon": ocr.get("OC_percent") or ocr.get("organic_carbon"),
                "electrical_conductivity": ocr.get("EC_dS_m") or ocr.get("electrical_conductivity"),
                "soil_type": ocr.get("soil_type"),
            },
            "soil_report_uploaded_at": __import__("datetime").date.today().isoformat(),
        }
        update_parcel_custom(farmer_id, parcel_id, patch)
        context_cache.invalidate(f"{farmer_id}:{parcel_id}")

    from app.services.soil_report_formatter import format_soil_chat_reply

    chat_en, chat_ta = format_soil_chat_reply(
        ocr,
        rec.get("recommendations", []),
        district=district,
    )

    return {
        "ocr": ocr,
        "recommendations": rec.get("recommendations", []),
        "soil_summary": rec.get("soil_summary", {}),
        "confidence": rec.get("confidence", 0),
        "model": rec.get("model", ""),
        "district": district,
        "chat_message_en": chat_en,
        "chat_message_ta": chat_ta,
    }


@router.post("/soil/analyze", response_model=SoilRecommendOut)
def analyze_soil(body: SoilAnalyzeIn, db=Depends(get_db), authorization: Optional[str] = Header(None)):
    from app.services.soil_crop_advisor import recommend_crops

    user = get_optional_user(authorization)
    if user and body.farmer_id:
        assert_farmer_owner(user, body.farmer_id)

    soil = _soil_dict_from_body(body)
    district = body.district
    if body.farmer_id and body.parcel_id:
        soil = _merge_parcel_soil(body.farmer_id, body.parcel_id, db, soil)
        if not district and soil.get("district"):
            district = soil["district"]

    rec = recommend_crops(soil, district=district, region=body.region)
    return SoilRecommendOut(**rec)


@router.post("/soil/check-crop", response_model=CropSuitabilityOut)
def check_crop_suitability(body: CropSuitabilityIn, db=Depends(get_db), authorization: Optional[str] = Header(None)):
    from app.services.soil_crop_advisor import check_crop_suitability as check_crop

    user = get_optional_user(authorization)
    if user and body.farmer_id:
        assert_farmer_owner(user, body.farmer_id)

    soil = _soil_dict_from_body(body)
    district = body.district
    if body.farmer_id and body.parcel_id:
        soil = _merge_parcel_soil(body.farmer_id, body.parcel_id, db, soil)
        if not district and soil.get("district"):
            district = soil["district"]

    result = check_crop(soil, body.crop_or_variety, district=district, region=body.region)
    return CropSuitabilityOut(**result)


@router.get("/soil/model-metrics")
def soil_model_metrics():
    from pathlib import Path
    import json
    p = Path(__file__).resolve().parents[3] / "ml" / "models" / "soil_crop_metrics.json"
    if not p.exists():
        return {"status": "not_trained", "message": "Run: python ml/train_soil_crop_model.py"}
    return json.loads(p.read_text(encoding="utf-8"))


"""Voice call assistant — briefing, alerts, conversational farm updates."""
from __future__ import annotations

from typing import Any, Optional

from app.models.schemas import AdvisoryOut
from app.services.advisory_engine import assess_risks, generate_advisory, predict_irrigation
from app.services.guest_advisory import generate_guest_advisory
from app.services.weather_alerts import generate_weather_alerts


def _pick_lang(language: str, en: str, ta: str) -> str:
    return ta if language == "Tamil" else en


def build_call_briefing(
    context: Optional[dict[str, Any]],
    farmer_name: str,
    language: str = "Tamil",
    is_guest: bool = False,
) -> dict[str, Any]:
    """Opening spoken briefing when farmer starts a call."""
    alerts = generate_weather_alerts(context) if context else []

    if is_guest or not context:
        greeting_ta = f"வணக்கம் {farmer_name}! நான் KrishiVoice call assistant. இது general Tamil Nadu weather update."
        greeting_en = f"Hello {farmer_name}! I am your KrishiVoice call assistant. Here is general Tamil Nadu weather guidance."
        if alerts:
            top = alerts[0]
            body_ta = top["spoken_ta"]
            body_en = top["spoken_en"]
        else:
            body_ta = "login பண்ணி உங்க farm location set pannunga — exact weather alert kidaikum."
            body_en = "Sign in and set your farm location for exact weather alerts."
        closing_ta = "என்ன doubt-ஆ irundhaalum kelunga — நான் help pannuren."
        closing_en = "Ask me anything about farming — I am here to help."
        text = _pick_lang(language, f"{greeting_en} {body_en} {closing_en}", f"{greeting_ta} {body_ta} {closing_ta}")
        return {
            "text": text,
            "language": language,
            "alerts": alerts,
            "alert_count": len(alerts),
            "mode": "guest" if is_guest else "personalized",
            "sections": ["greeting", "weather", "invite_questions"],
        }

    obs = context.get("observation")
    crop = context.get("crop")
    crop_name = crop.crop if crop else (obs.crop if obs else "Rice")
    stage = obs.growth_stage if obs else "Unknown"
    weather = context.get("weather_today")
    forecast = float(context.get("forecast_rainfall_mm") or 0)
    temp = float(weather.temperature) if weather else None
    moisture = context.get("soil_moisture")
    parcel = context.get("parcel")
    village = getattr(parcel, "village", None) or (parcel.get("village") if isinstance(parcel, dict) else "your field")

    greeting_ta = f"வணக்கம் {farmer_name}! KrishiVoice call assistant. {village} vayil update."
    greeting_en = f"Hello {farmer_name}! KrishiVoice call assistant. Update for {village}."

    weather_ta = ""
    weather_en = ""
    if temp is not None:
        weather_ta = f"இன்று temperature {temp:.0f} degree. நாளைக்கு {forecast:.0f} mm மழை forecast."
        weather_en = f"Today {temp:.0f} degrees. Tomorrow forecast {forecast:.0f} mm rain."

    crop_ta = f"உங்க {crop_name} crop {stage} stage-la irukku."
    crop_en = f"Your {crop_name} is in {stage} stage."

    if moisture is not None:
        crop_ta += f" Soil moisture {moisture:.0f} percent."
        crop_en += f" Soil moisture {moisture:.0f} percent."

    irrigation = predict_irrigation(context)
    irr_ta = "இன்று தண்ணீர் பாய்ச்ச வேண்டாம்." if not irrigation.irrigation_required else f"இன்று தண்ணீர் பாய்ச்ச recommended — {irrigation.urgency} urgency."
    irr_en = "No irrigation needed today." if not irrigation.irrigation_required else f"Irrigation recommended today — {irrigation.urgency} urgency."

    alert_ta = alert_en = ""
    high_alerts = [a for a in alerts if a["severity"] == "high"]
    if high_alerts:
        alert_ta = f"முக்கிய alert: {high_alerts[0]['spoken_ta']}"
        alert_en = f"Important alert: {high_alerts[0]['spoken_en']}"

    closing_ta = "வேற என்ன kelunga — weather, crop, disease, market — ellathukkum answer solluren."
    closing_en = "Ask me anything — weather, crop, disease, market — I will guide you."

    parts_ta = [greeting_ta, weather_ta, crop_ta, irr_ta, alert_ta, closing_ta]
    parts_en = [greeting_en, weather_en, crop_en, irr_en, alert_en, closing_en]
    text = _pick_lang(language, " ".join(p for p in parts_en if p), " ".join(p for p in parts_ta if p))

    return {
        "text": text,
        "language": language,
        "alerts": alerts,
        "alert_count": len(alerts),
        "high_alert_count": len(high_alerts),
        "mode": "personalized",
        "crop": crop_name,
        "growth_stage": stage,
        "temperature_c": temp,
        "forecast_rain_mm": forecast,
        "soil_moisture_pct": moisture,
    }


def wrap_call_response(advisory: AdvisoryOut, query: str, language: str) -> str:
    """Conversational wrapper for call-mode replies."""
    from app.services.general_faq import is_low_quality_answer

    base = advisory.recommendation
    if language == "Tamil" and advisory.tamil_response:
        base = advisory.tamil_response
    elif advisory.english_response:
        base = advisory.english_response

    if not base or is_low_quality_answer(base, query):
        if language == "Tamil":
            base = "Kelvigal clear-aa kelunga — crop, thanneer, pasu, loan — enna help venum?"
        else:
            base = "Please ask a clear question — crop, water, livestock, loan — how can I help?"

    # Clarification / short answers — no robotic prefix/suffix (sounds AI in voice call)
    is_clarify = advisory.evidence and advisory.evidence.get("clarification")
    if is_clarify or len(base) > 120:
        return base.strip()

    # Skip "Sure." wrappers — TTS sounds robotic; keep answer direct for voice
    return base.strip()


def process_call_query(
    query_text: str,
    context: Optional[dict[str, Any]],
    language: str,
    is_guest: bool,
    session_id: Optional[str] = None,
    use_web_search: bool = False,
) -> dict[str, Any]:
    """Process a voice query in call mode with conversational output."""
    if is_guest or not context:
        from app.services.voice_onboarding import process_guest_message, start_session
        sid = session_id
        if not sid:
            started = start_session(language)
            sid = started["session_id"]
        result = process_guest_message(sid, query_text)
        spoken = result["text"]
        adv = result.get("advisory")
        if not adv:
            adv = AdvisoryOut(
                recommendation=spoken,
                reason="Guest voice assistant with profile learning.",
                evidence=result.get("evidence", {}),
                confidence=0.85,
                action_time="Today",
                risk_level="low",
                tamil_response=spoken,
                english_response=spoken,
            )
        return {
            "text": spoken,
            "language": result.get("language", language),
            "intent": result.get("intent", "general_agriculture"),
            "advisory": adv,
            "entities": {"mode": "guest", "session_id": sid, "profile": result.get("profile", {})},
            "confidence": 0.85,
            "session_id": sid,
            "profile_completeness": result.get("profile_completeness", 0),
        }

    from app.services.agent_orchestrator import run_voice_agent

    farmer_id = (context or {}).get("farmer_id", "F0000")
    parcel_id = (context or {}).get("parcel_id")

    agent = run_voice_agent(
        query_text,
        context,
        farmer_id=farmer_id,
        parcel_id=parcel_id,
        language_preference=language,
        is_guest=False,
        use_web_search=use_web_search,
    )
    lang = agent["detected_language"]
    intent = agent["intent"]
    advisory = agent["advisory"]

    spoken = wrap_call_response(advisory, query_text, lang)
    if lang == "Tamil":
        advisory.recommendation = spoken
    else:
        advisory.recommendation = spoken

    return {
        "text": spoken,
        "language": lang,
        "intent": intent,
        "advisory": advisory,
        "entities": agent["entities"],
        "confidence": agent["nlp_confidence"],
    }

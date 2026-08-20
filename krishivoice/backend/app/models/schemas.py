from datetime import date
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, Field


class FarmerOut(BaseModel):
    farmer_id: str
    district: str
    taluk: str
    village: str
    farm_size: float
    experience: int
    primary_crop: str
    preferred_language: str

    class Config:
        from_attributes = True


class ParcelOut(BaseModel):
    parcel_id: str
    farmer_id: str
    district: str
    taluk: str
    village: str
    survey_no: Optional[str] = None
    area: float
    latitude: float
    longitude: float
    land_category: str
    irrigation_source: str
    soil_type: str
    is_custom_land: bool = False
    land_name: Optional[str] = None

    class Config:
        from_attributes = True


class SoilOut(BaseModel):
    sample_date: date
    ph: float
    nitrogen: float
    phosphorus: float
    potassium: float
    organic_carbon: Optional[float]
    soil_type: Optional[str]

    class Config:
        from_attributes = True


class WeatherOut(BaseModel):
    date: date
    rainfall: float
    temperature: float
    humidity: Optional[float]
    wind_speed: Optional[float]
    source: Optional[str] = "synthetic"
    soil_moisture_pct: Optional[float] = None


class OpenMeteoHourlyOut(BaseModel):
    source: str = "open-meteo"
    latitude: float
    longitude: float
    elevation_m: float
    rows: list[dict[str, Any]]
    daily: list[dict[str, Any]]


class IrrigationOut(BaseModel):
    event_date: date
    method: Optional[str]
    soil_moisture_before: Optional[float]
    soil_moisture_after: Optional[float]
    water_used: Optional[float]

    class Config:
        from_attributes = True


class CropObservationOut(BaseModel):
    obs_date: date
    crop: str
    growth_stage: Optional[str]
    plant_height: Optional[float]
    leaf_condition: Optional[str]
    pest: Optional[str]
    disease: Optional[str]
    ndvi: Optional[float]

    class Config:
        from_attributes = True


class RiskOut(BaseModel):
    water_stress: str
    disease_risk: str
    pest_risk: str
    weather_risk: str
    overall_risk: str
    confidence: float
    evidence: dict[str, Any]


class AdvisoryOut(BaseModel):
    recommendation: str
    reason: str
    evidence: dict[str, Any]
    confidence: float
    action_time: str
    risk_level: str
    tamil_response: Optional[str] = None
    english_response: Optional[str] = None


class VoiceQueryIn(BaseModel):
    farmer_id: Optional[str] = None
    parcel_id: Optional[str] = None
    query_text: str
    language: str = "Auto"
    guest: bool = False
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    use_web_search: bool = False


class VoiceQueryOut(BaseModel):
    intent: str
    entities: dict[str, Any]
    advisory: AdvisoryOut
    transcription_confidence: float = 1.0
    detected_language: str = "Tamil"
    normalized_query: Optional[str] = None
    nlp_confidence: float = 0.0
    profile_updated: bool = False
    profile_fields: dict[str, Any] = Field(default_factory=dict)
    conversation_id: Optional[str] = None


class YieldPredictionIn(BaseModel):
    parcel_id: str


class YieldPredictionOut(BaseModel):
    predicted_yield_tph: float
    confidence: float
    model: str
    features_used: dict[str, Any]


class IrrigationPredictionOut(BaseModel):
    irrigation_required: bool
    urgency: str
    recommended_timing: str
    reason: str
    confidence: float
    evidence: dict[str, Any]


class SpeakIn(BaseModel):
    text: str
    language: str = "Tamil"  # Tamil | English


class LoginIn(BaseModel):
    farmer_id: Optional[str] = None
    pin: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class RegisterIn(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None
    farmer_id: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None
    primary_crop: Optional[str] = None


class LoginOut(BaseModel):
    token: str
    farmer_id: str
    display_name: str
    message: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    auth_mode: str = "farmer"
    parcel_id: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    message_count: int = 0


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    meta: dict[str, Any] = Field(default_factory=dict)
    at: Optional[str] = None


class ConversationDetailOut(BaseModel):
    id: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    messages: list[ChatMessageOut] = Field(default_factory=list)


class ConversationCreateIn(BaseModel):
    title: str = "New chat"


class GuestVoiceQueryIn(BaseModel):
    query_text: str
    language: str = "Auto"
    session_id: Optional[str] = None
    use_web_search: bool = False


class GuestSessionStartIn(BaseModel):
    language: str = "Tamil"


class GuestSessionOut(BaseModel):
    session_id: str
    text: str
    language: str
    step: str
    profile_completeness: float = 0.0
    profile: dict[str, Any] = Field(default_factory=dict)
    intent: Optional[str] = None
    next_question: Optional[str] = None
    turn_count: int = 0
    advisory: Optional[AdvisoryOut] = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class DailyBriefingOut(BaseModel):
    text: str
    language: str
    date: str
    alerts: list[dict[str, Any]] = []
    high_alert_count: int = 0
    irrigation_required: bool = False
    evidence: dict[str, Any] = Field(default_factory=dict)
    weather_source: str = "open-meteo"


class FarmReportOut(BaseModel):
    text: str
    text_en: str = ""
    text_ta: str = ""
    language: str
    period: str
    date: str
    weather_source: str = "open-meteo-archive"
    location: str = ""
    alerts: list[dict[str, Any]] = []
    high_alert_count: int = 0
    irrigation_required: bool = False
    weather_summary: dict[str, Any] = Field(default_factory=dict)
    farm_summary: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)


class ParcelCustomIn(BaseModel):
    land_name: Optional[str] = None
    district: Optional[str] = None
    taluk: Optional[str] = None
    village: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area: Optional[float] = None
    crop: Optional[str] = None
    growth_stage: Optional[str] = None
    soil_moisture: Optional[float] = None
    soil: Optional[dict[str, Any]] = None
    segments: Optional[list[dict[str, Any]]] = None
    boundary: Optional[list[dict[str, float]]] = None
    land_type: Optional[str] = None
    irrigation_source: Optional[str] = None
    land_slope: Optional[str] = None
    drainage: Optional[str] = None
    water_table: Optional[str] = None
    soil_texture: Optional[str] = None
    field_condition: Optional[str] = None


class FarmerProfileOut(BaseModel):
    farmer_id: str
    display_name: str
    active_parcel_id: Optional[str]
    parcels_custom: dict[str, Any]
    farmer: Optional[FarmerOut] = None
    parcels: list[ParcelOut] = []


class WeatherAlertOut(BaseModel):
    id: str
    severity: str
    category: str
    title_en: str
    title_ta: str
    message_en: str
    message_ta: str
    spoken_en: str
    spoken_ta: str
    action_en: str = ""
    action_ta: str = ""
    evidence: dict[str, Any] = {}
    generated_at: str


class NotificationsOut(BaseModel):
    parcel_id: Optional[str] = None
    session_id: Optional[str] = None
    notification_count: int
    high_count: int
    medium_count: int = 0
    notifications: list[WeatherAlertOut]
    summary: dict[str, Any] = Field(default_factory=dict)
    weather_source: str = "open-meteo"


class AlertsOut(BaseModel):
    parcel_id: Optional[str] = None
    alert_count: int
    high_count: int
    alerts: list[WeatherAlertOut]
    weather_source: str = "open-meteo"


class CallBriefingIn(BaseModel):
    farmer_id: Optional[str] = None
    parcel_id: Optional[str] = None
    language: str = "Tamil"
    guest: bool = False
    farmer_name: Optional[str] = None


class CallBriefingOut(BaseModel):
    text: str
    language: str
    alert_count: int = 0
    high_alert_count: int = 0
    mode: str = "guest"
    alerts: list[dict[str, Any]] = []


class CallQueryIn(BaseModel):
    query_text: str
    farmer_id: Optional[str] = None
    parcel_id: Optional[str] = None
    language: str = "Auto"
    guest: bool = False
    use_web_search: bool = False


class CallQueryOut(BaseModel):
    text: str
    language: str
    intent: str
    advisory: AdvisoryOut
    entities: dict[str, Any] = {}
    confidence: float = 0.0


class FarmSegmentIn(BaseModel):
    segment_id: str
    name: str
    crop: str = "Rice"
    growth_stage: Optional[str] = None
    area_ha: Optional[float] = None
    soil_type: Optional[str] = None
    soil_moisture: Optional[float] = None
    soil: Optional[dict[str, Any]] = None
    latitude: float
    longitude: float
    color: Optional[str] = "#40916c"


class FarmMapOut(BaseModel):
    farmer_id: str
    parcel_id: str
    land_name: Optional[str] = None
    is_custom_land: bool = False
    district: str
    village: str
    taluk: Optional[str] = None
    centroid: dict[str, float]
    area_ha: float
    boundary: Optional[Any] = None
    segments: list[dict[str, Any]] = []
    crop: Optional[str] = None
    growth_stage: Optional[str] = None
    soil: Optional[dict[str, Any]] = None
    land_type: Optional[str] = None
    irrigation_source: Optional[str] = None
    land_slope: Optional[str] = None
    drainage: Optional[str] = None
    water_table: Optional[str] = None
    soil_texture: Optional[str] = None
    field_condition: Optional[str] = None


class SegmentsUpdateIn(BaseModel):
    segments: list[FarmSegmentIn]


class FarmLandCreateIn(BaseModel):
    land_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class GeocodeOut(BaseModel):
    latitude: float
    longitude: float
    display_name: str = ""
    land_name: str = ""
    village: str = ""
    taluk: str = ""
    district: str = ""
    state: str = "Tamil Nadu"


class SoilExtractOut(BaseModel):
    pH: Optional[float] = None
    nitrogen: Optional[float] = Field(None, alias="N_kg_ha")
    phosphorus: Optional[float] = Field(None, alias="P_kg_ha")
    potassium: Optional[float] = Field(None, alias="K_kg_ha")
    organic_carbon: Optional[float] = Field(None, alias="OC_percent")
    electrical_conductivity: Optional[float] = Field(None, alias="EC_dS_m")
    sand_percent: Optional[float] = None
    silt_percent: Optional[float] = None
    clay_percent: Optional[float] = None
    soil_type: Optional[str] = None
    district: Optional[str] = None
    drainage: Optional[str] = None
    confidence: float = 0.0
    fields_found: list[str] = Field(default_factory=list)
    extraction_method: Optional[str] = None
    source_file: Optional[str] = None

    class Config:
        populate_by_name = True


class SoilAnalyzeIn(BaseModel):
    farmer_id: Optional[str] = None
    parcel_id: Optional[str] = None
    district: Optional[str] = None
    region: Optional[str] = None
    pH: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    organic_carbon: Optional[float] = None
    electrical_conductivity: Optional[float] = None
    sand_percent: Optional[float] = None
    silt_percent: Optional[float] = None
    clay_percent: Optional[float] = None
    soil_type: Optional[str] = None
    drainage: Optional[str] = None


class CropRecommendationItem(BaseModel):
    crop: str
    score: float
    ml_score: float = 0.0
    locality_score: float = 0.0
    rule_score: float = 0.0
    reasons: list[str] = Field(default_factory=list)


class SoilRecommendOut(BaseModel):
    recommendations: list[CropRecommendationItem]
    district: Optional[str] = None
    soil_summary: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    model: str = ""
    message: Optional[str] = None
    ocr: Optional[dict[str, Any]] = None


class CropSuitabilityIn(BaseModel):
    crop_or_variety: str
    farmer_id: Optional[str] = None
    parcel_id: Optional[str] = None
    district: Optional[str] = None
    region: Optional[str] = None
    pH: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    organic_carbon: Optional[float] = None
    electrical_conductivity: Optional[float] = None
    soil_type: Optional[str] = None
    drainage: Optional[str] = None


class CropSuitabilityOut(BaseModel):
    query: str
    matched_variety: str
    parent_crop: str
    suitable: bool
    score: float
    rule_score: float
    reasons: list[str] = Field(default_factory=list)
    alternatives: list[CropRecommendationItem] = Field(default_factory=list)
    verdict_en: str = ""
    verdict_ta: str = ""

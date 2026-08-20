"""Generalized agricultural replies for guest users (no login / no parcel)."""
from __future__ import annotations

from app.models.schemas import AdvisoryOut
from app.services import tamil_responses as ta

GENERAL_EN = {
    "irrigation_query": (
        "General advice: Check soil moisture at 15–20 cm depth before irrigating. "
        "For rice in tillering stage, maintain adequate moisture but avoid flooding if rain is forecast.",
        "Based on standard Tamil Nadu rice cultivation practices (not your specific field).",
    ),
    "weather_query": (
        "I cannot access your exact location without a farmer profile. "
        "Log in and select your farm to get live weather for your parcel.",
        "Enable personalized weather via farmer login.",
    ),
    "crop_status": (
        "Log in with your farmer profile and select your parcel for crop stage based on your field records.",
        "Personalized crop status requires your farm profile.",
    ),
    "disease_risk": (
        "General: Scout fields after rainfall. Remove infected plants early. "
        "For rice, watch for blast and sheath blight in humid conditions.",
        "General TN rice disease guidance.",
    ),
    "pest_risk": (
        "General: Monitor for stem borer during tillering. Use light traps and field scouting weekly.",
        "General pest management guidance.",
    ),
    "yield_prediction": (
        "Yield depends on soil, weather, and management. Log in with your soil test data for a field-specific estimate.",
        "Personalized yield needs your parcel data.",
    ),
    "general_agriculture": (
        "KrishiVoice can give general Tamil Nadu farming guidance here. "
        "For advice based on YOUR soil, crop, and weather — log in and set up your farm profile.",
        "Guest mode — generalized only.",
    ),
}

GENERAL_TA = {
    "irrigation_query": ta.irrigation_uncertain(),
    "weather_query": "உங்க farm location சேர்க்க login பண்ணுங்க — அப்புறம் live weather க decídetta solluren.",
    "crop_status": "உங்க parcel select பண்ண login பண்ணுங்க — crop stage exact-ஆ சொல்ல mudiyum.",
    "disease_risk": "பொதுவா: மழைக்கு அப்புறம் வயல் பாருங்க. நோய் symptoms irundha udane remove பண்ணுங்க.",
    "pest_risk": "பொதுவா: tillering stage-ல stem borer-ku parunga. வாரத்துல ஒரு தடவை scout பண்ணுங்க.",
    "yield_prediction": "soil test data-ஓட login பண்ணுங்க — உங்க வயலுக்கு exact yield estimate கிடைக்கும்.",
    "general_agriculture": (
        "இது general advice மட்டும். உங்க soil, crop, weather based reply-ku "
        "login பண்ணி farm profile setup பண்ணுங்க."
    ),
}


def generate_guest_advisory(intent: str, language: str = "Tamil") -> AdvisoryOut:
    key = intent if intent in GENERAL_EN else "general_agriculture"
    en_rec, reason = GENERAL_EN[key]
    tamil = GENERAL_TA.get(key, GENERAL_TA["general_agriculture"])

    return AdvisoryOut(
        recommendation=tamil if language == "Tamil" else en_rec,
        reason=reason,
        evidence={"mode": "guest", "personalized": False, "hint": "Login for field-specific advice"},
        confidence=0.45,
        action_time="When convenient",
        risk_level="low",
        tamil_response=tamil if isinstance(tamil, str) else str(tamil),
        english_response=en_rec,
    )

"""
Colloquial Tamil (பேச்சு தமிழ்) response builders for farmers.
Matches natural field-side slang used in Thanjavur / Cuddalore.
"""
from __future__ import annotations

CROP_TA = {"Rice": "நெல்", "Groundnut": "நிலக்கடலை", "Sugarcane": "கரும்பு"}
STAGE_TA = {
    "Tillering": "கதிர் வரும் stage",
    "Seedling": "நாற்று stage",
    "Panicle Initiation": "பூக்கும் stage",
    "Flowering": "பூத்து இருக்கும் stage",
    "Maturity": "முதிர்ச்சி stage",
    "Germination": "முளைக்கும் stage",
    "Vegetative": "வளரும் stage",
    "Grand Growth": "நல்லா வளர்ந்த stage",
}


def crop_ta(name: str) -> str:
    return CROP_TA.get(name, name)


def stage_ta(name: str) -> str:
    return STAGE_TA.get(name, name)


def irrigation_not_required(moisture: float | None, rain_7d: float, forecast: float) -> str:
    m = f"{moisture:.0f}" if moisture is not None else "போதும்"
    parts = [
        f"அண்ணே, உங்க வயில்ல ஈரம் {m}% இருக்கு — போதுமானதா தான் இருக்கு.",
        "இன்னைக்கு தண்ணீர் பாய்ச்ச வேண்டாம்.",
    ]
    if rain_7d >= 10:
        parts.append(f"கடைசி ஒரு வாரத்துல {rain_7d:.0f} mm மழையும் padichirukku.")
    if forecast >= 5:
        parts.append(f"நாளைக்கும் மழை வரலாம் ({forecast:.0f} mm).")
    return " ".join(parts)


def irrigation_required(urgency: str, moisture: float | None) -> str:
    m = f"{moisture:.0f}%" if moisture is not None else "குறைவா"
    if urgency == "high":
        return f"அண்ணே, வயில்ல ஈரம் {m} தான் இருக்கு — குறைஞ்சிடுச்சு. இன்னைக்கே மாலை தண்ணீர் பாய்ச்சிடுங்க."
    return f"வயில்ல ஈரம் {m} — கொஞ்சம் குறைவு. இன்னைக்கு மாலை நேரத்துல தண்ணீர் பாய்ச்சலாம்."


def irrigation_uncertain() -> str:
    return (
        "அண்ணே, சரியா சொல்ல முடியல. வயில்ல நேர்ல போய் மண் ஈரம் பாத்துட்டு "
        "தண்ணீர் பாய்ச்சணுமா nu decide பண்ணுங்க."
    )


def crop_status(crop: str, stage: str) -> str:
    return f"உங்க {crop_ta(crop)} இப்போ {stage_ta(stage)}-ல இருக்கு அண்ணே."


def weather_forecast(forecast: float, recent: float, temp: float | None) -> str:
    lines = []
    if forecast >= 8:
        lines.append(f"நாளைக்கு மழை வர வாய்ப்பு நல்லா இருக்கு — சுமார் {forecast:.0f} mm வரலாம்.")
    elif forecast >= 2:
        lines.append(f"நாளைக்கு லைட்டா மழை வரலாம் — {forecast:.0f} mm.")
    else:
        lines.append("நாளைக்கு பெரிய மழை வர வாய்ப்பு kammi.")
    if recent >= 15:
        lines.append(f"இந்த வாரம் {recent:.0f} mm மழை padichirukku.")
    if temp is not None:
        lines.append(f"இப்போ temperature {temp:.0f}°C.")
    return " ".join(lines)


def disease_pest_risk(disease: str, pest: str) -> str:
    d_map = {"low": "குறைவு", "medium": "நடுத்தரம்", "high": "அதிகம்"}
    return (
        f"நோய் வர வாய்ப்பு {d_map.get(disease, disease)}. "
        f"பூச்சி problem {d_map.get(pest, pest)}. "
        "வயில்ல ஒரு round போய் பாத்துட்டு parunga."
    )


def general_ok() -> str:
    return "வயல் நல்லா தான் இருக்கு அண்ணே. கண்காணிப்பை continue பண்ணுங்க."


def yield_estimate(yield_tph: float) -> str:
    return f"இந்த season-ல சுமார் {yield_tph:.1f} டன்/hectare yield vara chance irukku."


def field_summary(
    location: str,
    crop: str,
    stage: str,
    moisture: float | None,
    recent_rain: float,
    forecast: float,
    land_type: str | None,
) -> str:
    m = f"{moisture:.0f}%" if moisture is not None else "set pannala"
    land = f" Land type: {land_type}." if land_type else ""
    return (
        f"{location}-la unga {crop_ta(crop)} {stage_ta(stage)}-la irukku.{land} "
        f"Moisture {m}. Ippa varaikkum {recent_rain:.0f} mm mazhai; naalaikku {forecast:.0f} mm forecast."
    )

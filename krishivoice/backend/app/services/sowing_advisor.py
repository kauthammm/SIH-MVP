"""Sowing window advisor — agronomic calendar + weather forecast."""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

# TN typical sowing windows (month ranges, inclusive)
SOWING_WINDOWS: dict[str, list[dict[str, Any]]] = {
    "Rice": [
        {"season": "Kharif", "start_month": 6, "end_month": 7, "label_en": "June–July (monsoon)", "label_ta": "ஜூன்–ஜூலை (மழைக்காலம்)"},
        {"season": "Rabi", "start_month": 12, "end_month": 1, "label_en": "Dec–Jan (Navarai)", "label_ta": "டிச–ஜன (நவரை)"},
    ],
    "Groundnut": [
        {"season": "Kharif", "start_month": 6, "end_month": 7, "label_en": "June–July", "label_ta": "ஜூன்–ஜூலை"},
        {"season": "Rabi", "start_month": 12, "end_month": 1, "label_en": "Dec–Jan", "label_ta": "டிச–ஜன"},
    ],
    "Maize": [
        {"season": "Kharif", "start_month": 6, "end_month": 7, "label_en": "June–July", "label_ta": "ஜூன்–ஜூலை"},
        {"season": "Rabi", "start_month": 1, "end_month": 2, "label_en": "Jan–Feb", "label_ta": "ஜன–பிப்"},
    ],
    "Cotton": [
        {"season": "Kharif", "start_month": 6, "end_month": 7, "label_en": "June–July", "label_ta": "ஜூன்–ஜூலை"},
    ],
    "Tomato": [
        {"season": "Kharif", "start_month": 6, "end_month": 8, "label_en": "June–Aug", "label_ta": "ஜூன்–ஆக"},
        {"season": "Rabi", "start_month": 11, "end_month": 1, "label_en": "Nov–Jan", "label_ta": "நவ–ஜன"},
    ],
    "Blackgram": [
        {"season": "Kharif", "start_month": 6, "end_month": 7, "label_en": "June–July", "label_ta": "ஜூன்–ஜூலை"},
    ],
    "Sugarcane": [
        {"season": "Year-round", "start_month": 1, "end_month": 12, "label_en": "Plant year-round; best Dec–Feb", "label_ta": "ஆண்டு முழுவதும்; டிச–பிப் நல்லது"},
    ],
}


def _in_window(month: int, start: int, end: int) -> bool:
    if start <= end:
        return start <= month <= end
    return month >= start or month <= end


def advise_sowing(
    crop: str,
    district: Optional[str] = None,
    forecast_rain_mm: float = 0,
    lang: str = "Tamil",
) -> dict[str, Any]:
    crop = (crop or "Rice").strip().title()
    windows = SOWING_WINDOWS.get(crop, SOWING_WINDOWS["Rice"])
    today = date.today()
    month = today.month

    active = [w for w in windows if _in_window(month, w["start_month"], w["end_month"])]
    status = "optimal" if active else "wait"
    next_win = windows[0]

    if forecast_rain_mm >= 40 and crop in ("Rice", "Maize", "Cotton"):
        rain_note_en = "Good rainfall expected — suitable for sowing if field is ready."
        rain_note_ta = "நல்ல மழை வரும் — வயல் ready-aa irundha sowing pannalam."
    elif forecast_rain_mm < 10 and crop in ("Rice",):
        rain_note_en = "Low rain forecast — delay paddy sowing or ensure irrigation."
        rain_note_ta = "மழை குறைவு — நெல் விதைப்பை தள்ளி வையுங்க, தண்ணீர் confirm pannunga."
        status = "delay"
    else:
        rain_note_en = f"Forecast rain ~{forecast_rain_mm:.0f} mm — plan field prep."
        rain_note_ta = f"மழை ~{forecast_rain_mm:.0f} mm expect — vayil ready pannunga."

    if active:
        w = active[0]
        en = f"{crop} sowing window is NOW ({w['label_en']}) in {district or 'your area'}. {rain_note_en}"
        ta = f"{crop} sowing time ippove ({w['label_ta']}) {district or 'unga area'}-la. {rain_note_ta}"
    else:
        en = f"Not ideal sowing month for {crop}. Next window: {next_win['label_en']}. {rain_note_en}"
        ta = f"{crop}-ku ippove sowing time illa. Next: {next_win['label_ta']}. {rain_note_ta}"

    return {
        "crop": crop,
        "status": status,
        "district": district,
        "windows": windows,
        "english": en,
        "tamil": ta,
        "confidence": 0.85,
    }

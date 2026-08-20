"""Natural-language soil report summary for chat."""
from __future__ import annotations

from typing import Any, Optional

from app.services.tamil_humanize import humanize_tamil_response


def format_soil_chat_reply(
    ocr: dict[str, Any],
    recommendations: list[dict[str, Any]],
    *,
    district: Optional[str] = None,
    lang: str = "Tamil",
) -> tuple[str, str]:
    ph = ocr.get("pH") or ocr.get("ph")
    n = ocr.get("N_kg_ha") or ocr.get("nitrogen")
    p = ocr.get("P_kg_ha") or ocr.get("phosphorus")
    k = ocr.get("K_kg_ha") or ocr.get("potassium")
    oc = ocr.get("OC_percent") or ocr.get("organic_carbon")
    ec = ocr.get("EC_dS_m") or ocr.get("electrical_conductivity")
    soil_type = ocr.get("soil_type") or "—"
    loc = district or ocr.get("district") or "உங்க locality"

    parts_ta = [f"உங்க soil test report-ஐ பார்த்தேன் ({loc})."]
    readings = []
    if ph is not None:
        readings.append(f"pH {ph}")
    if n is not None:
        readings.append(f"நைட்ரஜன் {n} kg/ha")
    if p is not None:
        readings.append(f"பாஸ்பரஸ் {p} kg/ha")
    if k is not None:
        readings.append(f"பொட்டாசியம் {k} kg/ha")
    if oc is not None:
        readings.append(f"கரிம கார்பன் {oc}%")
    if ec is not None:
        readings.append(f"EC {ec} dS/m")
    if readings:
        parts_ta.append(" — ".join(readings) + ".")
    if soil_type != "—":
        parts_ta.append(f"மண் வகை {soil_type}.")

    if recommendations:
        top = recommendations[:3]
        crops = ", ".join(r["crop"] for r in top)
        parts_ta.append(f"இந்த மண்ணுக்கு {crops} நல்லா பொருந்தும்.")
        if top[0].get("reasons"):
            parts_ta.append(top[0]["reasons"][0])

    ta = humanize_tamil_response(" ".join(parts_ta))

    en_parts = [f"I read your soil test report ({loc})."]
    if ph is not None:
        en_parts.append(f"pH {ph}.")
    if n is not None:
        en_parts.append(f"N {n}, P {p or '—'}, K {k or '—'} kg/ha.")
    if recommendations:
        en_parts.append(f"Best crops: {', '.join(r['crop'] for r in recommendations[:3])}.")

    en = " ".join(en_parts)
    if lang == "English":
        return en, en
    return en, ta

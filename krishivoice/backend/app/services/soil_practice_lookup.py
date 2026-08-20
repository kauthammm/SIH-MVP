"""Soil × crop irrigation & fertilizer guidance from canonical practice CSV."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Optional

import pandas as pd

from app.services.data_paths import root_dataset

SOIL_ALIASES: dict[str, tuple[str, ...]] = {
    "alluvial": ("alluvial", "வண்டல்"),
    "red": ("red", "red loam", "red sandy", "செம்மண்", "sandy loam"),
    "black": ("black", "black soil", "கரிசல்"),
    "sandy": ("sandy", "sand", "மணல்"),
    "clay": ("clay", "களிமண்"),
}

CROP_ALIASES: dict[str, tuple[str, ...]] = {
    "rice": ("rice", "paddy", "nell", "நெல்", "arisi"),
    "cotton": ("cotton", "paruthi", "பருத்தி"),
    "groundnut": ("groundnut", "nilakadalai", "நிலக்கடலை"),
    "sugarcane": ("sugarcane", "karumbu", "கரும்பு"),
    "maize": ("maize", "corn", "மக்காச்சோளம்"),
    "banana": ("banana", "வாழை"),
}


def _norm_soil(text: str) -> str:
    low = (text or "").lower()
    for key, aliases in SOIL_ALIASES.items():
        if any(a in low for a in aliases):
            return key
    return low.split()[0] if low else ""


def _norm_crop(text: str) -> str:
    low = (text or "").lower()
    for key, aliases in CROP_ALIASES.items():
        if any(a in low for a in aliases):
            return key
    return low.split()[0] if low else ""


@lru_cache(maxsize=1)
def _load_practices() -> pd.DataFrame:
    path = root_dataset("soil_practices")
    df = pd.read_csv(path, encoding="utf-8")
    df["_soil_key"] = df["soil_type"].astype(str).map(_norm_soil)
    df["_crop_key"] = df["crop"].astype(str).map(_norm_crop)
    return df


def lookup_practice(
    soil_type: str,
    crop: str,
) -> Optional[dict[str, Any]]:
    """Best-match row for soil + crop practice guidance."""
    df = _load_practices()
    sk = _norm_soil(soil_type)
    ck = _norm_crop(crop)
    if not sk or not ck:
        return None

    exact = df[(df["_soil_key"] == sk) & (df["_crop_key"] == ck)]
    if len(exact):
        return exact.iloc[0].to_dict()

    soil_only = df[df["_soil_key"] == sk]
    if len(soil_only):
        return soil_only.iloc[0].to_dict()

    crop_only = df[df["_crop_key"] == ck]
    if len(crop_only):
        return crop_only.iloc[0].to_dict()

    return None


def format_irrigation_guidance(practice: dict[str, Any], lang: str = "Tamil") -> tuple[str, str]:
    method = practice.get("recommended_irrigation") or practice.get("recommended_irrigation_method") or "drip"
    water = practice.get("crop_water_requirement") or ""
    soil_en = practice.get("soil_type") or ""
    crop_en = practice.get("crop") or ""
    method_en = str(method).split("/")[0].strip() if lang == "English" else method
    water_en = {"அதிகம்": "high", "மிதமான": "moderate", "குறைவு": "low"}.get(str(water).strip(), str(water))
    en = f"For {crop_en} on {soil_en} soil: use {method_en} irrigation. Water need: {water_en}.".strip()
    if lang == "English":
        return en, en
    note = practice.get("irrigation_note") or ""
    ta_name = practice.get("soil_name_tamil") or practice.get("soil_type") or ""
    crop_ta = practice.get("crop") or ""
    ta = f"{ta_name} + {crop_ta}-ku {method} பாசனம் பரிந்துரை. {note}".strip()
    return en, ta


def format_fertilizer_guidance(practice: dict[str, Any], lang: str = "Tamil", crop: str = "") -> tuple[str, str]:
    strategy = practice.get("fertilizer_strategy") or ""
    caution = practice.get("fertilizer_caution") or ""
    crop_label = crop or practice.get("crop") or "crop"
    en = f"For {crop_label}: {strategy} Caution: {caution}".strip()
    ta = f"{crop_label}-ku uram: {strategy} {caution}".strip()
    if lang == "English":
        return en, en
    return en, ta

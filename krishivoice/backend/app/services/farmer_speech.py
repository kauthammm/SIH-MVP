"""
Understand how farmers actually speak — crops, planting, soil, water — in Tamil & English.
Extracts profile fields and question focus from natural voice/text (no jargon required).
"""
from __future__ import annotations

import re
from typing import Any, Optional

from app.services.language_utils import normalize_query

# Tamil Nadu districts — voice recognition for farm location
_TN_DISTRICTS: list[tuple[str, str]] = [
    (r"\bthanjavur\b|thanjai|tanjore", "Thanjavur"),
    (r"\bcuddalore\b|kuddalore", "Cuddalore"),
    (r"\btrichy\b|tiruchirappalli|trichirapalli", "Tiruchirappalli"),
    (r"\bcoimbatore\b|kovai", "Coimbatore"),
    (r"\bmadurai\b", "Madurai"),
    (r"\bsalem\b", "Salem"),
    (r"\berode\b", "Erode"),
    (r"\btirunelveli\b|nellai", "Tirunelveli"),
    (r"\bvirudhunagar\b|virudunagar", "Virudhunagar"),
    (r"\bnamakkal\b", "Namakkal"),
    (r"\bkarur\b", "Karur"),
    (r"\bdindigul\b|dindukkal", "Dindigul"),
    (r"\bthoothukudi\b|tuticorin", "Thoothukudi"),
    (r"\bkanchipuram\b|kancheepuram", "Kanchipuram"),
    (r"\bviluppuram\b|vilupuram|villupuram", "Viluppuram"),
    (r"\bkrishnagiri\b", "Krishnagiri"),
    (r"\bdharmapuri\b", "Dharmapuri"),
    (r"\btiruvannamalai\b|thiruvannamalai", "Tiruvannamalai"),
    (r"\bperambalur\b", "Perambalur"),
    (r"\bariyalur\b", "Ariyalur"),
    (r"\bnagapattinam\b|nagai", "Nagapattinam"),
    (r"\bthiruvarur\b|thiruvaroor", "Thiruvarur"),
    (r"\bpondicherry\b|puducherry|pondy", "Puducherry"),
    (r"\bammapettai\b|ammapet", "Thanjavur"),
    (r"\bchidambaram\b", "Cuddalore"),
]

_LOCATION_CUE = re.compile(
    r"(?:en\s*(?:farm|field|nilam|vayal|thottam)|my\s*(?:farm|field|land)|"
    r"naan\s*(?:.*?)\s*(?:la|il|le)|"
    r"(?:farm|field|nilam|vayal|thottam)\s*(?:la|il|le|in|at)|"
    r"(?:village|oor|ur|gramam|town|district|mavattam|taluk|block))",
    re.IGNORECASE,
)

_VILLAGE_PATTERNS = [
    re.compile(r"(?:village|oor|ur|gramam)\s*(?:name\s*)?(?:is\s*)?[:.]?\s*([a-zA-Z\u0B80-\u0BFF][\w\s\-]{2,40})", re.I),
    re.compile(r"(?:en\s*oor|my\s*village|enga\s*oor)\s*(?:la\s*)?(?:name\s*)?(?:is\s*)?([a-zA-Z\u0B80-\u0BFF][\w\s\-]{2,40})", re.I),
    re.compile(r"([a-zA-Z][a-zA-Z\s\-]{2,30})\s*(?:la|il|le)\s*(?:en\s*)?(?:farm|field|nilam|vayal|irukku|pannuren)", re.I),
]
_CROP_RULES: list[tuple[str, str, float]] = [
    (r"(?:plant|grow|sow|seed|cultivat|vadiv|vithai|saad|podu|pott|pann|irukku|irukken|pannuren|pannirukken|pannuvom).{0,30}?(?:rice|paddy|nell|nel|arisi|நெல்|நெல)", "Rice", 3),
    (r"(?:rice|paddy|nell|nel|arisi|நெல்|நெல).{0,20}?(?:plant|grow|sow|seed|vadiv|vithai|saad|podu|pann)", "Rice", 3),
    (r"\b(?:rice|paddy|nell|nel|arisi|நெல்|நெல்)\b", "Rice", 2),
    (r"(?:plant|grow|sow|seed|vadiv|vithai|saad|podu).{0,30}?(?:groundnut|nilakadalai|peanut|நிலக்கடலை)", "Groundnut", 3),
    (r"\b(?:groundnut|nilakadalai|peanut|நிலக்கடலை)\b", "Groundnut", 2),
    (r"(?:plant|grow|sow|seed|vadiv|vithai|saad|podu).{0,30}?(?:sugarcane|karumbu|கரும்பு)", "Sugarcane", 3),
    (r"\b(?:sugarcane|karumbu|கரும்பு)\b", "Sugarcane", 2),
    (r"(?:plant|grow|sow|seed|vadiv|vithai|saad|podu).{0,30}?(?:blackgram|black\s*gram|ulundu|உளுந்து)", "Blackgram", 3),
    (r"\b(?:blackgram|black\s*gram|ulundu|உளுந்து)\b", "Blackgram", 2),
    (r"(?:plant|grow|sow|seed|vadiv|vithai|saad|podu|pott|pann).{0,30}?(?:cotton|paruthi|kaattan|kattan|காட்டன்|காட்டண்|பருத்தி)", "Cotton", 3),
    (r"(?:cotton|paruthi|kaattan|kattan|காட்டன்|காட்டண்|பருத்தி)", "Cotton", 2),
]

_STAGE_RULES: list[tuple[str, str, float]] = [
    (r"just\s*(?:plant|sow|seed|vadich|vithai|saad|podu)|ippod(?:han|u)\s*(?:vithai|saad|podu)|இப்ப(?:ோ|)த(?:ா|)ன\s*(?:விதை|போ)|போட்ட(?:ா|ேன்|து)", "Nursery", 3),
    (r"nursery|seedling|small\s*plant|konji\s*plant|konjam\s*plant|நாற்ற|நாற்றம்|சின்ன\s*செடி", "Nursery", 2),
    (r"tiller|tillering|konai|konai\s*varuthu|குத்து|konai\s*stage|young\s*plant", "Tillering", 3),
    (r"panicle|pi\s*stage|poo\s*varuthu|flowering|poo\s*poduthu|பூ|flower", "Panicle Initiation", 2),
    (r"flowering|poo\s*time|flower\s*stage|பூ\s*கட்ட", "Flowering", 2),
    (r"matur|harvest|ready\s*to\s*cut|cut\s*pan|koyy|koyy\s*ready|அறுவடை|முழுத", "Maturity", 3),
    (r"growing\s*well|valaruthu|valarum|vaguthu|வளர", "Tillering", 1.5),
]

_SOIL_RULES: list[tuple[str, str, float]] = [
    (r"black\s*(?:soil|cotton|cotton\s*soil)|karu\s*mann|karu\s*nilam|கருப்பு\s*மண்|black\s*land", "Black Cotton Soil", 3),
    (r"red\s*(?:soil|land|mann)|semm\s*mann|sevappu\s*mann|சிகப்பு\s*மண்", "Red Soil", 3),
    (r"clay\s*loam|mann\s*seri|sticky\s*soil|சேறு\s*மண்|kle\s*mann", "Clay Loam", 2),
    (r"sandy|sand\s*soil|manal\s*mann|மணல்\s*மண்|sandy\s*loam", "Sandy Loam", 2),
    (r"alluvial|aaru\s*mann|river\s*soil|delta\s*soil", "Alluvial", 2),
    (r"loam|good\s*soil|nalla\s*mann|நல்ல\s*மண்", "Loam", 1.5),
    (r"clay|klei|heavy\s*soil|களி\s*மண்", "Clay", 2),
]

_LAND_RULES: list[tuple[str, str, float]] = [
    (r"wet\s*land|wetland|wet\s*field|nana\s*nilam|nanjai|நன\s*|நன்செய்|irrigated\s*field", "Wetland", 3),
    (r"dry\s*land|dryland|dry\s*field|punjai|punsei|புஞ்சை|rain\s*only\s*field", "Dryland", 3),
    (r"garden\s*land|thottam|thottathu|தோட்ட", "Garden land", 2),
    (r"horticulture|fruit|fruit\s*garden", "Horticulture", 2),
]

_WATER_RULES: list[tuple[str, str, float]] = [
    (r"canal|kanal|canal\s*water|kanal\s*thanneer|கால்வாய்|canal\s*fed", "Canal", 3),
    (r"bore\s*well|borewell|well\s*water|bore|கிணறு|well\s*fed", "Borewell", 3),
    (r"rain\s*fed|rain\s*only|rainfed|mazhai\s*thanneer|மழை\s*தண்ணீர்|rain\s*water\s*only", "Rain-fed", 3),
    (r"tank|eri|lake|ஏரி|kulam", "Tank", 2),
    (r"drip|drip\s*irrigation", "Drip", 2),
    (r"sprinkler", "Sprinkler", 2),
]

_MOISTURE_RULES: list[tuple[str, float, float]] = [
    (r"very\s*dry|too\s*dry|sukka|sukkam|karai|karaiya|வறண்ட|dry\s*field|no\s*water|thanneer\s*ill|தண்ணீர்\s*இல்ல", 12.0, 3),
    (r"dry|need\s*water|paayich|paayikanum|thanni\s*vend|தண்ணீர்\s*வேண|water\s*needed|irrigation\s*need", 18.0, 2),
    (r"moist|ok|fine|nalla|normal|enough\s*water|thanni\s*iruk|தண்ணீர்\s*இருக", 28.0, 2),
    (r"wet|waterlogged|too\s*much\s*water|athigam\s*thanni|thanni\s*nirai|நிறைய\s*தண்ணீர்|flooded", 38.0, 3),
]

_PLANTING_ACTION = re.compile(
    r"(?:i\s*am\s*|naan\s*|en\s*|)?(?:plant|grow|sow|seed|vadiv|vithai|saad|podu|pott|pann|"
    r"starting|started|going\s*to|planning\s*to|ippod(?:u|han)|இப்ப(?:ோ|)த(?:ா|)ன|"
    r"vadich|vithai|saad|podu|pann|pannuren|pannirukken|pannuvom|pannanum|"
    r"போட்ட(?:ா|ேன்|து|ிருக்க|)|po(?:tt|d)(?:a|en|u|hu))",
    re.IGNORECASE,
)

_QUESTION_FOCUS_RULES: list[tuple[str, str, float]] = [
    (r"how\s*much\s*water|ethana\s*thanni|thanni\s*ethana|water\s*amount|paayich|paayikanum|irrigation|thanneer|"
     r"எவ்வளவு\s*தண்ணீர்|தண்ணீர்\s*தேவை|தேவைப்படும்|evvalavu\s*thanneer", "water", 3),
    (r"fertilizer|urea|dap|npk|manure|uram|உரம்|top\s*dress", "fertilizer", 3),
    (r"soil|mann|மண்|soil\s*type|soil\s*test", "soil", 3),
    (r"when\s*(?:to\s*)?(?:plant|sow|harvest|cut|irrigate)|eppo|eppadi|yeppo|yeppadi|எப்ப", "timing", 2),
    (r"rain|mazhai|weather|forecast|மழை|vaaippu", "weather", 3),
    (r"pest|poochi|insect|worm|பூச்சி|disease|noi|நோய", "pest_disease", 3),
    (r"yield|makasool|production|harvest|koyy|அறுவடை|output", "yield", 2),
    (r"price|rate|market|vila|விலை|sell", "market", 2),
    (r"scheme|subsidy|govt|government|help|assistance", "schemes", 2),
    (r"what\s*(?:crop|plant)|which\s*crop|enna\s*payir|என்ன\s*பயிர்", "crop_choice", 2),
    (r"how\s*is|status|condition|eppadi\s*iruk|எப்படி\s*இருக", "status", 2),
]


def _best_match(rules: list[tuple[str, str, float]], text: str) -> Optional[str]:
    scores: dict[str, float] = {}
    for pattern, value, weight in rules:
        if re.search(pattern, text, re.IGNORECASE):
            scores[value] = scores.get(value, 0) + weight
    if not scores:
        return None
    return max(scores, key=scores.get)


def _moisture_match(text: str) -> Optional[float]:
    best_val: Optional[float] = None
    best_score = 0.0
    for pattern, value, weight in _MOISTURE_RULES:
        if re.search(pattern, text, re.IGNORECASE) and weight > best_score:
            best_val = value
            best_score = weight
    return best_val


def _extract_location(text: str, normalized: str) -> dict[str, Any]:
    """Pull district/village from natural speech — e.g. 'Thanjavur la en farm'."""
    loc: dict[str, Any] = {}
    lower = normalized.lower()

    for pattern, district in _TN_DISTRICTS:
        if re.search(pattern, lower, re.IGNORECASE) or re.search(pattern, normalized, re.IGNORECASE):
            loc["district"] = district
            break

    for pat in _VILLAGE_PATTERNS:
        m = pat.search(normalized)
        if m:
            village = m.group(1).strip(" .,-")
            if village and len(village) > 2 and village.lower() not in ("my", "the", "en", "naan"):
                loc["village"] = village.title() if village.isascii() else village
                break

    if _LOCATION_CUE.search(normalized) or loc.get("district") or loc.get("village"):
        loc["location_mentioned"] = True
    return loc


def extract_farmer_speech(text: str) -> dict[str, Any]:
    """
    Extract farmer-friendly fields from natural speech.
    Example: 'I am planting rice in wet land with canal water, field is dry'
    """
    normalized = normalize_query(text)
    lower = normalized.lower()
    result: dict[str, Any] = {
        "raw_query": text,
        "normalized": normalized,
        "is_planting_declaration": bool(_PLANTING_ACTION.search(normalized)),
        "question_focus": [],
    }

    crop = _best_match(_CROP_RULES, normalized)
    if crop:
        result["crop"] = crop

    stage = _best_match(_STAGE_RULES, normalized)
    if stage:
        result["growth_stage"] = stage

    soil = _best_match(_SOIL_RULES, normalized)
    if soil:
        result["soil_type"] = soil
        result["soil_texture"] = soil

    land = _best_match(_LAND_RULES, normalized)
    if land:
        result["land_type"] = land

    water = _best_match(_WATER_RULES, normalized)
    if water:
        result["irrigation_source"] = water

    moisture = _moisture_match(normalized)
    if moisture is not None:
        result["soil_moisture"] = moisture

    location = _extract_location(text, normalized)
    if location:
        result.update({k: v for k, v in location.items() if v is not None})

    # Question focus (what they actually want to know)
    focus_scores: dict[str, float] = {}
    for pattern, topic, weight in _QUESTION_FOCUS_RULES:
        if re.search(pattern, lower, re.IGNORECASE) or re.search(pattern, normalized, re.IGNORECASE):
            focus_scores[topic] = focus_scores.get(topic, 0) + weight
    result["question_focus"] = sorted(focus_scores, key=focus_scores.get, reverse=True)  # type: ignore[arg-type]

    # Profile fields to auto-save (only when farmer is telling us about their farm)
    profile_fields: dict[str, Any] = {}
    for key in ("crop", "growth_stage", "soil_type", "soil_texture", "land_type", "irrigation_source", "soil_moisture", "district", "village"):
        if key in result:
            profile_fields[key] = result[key]
    if profile_fields.get("soil_type") and "soil" not in profile_fields:
        profile_fields["soil"] = {"soil_type": profile_fields["soil_type"]}

    # Save profile when declaring planting OR mentioning 2+ farm details OR location
    detail_count = len(profile_fields)
    has_location = bool(result.get("district") or result.get("village"))
    if result["is_planting_declaration"] or detail_count >= 2 or has_location:
        result["profile_updates"] = profile_fields
    elif detail_count == 1 and result["question_focus"]:
        # e.g. "how much water for rice" — save crop only
        if "crop" in profile_fields:
            result["profile_updates"] = {"crop": profile_fields["crop"]}
            if profile_fields.get("growth_stage"):
                result["profile_updates"]["growth_stage"] = profile_fields["growth_stage"]

    return result


def speech_to_profile_patch(speech: dict[str, Any]) -> dict[str, Any]:
    """Convert speech extraction to profile_store update dict."""
    updates = dict(speech.get("profile_updates") or {})
    if not updates:
        return {}

    patch: dict[str, Any] = {}
    if updates.get("crop"):
        patch["crop"] = updates["crop"]
    if updates.get("growth_stage"):
        patch["growth_stage"] = updates["growth_stage"]
    if updates.get("land_type"):
        patch["land_type"] = updates["land_type"]
    if updates.get("irrigation_source"):
        patch["irrigation_source"] = updates["irrigation_source"]
    if updates.get("soil_texture"):
        patch["soil_texture"] = updates["soil_texture"]
    if updates.get("soil_moisture") is not None:
        patch["soil_moisture"] = float(updates["soil_moisture"])
    if updates.get("soil_type"):
        patch["soil"] = {"soil_type": updates["soil_type"]}
    if updates.get("district"):
        patch["district"] = updates["district"]
    if updates.get("village"):
        patch["village"] = updates["village"]
        if not patch.get("land_name"):
            patch["land_name"] = updates["village"]
    return patch


def acknowledgment_for_updates(patch: dict[str, Any], lang: str = "English") -> str:
    """Short confirmation when we learned something from the farmer's voice."""
    if not patch:
        return ""
    parts_en = []
    parts_ta = []
    if patch.get("crop"):
        parts_en.append(f"crop: {patch['crop']}")
        parts_ta.append(f"பயிர்: {patch['crop']}")
    if patch.get("growth_stage"):
        parts_en.append(f"stage: {patch['growth_stage']}")
        parts_ta.append(f"நிலை: {patch['growth_stage']}")
    if patch.get("land_type"):
        parts_en.append(f"land: {patch['land_type']}")
        parts_ta.append(f"நிலம்: {patch['land_type']}")
    if patch.get("irrigation_source"):
        parts_en.append(f"water source: {patch['irrigation_source']}")
        parts_ta.append(f"தண்ணீர்: {patch['irrigation_source']}")
    if patch.get("soil_texture") or patch.get("soil"):
        st = patch.get("soil_texture") or (patch.get("soil") or {}).get("soil_type")
        parts_en.append(f"soil: {st}")
        parts_ta.append(f"மண்: {st}")
    if patch.get("soil_moisture") is not None:
        parts_en.append(f"moisture noted")
        parts_ta.append("ஈரப்பதம் note panniten")
    if patch.get("district"):
        parts_en.append(f"location: {patch['district']}")
        parts_ta.append(f"இடம்: {patch['district']}")
    if patch.get("village"):
        parts_en.append(f"village: {patch['village']}")
        parts_ta.append(f"கிராமம்: {patch['village']}")

    if lang == "Tamil":
        return f"நான் record panniten — {', '.join(parts_ta)}. "
    return f"I've noted your {', '.join(parts_en)}. "

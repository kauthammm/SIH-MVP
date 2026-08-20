"""Extract structured soil test values from PDF / image soil lab reports."""
from __future__ import annotations

import io
import re
from typing import Any, Optional

# Field patterns — Tamil + English lab report formats (TN STCR / university labs)
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("pH", re.compile(r"(?:p\s*H|Reaction|நெ\.?\s*நிலை|நி\.?\s*நிலை)\s*[:\-]?\s*(\d+\.?\d*)", re.I)),
    ("nitrogen", re.compile(
        r"(?:Available\s+N(?:itrogen)?|N(?:itrogen)?|N\s*\(kg/ha\)|நைட்ரஜன்|"
        r"கிடைக்க(?:ும்|க்கும்)\s*நைட்ரஜன்)\s*[:\(]?\s*(?:kg/ha|Kg/ha|kg\s*/\s*ha)?\)?\s*[:\-]?\s*(\d+\.?\d*)",
        re.I,
    )),
    ("phosphorus", re.compile(
        r"(?:Available\s+P(?:hosphorus)?|Olsen\s+P|Bray\s+P|P2O5|P\s*\(kg/ha\)|"
        r"பாஸ்பரஸ்|கிடைக்க(?:ும்|க்கும்)\s*பாஸ்பரஸ்)\s*[:\(]?\s*(?:kg/ha|Kg/ha)?\)?\s*[:\-]?\s*(\d+\.?\d*)",
        re.I,
    )),
    ("potassium", re.compile(
        r"(?:Available\s+K(?:\s*Potassium)?|K2O|K\s*\(kg/ha\)|"
        r"பொட்டாசியம்|கிடைக்க(?:ும்|க்கும்)\s*பொட்டாசியம்)\s*[:\(]?\s*(?:kg/ha|Kg/ha)?\)?\s*[:\-]?\s*(\d+\.?\d*)",
        re.I,
    )),
    ("organic_carbon", re.compile(
        r"(?:O\.?\s*C|Organic\s+Carbon|OC|கரிம\s+கார(?:bon|பன்)|கரிம\s+கர(?:bon|பன்))\s*[:\(]?\s*(?:%|percent)?\)?\s*[:\-]?\s*(\d+\.?\d*)",
        re.I,
    )),
    ("electrical_conductivity", re.compile(
        r"(?:E\.?\s*C|EC|Conductivity|மின்கடத்தல்|கடத்துத்திறன்)\s*[:\(]?\s*(?:dS/m|dS\s*/\s*m|mmho/cm)?\)?\s*[:\-]?\s*(\d+\.?\d*)",
        re.I,
    )),
    ("sand_percent", re.compile(r"Sand\s*[:\-]?\s*(\d+\.?\d*)\s*%?", re.I)),
    ("silt_percent", re.compile(r"Silt\s*[:\-]?\s*(\d+\.?\d*)\s*%?", re.I)),
    ("clay_percent", re.compile(r"Clay\s*[:\-]?\s*(\d+\.?\d*)\s*%?", re.I)),
    ("zinc", re.compile(r"(?:Zn|Zinc|துத்தநாகம்)\s*[:\-]?\s*(\d+\.?\d*)", re.I)),
    ("iron", re.compile(r"(?:Fe|Iron|இரும்பு)\s*[:\-]?\s*(\d+\.?\d*)", re.I)),
    ("boron", re.compile(r"(?:B|Boron|போரான்)\s*[:\-]?\s*(\d+\.?\d*)", re.I)),
]

_SOIL_TYPE_PATTERNS = [
    (re.compile(r"Red\s+(?:Sandy\s+)?Loam", re.I), "Red Loam"),
    (re.compile(r"Red\s+Sandy", re.I), "Red Sandy Loam"),
    (re.compile(r"Black\s+Soil", re.I), "Black Soil"),
    (re.compile(r"Alluvial", re.I), "Alluvial"),
    (re.compile(r"Laterite", re.I), "Laterite"),
    (re.compile(r"Clay\s+Loam", re.I), "Clay Loam"),
    (re.compile(r"Clay", re.I), "Clay"),
    (re.compile(r"Loam", re.I), "Loam"),
    (re.compile(r"Sandy", re.I), "Sandy Loam"),
]

_DISTRICT_HINT = re.compile(
    r"(Thanjavur|Cuddalore|Vellore|Tiruppur|Coimbatore|Madurai|Trichy|Tiruchirappalli|"
    r"Salem|Erode|Dindigul|Villupuram|Kanchipuram|Chennai|Tirunelveli|Thoothukudi|"
    r"Nagapattinam|Tiruvarur|Ariyalur|Perambalur|Namakkal|Dharmapuri|Krishnagiri|"
    r"Theni|Ramanathapuram|Sivaganga|Pudukkottai|Karur|Nilgiris|Tenkasi|Kallakurichi|Mayiladuthurai)",
    re.I,
)

_CORE_FIELDS = {"pH", "nitrogen", "phosphorus", "potassium", "organic_carbon", "electrical_conductivity"}


def _normalize_keys(result: dict[str, Any]) -> None:
    if "nitrogen" in result:
        result["N_kg_ha"] = result["nitrogen"]
    if "phosphorus" in result:
        result["P_kg_ha"] = result["phosphorus"]
    if "potassium" in result:
        result["K_kg_ha"] = result["potassium"]
    if "organic_carbon" in result:
        result["OC_percent"] = result["organic_carbon"]
    if "electrical_conductivity" in result:
        result["EC_dS_m"] = result["electrical_conductivity"]


def _finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    skip = {"fields_found", "confidence", "extraction_method", "raw_text_snippet", "source_file"}
    found = [k for k, v in result.items() if k not in skip and v is not None and v != ""]
    result["fields_found"] = found
    core = sum(1 for k in _CORE_FIELDS if k in found or k.replace("_", "") in str(found))
    result["confidence"] = round(min(0.95, 0.3 + 0.1 * len(found) + 0.05 * core), 2)
    _normalize_keys(result)
    return result


def merge_soil_extractions(*sources: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Merge regex + VL results; prefer numeric values, fill gaps from any source."""
    merged: dict[str, Any] = {}
    methods: list[str] = []
    for src in sources:
        if not src:
            continue
        method = src.get("extraction_method")
        if method:
            methods.append(str(method))
        if src.get("raw_text_snippet") and not merged.get("raw_text_snippet"):
            merged["raw_text_snippet"] = src["raw_text_snippet"]
        for k, v in src.items():
            if k in ("fields_found", "confidence", "extraction_method", "raw_text_snippet"):
                continue
            if v is None or v == "":
                continue
            if merged.get(k) is None:
                merged[k] = v

    if methods:
        merged["extraction_method"] = "+".join(dict.fromkeys(methods))
    return _finalize_result(merged)


def _extract_text_from_pdf(data: bytes) -> str:
    try:
        import pdfplumber
        parts = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages[:10]:
                t = page.extract_text() or ""
                parts.append(t)
                for table in page.extract_tables() or []:
                    for row in table:
                        parts.append(" ".join(str(c or "") for c in row))
        return "\n".join(parts)
    except Exception:
        pass
    try:
        import fitz  # pymupdf
        doc = fitz.open(stream=data, filetype="pdf")
        return "\n".join(doc.load_page(i).get_text() for i in range(min(len(doc), 10)))
    except Exception:
        return ""


def _extract_text_from_image(data: bytes) -> str:
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(img, lang="eng+tam")
    except Exception:
        return ""


def parse_soil_text(text: str) -> dict[str, Any]:
    """Parse raw OCR/text into soil parameters."""
    result: dict[str, Any] = {"raw_text_snippet": text[:2000] if text else "", "extraction_method": "regex"}
    if not text:
        result["fields_found"] = []
        result["confidence"] = 0.0
        return result

    for key, pat in _PATTERNS:
        m = pat.search(text)
        if m:
            try:
                result[key] = float(m.group(1))
            except ValueError:
                pass

    for pat, label in _SOIL_TYPE_PATTERNS:
        if pat.search(text):
            result["soil_type"] = label
            break

    dm = _DISTRICT_HINT.search(text)
    if dm:
        result["district"] = dm.group(1).title()

    return _finalize_result(result)


def extract_from_upload(filename: str, data: bytes) -> dict[str, Any]:
    """Main entry: PDF or image upload → structured soil dict."""
    lower = (filename or "").lower()
    is_binary = lower.endswith((".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"))

    if lower.endswith(".pdf"):
        text = _extract_text_from_pdf(data)
    elif lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff")):
        text = _extract_text_from_image(data)
    else:
        text = _extract_text_from_pdf(data) or data.decode("utf-8", errors="ignore")

    parsed = parse_soil_text(text)
    parsed["source_file"] = filename

    vl: Optional[dict[str, Any]] = None
    if is_binary:
        try:
            from app.services.openrouter_client import extract_soil_from_document, is_enabled
            if is_enabled():
                vl = extract_soil_from_document(data, filename)
        except Exception:
            pass

    if vl and vl.get("fields_found"):
        merged = merge_soil_extractions(parsed, vl)
        merged["source_file"] = filename
        return merged

    return parsed

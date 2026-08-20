"""OpenRouter API — VL OCR, LLM advisory polish (hyperlocal facts only)."""
from __future__ import annotations

import base64
import json
import re
from typing import Any, Optional

import httpx

from app.config import get_settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def is_enabled() -> bool:
    s = get_settings()
    return bool(s.openrouter_enabled and s.openrouter_api_key)


def _headers() -> dict[str, str]:
    s = get_settings()
    return {
        "Authorization": f"Bearer {s.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://krishivoice.local",
        "X-Title": "KrishiVoice",
    }


def chat(
    messages: list[dict[str, Any]],
    *,
    model: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    timeout: float = 90.0,
) -> Optional[str]:
    if not is_enabled():
        return None
    s = get_settings()
    payload = {
        "model": model or s.openrouter_llm_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(OPENROUTER_URL, headers=_headers(), json=payload)
            r.raise_for_status()
            data = r.json()
            return (data.get("choices") or [{}])[0].get("message", {}).get("content")
    except Exception:
        return None


def _pdf_page_to_png_b64(data: bytes, page: int = 0, dpi: int = 150) -> Optional[str]:
    try:
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        if page >= len(doc):
            return None
        pix = doc.load_page(page).get_pixmap(dpi=dpi)
        return base64.b64encode(pix.tobytes("png")).decode("ascii")
    except Exception:
        return None


def _image_b64(data: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _parse_vl_soil_json(raw: str) -> Optional[dict[str, Any]]:
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _vl_extract_page(image_url: str, *, page_hint: str = "") -> Optional[dict[str, Any]]:
    s = get_settings()
    prompt = (
        "You read Tamil Nadu soil test lab reports (STCR / university / private labs). "
        "Extract every visible soil value from this page. "
        "Labels may be English or Tamil: pH/நெ.நிலை, Available N/நைட்ரஜன், P/பாஸ்பரஸ், K/பொட்டாசியம், "
        "OC/கரிம கார்பன், EC/கடத்துத்திறன், Sand/Silt/Clay %, soil texture, district name.\n"
        f"{page_hint}\n"
        "Return ONLY JSON (no markdown):\n"
        '{"pH": null, "nitrogen": null, "phosphorus": null, "potassium": null, '
        '"organic_carbon": null, "electrical_conductivity": null, '
        '"sand_percent": null, "silt_percent": null, "clay_percent": null, '
        '"soil_type": null, "district": null, "drainage": null}\n'
        "N,P,K in kg/ha. EC in dS/m. OC in percent. Use numbers only, not text ranges."
    )
    content: list[dict[str, Any]] = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": image_url}},
    ]
    raw = chat(
        [{"role": "user", "content": content}],
        model=s.openrouter_vl_model,
        max_tokens=800,
        temperature=0.0,
        timeout=120.0,
    )
    if not raw:
        return None
    parsed = _parse_vl_soil_json(raw)
    if not parsed:
        return None

    out: dict[str, Any] = {"extraction_method": "openrouter_vl"}
    for k, v in parsed.items():
        if v is not None and v != "":
            try:
                if k in ("soil_type", "district", "drainage"):
                    out[k] = str(v).strip()
                else:
                    out[k] = float(v)
            except (TypeError, ValueError):
                out[k] = v
    return out


def extract_soil_from_document(data: bytes, filename: str) -> Optional[dict[str, Any]]:
    """Use Nemotron VL to read soil lab PDF/image → JSON fields (multi-page PDF)."""
    if not is_enabled():
        return None

    from app.services.soil_report_ocr import merge_soil_extractions

    lower = (filename or "").lower()
    partials: list[dict[str, Any]] = []

    if lower.endswith(".pdf"):
        try:
            import fitz
            doc = fitz.open(stream=data, filetype="pdf")
            page_count = min(len(doc), 5)
        except Exception:
            page_count = 1
        for page in range(page_count):
            b64 = _pdf_page_to_png_b64(data, page, dpi=200)
            if not b64:
                continue
            hint = f"PDF page {page + 1} of {page_count}."
            partial = _vl_extract_page(f"data:image/png;base64,{b64}", page_hint=hint)
            if partial:
                partials.append(partial)
    elif lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff")):
        mime = "image/jpeg" if lower.endswith((".jpg", ".jpeg")) else "image/png"
        partial = _vl_extract_page(_image_b64(data, mime))
        if partial:
            partials.append(partial)

    if not partials:
        return None

    merged = merge_soil_extractions(*partials)
    if not merged.get("fields_found"):
        return None
    merged["extraction_method"] = "openrouter_vl"
    return merged


def polish_advisory(
    *,
    query: str,
    en_draft: str,
    ta_draft: str,
    lang: str,
    farm_context: Optional[dict[str, Any]] = None,
    evidence: Optional[dict[str, Any]] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Rewrite draft advisory in natural Tamil/English using ONLY provided facts.
    Returns (en, ta) or (None, None) on failure.
    """
    if not is_enabled() or not en_draft:
        return None, None

    ctx_lines = []
    if farm_context:
        for k in ("district", "village", "crop", "soil_type", "pH", "ph"):
            v = farm_context.get(k)
            if v is not None:
                ctx_lines.append(f"{k}: {v}")

    system = (
        "You are a friendly Tamil Nadu block-level agriculture officer talking to a farmer on phone. "
        "Rewrite the draft in plain spoken Tamil — like a real person, not a chatbot. "
        "Use short sentences. Avoid formal words like 'பரிந்துரைக்கப்படுகிறது', 'நிபுணர் ஆலோசனை'. "
        "Light Tanglish is fine (crop, spray, kg, litre) but don't over-mix English. "
        "CRITICAL: Do NOT invent numbers, prices, weather mm, or dosages. "
        "Only use facts from the draft and farm context. Keep under 100 words."
    )
    user = (
        f"Farmer question: {query}\n"
        f"Farm context: {', '.join(ctx_lines) or 'none'}\n"
        f"Draft English: {en_draft}\n"
        f"Draft Tamil: {ta_draft}\n"
        f"Preferred language: {lang}\n"
        "Return JSON: {\"english\": \"...\", \"tamil\": \"...\"}"
    )

    raw = chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=500,
        temperature=0.3,
    )
    if not raw:
        return None, None

    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None, None
    try:
        from app.services.tamil_humanize import humanize_english_response, humanize_tamil_response
        obj = json.loads(m.group(0))
        en = humanize_english_response(obj.get("english") or "")
        ta = humanize_tamil_response(obj.get("tamil") or "")
        # Reject template placeholders from malformed LLM JSON
        if en in ("...", "…") or len(en) < 12:
            en = None
        if ta in ("...", "…") or len(ta) < 8:
            ta = None
        return en or None, ta or None
    except json.JSONDecodeError:
        return None, None

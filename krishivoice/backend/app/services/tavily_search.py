"""Tavily web search — trusted agriculture sources for Tamil Nadu farmers."""
from __future__ import annotations

import logging
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

TAVILY_URL = "https://api.tavily.com/search"

TRUSTED_AG_DOMAINS = [
    "tnau.ac.in",
    "icar.org.in",
    "agricoop.gov.in",
    "pmkisan.gov.in",
    "agritech.tn.gov.in",
    "kvk.res.in",
    "agri.tn.gov.in",
    "farmer.gov.in",
    "nabard.org",
    "icar.gov.in",
    "agriculture.tn.gov.in",
    "tn.gov.in",
]


def is_enabled() -> bool:
    s = get_settings()
    return bool(s.tavily_enabled and s.tavily_api_key)


def _domain_allowed(url: str, allowed: list[str]) -> bool:
    try:
        host = (urlparse(url).netloc or "").lower().replace("www.", "")
    except Exception:
        return False
    if not host:
        return False
    return any(host == d or host.endswith("." + d) for d in allowed)


def _filter_trusted_results(results: list[dict[str, Any]], allowed: list[str]) -> list[dict[str, Any]]:
    return [r for r in results if _domain_allowed(r.get("url") or "", allowed)]


def _farm_context_lines(ctx: Optional[dict[str, Any]]) -> list[str]:
    if not ctx:
        return []
    lines: list[str] = []
    for key in ("district", "village", "taluk"):
        v = ctx.get(key)
        if v:
            lines.append(f"{key}: {v}")
    obs = ctx.get("observation")
    if obs:
        crop = getattr(obs, "crop", None) if hasattr(obs, "crop") else None
        stage = getattr(obs, "growth_stage", None) if hasattr(obs, "growth_stage") else None
        if isinstance(obs, dict):
            crop = obs.get("crop") or crop
            stage = obs.get("growth_stage") or stage
        if crop:
            lines.append(f"crop: {crop}")
        if stage:
            lines.append(f"growth_stage: {stage}")
    return lines


def _build_search_query(query: str, ctx: Optional[dict[str, Any]]) -> str:
    parts = [query.strip(), "Tamil Nadu agriculture farmer"]
    ctx_lines = _farm_context_lines(ctx)
    if ctx_lines:
        parts.append(" ".join(v.split(": ", 1)[-1] for v in ctx_lines[:3]))
    text = " ".join(p for p in parts if p)
    return text[:380]


def _tavily_request(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        with httpx.Client(timeout=35.0) as client:
            r = client.post(TAVILY_URL, json=payload)
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        logger.warning("Tavily search failed: %s", exc)
        return None


def search_web(
    query: str,
    *,
    ctx: Optional[dict[str, Any]] = None,
    max_results: int = 5,
    trusted_only: Optional[bool] = None,
) -> dict[str, Any]:
    """Run Tavily search. When trusted_only, NEVER returns open-web results."""
    if not is_enabled():
        return {"ok": False, "error": "Tavily not configured", "results": []}

    s = get_settings()
    strict = s.tavily_trusted_only if trusted_only is None else trusted_only
    search_q = _build_search_query(query, ctx)

    payload: dict[str, Any] = {
        "api_key": s.tavily_api_key,
        "query": search_q,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": "basic",
        "topic": "general",
        "include_domains": TRUSTED_AG_DOMAINS,
    }

    data = _tavily_request(payload)
    if not data:
        return {"ok": False, "error": "Search request failed", "results": [], "search_query": search_q}

    raw_results = data.get("results") or []
    trusted = _filter_trusted_results(raw_results, TRUSTED_AG_DOMAINS)

    if strict and not trusted:
        return {
            "ok": False,
            "error": "No trusted-domain results (TNAU/ICAR/govt only)",
            "results": [],
            "search_query": search_q,
            "filtered_out": len(raw_results),
        }

    use_results = trusted if strict else raw_results
    answer = (data.get("answer") or "").strip() if use_results else ""

    results = []
    for item in use_results:
        results.append({
            "title": item.get("title") or "",
            "url": item.get("url") or "",
            "content": (item.get("content") or "")[:600],
            "score": item.get("score"),
        })

    return {
        "ok": bool(results or answer),
        "answer": answer,
        "results": results,
        "search_query": search_q,
        "response_time": data.get("response_time"),
        "trusted_only": strict,
        "domain_filter": "enforced" if strict else "off",
    }


def _format_sources(results: list[dict[str, Any]], limit: int = 2) -> str:
    parts = []
    for r in results[:limit]:
        title = (r.get("title") or "Source").strip()
        url = r.get("url") or ""
        if url:
            parts.append(f"{title} ({url})")
    return " Sources: " + "; ".join(parts) if parts else ""


def synthesize_web_answer(
    query: str,
    *,
    ctx: Optional[dict[str, Any]] = None,
    lang: str = "English",
) -> Optional[dict[str, Any]]:
    """Search trusted ag web only; refuse if no official-domain hits."""
    hit = search_web(query, ctx=ctx, trusted_only=True)
    if not hit.get("ok"):
        return None

    answer = hit.get("answer") or ""
    results = hit.get("results") or []

    if not answer and results:
        snippets = [r["content"] for r in results[:2] if r.get("content")]
        answer = " ".join(snippets)[:700]

    if not answer or len(answer) < 20:
        return None

    sources_note = _format_sources(results)
    en = f"{answer.strip()}{sources_note}".strip()

    ta = en
    if lang == "Tamil":
        try:
            from app.services.convo_translate import translate_advice_to_tamil
            ta = translate_advice_to_tamil(answer) + (
                " (official web source)" if sources_note else ""
            )
        except Exception:
            ta = en

    return {
        "english": en,
        "tamil": ta,
        "confidence": 0.82 if hit.get("answer") else 0.74,
        "evidence": {
            "source": "tavily_web",
            "search_query": hit.get("search_query"),
            "results": results[:3],
            "response_time": hit.get("response_time"),
            "domain_filter": hit.get("domain_filter"),
        },
        "reason": "Web search from trusted agriculture sources (Tavily).",
    }

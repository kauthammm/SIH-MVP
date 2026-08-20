"""
Voice-first guest onboarding: greet → understand → collect profile → personalized advice.
Works for non-login farmers using mic or text.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from app.models.schemas import AdvisoryOut
from app.services.guest_session import (
    add_message,
    create_session,
    get_session,
    missing_fields,
    profile_completeness,
    session_to_context,
    update_profile,
)
from app.services.farmer_speech import extract_farmer_speech, speech_to_profile_patch
from app.services.agent_orchestrator import run_voice_agent
from app.services.crop_recommendation import format_crop_recommendations, format_demand_forecast
from app.services.daily_briefing import build_daily_briefing
from app.services.openmeteo_weather import enrich_context_with_openmeteo
from app.services.voice_intent import process_voice_query

# Questions to ask when profile field is missing (en, ta)
FOLLOWUP_QUESTIONS = {
    "crop": (
        "What crop are you growing or planning to plant?",
        "என்ன பயிர் பண்றீங்க அல்லது விதைக்க போறீங்க?",
    ),
    "land_type": (
        "Is your field wet land with canal/tank water, or dry rain-fed land?",
        "நன்செய் நிலமா (கால்வாய் தண்ணீர்) இல்ல புஞ்சை rain-fed-aa?",
    ),
    "irrigation_source": (
        "Where does your water come from — canal, borewell, or rain only?",
        "தண்ணீர் எங்கிருந்து — கால்வாய், போர்வெல், இல்ல மழை மட்டுமா?",
    ),
    "district": (
        "Which district is your farm in?",
        "உங்க farm எந்த district-la?",
    ),
    "growth_stage": (
        "How is your crop now — just planted, growing well, or ready to harvest?",
        "crop ippove enna stage — ippodhan vithachenga, valarum, harvest-ku ready?",
    ),
    "soil_texture": (
        "What type of soil — red, black, sandy, or clay?",
        "mann enna type — sevappu, karuppu, manal, klei?",
    ),
}

GREETINGS = re.compile(
    r"^(hi|hello|hey|vanakkam|namaskaram|good\s*(morning|evening|afternoon)|"
    r"வணக்கம்|நமஸ்காரம்|eppadi|epdi|how\s*are\s*you)",
    re.IGNORECASE,
)

THANKS = re.compile(r"thank|nanri|nandri|நன்றி", re.IGNORECASE)


def _lang(session: dict) -> str:
    return session.get("language", "Tamil")


def _pick(lang: str, en: str, ta: str) -> str:
    return ta if lang == "Tamil" else en


def start_session(language: str = "Tamil") -> dict[str, Any]:
    session = create_session(language)
    lang = _lang(session)
    greeting = _pick(
        lang,
        "Hello! I'm KrishiVoice, your farming assistant. How can I help you today? "
        "You can tell me what crop you grow, ask about water, fertilizer, weather, or what to plant for profit.",
        "வணக்கம்! நான் KrishiVoice — உங்க farming assistant. எப்படி help pannalam? "
        "என்ன crop, தண்ணீர், உரம், weather, profit-ku enna plant pannalam-nu kelunga.",
    )
    session["greeted"] = True
    session["step"] = "listening"
    add_message(session["session_id"], "assistant", greeting, {"type": "greeting"})
    return {
        "session_id": session["session_id"],
        "text": greeting,
        "language": lang,
        "step": "listening",
        "profile_completeness": 0,
        "profile": {},
    }


def _next_question(profile: dict, lang: str) -> Optional[str]:
    missing = missing_fields(profile)
    if not missing:
        return None
    field = missing[0]
    q = FOLLOWUP_QUESTIONS.get(field)
    return q[1] if lang == "Tamil" else q[0] if q else None


def _is_greeting_only(text: str) -> bool:
    t = text.strip()
    return bool(GREETINGS.match(t)) and len(t.split()) <= 6


def _wants_recommendation(text: str, intent: str) -> bool:
    q = text.lower()
    if intent in ("general_agriculture", "crop_status"):
        if any(w in q for w in ("what to plant", "what crop", "best crop", "profit", "demand", "enna payir", "enna plant")):
            return True
    if any(w in q for w in ("what should i plant", "best vegetable", "high profit", "demand", "market demand", "future demand")):
        return True
    return intent == "market_query"


def process_guest_message(session_id: str, user_text: str) -> dict[str, Any]:
    session = get_session(session_id)
    if not session:
        started = start_session()
        return process_guest_message(started["session_id"], user_text)

    lang = _lang(session)
    add_message(session_id, "user", user_text)

    # Greeting-only turn
    if _is_greeting_only(user_text) and not session.get("profile"):
        reply = _pick(
            lang,
            "Hello! How can I help you with your farm today? Tell me your crop or ask any farming question.",
            "வணக்கம்! இன்னைக்கு enna help venum? Crop sollen or farming doubt kelunga.",
        )
        add_message(session_id, "assistant", reply)
        return _response(session, reply, step="listening")

    # Extract farm details from natural speech
    speech = extract_farmer_speech(user_text)
    patch = speech_to_profile_patch(speech)
    if not patch and speech.get("profile_updates"):
        patch = speech.get("profile_updates", {})

    # Map soil_type → soil_texture for session
    if patch.get("soil") and isinstance(patch["soil"], dict):
        patch["soil_texture"] = patch["soil"].get("soil_type")
    if patch.get("soil_type"):
        patch["soil_texture"] = patch["soil_type"]

    if patch:
        session = update_profile(session_id, patch) or session

    profile = session.get("profile", {})
    completeness = profile_completeness(profile)

    parsed = process_voice_query(user_text, "GUEST", None, language_preference=lang)
    intent = parsed["intent"]
    session["last_intent"] = intent

    # Build context from session + weather
    ctx = session_to_context(session)
    ctx = enrich_context_with_openmeteo(ctx)

    # Special: crop recommendation / demand
    if _wants_recommendation(user_text, intent):
        en, ta, evidence, conf = format_crop_recommendations(
            profile.get("land_type", "Wetland"),
            profile.get("district"),
            profile.get("irrigation_source"),
            lang,
        )
        if "demand" in user_text.lower() or "profit" in user_text.lower():
            den, dta, dev, _ = format_demand_forecast(profile.get("crop"), lang)
            en = f"{en} {den}"
            ta = f"{ta} {dta}"
        reply = _pick(lang, en, ta)
        add_message(session_id, "assistant", reply, {"intent": "crop_recommendation"})
        return _response(session, reply, intent="crop_recommendation", evidence=evidence, completeness=completeness)

    # Daily / weekly / monthly / yearly farm report
    from app.services.farm_reports import build_farm_report, detect_report_period
    report_period = detect_report_period(user_text)
    if report_period or any(w in user_text.lower() for w in ("report", "briefing", "அறிக்கை", "farm report")):
        period = report_period or "daily"
        report = build_farm_report(ctx, period=period, language=lang)
        reply = report["text"]
        add_message(session_id, "assistant", reply, {"type": "farm_report", "period": period})
        return _response(session, reply, intent="farm_report", evidence=report.get("evidence", {}), completeness=completeness)

    # Daily briefing request (legacy phrasing)
    if any(w in user_text.lower() for w in ("daily report", "today report", "briefing", "daily update", "innikki report")):
        briefing = build_daily_briefing(ctx, lang, is_guest=True)
        reply = briefing["text"]
        add_message(session_id, "assistant", reply, {"type": "daily_briefing"})
        return _response(session, reply, intent="daily_briefing", evidence=briefing.get("evidence", {}), completeness=completeness)

    # Agent-driven answer for guest (multi-turn + tools + RAG)
    agent_result = run_voice_agent(
        user_text,
        ctx,
        guest_session_id=session_id,
        language_preference=lang,
        is_guest=True,
    )
    adv = agent_result["advisory"]
    reply = adv.tamil_response if lang == "Tamil" else (adv.english_response or adv.recommendation)
    next_q = _next_question(profile, lang)
    if next_q and completeness < 0.7:
        reply = f"{reply} {_pick(lang, 'To give even better advice:', 'Better advice-ku:')} {next_q}"
    add_message(session_id, "assistant", reply, {"intent": agent_result["intent"], "agent_mode": True})
    return _response(
        session, reply,
        intent=agent_result["intent"],
        evidence=adv.evidence,
        advisory=adv,
        completeness=completeness,
    )


def _response(
    session: dict,
    text: str,
    intent: str = "general_agriculture",
    evidence: Optional[dict] = None,
    advisory: Optional[AdvisoryOut] = None,
    completeness: Optional[float] = None,
) -> dict[str, Any]:
    prof = session.get("profile", {})
    comp = completeness if completeness is not None else profile_completeness(prof)
    next_q = _next_question(prof, _lang(session))

    result: dict[str, Any] = {
        "session_id": session["session_id"],
        "text": text,
        "language": _lang(session),
        "step": "ready" if comp >= 0.7 else "collecting",
        "profile_completeness": comp,
        "profile": prof,
        "intent": intent,
        "next_question": next_q,
        "turn_count": session.get("turn_count", 0),
    }
    if evidence:
        result["evidence"] = evidence
    if advisory:
        result["advisory"] = advisory
    return result

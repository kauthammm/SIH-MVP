"""Voice agent orchestrator — full NLP pipeline for Tamil/Tanglish farming queries."""
from __future__ import annotations

from typing import Any, Optional

from app.models.schemas import AdvisoryOut
from app.services.advisory_engine import generate_advisory, _resolve_crop, _location_label
from app.services.agent_tools import run_tools
from app.services.confidence import (
    aggregate_confidence,
    clarification_prompt,
    confidence_band,
    needs_clarification,
)
from app.services.dialogue_state import (
    add_turn,
    load_dialogue,
    pending_slots,
    save_dialogue,
    session_id_for_farmer,
    session_id_for_guest,
    session_id_for_conversation,
    update_from_speech,
)
from app.services.advisory_search import (
    format_advisory_answer,
    search_advisory_dataset,
    search_advisory_tasks,
    STRONG_SCORE,
    MIN_SCORE,
)
from app.services.dynamic_advisory import compose_dynamic_answer
from app.services.farmer_speech import extract_farmer_speech, speech_to_profile_patch
from app.services.task_decomposer import decompose_tasks
from app.services.tanglish_normalize import expand_references, normalize_tanglish
from app.services.language_utils import detect_language
from app.services.voice_intent import detect_intent, extract_entities, process_voice_query
from app.services.prediction_engine import ML_INTENTS, run_ml_prediction
from app.services.general_faq import clarify_vague_query, is_low_quality_answer, match_general_faq, weak_match_clarification
from app.services.intent_resolver import resolve_tasks
from app.services.routing_audit import log_routing_event


def _reason_for_sources(
    ml_predictions: list,
    faq_used: bool,
    convo_used: bool,
    dynamic_used: bool,
    web_used: bool = False,
    canonical_used: bool = False,
) -> str:
    if ml_predictions:
        return "ML prediction on your farm soil, weather, and market data."
    if web_used:
        return "Web search from trusted agriculture sources (Tavily)."
    if canonical_used:
        return "Canonical Tamil Nadu farming Q&A (verified crop/soil/irrigation guidance)."
    if faq_used:
        return "Curated Tamil Nadu farming FAQ (loans, livestock, general guidance)."
    if convo_used:
        return "Matched from farmer advisory knowledge base."
    if dynamic_used:
        return "Personalized advice from your farm profile and crop reference."
    return "General agricultural guidance."


WEB_FIRST_INTENTS = frozenset({
    "general_agriculture",
    "livestock_query",
    "schemes_query",
    "crop_recommendation",
    "disease_risk",
    "pest_risk",
})

def _merge_entities(*parts: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for p in parts:
        for k, v in (p or {}).items():
            if v is not None and v != "":
                out[k] = v
    return out


def _ensure_weather_context(ctx: dict[str, Any], intent: str) -> dict[str, Any]:
    """Load Open-Meteo data for weather intents (guest default: Thanjavur)."""
    from app.services.openmeteo_weather import enrich_context_with_openmeteo
    from app.services.weather_alerts import build_guest_weather_context

    if intent not in ("weather_query", "tomorrow_weather", "rainfall_prediction"):
        return ctx or {}

    base = dict(ctx) if ctx else {}
    if not base.get("parcel"):
        base = build_guest_weather_context()
    return enrich_context_with_openmeteo(base) or base


def _synthesize_weather(tool: dict[str, Any], lang: str) -> tuple[str, str]:
    d = tool.get("data") or {}
    rain = d.get("rain_probability")
    temp = d.get("temperature")
    humidity = d.get("humidity")
    forecast_mm = d.get("forecast_mm")
    today_rain = d.get("today_rain_mm")
    time_ref = d.get("time_ref", "today")
    location = d.get("location") or "your area"
    when_ta = "நாளைக்கு" if time_ref == "tomorrow" else "இன்னைக்கு"
    when_en = "Tomorrow" if time_ref == "tomorrow" else "Today"

    parts_en: list[str] = [f"{when_en} in {location}"]
    parts_ta: list[str] = [f"{when_ta} {location}-la"]

    if temp is not None:
        parts_en.append(f"temperature around {float(temp):.0f}°C")
        parts_ta.append(f"temperature {float(temp):.0f} degree")
    if humidity is not None:
        parts_en.append(f"humidity {float(humidity):.0f}%")
        parts_ta.append(f"humidity {float(humidity):.0f}%")
    if time_ref == "today" and today_rain is not None:
        parts_en.append(f"rain so far {float(today_rain):.1f} mm")
        parts_ta.append(f"ippove mazhai {float(today_rain):.1f} mm")
    if forecast_mm is not None and float(forecast_mm) >= 1:
        parts_en.append(f"~{float(forecast_mm):.0f} mm rain expected")
        parts_ta.append(f"~{float(forecast_mm):.0f} mm mazhai expect pannalam")
    elif rain is not None:
        parts_en.append(f"rain chance {float(rain):.0f}%")
        parts_ta.append(f"mazhai chance {float(rain):.0f}%")

    if len(parts_en) <= 1:
        parts_en.append("live weather from Open-Meteo")
        parts_ta.append("Open-Meteo live weather ready")

    en = ". ".join(parts_en) + "."
    ta = ". ".join(parts_ta) + "."

    if forecast_mm is not None and float(forecast_mm) >= 8:
        en += " Skip extra irrigation and watch for disease."
        ta += " Extra thanneer avoid pannunga, noi paathu irunga."
    elif forecast_mm is not None and float(forecast_mm) <= 1 and time_ref == "today":
        en += " Dry day — plan irrigation if field is dry."
        ta += " Mazhai kammi — vayil dry-aa irundha thanneer plan pannunga."

    return en, ta


def _synthesize_irrigation(tool: dict[str, Any], lang: str) -> tuple[str, str]:
    from app.services.advisory_reference import format_irrigation_response
    from app.services.soil_practice_lookup import format_irrigation_guidance
    pred = tool.get("data", {}).get("prediction")
    guidance = tool.get("data", {}).get("guidance") or {}
    practice = tool.get("data", {}).get("practice") or {}
    crop = tool.get("data", {}).get("crop") or guidance.get("crop") or "crop"
    if practice:
        practice_en = dict(practice)
        if lang == "English" and crop:
            practice_en["crop"] = crop
        en, ta = format_irrigation_guidance(practice_en, lang)
        if pred and hasattr(pred, "irrigation_required"):
            if not pred.irrigation_required:
                if lang == "English":
                    en = f"No irrigation needed today. {pred.reason or ''} {en}".strip()
                    ta = f"Innikki thanneer vendaam. {pred.reason or ''} {ta}".strip()
                else:
                    ta = f"Innikki thanneer vendaam. {pred.reason or ''} {ta}".strip()
                    en = en
            elif pred.irrigation_required:
                if lang == "English":
                    en = f"Irrigation recommended — {pred.urgency} urgency. {en}".strip()
                ta = f"Thanneer pottanum — {pred.urgency} urgency. {ta}".strip()
        return en.strip(), ta.strip()
    if guidance and (guidance.get("water_mm_per_irrigation") or guidance.get("water_mm")):
        water = guidance.get("water_mm_per_irrigation") or guidance.get("water_mm")
        interval = guidance.get("interval_days", 5)
        stage = guidance.get("growth_stage", "Nursery")
        method_en = guidance.get("method_en", "")
        method_ta = guidance.get("method_ta", method_en)
        en = (
            f"For {crop} ({stage}): irrigate every {interval} days, "
            f"about {water} mm each time (~{guidance.get('times_per_week', 1)}x/week). {method_en}"
        )
        ta = (
            f"{crop} ({stage}): {interval} naal ku oru murai {water} mm thanneer "
            f"(week-la ~{guidance.get('times_per_week', 1)} murai). {method_ta}"
        )
        return en.strip(), ta.strip()
    if pred and hasattr(pred, "irrigation_required"):
        if pred.irrigation_required:
            en = f"Irrigation recommended — urgency {pred.urgency}. {pred.reason or ''}"
            ta = f"Thanneer pottanum — {pred.urgency} urgency. {pred.reason or ''}"
        else:
            en = f"No irrigation needed today. {pred.reason or ''}"
            ta = f"Innikki thanneer vendaam. {pred.reason or ''}"
        if guidance:
            en += f" Guide: {guidance.get('water_mm', '')} mm every {guidance.get('interval_days', '')} days."
            ta += f" Reference: {guidance.get('interval_days', '')} naal ku {guidance.get('water_mm', '')} mm."
        return en.strip(), ta.strip()
    if guidance:
        en = f"Typical irrigation: {guidance.get('water_mm')} mm every {guidance.get('interval_days')} days."
        ta = f"Usually {guidance.get('interval_days')} naal ku {guidance.get('water_mm')} mm thanneer."
        return en, ta
    return "Check soil moisture before irrigating.", "Mann erpadu paathu thanneer pottunga."


def _synthesize_fertilizer(tool: dict[str, Any], lang: str) -> tuple[str, str]:
    from app.services.soil_practice_lookup import format_fertilizer_guidance
    g = tool.get("data", {}).get("guidance") or {}
    practice = tool.get("data", {}).get("practice") or {}
    crop = tool.get("data", {}).get("crop") or "crop"
    if practice:
        return format_fertilizer_guidance(practice, lang, crop=str(crop or ""))
    if g:
        en = f"For {crop}: {g.get('product_en', 'fertilizer')} — N {g.get('n_kg_ha', 0)} kg/ha."
        ta = f"{crop}-ku: {g.get('product_ta', g.get('product_en', 'uram'))} — N {g.get('n_kg_ha', 0)} kg/ha."
        return en, ta
    return f"Share crop and growth stage for exact fertilizer advice.", "Exact uram advice-ku crop stage sollunga."


def _synthesize_market(tool: dict[str, Any], lang: str) -> tuple[str, str]:
    d = tool.get("data") or {}
    if d.get("en"):
        return d["en"], d.get("ta", d["en"])
    return "Market demand data loaded from forecast.", "Market demand data ready."


def _synthesize_convo(tool: dict[str, Any], lang: str) -> tuple[str, str]:
    data = tool.get("data") or {}
    en, ta = format_advisory_answer(data, lang=lang)
    if not en and not ta:
        return "", ""
    if lang == "Tamil":
        return en, ta
    return en, en


def _synthesize_rag(tool: dict[str, Any], lang: str) -> tuple[str, str]:
    chunks = tool.get("data", {}).get("chunks") or []
    if not chunks:
        return "I found general farming guidance in our knowledge base.", "Knowledge base-la general advice irukku."
    text = chunks[0].get("text", "")[:400]
    en = f"From agricultural guide: {text}"
    ta = f"Agriculture guide-la: {text[:350]}"
    return en, ta


def _synthesize_task(intent: str, tools: list[dict[str, Any]], lang: str) -> tuple[str, str, dict, float]:
    en_parts: list[str] = []
    ta_parts: list[str] = []
    evidence: dict[str, Any] = {"tools": []}
    confs: list[float] = []

    for t in tools:
        name = t.get("tool")
        confs.append(float(t.get("confidence", 0.5)))
        evidence["tools"].append({"tool": name, "confidence": t.get("confidence")})
        if name == "weather":
            e, a = _synthesize_weather(t, lang)
        elif name == "convo_dataset":
            e, a = _synthesize_convo(t, lang)
            score = float(t.get("data", {}).get("best_score") or 0)
            if e and a and score >= STRONG_SCORE and not is_low_quality_answer(e, t.get("data", {}).get("search_query") or ""):
                en_parts.append(e)
                ta_parts.append(a)
                evidence["tools"].append({"tool": name, "confidence": t.get("confidence"), "source": "convodataset", "score": score})
                confs.append(max(float(t.get("confidence", 0.5)), 0.7 + score * 0.3))
                conf = sum(confs) / len(confs) if confs else 0.75
                return " ".join(en_parts), " ".join(ta_parts), evidence, conf
            continue
        elif name == "irrigation":
            e, a = _synthesize_irrigation(t, lang)
        elif name == "fertilizer":
            e, a = _synthesize_fertilizer(t, lang)
        elif name == "market":
            e, a = _synthesize_market(t, lang)
        elif name == "agricultural_knowledge":
            e, a = _synthesize_rag(t, lang)
        elif name in ("pest", "disease"):
            risks = t.get("data", {}).get("risks") or []
            if risks:
                r = risks[0]
                rt = getattr(r, "risk_type", "risk")
                e = f"{rt} risk: {getattr(r, 'description', 'monitor field')}."
                a = f"{rt} risk — vayil monitor pannunga."
            else:
                e, a = "No major risk flagged right now.", "Ippove major risk illa."
        else:
            continue
        en_parts.append(e)
        ta_parts.append(a)

    if not en_parts:
        return "", "", evidence, 0.4

    conf = sum(confs) / len(confs) if confs else 0.5
    return " ".join(en_parts), " ".join(ta_parts), evidence, conf


def run_voice_agent(
    query_text: str,
    context: Optional[dict[str, Any]],
    *,
    farmer_id: Optional[str] = None,
    parcel_id: Optional[str] = None,
    guest_session_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    language_preference: str = "Auto",
    is_guest: bool = False,
    use_web_search: bool = False,
) -> dict[str, Any]:
    """
    Full agent pipeline:
    normalize → reference expand → decompose → tools → grounded response.
    """
    norm = normalize_tanglish(query_text)
    if conversation_id and user_id:
        session_id = session_id_for_conversation(user_id, conversation_id)
    elif is_guest:
        session_id = session_id_for_guest(guest_session_id)
    else:
        session_id = session_id_for_farmer(farmer_id or "G", parcel_id or "P")
    state = load_dialogue(session_id)

    # Seed dialogue memory from farm profile so we don't re-ask crop/location
    if context:
        obs = context.get("observation")
        prof_crop = None
        prof_stage = None
        if obs:
            prof_crop = getattr(obs, "crop", None) if hasattr(obs, "crop") else None
            prof_stage = getattr(obs, "growth_stage", None) if hasattr(obs, "growth_stage") else None
            if isinstance(obs, dict):
                prof_crop = obs.get("crop") or prof_crop
                prof_stage = obs.get("growth_stage") or prof_stage
        farm = state.setdefault("farm", {})
        if prof_crop and not farm.get("crop"):
            farm["crop"] = prof_crop
        if prof_stage and not farm.get("growth_stage"):
            farm["growth_stage"] = prof_stage
        if context.get("district") and not farm.get("district"):
            farm["district"] = context.get("district")
        if context.get("village") and not farm.get("village"):
            farm["village"] = context.get("village")

    expanded = expand_references(norm["normalized"], state)
    if norm.get("time_reference"):
        time_ent = {"time": norm["time_reference"]}
    else:
        time_ent = {}

    farmer_speech = extract_farmer_speech(expanded)
    base_entities = extract_entities(expanded)
    entities = _merge_entities(base_entities, time_ent, state.get("farm", {}), farmer_speech)

    state = update_from_speech(state, farmer_speech, entities)
    add_turn(state, "user", query_text, {"normalized": expanded, "entities": entities})

    tasks = decompose_tasks(expanded)
    lang = detect_language(expanded, language_preference)

    has_farm = bool(
        context
        and (
            context.get("observation")
            or context.get("soil")
            or context.get("parcel_id")
            or context.get("profile_customized")
        )
    )
    tasks, intent_resolution = resolve_tasks(tasks, has_farm_context=has_farm)

    vague = clarify_vague_query(expanded, lang)
    if vague:
        add_turn(state, "assistant", vague, {"type": "clarification"})
        save_dialogue(state)
        adv = AdvisoryOut(
            recommendation=vague,
            reason="Need more detail to answer safely.",
            evidence={"clarification": True, "intent_resolution": intent_resolution},
            confidence=0.55,
            action_time="Today",
            risk_level="low",
            tamil_response=vague if lang == "Tamil" else None,
            english_response=vague if lang != "Tamil" else vague,
        )
        return {
            "intent": tasks[0]["intent"] if tasks else "general_agriculture",
            "entities": entities,
            "advisory": adv,
            "detected_language": lang,
            "normalized_query": expanded,
            "nlp_confidence": 0.55,
            "farmer_speech": farmer_speech,
            "tasks": tasks,
            "agent_mode": True,
            "confidence_band": "medium",
        }

    # Only block for crop question when there is truly no farm profile at all
    missing = pending_slots(state, context)
    primary_intent = tasks[0]["intent"] if tasks else "general_agriculture"

    intents_needing_crop = {"irrigation_query", "fertilizer_query", "yield_prediction"}
    if primary_intent in intents_needing_crop and "crop" in missing and not context:
        prompt = clarification_prompt(["crop"], lang)
        add_turn(state, "assistant", prompt, {"type": "clarification"})
        save_dialogue(state)
        adv = AdvisoryOut(
            recommendation=prompt,
            reason="Missing crop information.",
            evidence={"missing_slots": missing},
            confidence=0.45,
            action_time="Today",
            risk_level="low",
            tamil_response=prompt if lang == "Tamil" else None,
            english_response=prompt if lang == "English" else prompt,
        )
        return {
            "intent": primary_intent,
            "entities": entities,
            "advisory": adv,
            "detected_language": lang,
            "normalized_query": expanded,
            "nlp_confidence": 0.45,
            "farmer_speech": farmer_speech,
            "tasks": tasks,
            "agent_mode": True,
            "confidence_band": "clarify",
        }

    # Guest without full context — use speech + RAG tools only
    ctx = context or {}
    if ctx and (entities.get("crop") or entities.get("growth_stage")):
        obs = ctx.get("observation")
        if obs and hasattr(obs, "__dict__"):
            if entities.get("crop"):
                obs.__dict__["crop"] = entities["crop"]
            if entities.get("growth_stage"):
                obs.__dict__["growth_stage"] = entities["growth_stage"]
        elif entities.get("crop"):
            class _Row:
                def __init__(self, d):
                    self.__dict__.update(d)
            ctx["observation"] = _Row({
                "crop": entities.get("crop"),
                "growth_stage": entities.get("growth_stage") or "Tillering",
            })

    all_en: list[str] = []
    all_ta: list[str] = []
    combined_evidence: dict[str, Any] = {"tasks": [], "intent_resolution": intent_resolution}
    tool_confs: list[float] = []
    primary = tasks[0]["intent"] if tasks else "general_agriculture"
    routing_branch = "pending"
    branch_scores: dict[str, Any] = {}

    convo_hits = search_advisory_tasks(tasks[:4], lang=lang, entities=entities)
    combined_evidence["advisory_dataset"] = convo_hits
    combined_evidence["convo_dataset"] = convo_hits
    combined_evidence["unified_retrieval"] = [
        {"sub_query": h.get("sub_query"), "all_sources": h.get("all_sources"), "winner": h.get("winning_source")}
        for h in convo_hits
    ]
    if convo_hits:
        branch_scores["rag_best"] = convo_hits[0].get("best_score")
        branch_scores["rag_winner"] = convo_hits[0].get("winning_source")
        branch_scores["rag_all_sources"] = convo_hits[0].get("all_sources")
        branch_scores["rag_strong_threshold"] = STRONG_SCORE
        branch_scores["rag_min_threshold"] = MIN_SCORE

    TOOLS_FIRST = frozenset({
        "irrigation_query", "fertilizer_query", "weather_query",
        "rainfall_prediction", "tomorrow_weather", "market_query",
    })

    ml_predictions: list[dict[str, Any]] = []
    faq_used = False
    canonical_used = False
    convo_used = False
    web_used = False
    for idx, task in enumerate(tasks[:4]):
        intent = task["intent"]
        sub_entities = _merge_entities(entities, task.get("entities") or {})
        sub_entities["detected_language"] = lang
        sub_q = task["sub_query"]
        hit_score = float(convo_hits[idx].get("best_score", 0) if idx < len(convo_hits) else 0)
        branch_scores[f"task_{idx}_rag_score"] = hit_score
        if idx < len(convo_hits):
            branch_scores[f"task_{idx}_rag_winner"] = convo_hits[idx].get("winning_source")
            branch_scores[f"task_{idx}_rag_all_sources"] = convo_hits[idx].get("all_sources")

        # --- Logged-in farm: ML + live tools BEFORE FAQ/RAG ---
        if has_farm and intent in ML_INTENTS:
            ml = run_ml_prediction(intent, ctx, sub_entities, lang=lang)
            if ml and ml.get("english"):
                routing_branch = "ml_prediction"
                ml_predictions.append(ml)
                en, ta = ml["english"], ml["tamil"]
                if len(tasks) > 1:
                    en, ta = f"({idx + 1}) {en}", f"({idx + 1}) {ta}"
                all_en.append(en)
                all_ta.append(ta)
                combined_evidence["tasks"].append({
                    "intent": intent, "sub_query": sub_q, "source": "ml_prediction",
                    **ml.get("evidence", {}),
                })
                tool_confs.append(float(ml.get("confidence", 0.8)))
                continue

        if intent in TOOLS_FIRST:
            from app.services.live_query_router import should_skip_answer_quality_check

            sub_ctx = ctx if ctx else {}
            if intent in ("weather_query", "tomorrow_weather", "rainfall_prediction"):
                sub_ctx = _ensure_weather_context(sub_ctx, intent)
            elif not sub_ctx:
                sub_ctx = {}
            tools = run_tools(intent, sub_ctx, sub_entities, sub_q)
            primary_name = {
                "irrigation_query": "irrigation",
                "fertilizer_query": "fertilizer",
                "weather_query": "weather",
                "tomorrow_weather": "weather",
                "rainfall_prediction": "weather",
                "market_query": "market",
            }.get(intent)
            synth_tools = tools
            if primary_name:
                primary_tool = next((t for t in tools if t.get("tool") == primary_name), None)
                if primary_tool:
                    synth_tools = [primary_tool]
            en, ta, ev, tc = _synthesize_task(intent, synth_tools, lang)
            skip_qc = should_skip_answer_quality_check(intent)
            if en and (skip_qc or not is_low_quality_answer(en, sub_q)):
                routing_branch = f"tools:{intent}"
                if len(tasks) > 1:
                    en, ta = f"({idx + 1}) {en}", f"({idx + 1}) {ta}"
                all_en.append(en)
                all_ta.append(ta)
                combined_evidence["tasks"].append({"intent": intent, "sub_query": sub_q, **ev, "weather_source": sub_ctx.get("weather_source")})
                tool_confs.append(tc)
                continue

        if use_web_search and intent in WEB_FIRST_INTENTS:
            from app.services.tavily_search import is_enabled as tavily_on, synthesize_web_answer
            if tavily_on():
                web = synthesize_web_answer(sub_q, ctx=ctx, lang=lang)
                if web and web.get("english"):
                    routing_branch = "tavily_web"
                    web_used = True
                    en, ta = web["english"], web["tamil"]
                    if len(tasks) > 1:
                        en, ta = f"({idx + 1}) {en}", f"({idx + 1}) {ta}"
                    all_en.append(en)
                    all_ta.append(ta)
                    combined_evidence["tasks"].append({
                        "intent": intent, "sub_query": sub_q, "source": "tavily_web",
                        **web.get("evidence", {}),
                    })
                    tool_confs.append(float(web.get("confidence", 0.8)))
                    continue

        if not use_web_search:
            faq = match_general_faq(sub_q, lang)
            if faq:
                routing_branch = "general_faq"
                faq_used = True
                en, ta = faq["english"], faq["tamil"]
                if len(tasks) > 1:
                    en, ta = f"({idx + 1}) {en}", f"({idx + 1}) {ta}"
                all_en.append(en)
                all_ta.append(ta)
                combined_evidence["tasks"].append({
                    "intent": intent, "sub_query": sub_q, "source": "general_faq", "faq_id": faq["id"],
                })
                tool_confs.append(float(faq.get("confidence", 0.88)))
                continue

        # Strong match from unified search across all datasets (tamil_decision, slang, tamil_ds, canonical, convo)
        unified_hit = convo_hits[idx] if idx < len(convo_hits) else {}
        win_source = unified_hit.get("winning_source") or unified_hit.get("source", "")
        branch_scores[f"task_{idx}_canonical_score"] = (unified_hit.get("all_sources") or {}).get("canonical_qa", 0)

        if hit_score >= STRONG_SCORE and intent not in ML_INTENTS and not (has_farm and intent in TOOLS_FIRST):
            en, ta = format_advisory_answer(unified_hit, lang=lang, task_index=idx, total_tasks=len(tasks))
            if en and not is_low_quality_answer(en, sub_q):
                routing_branch = f"rag_strong:{win_source}"
                convo_used = True
                if win_source == "canonical_qa":
                    canonical_used = True
                if len(tasks) > 1:
                    en, ta = f"({idx + 1}) {en}", f"({idx + 1}) {ta}"
                all_en.append(en)
                all_ta.append(ta)
                combined_evidence["tasks"].append({
                    "intent": intent,
                    "sub_query": sub_q,
                    "source": win_source,
                    "score": hit_score,
                    "all_sources": unified_hit.get("all_sources"),
                    "best_question": unified_hit.get("best_question"),
                })
                tool_confs.append(float(unified_hit.get("confidence", 0.85)))
                continue

        # Below threshold: web (if enabled) or clarification — NOT weak RAG
        if use_web_search:
            from app.services.tavily_search import is_enabled as tavily_on, synthesize_web_answer
            if tavily_on():
                web = synthesize_web_answer(sub_q, ctx=ctx, lang=lang)
                if web and web.get("english"):
                    routing_branch = "tavily_web_fallback"
                    web_used = True
                    all_en.append(web["english"])
                    all_ta.append(web["tamil"])
                    combined_evidence["tasks"].append({
                        "intent": intent, "sub_query": sub_q, "source": "tavily_web",
                        "trigger": "weak_rag_refused", "rag_score": hit_score,
                        **web.get("evidence", {}),
                    })
                    tool_confs.append(float(web.get("confidence", 0.72)))
                    continue

        clarify = weak_match_clarification(lang)
        routing_branch = "clarification_weak_match"
        branch_scores["refused_rag_score"] = hit_score
        all_en.append(clarify)
        all_ta.append(clarify)
        combined_evidence["tasks"].append({
            "intent": intent, "sub_query": sub_q, "source": "clarification",
            "rag_score": hit_score, "rag_refused": True,
        })
        tool_confs.append(0.45)

    if use_web_search and not web_used and not all_en:
        from app.services.tavily_search import is_enabled as tavily_on, synthesize_web_answer
        if tavily_on():
            web = synthesize_web_answer(expanded, ctx=ctx, lang=lang)
            if web and web.get("english"):
                web_used = True
                all_en.append(web["english"])
                all_ta.append(web["tamil"])
                combined_evidence["tasks"].append({
                    "intent": primary,
                    "sub_query": expanded,
                    "source": "tavily_web",
                    **web.get("evidence", {}),
                })
                tool_confs.append(float(web.get("confidence", 0.78)))

    intent_conf = tasks[0]["confidence"] if tasks else 0.5
    final_conf = aggregate_confidence({
        "asr": 0.85,
        "intent": intent_conf,
        "entity": 0.75 if entities else 0.4,
        "context": 0.8 if ctx else 0.35,
        "retrieval": tool_confs[-1] if tool_confs else 0.4,
        "tool": sum(tool_confs) / len(tool_confs) if tool_confs else 0.4,
    })

    # Fallback to existing advisory engine for rich logged-in answers
    query_meta = {
        "entities": entities,
        "farmer_speech": farmer_speech,
        "normalized_query": expanded,
        "tasks": tasks,
    }
    dynamic = None
    dynamic_used = False
    if ctx:
        dynamic = compose_dynamic_answer(ctx, query_meta, primary)
        # ML predictions take priority over static dataset text
        if ml_predictions:
            dynamic = None

    if all_en:
        en_text = " ".join(all_en)
        ta_text = " ".join(all_ta)
        if len(tasks) > 1:
            prefix_ta = f"{len(tasks)} kelvigal-ku answer: "
            prefix_en = f"Answers for {len(tasks)} questions: "
            en_text = prefix_en + en_text
            ta_text = prefix_ta + ta_text
        adv = AdvisoryOut(
            recommendation=ta_text if lang == "Tamil" else en_text,
            reason=_reason_for_sources(ml_predictions, faq_used, convo_used, dynamic_used, web_used, canonical_used),
            evidence=combined_evidence,
            confidence=final_conf,
            action_time="Today",
            risk_level="low",
            tamil_response=ta_text,
            english_response=en_text,
        )
    elif dynamic:
        dynamic_used = True
        en_text, ta_text, ev, conf, reason = dynamic
        combined_evidence.update(ev)
        final_conf = max(final_conf, conf)
        adv = AdvisoryOut(
            recommendation=ta_text if lang == "Tamil" else en_text,
            reason=reason,
            evidence=combined_evidence,
            confidence=final_conf,
            action_time="Today",
            risk_level="low",
            tamil_response=ta_text,
            english_response=en_text,
        )
        extra_en, extra_ta = [], []
        for task in tasks[1:4]:
            if task["intent"] == primary:
                continue
            sub_entities = _merge_entities(entities, task.get("entities") or {})
            tools = run_tools(task["intent"], ctx, sub_entities, task["sub_query"])
            e, t, ev2, _ = _synthesize_task(task["intent"], tools, lang)
            if e:
                extra_en.append(e)
                extra_ta.append(t)
                combined_evidence.setdefault("extra_tasks", []).append(ev2)
        if extra_en:
            adv.english_response = adv.english_response + " " + " ".join(extra_en)
            adv.tamil_response = adv.tamil_response + " " + " ".join(extra_ta)
            adv.recommendation = adv.tamil_response if lang == "Tamil" else adv.english_response
    elif ctx:
        adv = generate_advisory(ctx, primary, query_meta=query_meta)
        final_conf = max(final_conf, adv.confidence or 0.7)
        combined_evidence["fallback"] = "advisory_engine"
    else:
        convo = search_advisory_tasks([{"sub_query": expanded, "intent": primary}], lang=lang)
        best = convo[0].get("best_score", 0) if convo else 0
        branch_scores["guest_rag_score"] = best
        guest_adv = None
        if convo and best >= STRONG_SCORE:
            en, ta = format_advisory_answer(convo[0], lang=lang)
            if en and not is_low_quality_answer(en, expanded):
                routing_branch = "rag_strong_guest"
                guest_adv = AdvisoryOut(
                    recommendation=ta if lang == "Tamil" else en,
                    reason="Farmer advisory dataset match.",
                    evidence={"convo_dataset": convo[0], "intent_resolution": intent_resolution},
                    confidence=convo[0].get("confidence", 0.75),
                    action_time="Today",
                    risk_level="low",
                    tamil_response=ta,
                    english_response=en,
                )
                final_conf = guest_adv.confidence or 0.75
        if guest_adv is None:
            routing_branch = "clarification_guest"
            fallback = weak_match_clarification(lang)
            guest_adv = AdvisoryOut(
                recommendation=fallback,
                reason="No reliable match — clarification requested.",
                evidence={**combined_evidence, "rag_refused_score": best},
                confidence=0.4,
                action_time="Today",
                risk_level="low",
                tamil_response=fallback,
                english_response=fallback,
            )
        adv = guest_adv

    missing = pending_slots(state, ctx)
    band = confidence_band(final_conf)
    has_answer = bool(
        all_en
        or dynamic
        or (adv.recommendation and len(adv.recommendation or "") > 30)
    )

    # OpenRouter polish — skip for ML, FAQ, and web search (keep exact facts)
    skip_polish = bool(ml_predictions) or faq_used or canonical_used or web_used or any(
        t.get("source") in ("ml_prediction", "tavily_web") for t in combined_evidence.get("tasks", [])
    )
    if has_answer and adv and not skip_polish:
        try:
            from app.services.openrouter_client import polish_advisory, is_enabled as or_enabled
            if or_enabled():
                farm_ctx: dict[str, Any] = dict(state.get("farm") or {})
                if ctx:
                    parcel = ctx.get("parcel")
                    if parcel:
                        pd_ = parcel.__dict__ if hasattr(parcel, "__dict__") else dict(parcel)
                        farm_ctx.setdefault("district", pd_.get("district"))
                        farm_ctx.setdefault("village", pd_.get("village"))
                    soil = ctx.get("soil")
                    if soil:
                        sd = soil.__dict__ if hasattr(soil, "__dict__") else dict(soil)
                        farm_ctx.setdefault("pH", sd.get("ph") or sd.get("pH"))
                    obs = ctx.get("observation")
                    if obs:
                        od = obs.__dict__ if hasattr(obs, "__dict__") else dict(obs)
                        farm_ctx.setdefault("crop", od.get("crop"))
                en_p, ta_p = polish_advisory(
                    query=query_text,
                    en_draft=adv.english_response or adv.recommendation or "",
                    ta_draft=adv.tamil_response or adv.recommendation or "",
                    lang=lang,
                    farm_context=farm_ctx,
                    evidence=combined_evidence,
                )
                if en_p and ta_p and not is_low_quality_answer(en_p, query_text):
                    adv.english_response = en_p.strip()
                    adv.tamil_response = ta_p.strip()
                    adv.recommendation = adv.tamil_response if lang == "Tamil" else adv.english_response
                    combined_evidence["openrouter_polish"] = True
        except Exception:
            pass

    # Never replace a real answer with "please share more details"
    if needs_clarification(final_conf, missing, has_answer=has_answer) and not has_answer:
        prompt = clarification_prompt(missing, lang)
        adv.recommendation = prompt
        if lang == "Tamil":
            adv.tamil_response = prompt
        else:
            adv.english_response = prompt

    from app.services.tamil_humanize import humanize_english_response, humanize_tamil_response
    if adv.tamil_response:
        adv.tamil_response = humanize_tamil_response(adv.tamil_response)
    if adv.english_response:
        adv.english_response = humanize_english_response(adv.english_response)
    if adv.recommendation and lang == "Tamil" and adv.tamil_response:
        adv.recommendation = adv.tamil_response
    elif adv.recommendation and lang != "Tamil" and adv.english_response:
        adv.recommendation = adv.english_response

    response_text = adv.tamil_response if lang == "Tamil" and adv.tamil_response else (adv.english_response or adv.recommendation)

    combined_evidence["routing_branch"] = routing_branch
    combined_evidence["branch_scores"] = branch_scores
    if adv.evidence:
        adv.evidence = {**(adv.evidence or {}), "routing_branch": routing_branch, "branch_scores": branch_scores}

    log_routing_event(
        query=query_text,
        normalized_query=expanded,
        intent=primary,
        intent_confidence=float(tasks[0]["confidence"] if tasks else 0.5),
        entities=entities,
        tasks=tasks,
        routing_branch=routing_branch,
        branch_scores=branch_scores,
        farmer_id=farmer_id,
        parcel_id=parcel_id,
        use_web_search=use_web_search,
        has_farm_context=has_farm,
        answer_preview=response_text or "",
        reason=adv.reason or "",
    )

    add_turn(state, "assistant", response_text, {"intent": primary, "confidence": final_conf})
    state["conversation"]["last_intent"] = primary
    save_dialogue(state)

    return {
        "intent": primary,
        "entities": entities,
        "advisory": adv,
        "detected_language": lang,
        "normalized_query": expanded,
        "nlp_confidence": final_conf,
        "transcription_confidence": 0.85,
        "farmer_speech": farmer_speech,
        "tasks": tasks,
        "agent_mode": True,
        "confidence_band": band,
        "dialogue_session_id": session_id,
    }


def process_voice_with_agent(
    query_text: str,
    farmer_id: str,
    parcel_id: str,
    language_preference: str = "Auto",
    context: Optional[dict[str, Any]] = None,
    *,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    use_web_search: bool = False,
) -> dict[str, Any]:
    """Drop-in replacement wrapper used by API routes."""
    legacy = process_voice_query(query_text, farmer_id, parcel_id, language_preference=language_preference)
    result = run_voice_agent(
        query_text,
        context,
        farmer_id=farmer_id,
        parcel_id=parcel_id,
        conversation_id=conversation_id,
        user_id=user_id,
        language_preference=language_preference,
        is_guest=False,
        use_web_search=use_web_search,
    )
    result["legacy_intent"] = legacy.get("intent")
    result["confidence"] = result["nlp_confidence"]
    return result

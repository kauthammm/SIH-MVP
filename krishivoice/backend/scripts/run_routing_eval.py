#!/usr/bin/env python3
"""Run routing eval set — shows intent, branch, scores. Usage: python scripts/run_routing_eval.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EVAL_PATH = ROOT / "eval" / "routing_eval.json"


def _branch_from_evidence(evidence: dict) -> str:
    if evidence.get("routing_branch") and evidence.get("routing_branch") != "pending":
        return str(evidence["routing_branch"])
    tasks = evidence.get("tasks") or []
    if not tasks:
        if evidence.get("clarification"):
            return "clarification"
        if evidence.get("fallback"):
            return evidence["fallback"]
        return "unknown"
    src = tasks[0].get("source") or tasks[0].get("tool")
    if src == "ml_prediction":
        return "ml_prediction"
    if src == "general_faq":
        return "general_faq"
    if src == "tavily_web":
        return "tavily_web"
    tools = tasks[0].get("tools") or evidence.get("tools")
    if isinstance(tools, list) and tools:
        return f"tools:{tools[0].get('tool', '?')}"
    return str(src or "composite")


def main() -> None:
    from app.services.agent_orchestrator import run_voice_agent
    from app.services.csv_store import get_parcel_context

    cases = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    ctx = get_parcel_context("P0001")
    passed = 0
    failed = []

    print(f"Running {len(cases)} routing eval cases...\n")

    for case in cases:
        use_ctx = ctx if case.get("has_farm") else None
        farmer_id = "F0001" if case.get("has_farm") else None
        parcel_id = "P0001" if case.get("has_farm") else None

        result = run_voice_agent(
            case["query"],
            use_ctx,
            farmer_id=farmer_id,
            parcel_id=parcel_id,
            language_preference=case.get("lang", "English"),
            is_guest=not case.get("has_farm"),
            use_web_search=bool(case.get("web")),
        )
        adv = result["advisory"]
        evidence = adv.evidence or {}
        branch = _branch_from_evidence(evidence)
        if evidence.get("clarification") or (adv.reason or "").startswith("Need more detail"):
            branch = "clarification"

        intent_ok = result["intent"] == case.get("expect_intent") or case["expect_intent"] in (
            result["intent"], "general_agriculture", "livestock_query", "schemes_query"
        )
        expect = case.get("expect_branch", "")
        branch_ok = (
            branch == expect
            or (expect == "tools_or_ml" and (
                branch.startswith("tools") or branch == "ml_prediction"
            ))
            or (expect == "tools" and branch.startswith("tools"))
            or (expect.startswith("ml") and branch == "ml_prediction")
            or (expect == "clarification" and branch.startswith("clarification"))
            or (expect == "general_faq" and branch == "general_faq")
            or (expect == "tavily_web" and branch.startswith("tavily"))
        )

        ok = intent_ok and branch_ok
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed.append(case["id"])

        scores = {}
        ds = evidence.get("advisory_dataset") or evidence.get("convo_dataset")
        if ds and isinstance(ds, list) and ds:
            scores["rag_best"] = ds[0].get("best_score")

        print(f"[{status}] {case['id']}")
        print(f"  Q: {case['query'][:70]}")
        print(f"  intent: {result['intent']} (expect {case.get('expect_intent')})")
        print(f"  branch: {branch} (expect {expect}) scores={scores}")
        print(f"  reason: {adv.reason}")
        print()

    print(f"Results: {passed}/{len(cases)} passed")
    if failed:
        print("Failed:", ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()

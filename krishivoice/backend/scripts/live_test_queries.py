#!/usr/bin/env python3
"""Live API smoke tests after cleaned-data integration."""
from __future__ import annotations

import json
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8010/api/v1"

TESTS = [
    {
        "name": "ML crop recommendation",
        "path": "/voice/query",
        "body": {
            "query_text": "What crop suits my soil?",
            "farmer_id": "F0001",
            "parcel_id": "P0001",
            "language": "English",
        },
        "expect_branch": ("ml_prediction", "canonical_qa"),
    },
    {
        "name": "Irrigation tools + canonical practice",
        "path": "/voice/query",
        "body": {
            "query_text": "Should I irrigate rice today?",
            "farmer_id": "F0001",
            "parcel_id": "P0001",
            "language": "English",
        },
        "expect_branch": ("tools:", "ml_prediction"),
    },
    {
        "name": "Fertilizer (Tamil)",
        "path": "/voice/query",
        "body": {
            "query_text": "நெலுக்கு உரம் எவ்வளவு?",
            "farmer_id": "F0001",
            "parcel_id": "P0001",
            "language": "Tamil",
        },
        "expect_branch": ("tools:", "canonical_qa", "general_faq"),
    },
    {
        "name": "Canonical Q&A guest",
        "path": "/voice/query-guest",
        "body": {
            "query_text": "Enakku karisal mann soil irukku enna crop choose pannalam?",
            "language": "Tamil",
        },
        "expect_branch": ("canonical_qa", "clarification", "general_faq"),
    },
    {
        "name": "Voice call query",
        "path": "/voice/call/query",
        "body": {
            "query_text": "cotton irrigation advice",
            "farmer_id": "F0001",
            "parcel_id": "P0001",
            "language": "Tamil",
            "guest": False,
        },
        "expect_branch": ("tools:", "canonical_qa", "ml_prediction"),
    },
]


def post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def branch_from(adv: dict) -> str:
    ev = adv.get("evidence") or {}
    if ev.get("routing_branch"):
        return str(ev["routing_branch"])
    tasks = ev.get("tasks") or []
    if tasks:
        src = tasks[0].get("source") or ""
        if src == "ml_prediction":
            return "ml_prediction"
        if src == "canonical_qa":
            return "canonical_qa"
        tools = tasks[0].get("tools") or ev.get("tools") or []
        if isinstance(tools, list) and tools:
            return f"tools:{tools[0].get('tool', '?')}"
        return str(src)
    return "unknown"


def main() -> None:
    print("=== KrishiVoice Live Tests (cleaned data) ===\n")
    health = json.loads(urllib.request.urlopen(f"{BASE}/health", timeout=10).read())
    print(f"Health: {health['status']} | data={health.get('data_source')} | canonical={health.get('canonical_qa', {}).get('rows')}\n")

    passed = 0
    for t in TESTS:
        try:
            out = post(t["path"], t["body"])
            adv = out.get("advisory") or {}
            branch = branch_from(adv)
            text = (adv.get("recommendation") or adv.get("english_response") or "")[:120]
            intent = out.get("intent", "?")
            ok = any(branch.startswith(e) if e.endswith(":") else branch == e for e in t["expect_branch"])
            status = "PASS" if ok else "WARN"
            if ok:
                passed += 1
            print(f"[{status}] {t['name']}")
            print(f"  intent: {intent} | branch: {branch}")
            print(f"  answer: {text}...")
            print()
        except Exception as e:
            print(f"[FAIL] {t['name']}: {e}\n")

    print(f"Results: {passed}/{len(TESTS)} passed (WARN = unexpected branch but answered)")


if __name__ == "__main__":
    main()

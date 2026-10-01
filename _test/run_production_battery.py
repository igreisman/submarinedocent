#!/usr/bin/env python3
"""Run the 99-question golden battery against production and report pass/fail.

Always sends X-SubDocent-Test: 1 so questions do not reach the visitor log.

Usage:
    python3 _test/run_production_battery.py [--base-url URL]

Exits 0 when all accept-list answers are returned; 1 otherwise.
"""
import argparse
import json
import os
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(REPO, "_test", "golden_visitor_questions.jsonl")
# Header required by CLAUDE.md: every production /ask call from a script or test
TEST_HEADER = {"Content-Type": "application/json", "X-SubDocent-Test": "1"}


def ask(base_url: str, question: str) -> str | None:
    body = json.dumps({
        "question_text": question,
        "compartment_id": "",
        "playhead_time_ms": 0,
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/ask", data=body, headers=TEST_HEADER
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()).get("faq_id")
    except Exception as exc:
        return f"ERROR:{exc}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://submarinedocent.org")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    with open(GOLDEN) as fh:
        rows = [json.loads(l) for l in fh if l.strip()]

    passed, failed = [], []
    for row in rows:
        q = row["question"]
        accept = set(row["accept"])
        got = ask(base, q)
        ok = got in accept
        entry = {"q": q, "got": got, "accept": sorted(accept)}
        (passed if ok else failed).append(entry)
        time.sleep(0.15)

    total = len(rows)
    print(f"\n  {len(passed)}/{total} golden questions answered correctly ({base})\n")
    if failed:
        print("  FAILING:")
        for e in failed:
            print(f"    {e['q']!r}")
            print(f"      got:    {e['got']}")
            print(f"      accept: {e['accept']}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

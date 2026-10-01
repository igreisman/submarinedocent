#!/usr/bin/env python3
"""Two tests for ask-log security and seed hygiene.

1. Museum admin credential must not reach GET /admin/ask-log (expect 401).
2. ask_log.jsonl must not appear in a staged corpora/ seed.

Run with:
    python3 _test/test_ask_log_guards.py

The first test needs MUSEUM_ADMIN_USERNAME and MUSEUM_ADMIN_PASSWORD in the
environment (or it is skipped with a warning). The second test is purely local
and needs no network.
"""
import base64
import json
import os
import sys
import urllib.request
import urllib.error

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_URL = os.getenv("SUBDOCENT_BASE_URL", "https://submarinedocent.org").rstrip("/")


def _basic(user: str, pw: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()


def test_museum_cannot_reach_ask_log() -> bool:
    mu = os.getenv("MUSEUM_ADMIN_USERNAME", "").strip()
    mp = os.getenv("MUSEUM_ADMIN_PASSWORD", "").strip()
    if not mu or not mp:
        print("  SKIP museum-credential test: MUSEUM_ADMIN_USERNAME/PASSWORD not set")
        return True
    req = urllib.request.Request(
        f"{BASE_URL}/admin/ask-log",
        headers={"Authorization": _basic(mu, mp)},
    )
    try:
        with urllib.request.urlopen(req) as r:
            print(f"  FAIL museum credential reached /admin/ask-log (HTTP {r.status})")
            return False
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"  OK   museum credential rejected with 401")
            return True
        print(f"  FAIL unexpected HTTP {e.code} from /admin/ask-log")
        return False
    except Exception as e:
        print(f"  FAIL unexpected error: {e}")
        return False


def test_ask_log_not_in_seed() -> bool:
    corpora = os.path.join(REPO, "corpora")
    path = os.path.join(corpora, "ask_log.jsonl")
    if os.path.exists(path):
        print(f"  FAIL ask_log.jsonl found in corpora/: {path}")
        return False
    print("  OK   ask_log.jsonl is not in corpora/")
    return True


def main() -> int:
    results = [
        test_museum_cannot_reach_ask_log(),
        test_ask_log_not_in_seed(),
    ]
    passed = sum(results)
    total = len(results)
    print(f"\n  {passed}/{total} ask-log guard tests passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

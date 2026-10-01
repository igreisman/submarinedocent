#!/usr/bin/env python3
"""Two tests for ask-log security and seed hygiene.

1. Museum admin credential must not reach GET /admin/ask-log (expect 401).
   Runs entirely locally via TestClient with a stand-in credential; never
   skipped, never hits production.
2. ask_log.jsonl must not appear in a staged corpora/ seed.

Run with:
    CONTENT_ROOT=corpora python3 _test/test_ask_log_guards.py
"""
import base64
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def _basic(user: str, pw: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()


def test_museum_cannot_reach_ask_log() -> bool:
    """Museum credential is rejected with 401 on /admin/ask-log.

    Uses TestClient with a stand-in credential injected into the environment
    so the test never requires the real museum password and never hits production.
    """
    # Use credentials that do not match the main admin.
    fake_museum_user = "test-museum-user"
    fake_museum_pass = "test-museum-pass"
    os.environ.setdefault("ADMIN_USERNAME", "real-admin")
    os.environ.setdefault("ADMIN_PASSWORD", "real-admin-pass")
    os.environ["MUSEUM_ADMIN_USERNAME"] = fake_museum_user
    os.environ["MUSEUM_ADMIN_PASSWORD"] = fake_museum_pass

    from starlette.testclient import TestClient
    from api import main as m

    # Force the auth env vars to be read by the module-level variables.
    m.MUSEUM_ADMIN_USERNAME = fake_museum_user
    m.MUSEUM_ADMIN_PASSWORD = fake_museum_pass
    m.ADMIN_USERNAME = os.environ["ADMIN_USERNAME"]
    m.ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

    client = TestClient(m.app, raise_server_exceptions=False)
    resp = client.get(
        "/admin/ask-log",
        headers={"Authorization": _basic(fake_museum_user, fake_museum_pass)},
    )
    if resp.status_code == 401:
        print("  OK   museum credential rejected with 401")
        return True
    print(f"  FAIL /admin/ask-log returned {resp.status_code} for museum credential")
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

#!/usr/bin/env python3
"""A FAQ write must reject a value the corpus does not know.

category, doc_type, era and authority_level each take a fixed vocabulary.
Until 22 September 2026 nothing checked them, and it showed: eleven of the
first twenty USS Cod records named a category that does not exist, always by
dropping the spaces from "U. S.", and every one of the twenty named a
doc_type, authority_level and platform the corpus has never used.

A bad category was the worst of them. _ensure_category_exists() created the
missing category rather than refusing it, so the corpus would have grown a
second near-identical entry, the dashboard would have shown both, the records
would have split between them, and nothing would have said so.

    python3 _test/test_faq_write_validation.py

Runs against a temporary copy of the real corpora. It writes, so it must never
be pointed at corpora/ itself.
"""
import base64
import json
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

failures = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}{('  ' + detail) if not ok else ''}")
    if not ok:
        failures.append(label)


def main():
    root = tempfile.mkdtemp(prefix="writevalidation-")
    corpora = os.path.join(root, "corpora")
    shutil.copytree(os.path.join(REPO, "corpora"), corpora)

    os.environ["CONTENT_ROOT"] = corpora
    os.environ["ADMIN_USERNAME"] = "t"
    os.environ["ADMIN_PASSWORD"] = "t"
    sys.path.insert(0, REPO)
    from api import main as m
    from fastapi.testclient import TestClient

    client = TestClient(m.app)
    auth = {"Authorization": "Basic " + base64.b64encode(b"t:t").decode()}
    base = {"title": "A validation test record", "text": "<p>Body.</p>"}
    categories_before = len(m.CATEGORIES)

    # Rejected, with the allowed values named. These are the exact values that
    # arrived in the Cod batches.
    for label, field, value in [
        ("category typo, spaces dropped from U. S.", "category", "US WW2 Subs in General"),
        ("category typo, Operating", "category", "Operating US Subs in WW2"),
        ("doc_type", "doc_type", "faq"),
        ("authority_level", "authority_level", "reviewed"),
        ("era", "era", "postwar"),
    ]:
        r = client.post("/admin/faq", headers=auth, json={**base, field: value})
        check(f"create rejects {label}", r.status_code == 400, str(r.status_code))
        if r.status_code == 400:
            detail = str(r.json().get("detail", ""))
            check(f"  the error names the field ({field})", field in detail, detail[:70])
            if field == "category":
                check("  the error lists valid categories",
                      "Boat Histories" in detail, detail[:70])

    # A category must never be created as a side effect of a FAQ write.
    check("no category was invented", len(m.CATEGORIES) == categories_before,
          f"{categories_before} -> {len(m.CATEGORIES)}")

    # Accepted.
    r = client.post("/admin/faq", headers=auth, json={**base, "category": "Boat Histories"})
    check("create accepts a known category", r.status_code == 200, str(r.status_code))
    r = client.post("/admin/faq", headers=auth, json={**base, "category": ""})
    check("create accepts an empty category", r.status_code == 200, str(r.status_code))
    r = client.post("/admin/faq", headers=auth, json=base)
    check("create accepts a record with no vocabulary fields", r.status_code == 200,
          str(r.status_code))

    # The update path validates too, and a partial update stays partial.
    target = next(e["chunk_id"] for e in m.FAQ_ALL
                  if str(e.get("chunk_id", "")).startswith("faq_"))
    r = client.put(f"/admin/faq/{target}", headers=auth,
                   json={"category": "Crews Aboard US Subs in WW2"})
    check("update rejects a category typo", r.status_code == 400, str(r.status_code))
    before = next(e for e in m.FAQ_ALL if e["chunk_id"] == target).get("category")
    r = client.put(f"/admin/faq/{target}", headers=auth, json={"category": "Torpedoes"})
    check("update accepts a known category", r.status_code == 200, str(r.status_code))
    r = client.put(f"/admin/faq/{target}", headers=auth, json={"title": "Retitled only"})
    after = next(e for e in m.FAQ_ALL if e["chunk_id"] == target)
    check("a title-only update does not disturb the category",
          after.get("category") == "Torpedoes", repr(after.get("category")))

    shutil.rmtree(root, ignore_errors=True)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

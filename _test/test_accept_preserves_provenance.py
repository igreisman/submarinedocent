#!/usr/bin/env python3
"""accept_faq() must never overwrite `source` without keeping the original.

Promotion rewrites source to accepted_from_<old_id>. If the value it replaces
is not kept, the record stops declaring where its text came from, and a rights
question can only be answered by pattern-matching an id prefix -- which is one
rename away from unanswerable.

That is not hypothetical. The 17 September 2026 removal of material derived
from a museum's tour had to reconstruct lineage from the accepted_from_*
pattern to find the two promoted chunks, which were the only two that could
actually answer a visitor. A filter on `source` alone would have spared exactly
those.

    python3 _test/test_accept_preserves_provenance.py

Needs no server and no network.
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
    root = tempfile.mkdtemp(prefix="accepttest-")
    corpora = os.path.join(root, "corpora")
    shutil.copytree(os.path.join(REPO, "sample_data", "corpora"), corpora)

    drafts = [
        {"chunk_id": "der_900", "doc_type": "dieselsubs_faq", "title": "A generated draft",
         "text": "<p>Body.</p>", "source": "some_museum_tour", "category": "Museums"},
        # No source at all: nothing to preserve, and nothing should be invented.
        {"chunk_id": "der_901", "doc_type": "dieselsubs_faq", "title": "A sourceless draft",
         "text": "<p>Body.</p>", "category": "Museums"},
        # Already carries original_source: an earlier value must not be clobbered.
        {"chunk_id": "der_902", "doc_type": "dieselsubs_faq", "title": "A twice-promoted draft",
         "text": "<p>Body.</p>", "source": "accepted_from_der_1",
         "original_source": "the_true_origin", "category": "Museums"},
    ]
    with open(os.path.join(corpora, "dieselsubs_faq_corpus.jsonl"), "w", encoding="utf-8") as f:
        for d in drafts:
            f.write(json.dumps(d) + "\n")

    os.environ["CONTENT_ROOT"] = corpora
    os.environ["ADMIN_USERNAME"] = "t"
    os.environ["ADMIN_PASSWORD"] = "t"
    sys.path.insert(0, REPO)
    from api import main as m
    from fastapi.testclient import TestClient

    client = TestClient(m.app)
    auth = {"Authorization": "Basic " + base64.b64encode(b"t:t").decode()}

    def accept(cid):
        r = client.post(f"/admin/faq/{cid}/accept", headers=auth)
        if r.status_code != 200:
            return None, r
        new_id = r.json().get("new_id")
        rows = {x["chunk_id"]: x for x in m.FAQ_ALL}
        return rows.get(new_id), r

    got, resp = accept("der_900")
    check("a draft with a source is accepted", got is not None, str(resp.status_code))
    if got:
        check("source is rewritten to accepted_from_*",
              str(got.get("source", "")).startswith("accepted_from_"), repr(got.get("source")))
        check("the original source is preserved",
              got.get("original_source") == "some_museum_tour", repr(got.get("original_source")))
        check("pampanito_specific is not invented",
              "pampanito_specific" not in got, repr(got.get("pampanito_specific")))

    got, _ = accept("der_901")
    if got:
        check("a sourceless draft gains no invented original_source",
              "original_source" not in got, repr(got.get("original_source")))

    got, _ = accept("der_902")
    if got:
        check("an existing original_source is not clobbered",
              got.get("original_source") == "the_true_origin", repr(got.get("original_source")))

    shutil.rmtree(root, ignore_errors=True)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

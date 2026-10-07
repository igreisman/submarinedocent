#!/usr/bin/env python3
"""Phrasings route their wording to their record, and no further.

A phrasing is another wording of a record's question, written by a curator
and never shown to visitors ("what did they do for fun" for "What did they
do for entertainment once they completed qualifications?").  It is scored
like the title, with one guard: a phrasing earns the full title boost only if
the question also covers two thirds of the phrasing's own words.  Without the
guard, "how big is the boat?" searches as "big" alone, and a phrasing "how
big is a torpedo" covered it entirely (6 October 2026).

    python3 _test/test_phrasings.py

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
TEST = {"X-SubDocent-Test": "1"}   # keeps these out of the visitor question log
failures = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}{('  ' + detail) if not ok else ''}")
    if not ok:
        failures.append(label)


def main():
    root = tempfile.mkdtemp(prefix="phrasings-")
    corpora = os.path.join(root, "corpora")
    shutil.copytree(os.path.join(REPO, "corpora"), corpora,
                    ignore=shutil.ignore_patterns("tts_cache"))

    os.environ["CONTENT_ROOT"] = corpora
    os.environ["ADMIN_USERNAME"] = "t"
    os.environ["ADMIN_PASSWORD"] = "t"
    sys.path.insert(0, REPO)
    from api import main as m
    from fastapi.testclient import TestClient

    client = TestClient(m.app)
    auth = {"Authorization": "Basic " + base64.b64encode(b"t:t").decode()}

    def ask(q):
        r = client.post("/ask", json={"question_text": q, "compartment_id": "", "playhead_time_ms": 0},
                        headers=TEST)
        d = r.json() if r.status_code == 200 else {}
        ref = d.get("refusal") or {}
        return "fallback" if ref.get("reason") == "fallback" else (
            "refusal" if ref.get("is_refusal") else d.get("faq_id"))

    def put(cid, body):
        return client.put(f"/admin/faq/{cid}", json=body, headers=auth)

    def record(cid):
        return next(e for e in m.FAQ_ALL if e["chunk_id"] == cid)

    # 1. A phrasing routes its wording to its record.
    q, target = "what did they do for fun", "faq_1185"
    check("premise: without a phrasing the question misses its record", ask(q) != target, ask(q))
    r = put(target, {"phrasings": [q]})
    check("phrasing saved", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    check("with the phrasing it reaches its record", ask(q) == target, ask(q))
    listed = next(e for e in client.get("/admin/faqs", headers=auth).json() if e["chunk_id"] == target)
    check("the editor's list carries phrasings", listed.get("phrasings") == [q], repr(listed.get("phrasings")))
    with open(os.path.join(corpora, "dieselsubs_faq_corpus.jsonl"), encoding="utf-8") as f:
        saved = {x["chunk_id"]: x for x in (json.loads(l) for l in f if l.strip())}
    check("phrasing persisted to the corpus file", saved[target].get("phrasings") == [q])

    # 2. The guard: a short question does not ride a phrasing it barely shares.
    before = ask("how big is the boat?")
    put("faq_1194", {"phrasings": ["how big is a torpedo"]})
    check("guard: 'how big is the boat?' does not move to the torpedo record",
          ask("how big is the boat?") == before, f"{before} -> {ask('how big is the boat?')}")
    saved_cov = m.PHRASING_MIN_COVERAGE
    m.PHRASING_MIN_COVERAGE = 0.0
    try:
        check("premise: without the guard it would have moved",
              ask("how big is the boat?") == "faq_1194", ask("how big is the boat?"))
    finally:
        m.PHRASING_MIN_COVERAGE = saved_cov

    # 3. Only answerable records use phrasings.
    check("a draft's phrasings are ignored",
          m._record_phrasings({"chunk_id": "der_1", "phrasings": ["x y"]}) == [])
    check("a short's phrasings are ignored",
          m._record_phrasings({"chunk_id": "shorts_1", "phrasings": ["x y"]}) == [])

    # 4. Writes: validated, partial, and all-or-nothing.
    title = record(target)["title"]
    for bad, why in ((["<b>bold</b>"], "HTML"), ("not a list", "a string"), ([1, 2], "numbers"),
                     (["x" * 201], "over 200 characters"), ([f"wording {i}" for i in range(21)], "over 20")):
        r = put(target, {"title": "A changed title", "phrasings": bad})
        check(f"rejects {why}", r.status_code == 400, f"got {r.status_code}")
    check("a rejected write changes nothing", record(target)["title"] == title
          and record(target).get("phrasings") == [q], repr(record(target).get("phrasings")))
    put(target, {"title": title})
    check("a save without the field keeps phrasings", record(target).get("phrasings") == [q])
    put(target, {"phrasings": ["  what did they do   for fun ", "What did they do for fun", ""]})
    check("spacing tidied, duplicates and blanks dropped", record(target).get("phrasings") == [q],
          repr(record(target).get("phrasings")))
    put(target, {"phrasings": []})
    check("an empty list removes the field", "phrasings" not in record(target))
    check("and the question misses its record again", ask(q) != target, ask(q))

    r = client.post("/admin/faq", json={"title": "A new test record?", "text": "<p>Body.</p>",
                                         "phrasings": ["another way to ask"]}, headers=auth)
    new_id = r.json().get("chunk_id") if r.status_code == 200 else None
    check("a new record can be created with phrasings",
          new_id and record(new_id).get("phrasings") == ["another way to ask"], f"{r.status_code} {r.text[:200]}")

    shutil.rmtree(root, ignore_errors=True)
    print(f"\n  {'OK' if not failures else str(len(failures)) + ' FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

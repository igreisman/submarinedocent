#!/usr/bin/env python3
"""An answerable FAQ's Source line names its current title.

display_citation is what a visitor reads under "Source" on Ask the Docent and
on the museum pages.  It used to be written once, at creation, and never again,
so an admin title edit left it naming the old title: on 2 October 2026 the
retitled faq_1361 answered under "Why is there a broom at the top of the
submarine?", a title it no longer had.

    python3 _test/test_faq_display_citation.py

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
    root = tempfile.mkdtemp(prefix="displaycitation-")
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

    def stored(chunk_id):
        with open(os.path.join(corpora, "dieselsubs_faq_corpus.jsonl")) as fh:
            for line in fh:
                rec = json.loads(line)
                if rec["chunk_id"] == chunk_id:
                    return rec
        return None

    target = next(e for e in m.FAQ_ALL if e["chunk_id"].startswith("faq_"))
    cid = target["chunk_id"]
    new_title = target["title"].rstrip("?") + ", retitled?"

    r = client.put(f"/admin/faq/{cid}", json={"title": new_title}, headers=auth)
    check("title edit returns 200", r.status_code == 200, f"got {r.status_code}")
    rec = stored(cid)
    check("title edit rewrites display_citation",
          rec["display_citation"] == f"SubmarineDocent FAQ: {new_title}",
          repr(rec["display_citation"]))

    r = client.put(f"/admin/faq/{cid}", json={"text": "<p>Text only.</p>"}, headers=auth)
    rec = stored(cid)
    check("text-only edit keeps it on the current title",
          rec["display_citation"] == f"SubmarineDocent FAQ: {new_title}",
          repr(rec["display_citation"]))

    r = client.post("/admin/faq", json={"title": "A citation test record", "text": "<p>Body.</p>",
                                        "category": target.get("category", "")}, headers=auth)
    check("create returns 200", r.status_code == 200, f"got {r.status_code} {r.text[:200]}")
    new_id = r.json().get("chunk_id")
    rec = stored(new_id)
    check("create writes the format",
          rec and rec["display_citation"] == "SubmarineDocent FAQ: A citation test record",
          repr(rec and rec.get("display_citation")))

    check("no em dash in any answerable citation written here",
          all("—" not in (stored(c) or {}).get("display_citation", "") for c in (cid, new_id)))

    shutil.rmtree(root, ignore_errors=True)
    print(f"\n  {'OK' if not failures else str(len(failures)) + ' FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

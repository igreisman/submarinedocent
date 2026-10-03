#!/usr/bin/env python3
"""A record's boat is its subject matter, kept apart from museum_id.

boat holds a hull number from corpora/boats.jsonl.  It drives the FAQ page's
By boat list; museum_id stays what a participating museum owns or vets.
Pampanito's records carry a boat and never a museum_id.

    python3 _test/test_faq_boat_field.py

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
    root = tempfile.mkdtemp(prefix="boatfield-")
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

    check("boats table loaded", "SS-383" in m.BOATS and "SS-224" in m.BOATS, f"{len(m.BOATS)} boats")

    target = next(e for e in m.FAQ_ALL if e["chunk_id"].startswith("faq_") and not e.get("museum_id"))
    cid = target["chunk_id"]

    r = client.put(f"/admin/faq/{cid}", json={"boat": "SS-999"}, headers=auth)
    check("unknown hull number refused", r.status_code == 400, f"got {r.status_code}")
    check("refused write leaves no boat", "boat" not in (stored(cid) or {}))

    # A flagged record: writing a boat retires pampanito_specific.
    flagged = next((e for e in m.FAQ_ALL if e.get("pampanito_specific")), None)
    if flagged:
        fid = flagged["chunk_id"]
        r = client.put(f"/admin/faq/{fid}", json={"boat": "SS-383"}, headers=auth)
        rec = stored(fid)
        check("known hull number stored", r.status_code == 200 and rec.get("boat") == "SS-383", repr(rec.get("boat")))
        check("writing boat removes pampanito_specific", "pampanito_specific" not in rec)
        check("no museum_id added with a boat", not rec.get("museum_id"), repr(rec.get("museum_id")))

        r = client.put(f"/admin/faq/{fid}", json={"text": "<p>Text only.</p>"}, headers=auth)
        check("a save without boat leaves it alone", stored(fid).get("boat") == "SS-383")

        payload = client.get("/api/faqs", params={"boat": "SS-383"}).json()
        entries = [f for g in payload for f in g["faqs"]]
        check("/api/faqs?boat= returns only that boat",
              entries and all(f["boat"] == "SS-383" for f in entries), f"{len(entries)} entries")
        check("entries carry the display name",
              any(f["id"] == fid and f["boat_name"] == "USS Pampanito (SS-383)" for f in entries))

        r = client.put(f"/admin/faq/{fid}", json={"boat": ""}, headers=auth)
        check("empty boat clears it", "boat" not in stored(fid))
    else:
        print("  (no pampanito_specific record left; flag checks skipped)")

    r = client.post("/admin/faq", json={"title": "A boat field test record", "text": "<p>Body.</p>",
                                        "category": target.get("category", ""), "boat": "SS-224"},
                    headers=auth)
    new_id = r.json().get("chunk_id")
    check("create carries boat", r.status_code == 200 and (stored(new_id) or {}).get("boat") == "SS-224",
          f"{r.status_code} {r.text[:120]}")

    boats = client.get("/api/boats").json()
    check("/api/boats lists display names",
          any(b["hull"] == "SS-224" and b["display_name"] == "USS Cod (SS-224)" for b in boats))
    for old in ("pampanito-hub.html", "pampanito-patrols.html", "pampanito-patrol-1.html",
                "pampanito-patrol-2.html", "pampanito-patrol-3.html"):
        r = client.get(f"/web/{old}", follow_redirects=False)
        check(f"removed page {old} redirects to Pampanito's boat section",
              r.status_code == 301 and r.headers.get("location") == "/web/faqs.html?boat=SS-383",
              f"{r.status_code} {r.headers.get('location')}")
    r = client.put("/admin/patrol/1", json={"html": "<p>x</p>"}, headers=auth)
    check("the patrol page writer is gone", r.status_code in (404, 405), f"got {r.status_code}")

    shutil.rmtree(root, ignore_errors=True)
    print(f"\n  {'OK' if not failures else str(len(failures)) + ' FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

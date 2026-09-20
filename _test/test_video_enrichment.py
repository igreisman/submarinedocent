#!/usr/bin/env python3
"""Regression test: a partial admin video update must not scrape over
curated fields.

Unlike the other scripts in this directory, this one needs no running server
and no corpora. It boots the app in-process against a temporary content root
and stubs the YouTube fetch, so it is safe to run in CI.

    python3 _test/test_video_enrichment.py

The bug it guards against: _enrich_video_payload_from_youtube() decided a
record needed scraping when the *payload* carried none of
title/description/channel_name/channel_url/thumbnail_url. A rights-only
update sends exactly that, so it was indistinguishable from a blank create.
On 20 September 2026 a rights update on vid_032 replaced a hand-written
description with YouTube's "Enjoy the videos and music you love" boilerplate,
silently, returning 200.
"""
import base64
import json
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BOILERPLATE = "Enjoy the videos and music you love, upload original content."
CURATED = "An hour-long programme written by hand, which must survive."

SEED = {
    "id": "vid_001",
    "video_url": "https://www.youtube.com/watch?v=r5fykhn2Nro",
    "title": "A curated title",
    "description": CURATED,
    "channel_name": "Some Channel",
    "channel_url": "https://www.youtube.com/@some",
    "thumbnail_url": "https://i.ytimg.com/vi/r5fykhn2Nro/hqdefault.jpg",
    "rights_status": "not_required",
    "rights_note": "Embeddable under YouTube Terms of Service",
    "category": "Museums",
}

failures = []


def check(label, condition, detail=""):
    if condition:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}{('  ' + detail) if detail else ''}")
        failures.append(label)


def main():
    root = tempfile.mkdtemp(prefix="enrichtest-")
    corpora = os.path.join(root, "corpora")
    shutil.copytree(os.path.join(REPO, "sample_data", "corpora"), corpora)
    with open(os.path.join(corpora, "videos.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps(SEED) + "\n")

    os.environ["CONTENT_ROOT"] = corpora
    os.environ["ADMIN_USERNAME"] = "t"
    os.environ["ADMIN_PASSWORD"] = "t"
    sys.path.insert(0, REPO)
    from api import main as m
    from fastapi.testclient import TestClient

    # Never touch the network. If the fix regresses, this is what lands.
    async def fake_metadata(url):
        return {"title": "YouTube title", "description": BOILERPLATE,
                "channel_name": "YouTube channel",
                "channel_url": "https://youtube.com/@scraped",
                "thumbnail_url": "https://img/scraped.jpg"}
    m._youtube_metadata = fake_metadata

    client = TestClient(m.app)
    auth = {"Authorization": "Basic " + base64.b64encode(b"t:t").decode()}

    # 1. The actual regression: rights-only update on an existing record.
    r = client.put("/admin/videos/vid_001", headers=auth, json={
        "video_url": SEED["video_url"],
        "rights_status": "granted",
        "rights_note": "Permission granted by email.",
    })
    check("rights-only update returns 200", r.status_code == 200, str(r.status_code))
    entry = r.json().get("entry", {})
    check("description survives a rights-only update",
          entry.get("description") == CURATED, repr(entry.get("description"))[:90])
    check("title survives a rights-only update",
          entry.get("title") == SEED["title"], repr(entry.get("title"))[:60])
    check("channel_name survives a rights-only update",
          entry.get("channel_name") == SEED["channel_name"])
    check("the rights fields did change",
          entry.get("rights_status") == "granted"
          and entry.get("rights_note") == "Permission granted by email.")

    # 2. It must still fill a record that genuinely has nothing.
    r = client.post("/admin/videos", headers=auth,
                    json={"video_url": "https://www.youtube.com/watch?v=abcdefghijk"})
    check("create with only a url returns 200", r.status_code == 200, str(r.status_code))
    created = r.json().get("entry", {})
    check("a bare create is still enriched",
          created.get("description") == BOILERPLATE, repr(created.get("description"))[:60])

    # 3. An explicit field in the payload still wins over the scrape.
    r = client.put("/admin/videos/vid_001", headers=auth, json={
        "video_url": SEED["video_url"], "description": "Explicitly set."})
    check("an explicit description is honoured",
          r.json().get("entry", {}).get("description") == "Explicitly set.")

    shutil.rmtree(root, ignore_errors=True)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

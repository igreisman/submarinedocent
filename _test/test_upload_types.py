#!/usr/bin/env python3
"""Uploads cannot carry script that runs as the site.

Museum-page and FAQ uploads are served from submarinedocent.org itself, so an
.html or .svg file among them would run with the site's origin for anyone who
opened it.  Until 3 October 2026 museum uploads accepted .html, .htm and .svg,
and FAQ uploads accepted .svg.

    python3 _test/test_upload_types.py

Runs against a temporary copy of the real corpora. It writes, so it must never
be pointed at corpora/ itself.
"""
import base64
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
    root = tempfile.mkdtemp(prefix="uploadtypes-")
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

    r = client.post("/admin/museum_pages", json={"museum_id": 10, "title": "Upload test page"}, headers=auth)
    check("test page created", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    page_id = (r.json().get("page") or r.json()).get("id")

    for name, body in (("evil.html", b"<script>alert(1)</script>"),
                       ("evil.htm", b"<script>alert(1)</script>"),
                       ("evil.svg", b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>")):
        r = client.post(f"/admin/museum_pages/{page_id}/uploads", files={"file": (name, body)}, headers=auth)
        check(f"museum upload refuses {name}", r.status_code == 400, f"got {r.status_code}")
    r = client.post("/admin/faq-uploads", files={"file": ("evil.svg", b"<svg/>")}, headers=auth)
    check("FAQ upload refuses .svg", r.status_code == 400, f"got {r.status_code}")

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    r = client.post(f"/admin/museum_pages/{page_id}/uploads", files={"file": ("ok.png", png)}, headers=auth)
    check("museum upload still accepts .png", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    url = (r.json().get("attachment") or r.json()).get("url") if r.status_code == 200 else None
    if url:
        g = client.get(url)
        check("png is served", g.status_code == 200, f"got {g.status_code}")
        check("served with nosniff", g.headers.get("x-content-type-options") == "nosniff")
        check("served with a sandbox policy", "sandbox" in (g.headers.get("content-security-policy") or ""))

    # A file already on the disk from before the fix must not be served.
    planted_dir = os.path.join(m._MUSEUM_UPLOADS_DIR, str(page_id))
    os.makedirs(planted_dir, exist_ok=True)
    for name in ("planted.html", "planted.svg"):
        with open(os.path.join(planted_dir, name), "w") as fh:
            fh.write("<script>alert(1)</script>")
        g = client.get(f"/museum_uploads/{page_id}/{name}")
        check(f"existing {name} is not served", g.status_code == 404, f"got {g.status_code}")
    with open(os.path.join(m._FAQ_UPLOADS_DIR, "planted.svg"), "w") as fh:
        fh.write("<svg/>")
    g = client.get("/faq_uploads/planted.svg")
    check("existing FAQ .svg is not served", g.status_code == 404, f"got {g.status_code}")

    shutil.rmtree(root, ignore_errors=True)
    print(f"\n  {'OK' if not failures else str(len(failures)) + ' FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

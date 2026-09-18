#!/usr/bin/env python3
"""Push video records from a JSONL file to the live site's admin API.

Production keeps videos.jsonl on the Render persistent disk, so editing the
committed corpora/videos.jsonl does not change the live page (see
docs/AddingVideos.md). This script does what the admin editor does, once per
record, so a batch of videos can be added without filling in the form 90 times.

Usage:
    python3 scripts/import_videos.py videos_new.jsonl
    python3 scripts/import_videos.py videos_new.jsonl --site https://submarinedocent.org
    python3 scripts/import_videos.py videos_new.jsonl --dry-run

You will be prompted for the admin username and password. Records whose
video_url already exists on the site are skipped, so it is safe to re-run.
"""
import argparse, base64, getpass, json, sys, urllib.error, urllib.request

FIELDS = ("video_url", "title", "description", "video_credit", "video_credit_url",
          "channel_name", "channel_url", "category", "tags", "rights_note",
          "rights_status", "display_order", "duration", "video_start")


def call(site, path, auth, method="GET", body=None):
    req = urllib.request.Request(site + path, method=method)
    req.add_header("Authorization", "Basic " + auth)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, data, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8") or "null")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("--site", default="https://submarinedocent.org")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delete", action="store_true",
                    help="Treat the input as a list of video URLs (one per line, or JSONL records "
                         "with video_url) and DELETE the matching videos from the site.")
    ap.add_argument("--update-existing", action="store_true",
                    help="For records whose video_url is already on the site, send the file's "
                         "fields as an update instead of skipping. A record with only video_url "
                         "and category, for example, changes just the category.")
    args = ap.parse_args()
    site = args.site.rstrip("/")

    records = []
    with open(args.jsonl, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            if line.startswith("http"):
                records.append({"video_url": line})
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.exit(f"line {i}: bad JSON: {e}")
    print(f"{len(records)} records in {args.jsonl}")

    user = input("Admin username: ").strip()
    pw = getpass.getpass("Admin password: ")
    auth = base64.b64encode(f"{user}:{pw}".encode()).decode()

    try:
        existing = call(site, "/admin/videos", auth)
    except urllib.error.HTTPError as e:
        sys.exit(f"Could not read {site}/admin/videos: HTTP {e.code}. Wrong password?")
    if isinstance(existing, dict):
        existing = existing.get("entries") or existing.get("videos") or []
    have = {str(e.get("video_url") or "").strip(): str(e.get("id") or "") for e in existing}
    print(f"{len(have)} videos already on the site")

    if args.delete:
        deleted = missing = failed = 0
        for r in records:
            url = str(r.get("video_url") or "").strip()
            vid_id = have.get(url)
            if not vid_id:
                print("not on site:", url)
                missing += 1
                continue
            if args.dry_run:
                print(f"would delete {vid_id}: {url}")
                deleted += 1
                continue
            try:
                call(site, f"/admin/videos/{vid_id}", auth, "DELETE")
                print("deleted", vid_id, "|", url)
                deleted += 1
            except urllib.error.HTTPError as e:
                print("FAILED delete", vid_id, "HTTP", e.code)
                failed += 1
        print(f"done: {deleted} deleted, {missing} not on site, {failed} failed")
        return

    added = skipped = updated = failed = 0
    for r in records:
        url = str(r.get("video_url") or "").strip()
        payload = {k: r[k] for k in FIELDS if k in r and r[k] not in (None, "")}
        if url in have:
            if not args.update_existing:
                skipped += 1
                continue
            vid_id = have[url]
            label = payload.get("title") or url
            if args.dry_run:
                print(f"would update {vid_id}: {label} -> {sorted(k for k in payload if k != 'video_url')}")
                updated += 1
                continue
            try:
                call(site, f"/admin/videos/{vid_id}", auth, "PUT", payload)
                print("updated", vid_id, "|", label)
                updated += 1
            except urllib.error.HTTPError as e:
                print("FAILED update", vid_id, "HTTP", e.code, e.read().decode("utf-8", "replace")[:200])
                failed += 1
            continue
        if args.dry_run:
            print("would add:", payload.get("title"))
            added += 1
            continue
        try:
            out = call(site, "/admin/videos", auth, "POST", payload)
            print("added", out.get("entry", {}).get("id"), "|", payload.get("title"))
            added += 1
            have[url] = str(out.get("entry", {}).get("id") or "")
        except urllib.error.HTTPError as e:
            print("FAILED", payload.get("title"), "HTTP", e.code, e.read().decode("utf-8", "replace")[:200])
            failed += 1
    print(f"done: {added} added, {updated} updated, {skipped} already present, {failed} failed")


if __name__ == "__main__":
    main()

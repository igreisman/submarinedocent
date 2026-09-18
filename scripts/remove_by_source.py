#!/usr/bin/env python3
"""
scripts/remove_by_source.py

Remove FAQ chunks by their `source` field, through the app's own
_save_faq_corpus() so the write is atomic and the answerable view is rebuilt.

Dry run by default. Nothing is written without --apply.

    ./.venv/bin/python3 scripts/remove_by_source.py --source pampanito_docent
    ./.venv/bin/python3 scripts/remove_by_source.py --source pampanito_docent --apply

THE ACCEPTED-LINEAGE TRAP
-------------------------
accept_faq() rewrites a promoted draft's source:

    entry["source"] = f"accepted_from_{old_id}"

so a chunk generated from the Association's tour and later accepted no longer
says `pampanito_docent` -- it says `accepted_from_pam_032`. Matching on the
source string alone silently spares exactly the chunks that are answerable,
which is the opposite of what a removal is for.

This script therefore also matches `accepted_from_<prefix>_*` for the id
prefixes given by --accepted-prefix (default: pam, because every pam_ chunk
carried source=pampanito_docent). Pass --no-lineage to match the source string
only.

Run against a corpus other than the one CONTENT_ROOT resolves to with
--faq-path, which is how the bundled corpora/ copy is cleaned after production.

--via-api removes from a running deployment instead of a file. It resolves the
same set from that deployment's own corpus (pulled via /admin/backup) and then
issues DELETE /admin/faq/{chunk_id} for each, sequentially. This is the right
mode for production: the deletes go through the running app, so its in-memory
FAQ_ALL and the answerable FAQ view are both updated and no restart is needed.
Editing /data from a Render shell would instead leave the live process serving a
stale corpus until restart, and any admin save in that window would write the
removed chunks straight back.

Credentials and the base URL come from the environment only -- never from an
argument, which would put them in shell history and process listings:

    export SUBDOCENT_BASE_URL=https://submarinedocent.org
    export ADMIN_USERNAME=... ADMIN_PASSWORD=...
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def selected(entries, source, accepted_prefixes, use_lineage):
    """Chunks to remove, and why each was matched."""
    out = []
    for e in entries:
        src = str(e.get("source") or "")
        if src == source:
            out.append((e, f"source == {source}"))
        elif use_lineage and src.startswith("accepted_from_"):
            origin = src[len("accepted_from_"):]
            prefix = origin.split("_")[0]
            if prefix in accepted_prefixes:
                out.append((e, f"accepted lineage: {src}"))
    return out


def _env(name):
    v = os.getenv(name, "").strip()
    if not v:
        sys.exit(f"{name} is not set. Export it; this script never takes it as an argument.")
    return v


def _api(base, auth, method, path):
    req = urllib.request.Request(base.rstrip("/") + path, method=method)
    req.add_header("Authorization", "Basic " + auth)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def live_corpus(base, auth):
    """The deployment's own FAQ corpus, via /admin/backup."""
    import io
    import tarfile
    status, body = _api(base, auth, "GET", "/admin/backup")
    if status != 200:
        sys.exit(f"GET /admin/backup returned {status}: {body[:200]!r}")
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as tar:
        member = next((m for m in tar.getmembers()
                       if m.name.endswith("dieselsubs_faq_corpus.jsonl")), None)
        if member is None:
            sys.exit("no dieselsubs_faq_corpus.jsonl in the backup archive")
        raw = tar.extractfile(member).read().decode("utf-8")
    return [json.loads(l) for l in raw.splitlines() if l.strip()]


def run_via_api(args, prefixes):
    base = _env("SUBDOCENT_BASE_URL")
    auth = base64.b64encode(
        f"{_env('ADMIN_USERNAME')}:{_env('ADMIN_PASSWORD')}".encode()).decode()

    entries = live_corpus(base, auth)
    print(f"target: {base}")
    print(f"        {len(entries)} chunks in the live corpus\n")

    hits = selected(entries, args.source, prefixes, not args.no_lineage)
    if not hits:
        print(f"Nothing matches source {args.source!r}. Nothing to do.")
        return

    print(f"{len(hits)} chunk(s) match:\n")
    for e, why in sorted(hits, key=lambda t: t[0].get("chunk_id", "")):
        cid = e.get("chunk_id", "?")
        print(f"  {cid:10s} {(e.get('title') or '')[:70]}")
        if why.startswith("accepted"):
            print(f"             ^ matched by {why}")

    if not args.apply:
        print(f"\nDRY RUN. Nothing sent. Re-run with --apply to DELETE these "
              f"{len(hits)} chunk(s) from {base}.")
        return

    print(f"\nDeleting {len(hits)} chunk(s), sequentially:\n")
    done = 0
    for e, _why in sorted(hits, key=lambda t: t[0].get("chunk_id", "")):
        cid = e.get("chunk_id")
        status, body = _api(base, auth, "DELETE", f"/admin/faq/{cid}")
        print(f"  {cid:10s} {status}")
        if status != 200:
            print(f"\nSTOPPED on the first non-200. {done} removed before this one.")
            print(f"  response: {body[:300]!r}")
            sys.exit(1)
        done += 1
        time.sleep(0.5)
    print(f"\nRemoved {done} chunk(s) from {base}.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="exact source value to remove")
    ap.add_argument("--accepted-prefix", action="append", default=None,
                    help="id prefix whose accepted_from_* descendants also go "
                         "(repeatable; default: pam)")
    ap.add_argument("--no-lineage", action="store_true",
                    help="match the source string only, sparing accepted descendants")
    ap.add_argument("--faq-path", help="corpus to operate on instead of the resolved one")
    ap.add_argument("--via-api", action="store_true",
                    help="remove from a running deployment through "
                         "DELETE /admin/faq/{chunk_id} instead of editing a file")
    ap.add_argument("--apply", action="store_true", help="write the change; omit for a dry run")
    args = ap.parse_args()
    prefixes = set(args.accepted_prefix or ["pam"])

    if args.via_api:
        if args.faq_path:
            sys.exit("--via-api resolves the set from the deployment; --faq-path does not apply")
        run_via_api(args, prefixes)
        return

    from api import main as m

    if args.faq_path:
        resolved = os.path.abspath(args.faq_path)
        if not os.path.exists(resolved):
            sys.exit(f"--faq-path not found: {resolved}")
        # Same post-import override compare_gate.py uses: FAQ_PATH is derived at
        # import from CORPORA_DIR, and no environment variable names a file.
        m.FAQ_PATH = resolved
        m.FAQ_ALL = m.load_jsonl(resolved)
        m.FAQ = m._retrievable_faq(m.FAQ_ALL)

    print(f"corpus: {m.FAQ_PATH}")
    print(f"        {len(m.FAQ_ALL)} chunks, {len(m.FAQ)} answerable\n")

    hits = selected(m.FAQ_ALL, args.source, prefixes, not args.no_lineage)
    if not hits:
        print(f"Nothing matches source {args.source!r}. Nothing to do.")
        return

    answerable = {e.get("chunk_id") for e in m.FAQ}
    live = [(e, why) for e, why in hits if e.get("chunk_id") in answerable]

    print(f"{len(hits)} chunk(s) match, of which {len(live)} are answerable today:\n")
    for e, why in sorted(hits, key=lambda t: t[0].get("chunk_id", "")):
        cid = e.get("chunk_id", "?")
        flag = "ANSWERABLE" if cid in answerable else "draft"
        print(f"  [{flag:10s}] {cid:10s} {(e.get('title') or '')[:62]}")
        if why.startswith("accepted"):
            print(f"               ^ matched by {why}")

    if not args.apply:
        print(f"\nDRY RUN. Nothing written. Re-run with --apply to remove these "
              f"{len(hits)} chunk(s).")
        return

    doomed = {id(e) for e, _ in hits}
    before = len(m.FAQ_ALL)
    kept = [e for e in m.FAQ_ALL if id(e) not in doomed]
    # Mutate in place: _save_faq_corpus() writes from the module-level FAQ_ALL,
    # so rebinding a local name here would save the unchanged list.
    m.FAQ_ALL[:] = kept
    m._save_faq_corpus()

    after = len(m.FAQ_ALL)
    print(f"\nRemoved {before - after} chunk(s). {after} remain, "
          f"{len(m.FAQ)} answerable.")
    print(f"Wrote {m.FAQ_PATH}")


if __name__ == "__main__":
    main()

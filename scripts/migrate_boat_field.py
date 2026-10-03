#!/usr/bin/env python3
"""
scripts/migrate_boat_field.py

One-off migration to the boat field, approved by Irving on 3 October 2026.

A record's ``boat`` (a hull number from corpora/boats.jsonl) says what it is
about.  ``museum_id`` stays what a participating museum owns or vets: Cod's
records keep it, Pampanito's never get one.

WHAT IT DOES
------------
  * boat SS-383 on every answerable record whose title names Pampanito, plus
    faq_606, faq_778 and faq_786 (they describe her fittings)
  * boat SS-224 on every record with museum_id 10 (Cod)
  * boat SS-268 on faq_1240 (Puffer) and SS-191 on faq_1242 (Sculpin)
  * every other record carrying pampanito_specific gets boat "" (no boat),
    which retires the flag: the API removes pampanito_specific whenever a boat
    is written
  * faq_1334 moves to "Boat Histories"; the then-empty category
    "Pampanito War Patrols" is deleted

The plan is computed from a snapshot of the live corpus and checked against the
counts measured on 3 October.  If the live corpus no longer matches, it stops
rather than tag records nobody reviewed.

USAGE
-----
    export SUBDOCENT_BASE_URL=https://submarinedocent.org
    export ADMIN_USERNAME=... ADMIN_PASSWORD=...
    python3 scripts/migrate_boat_field.py CORPUS.jsonl            # dry run
    python3 scripts/migrate_boat_field.py CORPUS.jsonl --apply

CORPUS.jsonl is dieselsubs_faq_corpus.jsonl from a backup taken just before.
Take another backup after --apply and diff the two.
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

PAMPANITO, COD, PUFFER, SCULPIN = "SS-383", "SS-224", "SS-268", "SS-191"
REVIEWED_PAMPANITO = {"faq_606", "faq_778", "faq_786"}
REVIEWED_NO_BOAT = {"faq_591", "faq_592", "faq_594", "faq_595", "faq_800"}
EXPLICIT = {"faq_1240": PUFFER, "faq_1242": SCULPIN}
CATEGORY_MOVE = ("faq_1334", "Boat Histories")
CATEGORY_DELETE = "Pampanito War Patrols"
# Measured on the 3 October 2026 backup; see boat-field-proposal.md.
EXPECTED = {PAMPANITO: 30, COD: 20, PUFFER: 1, SCULPIN: 1, "no_boat_flagged": 21}


def plan(records):
    answerable = [r for r in records if str(r.get("chunk_id", "")).startswith(("faq_", "fix_"))]
    boats, problems = {}, []
    for r in answerable:
        cid = r["chunk_id"]
        wanted = set()
        if re.search(r"\bPampanito\b", r.get("title", "")) or cid in REVIEWED_PAMPANITO:
            wanted.add(PAMPANITO)
        if str(r.get("museum_id") or "").strip() == "10":
            wanted.add(COD)
        if cid in EXPLICIT:
            wanted.add(EXPLICIT[cid])
        if len(wanted) > 1:
            problems.append(f"{cid}: more than one boat {sorted(wanted)}")
        elif wanted:
            boats[cid] = wanted.pop()
        elif r.get("pampanito_specific"):
            boats[cid] = ""
    for cid in REVIEWED_NO_BOAT:
        if boats.get(cid, "") != "":
            problems.append(f"{cid}: reviewed as no boat but planned {boats.get(cid)!r}")
    counts = {h: sum(1 for b in boats.values() if b == h) for h in (PAMPANITO, COD, PUFFER, SCULPIN)}
    counts["no_boat_flagged"] = sum(1 for b in boats.values() if b == "")
    for key, n in EXPECTED.items():
        if counts.get(key) != n:
            problems.append(f"expected {n} for {key}, planned {counts.get(key)}")
    by_id = {r["chunk_id"]: r for r in answerable}
    move_id, move_to = CATEGORY_MOVE
    if move_id not in by_id:
        problems.append(f"{move_id} not found")
    others = [r["chunk_id"] for r in answerable
              if r.get("category") == CATEGORY_DELETE and r["chunk_id"] != move_id]
    if others:
        problems.append(f"{CATEGORY_DELETE!r} also holds {others}; it would not be empty")
    return boats, counts, problems


def call(base, auth, method, path, body):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method=method,
                                 headers={"Content-Type": "application/json", "Authorization": auth})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    records = [json.loads(l) for l in open(args.corpus, encoding="utf-8") if l.strip()]
    boats, counts, problems = plan(records)
    print(f"planned: {counts}; {len(boats)} records written")
    print(f"then: {CATEGORY_MOVE[0]} -> {CATEGORY_MOVE[1]!r}; delete category {CATEGORY_DELETE!r}")
    if problems:
        print("STOP:\n  " + "\n  ".join(problems))
        return 1
    if not args.apply:
        print("dry run; nothing written")
        return 0

    base = os.environ["SUBDOCENT_BASE_URL"].rstrip("/")
    auth = "Basic " + base64.b64encode(
        f'{os.environ["ADMIN_USERNAME"]}:{os.environ["ADMIN_PASSWORD"]}'.encode()).decode()
    done = 0
    for cid, hull in sorted(boats.items()):
        status = call(base, auth, "PUT", f"/admin/faq/{cid}", {"boat": hull})
        if status != 200:
            print(f"STOP: {cid} returned {status} after {done} writes")
            return 1
        done += 1
    print(f"{done} boat writes, all 200")
    status = call(base, auth, "PUT", f"/admin/faq/{CATEGORY_MOVE[0]}", {"category": CATEGORY_MOVE[1]})
    print(f"move {CATEGORY_MOVE[0]}: {status}")
    if status != 200:
        return 1
    status = call(base, auth, "DELETE", "/admin/faq-categories", {"title": CATEGORY_DELETE})
    print(f"delete category {CATEGORY_DELETE!r}: {status}")
    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())

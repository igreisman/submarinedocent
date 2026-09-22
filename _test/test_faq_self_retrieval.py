#!/usr/bin/env python3
"""Every FAQ title must retrieve its own record.

If a visitor types a question the corpus answers word for word, they must get
that answer and not a neighbour's. This runs the title of every answerable
record (faq_, fix_) through retrieve() and fails if any of them does not come
back as its own.

Needs no running server: it imports the app and calls retrieve() directly. It
does need the real corpora, so CI runs it against corpora/ rather than sample
content.

    python3 _test/test_faq_self_retrieval.py

History. On 22 September this stood at 347 of 366. Three separate causes:

  * add_hits() scored a chunk on its body and discarded it before the title
    boosts could run, so a record whose title matched the question exactly was
    thrown away when its body did not repeat the title's words. 16 records.
  * remove_compartment_noise() stripped "battery" from any question naming the
    after or forward battery. For "What is in the after battery?" that was the
    only surviving token, so nothing could score and the question returned no
    answer at all. 2 records.
  * Two records shared the title "What was a trim dive?". One had to lose.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def main():
    from api import main as m

    faq = [r for r in m.FAQ
           if str(r.get("chunk_id", "")).startswith(("faq_", "fix_"))]
    if not faq:
        print("no answerable FAQ records loaded; is CONTENT_ROOT right?")
        return 1

    # A title carried by two records cannot be satisfied by both, and the
    # failure it causes looks like a retrieval bug rather than a content one.
    seen, dupes = {}, []
    for r in faq:
        key = " ".join((r.get("title") or "").lower().split())
        if key and key in seen:
            dupes.append((seen[key], r["chunk_id"], r.get("title")))
        seen[key] = r["chunk_id"]

    misses = []
    for r in faq:
        cid = r["chunk_id"]
        title = (r.get("title") or "").strip()
        if not title:
            misses.append((cid, "(no title)", "-", 0))
            continue
        hits = m.retrieve(question_text=title, compartment_id="",
                          playhead_time_ms=0, top_k=8)
        ids = [h[1].get("chunk_id") for h in hits]
        resp = m.synthesize_extractive(question_text=title, hits=hits) if hits else {}
        got = resp.get("faq_id") or (ids[0] if ids else "")
        if got != cid:
            rank = ids.index(cid) + 1 if cid in ids else 0
            misses.append((cid, title, got or "(no answer)", rank))

    print(f"  {len(faq) - len(misses)}/{len(faq)} FAQ titles retrieve their own record")

    if dupes:
        print(f"\n  {len(dupes)} duplicate title(s):")
        for a, b, t in dupes:
            print(f"    {a} and {b} share {t!r}")
    if misses:
        print(f"\n  {len(misses)} title(s) did not:")
        for cid, title, got, rank in misses:
            where = f"own record at rank {rank}" if rank else "own record not retrieved at all"
            print(f"    {cid:10s} {title[:58]}")
            print(f"               answered by {got}, {where}")
        return 1
    if dupes:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

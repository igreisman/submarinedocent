#!/usr/bin/env python3
"""Every FAQ answer must open with its record's first paragraph and keep its text.

test_faq_self_retrieval.py proves each title retrieves its own record.  It
compares faq_id only, so it passed while visitors read the wrong words.  This
runs the same titles through retrieve() and synthesize_extractive() and checks
what the visitor actually reads:

  * the answer opens with the first sentence of the record's first answer
    paragraph (after the question paragraph, for the records that have one);
  * the answer keeps at least 80% of the record's own words.

    CONTENT_ROOT=corpora python3 _test/test_faq_answer_opening.py

History. On 1 October 2026, 52 of 383 records failed the opening check.
synthesize_extractive joined bare sentences for any record without a question
paragraph, which flattened every paragraph break but one, and clean_for_audio
then deleted the whole opening as a dangling header: faq_1114 answered a
question about trash with the after torpedo room flushing list, and faq_1244
kept 8 of 408 words.  The last 8 were the "why" check swapping in a
neighbour's text under the record's own title.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

MIN_KEPT = 0.80


def _norm(s: str) -> str:
    return " ".join((s or "").split()).lower()


def main():
    from api import main as m

    faq = [r for r in m.FAQ
           if str(r.get("chunk_id", "")).startswith(("faq_", "fix_"))]
    if not faq:
        print("no answerable FAQ records loaded; is CONTENT_ROOT right?")
        return 1

    failures = []
    for r in faq:
        cid = r["chunk_id"]
        title = (r.get("title") or "").strip()
        paras = [p.strip() for p in re.split(r"\n\n+", m.chunk_display_text(r)) if p.strip()]
        question = paras[0] if paras and paras[0].endswith("?") else None
        body = paras[1:] if question else paras
        if not title or not body:
            continue

        hits = m.retrieve(question_text=title, compartment_id="",
                          playhead_time_ms=0, top_k=8)
        resp = m.synthesize_extractive(question_text=title, hits=hits) if hits else {}
        answer = resp.get("answer_short") or ""
        if question and answer.startswith(question):
            answer = answer[len(question):]

        first = _norm(m.split_sentences(body[0])[0])[:60]
        body_words = len(_norm(" ".join(body)).split())
        kept = len(_norm(answer).split()) / body_words if body_words else 1.0

        problems = []
        if not _norm(answer).startswith(first):
            problems.append(f"opens with {answer.strip()[:60]!r}")
        if kept < MIN_KEPT:
            problems.append(f"keeps {kept:.0%} of its words")
        if problems:
            failures.append((cid, title, "; ".join(problems)))

    print(f"  {len(faq) - len(failures)}/{len(faq)} FAQ answers open with their "
          f"first paragraph and keep at least {MIN_KEPT:.0%} of their text")
    for cid, title, why in failures:
        print(f"    {cid:10s} {title[:58]}")
        print(f"               {why}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

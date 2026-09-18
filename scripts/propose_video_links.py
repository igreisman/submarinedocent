#!/usr/bin/env python3
"""
scripts/propose_video_links.py

For each video in corpora/videos.jsonl, score every FAQ chunk with the
project's own overlap_score() and write the top candidates to a CSV for
human review. Nothing is written back to the corpus by this script.

Run from the repo root:
    python scripts/propose_video_links.py
    python scripts/propose_video_links.py --top 5 --floor 0.15 --out review.csv

Then fill the `accept` column (y / blank) and hand the CSV to
scripts/apply_video_links.py.

TWO ADAPTERS TO CONFIRM against api/main.py before the first run.
They are marked ADAPTER below. Everything else is plain data handling.
"""

import argparse
import csv
import json
import os
import re
import sys

# Make `api` importable when run from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importing main loads every corpus at import time. That is what we want:
# it gives us the same in-memory FAQ chunks, IDF table, and average chunk
# length that /ask uses, so scores here match scores in production.
from api import main as m  # noqa: E402

# main.py reads .env.local at import (api/main.py:50), so CONTENT_ROOT from
# that file applies here too and can silently point this at the local scratch
# corpus instead of the committed one.  The chunk_ids differ between them, so
# a CSV produced against the wrong corpus proposes links that will not apply.
def _announce_corpus() -> None:
    print(f"corpus dir: {m.CORPORA_DIR}")
    if os.path.basename(m.CORPORA_DIR) != "corpora":
        print("  WARNING: not the committed corpora/ directory. "
              "Re-run with CONTENT_ROOT=corpora to score the corpus that ships.")


# ---------------------------------------------------------------------------
# ADAPTER 1: scoring
#
# overlap_score() lives at api/main.py:1763. Its exact signature is not
# known to this script. Wire it here so the rest of the file stays stable.
# The contract this function must satisfy: given a plain-text query and one
# FAQ chunk dict, return the same float that retrieve() would produce for
# that chunk (before any of the hand-tuned multipliers, or after; be
# consistent, and say which in the CSV header comment).
#
# Likely shapes, pick the one that matches main.py:
#   a) m.overlap_score(query_tokens, chunk_tokens, idf, avg_len)
#   b) m.overlap_score(query, chunk)          # tokenises internally
#   c) m.overlap_score(query, chunk["text"], corpus_name="faq")
# ---------------------------------------------------------------------------
def score_chunk(query: str, chunk: dict) -> float:
    # CONFIRMED against api/main.py:1763 --
    #   overlap_score(query_tokens: List[str], text: str) -> float
    # It takes a token LIST and the raw chunk TEXT, not a query string and a
    # chunk dict.  Synonym expansion, IDF and BM25 length-normalisation all
    # happen inside it.  The query is put through the same two steps retrieve()
    # applies before scoring, so a video's text is tokenised exactly as a
    # visitor's question would be.
    #
    # This is the score BEFORE retrieve()'s hand-tuned multipliers (FAQ corpus
    # weight 1.2, title-coverage boost, exact-title boost, quantity boost).
    # Those exist to rank a question against chunks; they do not apply to
    # ranking a video against chunks.
    q_tokens = m.tokenize(query)
    q_tokens = m.remove_compartment_noise(q_tokens, query)
    return m.overlap_score(q_tokens, chunk.get("text", "") or "")


# ---------------------------------------------------------------------------
# ADAPTER 2: rights gate
#
# _video_payload() normalises video_url and enforces rights_status. Reuse
# it as the single source of truth for "may this video be shown". The
# assumption here is that it returns None (or falsy) when the gate fails.
# If it raises instead, catch the exception and return False.
# ---------------------------------------------------------------------------
def video_allowed(video: dict) -> bool:
    # CONFIRMED against api/main.py:2198 -- _video_payload(entry: Dict) takes
    # the WHOLE record and reads entry.get("video_url") itself.  Handing it the
    # URL string made every call raise AttributeError, which the except below
    # swallowed into False: all 99 videos were reported "skipped by rights
    # gate" and the script wrote an empty CSV.
    #
    # It returns None when the URL is missing/unsafe or _rights_cleared(entry)
    # fails, so None is the gate result, not an error.
    try:
        return m._video_payload(video) is not None
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Category mapping
#
# videos.jsonl categories and FAQ categories were authored separately.
# Fill this in after running with --report-categories once. Left side is
# the video category, right side is a list of FAQ categories to search
# first. A video category with no entry searches all FAQ chunks.
# ---------------------------------------------------------------------------
CATEGORY_BOOST = 1.5

# Only the subject-matter video categories appear here. Documentaries, Oral
# Histories, Museums and Famous Boats & Patrols describe what a video *is*,
# not what it is *about* -- a museum walkthrough covers compartments,
# torpedoes, crew life and diving in one reel -- so any mapping for them
# would be arbitrary. They are absent on purpose and get no boost.
#
# The right-hand names are FAQ categories exactly as they appear in the
# corpus. "Attacks and Battles, Small and Large" contains a comma of its
# own; it is one category, never split.
CATEGORY_MAP = {
    "Torpedo Data Computer": ["Torpedoes"],
    "Life Aboard": ["Life Aboard US WW2 Subs", "Crews Aboard US Subs in WW2"],
    "Losses & Rescues": ["Attacks and Battles, Small and Large",
                         "US WW2 Subs in General"],
    "Technology & Systems": ["Diving and Surfacing", "Hull and Compartments"],
}


def boosted_categories(video_category: str) -> set:
    """FAQ categories to boost for a video, or an empty set for no boost.

    A video's category field can carry several categories comma-joined
    ("Museums, Torpedo Data Computer"), which is how a video ends up
    cross-listed on the videos page. Splitting here is what lets the
    Torpedo Data Computer half of that pair still earn its boost; a literal
    lookup misses it entirely. The split is on the VIDEO side only.
    """
    out = set()
    for part in (video_category or "").split(","):
        out.update(CATEGORY_MAP.get(part.strip(), []))
    return out

TAG_RE = re.compile(r"<[^>]+>")


def strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", s or "")).strip()


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_faq_chunks():
    # Prefer the in-memory corpus main.py already loaded so scores are
    # computed against exactly what production sees. Fall back to disk.
    for name in ("FAQ", "FAQ_CHUNKS", "faq_chunks", "FAQ_CORPUS", "faq_corpus"):
        if hasattr(m, name):
            chunks = getattr(m, name)
            if isinstance(chunks, list) and chunks:
                return chunks
    return load_jsonl(m.FAQ_PATH)


def load_videos():
    path = os.path.join(os.path.dirname(m.FAQ_PATH), "videos.jsonl")
    if not os.path.exists(path):
        path = os.path.join("corpora", "videos.jsonl")
    return load_jsonl(path)


def video_query(v: dict) -> str:
    parts = [v.get("title", ""), strip_html(v.get("description", ""))]
    tags = v.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    parts.extend(tags)
    return " ".join(p for p in parts if p)


def main():
    _announce_corpus()
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=3, help="candidates per video")
    ap.add_argument("--floor", type=float, default=0.0,
                    help="minimum score to list a candidate")
    ap.add_argument("--out", default="video_link_candidates.csv")
    ap.add_argument("--report-categories", action="store_true",
                    help="print category names from both corpora and exit")
    args = ap.parse_args()

    chunks = load_faq_chunks()
    videos = load_videos()

    if args.report_categories:
        vc = sorted({v.get("category", "") for v in videos})
        fc = sorted({c.get("category", "") for c in chunks})
        print("VIDEO categories:", *vc, sep="\n  ")
        print("\nFAQ categories:", *fc, sep="\n  ")
        return

    rows = []
    skipped_rights = []
    unmapped = set()

    for v in videos:
        if not video_allowed(v):
            skipped_rights.append(v.get("id"))
            continue

        q = video_query(v)
        vcat = v.get("category", "")
        boost_cats = boosted_categories(vcat)
        if not boost_cats:
            unmapped.add(vcat)

        # Every video is scored against every chunk. Half the FAQ corpus has
        # no category at all, so gating on the map would have put the largest
        # pool of chunks permanently out of reach.
        scored = []
        for c in chunks:
            base = score_chunk(q, c)
            if base <= 0:
                continue
            boosted = c.get("category", "") in boost_cats
            s = base * CATEGORY_BOOST if boosted else base
            if s < args.floor:
                continue
            scored.append((s, base, boosted, c))

        scored.sort(key=lambda t: t[0], reverse=True)

        for s, base, boosted, c in scored[: args.top]:
            rows.append({
                "video_id": v.get("id"),
                "video_title": v.get("title", ""),
                "video_category": vcat,
                "chunk_id": c.get("chunk_id"),
                "faq_title": c.get("title", ""),
                "faq_category": c.get("category", ""),
                "score": f"{s:.4f}",
                "base_score": f"{base:.4f}",
                "boosted": "y" if boosted else "",
                "already_has_video": "y" if c.get("video_url") else "",
                "accept": "",
            })

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                           ["video_id", "video_title", "video_category", "chunk_id",
                            "faq_title", "faq_category", "score", "base_score",
                            "boosted", "already_has_video", "accept"])
        w.writeheader()
        w.writerows(rows)

    print(f"videos: {len(videos)}  allowed: {len(videos) - len(skipped_rights)}  "
          f"skipped by rights gate: {len(skipped_rights)}")
    print(f"faq chunks: {len(chunks)}")
    print(f"candidate rows written: {len(rows)} -> {args.out}")
    if skipped_rights:
        print("skipped video ids:", ", ".join(str(x) for x in skipped_rights))
    if unmapped:
        print("video categories with no CATEGORY_MAP entry (searched all chunks):")
        for u in sorted(unmapped):
            print("  ", u)


if __name__ == "__main__":
    main()
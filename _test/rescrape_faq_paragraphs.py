#!/usr/bin/env python3
"""
Rescrape dieselsubs.com FAQ pages to recover paragraph structure.
Updates dieselsubs_faq_corpus.jsonl in-place, replacing flat text
with properly paragraph-separated text (joined with \n\n).

Usage: python3 rescrape_faq_paragraphs.py [--dry-run]
"""

import json
import re
import subprocess
import sys
import time


BASE_URL = "https://dieselsubs.com/faq/"
CORPUS_PATH = "corpora/dieselsubs_faq_corpus.jsonl"
DRY_RUN = "--dry-run" in sys.argv
LIMIT = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--limit=")), None)


def fetch_html(slug: str):
    url = BASE_URL + slug + "/"
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "25", "-A", "Mozilla/5.0", url],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout if result.returncode == 0 else None
    except Exception as e:
        print(f"  CURL ERROR {slug}: {e}")
        return None


def extract_paragraphs(html: str):
    """Extract <p> text from faq-answer / answer-content div."""
    m = re.search(r'<div[^>]+class="[^"]*(?:faq-answer|answer-content)[^"]*"[^>]*>', html)
    if not m:
        return None

    # Grab div body with depth tracking
    start = m.end()
    depth = 1
    i = start
    while i < len(html) and depth > 0:
        open_m = re.search(r'<div[\s>]', html[i:])
        close_m = re.search(r'</div>', html[i:])
        if close_m and (not open_m or close_m.start() < open_m.start()):
            i += close_m.end()
            depth -= 1
        elif open_m:
            i += open_m.end()
            depth += 1
        else:
            break
    body = html[start:i]

    # Extract <p>...</p> blocks
    paras = []
    for pm in re.finditer(r'<p[^>]*>(.*?)</p>', body, re.DOTALL | re.IGNORECASE):
        text = re.sub(r'<[^>]+>', ' ', pm.group(1))
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)
        text = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), text)
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            paras.append(text)
    return paras if paras else None


def fetch_paragraphs(slug: str):
    html = fetch_html(slug)
    if not html:
        return None
    return extract_paragraphs(html)


def main():
    with open(CORPUS_PATH, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f if line.strip()]

    updated = 0
    skipped = 0
    failed = 0

    for i, ch in enumerate(chunks):
        if ch.get("doc_type") != "dieselsubs_faq":
            continue

        # faq_NNN entries are the curated, authoritative versions — never overwrite them
        if ch.get("chunk_id", "").startswith("faq_"):
            skipped += 1
            continue

        slug = ch.get("slug", "")
        if not slug:
            skipped += 1
            continue

        if LIMIT and (updated + failed) >= LIMIT:
            break

        # Check if it already has multiple body paragraphs (e.g. faq_966)
        raw_parts = ch["text"].split("\n\n")
        if len(raw_parts) > 2:
            print(f"  SKIP {ch['chunk_id']} (already has {len(raw_parts)-1} body paras)")
            skipped += 1
            continue

        question_line = raw_parts[0].strip()

        print(f"[{i+1}] {ch['chunk_id']} — {slug}", end=" ... ", flush=True)
        paras = fetch_paragraphs(slug)

        if not paras:
            print("NO PARAGRAPHS FOUND")
            failed += 1
            time.sleep(0.3)
            continue

        new_body = "\n\n".join(paras)
        new_text = question_line + "\n\n" + new_body

        if new_text == ch["text"].replace("\xa0", " "):
            print("unchanged")
            skipped += 1
        else:
            para_count = len(paras)
            print(f"{para_count} para(s)")
            if not DRY_RUN:
                ch["text"] = new_text
            updated += 1

        time.sleep(0.2)  # polite crawl rate

    print(f"\nDone. updated={updated}, skipped={skipped}, failed={failed}")

    if not DRY_RUN and updated > 0:
        with open(CORPUS_PATH, "w", encoding="utf-8") as f:
            for ch in chunks:
                f.write(json.dumps(ch, ensure_ascii=False) + "\n")
        print(f"Corpus written: {CORPUS_PATH}")


if __name__ == "__main__":
    main()

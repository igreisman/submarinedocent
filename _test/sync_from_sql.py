#!/usr/bin/env python3
"""
sync_from_sql.py — Rebuild faq_NNN corpus entries from a dieselsubs.com
phpMyAdmin SQL dump.

Workflow:
  1. Export the `dieselsu_faqs` database from phpMyAdmin (Structure + Data)
  2. Run:  python3 sync_from_sql.py /path/to/dieselsu_faqs.sql
  3. Restart the server so the new corpus is loaded.

Only published FAQs are imported. All non-faq_ corpus entries (der_, pam_,
fix_) are left untouched.
"""

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

CORPUS_PATH = Path(__file__).parent / "corpora" / "dieselsubs_faq_corpus.jsonl"

# ── HTML → plain text ──────────────────────────────────────────────────────

class _Stripper(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get(self):
        return "".join(self._parts)


def strip_html(html: str) -> str:
    """Convert HTML to plain text, collapsing whitespace."""
    if not html:
        return ""
    # Block-level tags → newlines so paragraphs/list items separate cleanly
    html = re.sub(r"</(p|li|tr|div|h\d)\s*>", "\n", html, flags=re.I)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"<td\b[^>]*>", " ", html, flags=re.I)
    s = _Stripper()
    s.feed(html)
    text = s.get()
    # Collapse runs of blank lines to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── SQL row parser ─────────────────────────────────────────────────────────

def _parse_rows(values_block: str) -> list[list]:
    """
    Parse the VALUES portion of a MySQL multi-row INSERT.
    Each row is a tuple like (1, 'foo', NULL, 42, ...).
    Handles backslash escapes inside single-quoted strings.
    """
    rows = []
    i = 0
    n = len(values_block)

    while i < n:
        # Find opening paren
        while i < n and values_block[i] != "(":
            i += 1
        if i >= n:
            break
        i += 1  # skip '('

        row = []
        while i < n:
            # Skip leading whitespace
            while i < n and values_block[i] in " \t\r\n":
                i += 1
            if i >= n:
                break

            ch = values_block[i]

            if ch == ")":  # end of row
                i += 1
                break

            elif ch == ",":
                i += 1  # skip comma between values
                continue

            elif values_block[i:i+4] == "NULL":
                row.append(None)
                i += 4

            elif ch == "'":  # string value
                i += 1
                buf = []
                while i < n:
                    c = values_block[i]
                    if c == "\\" and i + 1 < n:
                        nxt = values_block[i + 1]
                        esc = {"'": "'", "\\": "\\", "n": "\n",
                               "r": "\r", "t": "\t", "0": "\0"}.get(nxt, nxt)
                        buf.append(esc)
                        i += 2
                    elif c == "'":
                        i += 1
                        break
                    else:
                        buf.append(c)
                        i += 1
                row.append("".join(buf))

            else:  # number or keyword
                j = i
                while j < n and values_block[j] not in ", )\t\r\n":
                    j += 1
                token = values_block[i:j]
                try:
                    row.append(int(token))
                except ValueError:
                    try:
                        row.append(float(token))
                    except ValueError:
                        row.append(token)
                i = j

        if row:
            rows.append(row)

    return rows


def _extract_inserts(sql: str, table: str) -> tuple[list[str], list[str]]:
    """
    Return (column_names, all_values_blocks) for every INSERT INTO `table`
    statement in the SQL dump (phpMyAdmin may split large tables across multiple
    INSERT statements).
    """
    pattern = re.compile(
        rf"INSERT INTO `{re.escape(table)}`\s*\(([^)]+)\)\s*VALUES\s*(.+?);\s*$",
        re.DOTALL | re.MULTILINE,
    )
    columns: list[str] = []
    blocks: list[str] = []
    for m in pattern.finditer(sql):
        if not columns:
            columns = [c.strip().strip("`") for c in m.group(1).split(",")]
        blocks.append(m.group(2))
    return columns, blocks


# ── Main ───────────────────────────────────────────────────────────────────

def parse_sql(path: Path) -> tuple[dict[int, str], list[dict]]:
    """Return (categories_map, faqs_list) from a phpMyAdmin SQL dump."""
    sql = path.read_text(encoding="utf-8", errors="replace")

    # ── categories ──────────────────────────────────────────────────────
    cat_cols, cat_blocks = _extract_inserts(sql, "categories")
    categories: dict[int, str] = {}
    for cat_block in cat_blocks:
        for row in _parse_rows(cat_block):
            if len(row) >= len(cat_cols):
                r = dict(zip(cat_cols, row))
                categories[r["id"]] = r["name"]

    # ── faqs ─────────────────────────────────────────────────────────────
    faq_cols, faq_blocks = _extract_inserts(sql, "faqs")
    faqs: list[dict] = []
    for faq_block in faq_blocks:
        for row in _parse_rows(faq_block):
            if len(row) >= len(faq_cols):
                faqs.append(dict(zip(faq_cols, row)))

    return categories, faqs


def faq_to_chunk(faq: dict, categories: dict[int, str]) -> dict:
    """Convert a MySQL faqs row → corpus chunk."""
    title = (faq.get("title") or "").strip()
    content = faq.get("content")   # plain text, may be None
    answer  = faq.get("answer") or ""

    if content:
        body = content.strip()
    else:
        body = strip_html(answer)

    text = f"{title}\n\n{body}" if body else title

    raw_tags = faq.get("tags") or ""
    topic_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

    cat_id = faq.get("category_id")
    category = categories.get(cat_id, "") if cat_id else ""

    return {
        "chunk_id": f"faq_{faq['id']}",
        "doc_type": "dieselsubs_faq",
        "source": "dieselsubs.com FAQ",
        "title": title,
        "slug": faq.get("slug", ""),
        "category": category,
        "text": text,
        "topic_tags": topic_tags,
        "authority_level": "reference_faq",
        "era": "ww2",
        "platform": ["us_diesel_electric_submarines"],
        "pampanito_specific": True,
        "display_citation": f"DieselSubs FAQ \u2014 {title}",
    }


def sync_from_string(sql_text: str, faq_list: list, save_fn) -> dict:
    """
    Parse *sql_text* (the content of a phpMyAdmin SQL dump) and update
    *faq_list* in-place, then call *save_fn()* to persist.

    Used by the FastAPI admin endpoint so staff can upload the SQL file
    through the browser — no terminal, no server restart needed.

    Returns a dict with import statistics.
    """
    # Reuse the same parse logic, but operate on a string
    categories: dict[int, str] = {}
    cat_cols, cat_blocks = _extract_inserts(sql_text, "categories")
    for block in cat_blocks:
        for row in _parse_rows(block):
            if len(row) >= len(cat_cols):
                r = dict(zip(cat_cols, row))
                categories[r["id"]] = r["name"]

    faq_cols, faq_blocks = _extract_inserts(sql_text, "faqs")
    raw_faqs: list[dict] = []
    for block in faq_blocks:
        for row in _parse_rows(block):
            if len(row) >= len(faq_cols):
                raw_faqs.append(dict(zip(faq_cols, row)))

    published = [
        f for f in raw_faqs
        if f.get("status") == "published" and f.get("is_published") == 1
    ]
    new_chunks = [faq_to_chunk(f, categories) for f in published]

    others = [e for e in faq_list if not e.get("chunk_id", "").startswith("faq_")]
    old_count = len(faq_list) - len(others)

    faq_list.clear()
    faq_list.extend(new_chunks + others)
    save_fn()

    return {
        "imported": len(new_chunks),
        "replaced": old_count,
        "kept_other": len(others),
        "total": len(faq_list),
    }


def sync(sql_path: Path, corpus_path: Path = CORPUS_PATH, dry_run: bool = False):
    print(f"Reading SQL dump: {sql_path}")
    categories, faqs = parse_sql(sql_path)
    print(f"  {len(categories)} categories, {len(faqs)} FAQ rows total")

    published = [
        f for f in faqs
        if f.get("status") == "published" and f.get("is_published") == 1
    ]
    print(f"  {len(published)} published FAQs")

    new_chunks = [faq_to_chunk(f, categories) for f in published]

    # Load existing corpus
    existing = []
    if corpus_path.exists():
        existing = [json.loads(l) for l in corpus_path.read_text().splitlines() if l.strip()]

    # Keep non-faq_ entries unchanged
    others = [c for c in existing if not c.get("chunk_id", "").startswith("faq_")]
    old_faq_count = len(existing) - len(others)

    combined = new_chunks + others

    if dry_run:
        print(f"\nDRY RUN — would write {len(new_chunks)} faq_ + {len(others)} other = {len(combined)} total entries")
        print(f"(replaced {old_faq_count} old faq_ entries)")
        return

    # Atomic write
    tmp = corpus_path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for chunk in combined:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    tmp.replace(corpus_path)

    print(f"\nWrote {len(new_chunks)} faq_ entries (was {old_faq_count})")
    print(f"Kept {len(others)} other entries (der_/pam_/fix_)")
    print(f"Total: {len(combined)} entries in {corpus_path}")
    print("\nRestart the server to load the updated corpus.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default to most recent SQL dump in Downloads
        candidates = sorted(Path.home().glob("Downloads/dieselsu_faqs*.sql"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            print("Usage: python3 sync_from_sql.py /path/to/dieselsu_faqs.sql")
            sys.exit(1)
        sql_path = candidates[0]
        print(f"Using: {sql_path}")
    else:
        sql_path = Path(sys.argv[1])

    if not sql_path.exists():
        print(f"File not found: {sql_path}")
        sys.exit(1)

    dry = "--dry-run" in sys.argv
    sync(sql_path, dry_run=dry)

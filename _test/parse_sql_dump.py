#!/usr/bin/env python3
"""
Parse MySQL dump of lost_submarines table and output JSONL.
Usage: python3 parse_sql_dump.py [sql_file] [output_jsonl]
"""

import json
import re
import sys
from datetime import date

COLUMNS = [
    'date_lost', 'date_lost_sort', 'fatalities_text', 'fatalities_num',
    'id', 'boat_number', 'name', 'designation', 'class_info',
    'last_captain', 'location', 'cause', 'loss_narrative', 'prior_history',
    'display_order', 'photo_boat', 'created_at', 'updated_at', 'photo_captain',
    'image1', 'image1_subtitle', 'image2', 'image2_subtitle',
    'image3', 'image3_subtitle', 'image4', 'image4_subtitle',
    'image5', 'image5_subtitle', 'image6', 'image6_subtitle',
    'image7', 'image7_subtitle', 'image8', 'image8_subtitle',
    'image9', 'image9_subtitle', 'image10', 'image10_subtitle',
    'construction'
]


def determine_era(date_sort_str):
    if not date_sort_str:
        return 'wwii'
    try:
        d = date.fromisoformat(str(date_sort_str))
        if d < date(1941, 12, 7):
            return 'pre-wwii'
        elif d > date(1945, 8, 15):
            return 'post-wwii'
        else:
            return 'wwii'
    except Exception:
        return 'wwii'


def clean_text(s):
    """Normalize line endings and strip leading/trailing whitespace."""
    if s is None:
        return None
    return s.replace('\r\n', '\n').replace('\r', '\n').strip()


def parse_string(text, pos):
    """
    Parse a MySQL single-quoted string starting at pos (which must be "'").

    Handles:
      - Backslash escapes: \\n \\r \\t \\' \\\\
      - Double-quote escaping: '' -> '
      - Unescaped apostrophes (heuristic): a lone ' that is NOT immediately
        followed (after optional horizontal whitespace) by a comma or closing
        paren is treated as a literal apostrophe, not the end of the string.
    """
    assert text[pos] == "'", f"Expected quote at pos {pos}, got {text[pos]!r}"
    pos += 1
    buf = []

    while pos < len(text):
        c = text[pos]

        # Backslash escape
        if c == '\\' and pos + 1 < len(text):
            nc = text[pos + 1]
            esc = {'n': '\n', 'r': '\r', 't': '\t', "'": "'",
                   '\\': '\\', '0': '\x00'}
            buf.append(esc.get(nc, nc))
            pos += 2
            continue

        # Potential end-of-string quote
        if c == "'":
            peek = pos + 1
            # Skip horizontal whitespace only (not newlines - newlines can be
            # inside multiline string values)
            while peek < len(text) and text[peek] in (' ', '\t'):
                peek += 1

            if peek >= len(text):
                pos += 1
                break

            nxt = text[peek]

            if nxt in (',', ')'):
                # Legitimate end of string
                pos += 1
                break
            elif nxt == "'":
                # '' escaping -> single quote
                buf.append("'")
                pos += 2
                continue
            else:
                # Treat as an unescaped apostrophe (e.g. O'Kane, ship's, etc.)
                buf.append("'")
                pos += 1
                continue

        buf.append(c)
        pos += 1

    return ''.join(buf), pos


def parse_value(text, pos):
    """Parse one SQL value: string, NULL, or integer/float."""
    while pos < len(text) and text[pos] in (' ', '\t'):
        pos += 1

    if pos >= len(text):
        return None, pos

    c = text[pos]

    if c == "'":
        return parse_string(text, pos)

    if text[pos:pos + 4] == 'NULL':
        return None, pos + 4

    # Number
    end = pos
    while end < len(text) and text[end] not in (',', ')'):
        end += 1
    raw = text[pos:end].strip()
    try:
        val = int(raw) if '.' not in raw else float(raw)
    except ValueError:
        val = raw
    return val, end


def parse_row(text, pos):
    """Parse one row tuple starting at '('."""
    assert text[pos] == '(', f"Expected '(' at pos {pos}"
    pos += 1
    values = []

    while pos < len(text):
        # Skip whitespace including newlines within a row value list
        while pos < len(text) and text[pos] in (' ', '\t', '\r', '\n'):
            pos += 1

        if pos >= len(text):
            break

        if text[pos] == ')':
            pos += 1
            break

        if text[pos] == ',':
            pos += 1
            continue

        val, pos = parse_value(text, pos)
        values.append(val)

    return values, pos


def parse_sql(content):
    boats = []

    # The INSERT INTO ... VALUES blocks for lost_submarines
    boats = []

    # The INSERT INTO ... VALUES blocks for lost_submarines
    for m in re.finditer(
            r"INSERT INTO `lost_submarines`[^;]*?VALUES\s*\n",
            content, re.DOTALL):

        pos = m.end()

        while pos < len(content):
            # Skip whitespace and commas between rows
            while pos < len(content) and content[pos] in (' ', '\t', '\r', '\n', ','):
                pos += 1
            if pos >= len(content):
                break

            if content[pos] == ';':
                pos += 1
                break

            if content[pos] == '(':
                row_vals, pos = parse_row(content, pos)

                if len(row_vals) >= len(COLUMNS):
                    d = dict(zip(COLUMNS, row_vals))
                    era = determine_era(d.get('date_lost_sort'))

                    boat = {
                        'id': d['id'],
                        'boat_number': d.get('boat_number'),
                        'name': d.get('name'),
                        'designation': d.get('designation'),
                        'date_lost': clean_text(d.get('date_lost')),
                        'date_lost_sort': d.get('date_lost_sort'),
                        'fatalities_num': int(d.get('fatalities_num') or 0),
                        'fatalities_text': clean_text(d.get('fatalities_text')),
                        'last_captain': clean_text(d.get('last_captain')),
                        'location': clean_text(d.get('location')),
                        'cause': clean_text(d.get('cause')),
                        'class_info': clean_text(d.get('class_info')),
                        'loss_narrative': clean_text(d.get('loss_narrative')),
                        'photo_boat': d.get('photo_boat'),
                        'photo_captain': d.get('photo_captain'),
                        'era': era,
                    }
                    boats.append(boat)
                else:
                    print(f"  WARNING: row had only {len(row_vals)} values "
                          f"(expected {len(COLUMNS)})", file=sys.stderr)
            else:
                pos += 1  # skip unexpected char

    return boats
if __name__ == '__main__':
    sql_path = sys.argv[1] if len(sys.argv) > 1 else 'lost_subs_source.sql'
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'corpora/eternal_patrol.jsonl'

    with open(sql_path, encoding='utf-8') as f:
        content = f.read()

    boats = parse_sql(content)
    print(f"Parsed {len(boats)} boats", file=sys.stderr)

    # Sort by date
    boats.sort(key=lambda b: b.get('date_lost_sort') or '')

    with open(out_path, 'w', encoding='utf-8') as f:
        for boat in boats:
            f.write(json.dumps(boat, ensure_ascii=False) + '\n')

    print(f"Written to {out_path}", file=sys.stderr)

    # Quick summary
    by_era = {}
    for b in boats:
        by_era[b['era']] = by_era.get(b['era'], 0) + 1
    print(f"By era: {by_era}", file=sys.stderr)
    total_fat = sum(b['fatalities_num'] for b in boats)
    print(f"Total fatalities: {total_fat}", file=sys.stderr)

#!/usr/bin/env python3
"""
pdf_to_html.py
Converts a scanned submarine war patrol PDF to separate HTML files — one per patrol.
Trailing documents are analyzed and assigned to the appropriate patrol or a new file.

Two-pass approach:
  Pass 1 — Quick structural scan (low-res) to identify patrol boundaries and doc types.
  Pass 2 — Full OCR pass, grouped by patrol, generating one HTML file each.

Usage:
    python pdf_to_html.py input.pdf output_dir/
    python pdf_to_html.py input.pdf output_dir/ --dpi 200 --scan-dpi 72
    python pdf_to_html.py input.pdf output_dir/ --scan-only
    python pdf_to_html.py input.pdf output_dir/ --structure output_dir/structure.json
"""

import anthropic
import base64
import argparse
import json
import sys
import time
from io import BytesIO
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image

MODEL        = "claude-opus-4-20250514"
SCAN_DPI     = 72
OCR_DPI      = 200
MAX_WIDTH    = 1600
JPEG_QUALITY = 85
RETRY_LIMIT  = 3
RETRY_DELAY  = 5

STRUCTURE_SYSTEM = """You are analyzing scanned WWII submarine war patrol document pages to identify their structure.
For each page, identify:
1. Whether it starts a new war patrol (e.g., "First War Patrol", "Second War Patrol", "Patrol No. 3")
2. Whether it is a trailing/appended document after all patrols end — e.g., endorsements, fitness reports,
   medical reports, awards, commendations, ship history, photograph indexes, muster rolls, etc.
3. Which patrol number the page belongs to (1, 2, 3... or null if cover/unknown)
4. A short label describing the page content

Respond ONLY with a JSON array. Each element:
  page       (int)      — 1-indexed page number
  patrol     (int|null) — patrol number this page belongs to
  new_patrol (bool)     — true only if this page starts a new patrol section
  doc_type   (str)      — one of: "cover", "patrol", "trailing_doc", "unknown"
  label      (str)      — short description
  assign_to  (int|null) — for trailing_doc: which patrol it logically belongs to, or null for standalone docs file

Raw JSON only. No preamble, no markdown fences."""

OCR_SYSTEM = """You are an expert OCR system transcribing scanned WWII submarine war patrol documents.
Output clean, accurate HTML fragments.

Rules:
- Preserve all text exactly, including abbreviations and archaic spelling.
- Use <h2> for dates (e.g., 15 March 1944) and major section headings.
- Use <h3> for subsection headings.
- Use <table> for time-log entries with columns: Time | Zone | Entry.
- Use <p> for narrative paragraphs.
- Use <em> for underlined text, <strong> for bold.
- Preserve tabular data as <table> elements.
- Output only the HTML fragment — no <html>, <head>, or <body> tags.
- No commentary, no markdown fences."""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body  {{ font-family: Georgia, serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; color: #222; line-height: 1.6; }}
    h1   {{ border-bottom: 3px solid #333; padding-bottom: .5rem; }}
    h2   {{ margin-top: 2.5rem; border-bottom: 1px solid #999; color: #333; }}
    h3   {{ margin-top: 1.5rem; color: #555; }}
    section {{ margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px dashed #ddd; }}
    .page-label {{ font-size: .7rem; color: #aaa; text-align: right; margin-bottom: .25rem; font-family: monospace; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .9rem; }}
    th, td {{ border: 1px solid #ccc; padding: .35rem .7rem; vertical-align: top; }}
    th    {{ background: #f0f0f0; font-weight: bold; }}
    td:first-child {{ white-space: nowrap; font-family: monospace; }}
    p     {{ margin: .4rem 0; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p><em>Transcribed by Claude from scanned PDF — {page_count} pages</em></p>
{body}
</body>
</html>
"""

ORDINALS = {1:"First",2:"Second",3:"Third",4:"Fourth",5:"Fifth",
            6:"Sixth",7:"Seventh",8:"Eighth",9:"Ninth",10:"Tenth"}


def page_to_base64(img, max_width=MAX_WIDTH, quality=JPEG_QUALITY):
    if img.width > max_width:
        img = img.resize((max_width, int(img.height * max_width / img.width)), Image.LANCZOS)
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
    return base64.standard_b64encode(buf.getvalue()).decode()


def call_claude(client, system, messages, max_tokens=4096):
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            r = client.messages.create(
                model=MODEL, max_tokens=max_tokens,
                system=system, messages=messages)
            return r.content[0].text
        except anthropic.RateLimitError:
            if attempt < RETRY_LIMIT:
                print(f"    rate limit — waiting {RETRY_DELAY}s")
                time.sleep(RETRY_DELAY)
            else:
                raise


def scan_structure(client, images, batch_size=10):
    print(f"\n🔍 Pass 1 — Structural scan ({len(images)} pages, batches of {batch_size}) …")
    all_results = []

    for batch_start in range(0, len(images), batch_size):
        batch = images[batch_start:batch_start + batch_size]
        end   = batch_start + len(batch)
        print(f"   Pages {batch_start+1}–{end} …", end=" ", flush=True)

        content = []
        for i, img in enumerate(batch):
            b64 = page_to_base64(img, max_width=800, quality=65)
            content.append({"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":b64}})
            content.append({"type":"text","text":f"[Page {batch_start+i+1}]"})
        content.append({"type":"text","text":(
            f"Pages {batch_start+1}–{end} of a scanned submarine war patrol document. "
            "Return the JSON structure array as instructed.")})

        raw = call_claude(client, STRUCTURE_SYSTEM, [{"role":"user","content":content}], max_tokens=2048)
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

        try:
            results = json.loads(raw)
            all_results.extend(results)
            print(f"✓")
        except json.JSONDecodeError as e:
            print(f"\n    ⚠ JSON error: {e} — marking pages as unknown")
            for i in range(len(batch)):
                all_results.append({"page":batch_start+i+1,"patrol":None,"new_patrol":False,
                                     "doc_type":"unknown","label":"unknown","assign_to":None})

    return all_results


def build_patrol_groups(structure):
    groups = {}
    docs_group = []
    current_patrol = None

    for entry in structure:
        page     = entry["page"]
        doc_type = entry.get("doc_type","unknown")

        if entry.get("new_patrol") and entry.get("patrol"):
            current_patrol = entry["patrol"]

        if doc_type in ("patrol","unknown") and (entry.get("patrol") or current_patrol):
            patrol = entry.get("patrol") or current_patrol
            groups.setdefault(patrol, []).append(page)

        elif doc_type == "trailing_doc":
            assign_to = entry.get("assign_to")
            if assign_to:
                groups.setdefault(assign_to, []).append(page)
            else:
                docs_group.append(page)

        elif doc_type == "cover":
            if 1 in groups:
                groups[1].insert(0, page)
            else:
                docs_group.append(page)

    if docs_group:
        groups["docs"] = docs_group

    return groups


def ocr_pages(client, page_images_dict, structure_by_page, cache_path=None):
    # Load existing cache if present (resume support)
    results = {}
    if cache_path and cache_path.exists():
        results = {int(k): v for k, v in json.loads(cache_path.read_text()).items()}
        print(f"\n📖 Pass 2 — OCR ({len(page_images_dict)} pages, {len(results)} already cached) …")
    else:
        print(f"\n📖 Pass 2 — OCR ({len(page_images_dict)} pages) …")

    total = len(page_images_dict)
    for idx, (page_num, img) in enumerate(sorted(page_images_dict.items()), 1):
        if page_num in results:
            print(f"   [{idx}/{total}] Page {page_num}: skipped (cached) ✓")
            continue
        label = structure_by_page.get(page_num, {}).get("label", "")
        print(f"   [{idx}/{total}] Page {page_num}: {label} …", end=" ", flush=True)
        b64 = page_to_base64(img)
        html = call_claude(client, OCR_SYSTEM, [{"role":"user","content":[
            {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":b64}},
            {"type":"text","text":f"Transcribe page {page_num} into HTML as instructed."}
        ]}])
        results[page_num] = html
        # Save after every page so crashes don't lose work
        if cache_path:
            cache_path.write_text(json.dumps(results, indent=2))
        print("✓")
    return results


def write_html(output_path, title, page_nums, ocr_results):
    sections = []
    for p in sorted(page_nums):
        frag = ocr_results.get(p, f"<p><em>[Page {p} not available]</em></p>")
        sections.append(f'  <div class="page-label">— page {p} —</div>\n  {frag}')
    body = "\n\n".join(sections)
    html = HTML_TEMPLATE.format(title=title, page_count=len(page_nums), body=body)
    output_path.write_text(html, encoding="utf-8")
    print(f"   → {output_path.name}  ({output_path.stat().st_size//1024} KB, {len(page_nums)} pages)")


def main():
    parser = argparse.ArgumentParser(description="PDF → per-patrol HTML via Claude OCR")
    parser.add_argument("input_pdf")
    parser.add_argument("output_dir")
    parser.add_argument("--dpi",       type=int, default=OCR_DPI)
    parser.add_argument("--scan-dpi",  type=int, default=SCAN_DPI)
    parser.add_argument("--start",     type=int, default=1)
    parser.add_argument("--end",       type=int, default=None)
    parser.add_argument("--scan-only", action="store_true", help="Run structure scan only and exit")
    parser.add_argument("--structure", default=None, help="Path to saved structure.json to skip scan pass")
    args = parser.parse_args()

    input_path = Path(args.input_pdf)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"Error: {input_path} not found"); sys.exit(1)

    client = anthropic.Anthropic()

    # Pass 1 — structure
    if args.structure:
        print(f"📂 Loading structure from {args.structure} …")
        structure = json.loads(Path(args.structure).read_text())
    else:
        print(f"📄 Loading PDF for scan pass @ {args.scan_dpi} DPI …")
        scan_images = convert_from_path(str(input_path), dpi=args.scan_dpi,
                                         first_page=args.start, last_page=args.end)
        structure = scan_structure(client, scan_images)
        struct_path = output_dir / "structure.json"
        struct_path.write_text(json.dumps(structure, indent=2))
        print(f"\n   Structure saved → {struct_path}")

    if args.scan_only:
        print("\n📋 Structure map:")
        for e in structure:
            print(f"  Page {e['page']:3d}  patrol={e.get('patrol')}  "
                  f"type={e.get('doc_type'):<12}  assign_to={e.get('assign_to')}  {e.get('label')}")
        return

    structure_by_page = {e["page"]: e for e in structure}
    groups = build_patrol_groups(structure)

    print(f"\n📂 Groups:")
    for key, pages in sorted(groups.items(), key=lambda x: (str(x[0]))):
        label = f"Patrol {key}" if isinstance(key, int) else "Documents"
        print(f"   {label}: {len(pages)} pages  ({min(pages)}–{max(pages)})")

    all_needed = sorted({p for pages in groups.values() for p in pages})
    first_p, last_p = min(all_needed), max(all_needed)

    print(f"\n📄 Loading PDF for OCR pass @ {args.dpi} DPI …")
    ocr_images_list = convert_from_path(str(input_path), dpi=args.dpi,
                                          first_page=first_p, last_page=last_p)
    ocr_images = {first_p + i: img for i, img in enumerate(ocr_images_list)
                  if (first_p + i) in all_needed}

    cache_path = output_dir / "ocr_cache.json"
    ocr_results = ocr_pages(client, ocr_images, structure_by_page, cache_path=cache_path)

    vessel = input_path.stem.split("_")[0].upper().replace("-", " ")
    print(f"\n✍️  Writing HTML files …")
    for key, pages in sorted(groups.items(), key=lambda x: (0 if isinstance(x[0], int) else 1, str(x[0]))):
        if isinstance(key, int):
            ordinal = ORDINALS.get(key, f"{key}th")
            title   = f"{vessel} — {ordinal} War Patrol"
            fname   = f"patrol_{key:02d}.html"
        else:
            title = f"{vessel} — Supporting Documents"
            fname = "documents.html"
        write_html(output_dir / fname, title, pages, ocr_results)

    print(f"\n✅ Done — {len(groups)} file(s) in {output_dir}/")


if __name__ == "__main__":
    main()

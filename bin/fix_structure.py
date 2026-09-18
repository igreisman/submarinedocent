#!/usr/bin/env python3
"""
fix_structure.py
Fixes misclassified patrol numbers (13, 17) in structure.json.
Sets them to trailing_doc with assign_to=None so they go into documents.html.
"""

import json
import sys
from pathlib import Path

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/structure.json")

data = json.loads(path.read_text())

fixed = 0
for entry in data:
    if entry.get("patrol") in (13, 17):
        entry["patrol"] = None
        entry["new_patrol"] = False
        entry["doc_type"] = "trailing_doc"
        entry["assign_to"] = None
        print(f"  Fixed page {entry['page']:3d}: {entry['label']}")
        fixed += 1

path.write_text(json.dumps(data, indent=2))
print(f"\n✅ Fixed {fixed} entries → {path}")

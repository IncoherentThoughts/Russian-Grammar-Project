#!/usr/bin/env python3
"""Harvest the English translations of Dialogues/Texts from the Key to Exercises.

The scan's built-in OCR layer is English-only, which is exactly what the Key's
translation blocks are, so they can be read straight from the PDF (no vision pass).
Blocks are the section-numbered headings (`5.12 Dialogues`, `29.9`) between exercise
answers; each runs until the next section or exercise heading. Output is
transcripts/key.md with `### N.x` headings, reviewed and corrected by hand.

    .venv/bin/python scripts/harvest_key.py            # writes transcripts/key.md
"""
import pathlib
import re
import sys

import pymupdf

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY_PAGES = range(461, 511)
# The Key mislabels a few translation blocks; map them to the section they translate.
RELABEL = {"23.7": "23.8", "20.10": "20.11"}
SKIP = {"20.2"}  # an exercise line the heading regex mistakes for a section
SEC = re.compile(r"^\s*(\d{1,2})\.\s?(\d{1,2})\s*(.*)$")
EXER = re.compile(r"^\s*\d{1,2}/\d\s*$")


def main(out):
    doc = pymupdf.open(str(ROOT / "Russian Course (Bookmarks).pdf"))
    blocks, cur = [], None
    for p in KEY_PAGES:
        for line in doc[p - 1].get_text().splitlines():
            if re.match(r"^\s*(KEY TO EXERCISES|\d{3})\s*$", line):
                continue  # running header / page number
            if EXER.match(line):
                cur = None
                continue
            m = SEC.match(line)
            if m and len(line) < 60:
                cur = {"sec": f"{m.group(1)}.{m.group(2)}", "title": m.group(3).strip(), "lines": []}
                blocks.append(cur)
                continue
            if cur is not None and line.strip():
                cur["lines"].append(line.strip())
    text = ["# Key: translations of Dialogues and Texts", ""]
    for b in blocks:
        if b["sec"] in SKIP:
            continue
        b["sec"] = RELABEL.get(b["sec"], b["sec"])
        body = " ".join(b["lines"])
        body = re.sub(r"\(I I\)", "(11)", body).replace("(I)", "(1)").replace("(l)", "(1)")
        latin = sum(ch.isascii() and ch.isalpha() for ch in body)
        if latin < 0.6 * sum(ch.isalpha() for ch in body):
            continue  # Russian answer block mis-read as a translation
        body = re.sub(r"\((\d{1,2})\)\s*", r"\n(\1) ", body)  # one numbered dialogue per line
        text.append(f"### {b['sec']} {b['title']}".rstrip())
        text.append(body.strip())
        text.append("")
    out.write_text("\n".join(text))
    print(f"{out}: {len(blocks)} blocks")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "transcripts" / "key.md")

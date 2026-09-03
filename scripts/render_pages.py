#!/usr/bin/env python3
"""Render a page range of the course PDF to PNGs for OCR / inspection.

Usage:
    python3 scripts/render_pages.py START END [--dpi 300] [--out research/pages]

START and END are 1-based PDF page numbers (inclusive). Output files are named
p{page:03d}.png inside the output directory, which is created if missing.
research/pages/ is gitignored, so rendered pages never enter the repo.
"""

import argparse
import sys
from pathlib import Path

import fitz  # PyMuPDF

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = REPO_ROOT / "Russian Course (Bookmarks).pdf"
DEFAULT_OUT = REPO_ROOT / "research" / "pages"


def render_pages(pdf_path: Path, start: int, end: int, dpi: int, out_dir: Path) -> list:
    """Render pages start..end (1-based, inclusive) to PNG; return written paths."""
    doc = fitz.open(str(pdf_path))
    try:
        page_count = doc.page_count
        if start < 1 or end > page_count or start > end:
            raise ValueError(
                f"page range {start}-{end} is outside 1-{page_count} or reversed"
            )
        out_dir.mkdir(parents=True, exist_ok=True)
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        written = []
        for page_num in range(start, end + 1):
            page = doc[page_num - 1]
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            out_path = out_dir / f"p{page_num:03d}.png"
            pix.save(str(out_path))
            written.append(out_path)
        return written
    finally:
        doc.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("start", type=int, help="first PDF page (1-based)")
    parser.add_argument("end", type=int, help="last PDF page (1-based, inclusive)")
    parser.add_argument("--dpi", type=int, default=300, help="render resolution (default 300)")
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT, help="output directory (default research/pages)"
    )
    parser.add_argument(
        "--pdf", type=Path, default=DEFAULT_PDF, help="PDF to render (default: course PDF in repo root)"
    )
    args = parser.parse_args(argv)

    if not args.pdf.is_file():
        print(f"error: PDF not found: {args.pdf}", file=sys.stderr)
        return 1
    try:
        written = render_pages(args.pdf, args.start, args.end, args.dpi, args.out)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

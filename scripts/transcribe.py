#!/usr/bin/env python3
"""Transcribe rendered page PNGs with a Claude vision model.

Usage:
  .venv/bin/python scripts/transcribe.py 54 63 --model claude-sonnet-5 --out research/transcripts/sonnet
  .venv/bin/python scripts/transcribe.py 54 63 --model claude-opus-5   --out research/transcripts/opus

Synchronous, one request per page (fine for a prototype; the full book should
use the Message Batches API — see docs/research/extraction-options.md §3.4).
Needs ANTHROPIC_API_KEY in the environment. Pages are read from research/pages/p{NNN}.png
(render them first with scripts/render_pages.py).
"""
import argparse
import base64
import pathlib
import re
import sys
import time
import unicodedata

import anthropic

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROMPT = (ROOT / "prompts" / "transcribe.md").read_text()
ACUTE = "́"


def transcribe(client, model, png: pathlib.Path, effort: str) -> tuple[str, dict]:
    data = base64.standard_b64encode(png.read_bytes()).decode()
    resp = client.messages.create(
        model=model,
        max_tokens=8000,
        system=PROMPT,
        output_config={"effort": effort},
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}},
                {"type": "text", "text": "Transcribe this page."},
            ],
        }],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    text = unicodedata.normalize("NFC", text)
    usage = {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
    return text, usage


def accent_report(text: str) -> str:
    """Cheap sanity check: Cyrillic words with 2+ vowels that carry no accent and no ё."""
    vowels = "аеиоуыэюяАЕИОУЫЭЮЯ"
    missing = []
    for w in re.findall(r"[А-Яа-яЁё́]+", text):
        nv = sum(ch in vowels for ch in w)
        if nv >= 2 and ACUTE not in w and "ё" not in w and "Ё" not in w:
            missing.append(w)
    return f"{len(missing)} unaccented polysyllables: {' '.join(missing[:30])}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("start", type=int)
    ap.add_argument("end", type=int)
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--pages", default=str(ROOT / "research" / "pages"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()
    total = {"in": 0, "out": 0}
    for p in range(a.start, a.end + 1):
        png = pathlib.Path(a.pages) / f"p{p:03d}.png"
        if not png.exists():
            sys.exit(f"missing {png}; run scripts/render_pages.py first")
        t0 = time.time()
        text, usage = transcribe(client, a.model, png, a.effort)
        (out / f"p{p:03d}.md").write_text(text)
        total["in"] += usage["in"]
        total["out"] += usage["out"]
        print(f"p{p:03d}  {time.time()-t0:5.1f}s  in={usage['in']} out={usage['out']}  {accent_report(text)}")
    print("total tokens", total)


if __name__ == "__main__":
    main()

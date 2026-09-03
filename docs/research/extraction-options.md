# Research: extracting stress-marked Cyrillic from the scanned PDF

Resolves issue #2. Reading research only; no OCR was run on the PDF. Facts below were checked against primary sources (tesseract docs and repos, the installed tesseract and PyMuPDF binaries, Anthropic platform docs) on 2026-09-02. Each claim cites its source.

## TL;DR recommendation

**Use route 2 — render pages with PyMuPDF at 300 dpi and transcribe them with a Claude vision model (Claude Opus 5 by default, Claude Sonnet 5 as the cheaper fallback) via the Message Batches API.** Tesseract cannot do this job on its own: the Russian LSTM model's character set contains no acute accent (neither combining U+0301 nor any precomposed stressed vowel), so tesseract `rus` is structurally unable to emit the stress marks the book prints on every stressed vowel. Keep tesseract as an optional *check* (route 3), not as the text source.

Estimated cost for ~380 pages: roughly **$25–30 with Opus 5 at standard prices, ~$13–15 via Batches**; Sonnet 5 about 40% of that. Details and assumptions in section 5.

## 1. What we are extracting

- `Russian Course (Bookmarks).pdf`: 523 pages, page box 348 × 534.48 pt (verified with PyMuPDF; `doc[8].rect`). The scanned image on PDF p. 9 is 2900 × 4454 px, i.e. the scan was made at roughly **600 dpi** (2900 px / (348 pt / 72) ≈ 600). So rendering at up to 600 dpi loses nothing; rendering above that only interpolates.
- Relevant range: PDF pp. 9–395 (~380 pages), of which 386–395 are the Grammatical Tables (per `CLAUDE.md`).
- The existing text layer was OCR'd as English and is wrong for every Cyrillic word (per `CLAUDE.md`); it must be ignored, which rules out `page.get_text()` and also PyMuPDF's partial-OCR mode (see 4.3).
- The book marks stress with an acute accent over the vowel. In Unicode that is either a combining acute (U+0301) after the base vowel, or — for ё — the letter itself (ё is always stressed). Whatever route we choose must be able to *emit* U+0301.

## 2. Route 1: tesseract 5 with `rus`

### 2.1 Local state (checked)

```
$ tesseract --version      → tesseract 5.5.0, leptonica 1.85.0
$ tesseract --list-langs   → eng, jpn, jpn_vert, osd, snum   (tessdata dir: /usr/local/share/tessdata/)
$ brew info tesseract-lang → stable 4.1.0 (bottled), Not installed
```

### 2.2 Which traineddata: `tessdata` vs `tessdata_fast` vs `tessdata_best`

From the tessdoc "Traineddata Files" page (<https://tesseract-ocr.github.io/tessdoc/Data-Files.html>):

- `tessdata_fast`: "best 'value for money' in speed vs accuracy, `Integer` models" — fastest, least accurate.
- `tessdata_best`: "best results on Google's eval data, slower, `Float` models. These are the only models that can be used as base for finetune training." — slowest, most accurate.
- `tessdata`: "legacy tesseract models from 2016. The LSTM models have been updated with Integer version of tessdata_best LSTM models." Only this set also supports the legacy (`--oem 0`) recogniser.
- "When using the traineddata files from the `tessdata_best` and `tessdata_fast` repositories, only the new LSTM-based OCR engine (–oem 1) is supported."

The `tessdata_fast` README (<https://github.com/tesseract-ocr/tessdata_fast>) adds: "Fine tuning/incremental training will **NOT** be possible from these `fast` models, as they are 8-bit integer." That matters here (see 2.4): if we ever wanted to teach tesseract the acute accent, only `tessdata_best` could serve as the base.

### 2.3 Installing on macOS

**Homebrew.** The `tesseract-lang` formula (<https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/t/tesseract-lang.rb>) downloads `https://github.com/tesseract-ocr/tessdata_fast/archive/refs/tags/4.1.0.tar.gz` (sha256 `d0e3bb6f…530f9`), deletes `eng`/`osd` (already shipped by `tesseract`), and installs every remaining language into `share/tessdata`. So `brew install tesseract-lang` gives you **`tessdata_fast` `rus`** (plus ~120 other languages, hundreds of MB):

```sh
brew install tesseract-lang          # tessdata_fast 4.1.0, all languages
tesseract --list-langs | grep rus     # expect: rus
```

**Manual (`tessdata_best`, single file).** The docs' install page for macOS says only "brew install tesseract" and that "The tesseract directory can then be found using `brew info tesseract`" (<https://tesseract-ocr.github.io/tessdoc/Installation.html>). The tessdata directory on this machine is `/usr/local/share/tessdata/` (from `--list-langs`), and `--tessdata-dir PATH` or `TESSDATA_PREFIX` can point elsewhere (`tesseract --help-extra`; FAQ <https://tesseract-ocr.github.io/tessdoc/FAQ.html>). So:

```sh
# best (float) model — ~15 MB; put it beside the existing eng.traineddata
curl -L -o /usr/local/share/tessdata/rus.traineddata \
  https://github.com/tesseract-ocr/tessdata_best/raw/main/rus.traineddata
# or keep it out of the Homebrew tree and pass --tessdata-dir
mkdir -p ~/tessdata_best && curl -L -o ~/tessdata_best/rus.traineddata \
  https://github.com/tesseract-ocr/tessdata_best/raw/main/rus.traineddata
tesseract page.png out -l rus --oem 1 --tessdata-dir ~/tessdata_best
```

(Note `--tessdata-dir` replaces the whole directory, so `eng` must be present in the same dir if you use `rus+eng`.)

### 2.4 Does `rus` recognise the acute stress accent? **No.**

The LSTM recogniser can only output symbols listed in the model's unicharset. The `rus` unicharset used to train the LSTM models (<https://github.com/tesseract-ocr/langdata_lstm/blob/main/rus/rus.unicharset>, 125 entries) contains the Cyrillic alphabet incl. Ё/ё, digits and common punctuation, and:

- **no combining acute accent U+0301**,
- **no precomposed stressed vowel** (no а́/е́/и́/о́/у́/ы́/э́/ю́/я́, no ѐ U+0450 / ѝ U+045D),
- the only accent-like glyph is the ASCII grave `` ` `` (U+0060),
- **no Latin letters at all**.

The companion `rus/desired_characters` file in the same repo lists the same inventory (ASCII punctuation, digits, typographic symbols, full Cyrillic alphabet) with no accent marks and no Latin letters.

Consequence: given a stressed `а́`, `rus` will at best emit a bare `а` (accent absorbed as noise) and at worst a stray `` ` ``, apostrophe or a wrong letter. Stress is exactly the information this project needs, so tesseract `rus` — fast *or* best — cannot be the text source. Recovering stress would require fine-tuning `tessdata_best/rus` on synthetic accented text, which is a separate project and is not being proposed here.

### 2.5 Other tesseract facts that matter if it is used for layout

- DPI: "Tesseract works best on images which have a DPI of at least 300 dpi" (<https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html>). Rendering the scan at 300 dpi gives 1450 × 2227 px; at 600 dpi (native) 2900 × 4454 px. PNGs rendered from a PDF carry no DPI metadata, so pass `--dpi 300` (tesseract 5 option; also settable as `-c user_defined_dpi=300`, both visible in `tesseract --help-extra` / `--print-parameters`).
- Page segmentation (`tesseract --help-psm`, tesseract 5.5.0): `3 auto` is the default and does its own column finding; `4 single_column` "Assume a single column of text of variable sizes"; `6 single_block`; `11 sparse_text`; `1 auto_osd` adds orientation/script detection. For the two-column example/translation blocks, try `--psm 3` first (auto layout) and fall back to cropping each column and running `--psm 4` or `6` per crop. The docs warn: "It is known tesseract has a problem to recognize text/data from tables … without custom segmentation/layout analysis" (ImproveQuality, "Tables").
- Multi-language: `-l rus+eng` (`--help-extra`: `-l LANG[+LANG]`). The docs note "The time taken for OCR as well as the output can be different based on the order of languages" (<https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html>) — list the dominant script first. Because `rus` has no Latin letters, `rus+eng` is the only way to get the English translations at all from tesseract.
- Structured output: append `tsv`, `hocr` or `alto` config names to get word boxes (Command-Line-Usage). `tsv` is the easiest to post-process for column detection.
- Binarisation: tesseract 5 added Leptonica Otsu and Sauvola (`-c thresholding_method=2` for Sauvola; `--print-parameters` shows `thresholding_method 0=Otsu,1=LeptonicaOtsu,2=Sauvola`). Worth trying on greyish scans.

## 3. Route 2: PyMuPDF page render + Claude vision

### 3.1 Rendering with PyMuPDF (installed: PyMuPDF 1.26.5 / MuPDF 1.26.10 on python3.9)

`Page.get_pixmap(matrix=None, dpi=None, colorspace=None, clip=None, alpha=None, annots=None)` — "dpi: desired dots per inch. If given, matrix is ignored"; `colorspace` accepts `gray`; `Pixmap.save()` picks the format from the extension, "Default is PNG. Others are JPEG, JPG, PNM, …" (docstrings of the installed package; <https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_pixmap>).

```python
# render.py — python3.9, PyMuPDF 1.26.5
import fitz, pathlib
doc = fitz.open("Russian Course (Bookmarks).pdf")
out = pathlib.Path("research/pages"); out.mkdir(parents=True, exist_ok=True)   # gitignored
for pno in range(8, 395):                      # PDF pp. 9–395 (0-based 8..394)
    pix = doc[pno].get_pixmap(dpi=300, colorspace="gray")   # 1450 x 2227 px
    pix.save(out / f"p{pno+1:03d}.png")
```

### 3.2 Image limits and token cost (Anthropic vision docs, <https://platform.claude.com/docs/en/build-with-claude/vision>)

- Formats: JPEG, PNG, GIF, WebP. Max 8000 × 8000 px, max 10 MB base64 per image on the Claude API; 32 MB per request; up to 600 images per request on 1M-context models (100 on 200k models), but if a request has **more than 20 images** every image must be ≤ 2000 px on each side.
- Token cost: "Each patch is a 28×28-pixel block … An image, therefore, costs ⌈width / 28⌉ × ⌈height / 28⌉ visual tokens."
- Resolution tiers: **High-resolution — "Claude 4.7 and later models" — max long edge 2576 px, max 4784 visual tokens.** Standard (all other models, incl. Haiku 4.5) — 1568 px / 1568 tokens. Larger images are downscaled to fit.
- Quality guidance: "If the image contains important text, make sure it's legible and not too small"; heavy JPEG compression "can make text difficult to read"; prefer pre-resizing so the API does not resize behind your back.
- Images should come before the text prompt ("Claude works best when images come before text").

Applied to this page box (348 × 534 pt):

| Render dpi | Pixels | Visual tokens (high-res tier) | Note |
|---|---|---|---|
| 200 | 967 × 1485 | 35 × 54 = 1,890 | ~the "1000×1500" in the ticket |
| **300** | **1450 × 2227** | **52 × 80 = 4,160** | fits under 2576 px / 4784 tokens; **recommended** |
| 350 | 1692 × 2598 | long edge > 2576 → downscaled | no gain over 300 |
| 600 (native) | 2900 × 4454 | downscaled to ≈1677 × 2576 → 4,784 | 4× the file size for no extra tokens |

On a standard-tier model (Haiku 4.5) any of these is downscaled to ≤ 1,568 tokens, i.e. roughly 950 × 1450 px — probably still legible for body text but marginal for the accents, which are the smallest marks on the page.

### 3.3 Which model

All current models "support text and image input … vision" (<https://platform.claude.com/docs/en/models/overview>). High-resolution vision (2576 px) is on Claude 4.7 and later, so: Claude Fable 5.1, Claude Opus 5, Claude Opus 4.8/4.7, Claude Sonnet 5. Haiku 4.5 is standard tier.

Recommendation: **`claude-opus-5`** as the default (Anthropic's own "start with Claude Opus 5 for most workloads"), with **`claude-sonnet-5`** as the cheap comparison model in the Lesson-5 prototype (issue #4). Fable 5.1 is 2× Opus's price and is only worth it if Opus measurably misses accents on the prototype pages. Thinking is adaptive on these models; for a transcription task set `output_config={"effort": "low"}` or `"medium"` so thinking tokens (billed as output) stay small.

Pricing (<https://platform.claude.com/docs/en/about-claude/pricing>, per MTok, input / output; Batch = 50% off both): Fable 5.1 $10 / $50 (batch $5 / $25); Opus 5 $5 / $25 (batch $2.50 / $12.50); Sonnet 5 $2 / $10 (batch $1 / $5); Haiku 4.5 $1 / $5 (batch $0.50 / $2.50). Note "Claude 4.7 and later models … use a newer tokenizer … approximately 30% more tokens for the same text" — relevant to the Cyrillic output side.

### 3.4 Batches API

"The Batch API allows asynchronous processing of large volumes of requests with a 50% discount on both input and output tokens." Limits: "100,000 Message requests or 256 MB in size, whichever is reached first"; "most batches completing within 1 hour … Batches expire if processing does not complete within 24 hours"; results kept 29 days; Vision is listed as supported (<https://platform.claude.com/docs/en/build-with-claude/batch-processing>). 380 pages × ~1.5 MB base64 PNG ≈ 570 MB, so either split into 3–4 batches of ≤100 pages, or upload the PNGs once with the Files API and reference `file_id`s (allowed for `image` blocks per the vision docs), which keeps each batch tiny.

### 3.5 Prompt considerations

- One page per request (not 20 pages in one request): keeps each output small, avoids the >20-image 2000 px rule, and makes retries page-granular.
- Ask for a faithful transcription in Markdown, not an interpretation: keep headings, numbered examples, the two-column example/translation layout as a table or `example — translation` lines, tables as Markdown tables, and page-header/footer text separated.
- Say explicitly: "Every stressed vowel in the source carries an acute accent. Reproduce it as the base vowel followed by U+0301 (combining acute), e.g. `сло́во`. Never omit it, never move it, never add one where the print has none. ё never takes an accent." Ask the model to flag words where the accent is unreadable rather than guessing (e.g. `сло(?)во`).
- Ask it to keep Latin/English text as-is, and to output NFD or NFC consistently (pick NFC with U+0301 kept separate; there are no precomposed Cyrillic-with-acute code points other than ѐ/ѝ, so normalisation will not collapse them).
- Post-process: a regex sanity check that every Cyrillic word of ≥2 syllables in an example line has exactly one U+0301 (or a ё) catches most misses cheaply.

### 3.6 Sketch of the call (Python SDK; `anthropic` 0.116.0 is installed for python3.9 — 1.x needs Python ≥ 3.10; python3.10–3.12 are on this Mac without the SDK)

```python
import anthropic, base64, pathlib
client = anthropic.Anthropic()          # ANTHROPIC_API_KEY or `ant auth login`
SYSTEM = open("prompts/transcribe.md").read()

def request(png: pathlib.Path):
    return {
        "custom_id": png.stem,           # p009 … p395
        "params": {
            "model": "claude-opus-5",
            "max_tokens": 8000,
            "output_config": {"effort": "low"},
            "system": SYSTEM,
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                             "data": base64.b64encode(png.read_bytes()).decode()}},
                {"type": "text", "text": "Transcribe this page."},
            ]}],
        },
    }

pngs = sorted(pathlib.Path("research/pages").glob("p*.png"))
for i in range(0, len(pngs), 100):       # ≤100 pages/batch keeps well under 256 MB
    batch = client.messages.batches.create(requests=[request(p) for p in pngs[i:i+100]])
    print(batch.id)
# later: poll client.messages.batches.retrieve(id).processing_status == "ended",
# then client.messages.batches.results(id), keyed by custom_id (results arrive in any order).
```

## 4. Route 3: hybrid (tesseract for layout, Claude for text)

### 4.1 What tesseract can contribute

Even without accents, `tesseract page.png out -l rus+eng --psm 3 --dpi 300 tsv` returns block/paragraph/line/word boxes with (accent-less) text. Uses:

- **Column detection**: cluster word boxes by x-position to find the two-column example/translation regions, then crop each column and send crops (or the full page plus the box list) to Claude. This can help when the model merges the two columns.
- **Diff check**: strip U+0301 from Claude's output and compare with tesseract's text per line; disagreements point to pages worth eyeballing. Note tesseract `rus` will itself be noisy on accented words (2.4), so expect false positives exactly on the words we care about.
- **Page classification**: cheap detection of nearly-blank pages, tables (`textord_tabfind_find_tables` is on by default), or pages that are all-English (skip / cheaper model).

### 4.2 Verdict

Worth it only as a *verification* layer or if the prototype shows Claude scrambling columns. It does not reduce cost meaningfully (the vision call still has to see the whole page to read accents), and it adds a dependency (`tesseract-lang` or a manual `rus.traineddata`) plus a coordinate-mapping step. Ticket #3 ("install a Russian tesseract model and a page-render harness") should therefore be re-scoped: the page-render harness is needed; the Russian model is optional and only for 4.1-style checks.

### 4.3 PyMuPDF's built-in tesseract path is not the right tool here

`Page.get_textpage_ocr(flags=0, language="eng", dpi=72, full=False, tessdata=None)` exists (installed source, `pymupdf/utils.py`). With `full=False` it "OCR[s] … only its images (default)" and *extends the normal text page*, i.e. it would keep the bad English text layer; with `full=True` it renders the page at `dpi` and OCRs the whole thing. It needs tesseract's tessdata via the `tessdata` argument, `TESSDATA_PREFIX`, or auto-discovery from `tesseract --list-langs` (`pymupdf.get_tessdata`), and the docs say the auto-discovery "should probably not be relied upon" (<https://pymupdf.readthedocs.io/en/latest/installation.html>, "Enabling Integrated OCR Support"). It inherits the same unicharset limitation as the CLI, so it cannot produce accents either. Use it only if the hybrid route is adopted and you prefer Python over the CLI.

## 5. Cost and time estimate (~380 pages)

Assumptions: 300 dpi greyscale PNG per page → 4,160 visual tokens + ~400 tokens of prompt; output ≈ 2,000 tokens per page (a dense grammar page is ~350–450 words; Cyrillic on the 4.7+ tokenizer is several tokens per word; add a little thinking at `effort: low`). Prices from 3.3.

| Model | Input/page | Output/page | ≈ per page | 380 pages, standard | 380 pages, Batch |
|---|---|---|---|---|---|
| Claude Opus 5 | 4,560 × $5/M = $0.023 | 2,000 × $25/M = $0.050 | $0.073 | **≈ $28** | **≈ $14** |
| Claude Sonnet 5 | $0.009 | $0.020 | $0.029 | ≈ $11 | ≈ $5.5 |
| Claude Fable 5.1 | $0.046 | $0.100 | $0.146 | ≈ $55 | ≈ $28 |
| Claude Haiku 4.5 (std tier, ≤1,568 img tokens) | $0.002 | $0.010 | $0.012 | ≈ $4.5 | ≈ $2.3 |

Output length is the dominant uncertainty (±50% on the totals). Even the worst case (Fable 5.1, standard, long outputs) is under $100, so model choice should be driven by accent accuracy on the prototype, not by cost. Time: batches "most … completing within 1 hour"; rendering 380 pages at 300 dpi with PyMuPDF is a couple of minutes. Tesseract at 300 dpi is a few seconds per page with `tessdata_best`, faster with `fast`.

## 6. Recommendation and next steps

1. **Adopt route 2** (PyMuPDF 300 dpi greyscale PNG → Claude vision, one page per request, Batches API, `claude-opus-5` default). Tesseract `rus` is disqualified as a text source because its unicharset has no acute accent (2.4).
2. In the Lesson-5 prototype (#4), run the same pages through `claude-opus-5` and `claude-sonnet-5` with the same prompt and count accent errors against the scan by hand; pick the cheapest model with zero systematic accent loss. Also try 200 dpi vs 300 dpi once, to confirm 300 is worth the 2.2× input tokens.
3. Re-scope #3: the page-render harness (3.1) is required; installing a Russian tesseract model is optional and only for the hybrid checks in 4.1. If it is installed, `brew install tesseract-lang` (tessdata_fast) is fine for layout/diff purposes; `tessdata_best` is only needed if anyone ever fine-tunes.
4. Keep rendered pages in `research/pages/` (already gitignored) and store transcriptions per page (e.g. `research/text/p009.md`) so re-runs are page-granular.

## Sources

- tessdoc, Traineddata Files: <https://tesseract-ocr.github.io/tessdoc/Data-Files.html>
- tessdoc, Improving quality: <https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html>
- tessdoc, Command line usage: <https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html>
- tessdoc, Installation (macOS) and FAQ: <https://tesseract-ocr.github.io/tessdoc/Installation.html>, <https://tesseract-ocr.github.io/tessdoc/FAQ.html>
- tessdata_fast README: <https://github.com/tesseract-ocr/tessdata_fast>; tessdata_best README: <https://github.com/tesseract-ocr/tessdata_best>
- langdata_lstm `rus/rus.unicharset` and `rus/desired_characters`: <https://github.com/tesseract-ocr/langdata_lstm/tree/main/rus>
- Homebrew `tesseract-lang` formula: <https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/t/tesseract-lang.rb>
- Local: `tesseract --version`, `--list-langs`, `--help-extra`, `--help-psm`, `--help-oem`, `--print-parameters`; `brew info tesseract tesseract-lang`
- PyMuPDF docs: <https://pymupdf.readthedocs.io/en/latest/page.html>, <https://pymupdf.readthedocs.io/en/latest/recipes-ocr.html>, <https://pymupdf.readthedocs.io/en/latest/installation.html>; installed package docstrings/source (PyMuPDF 1.26.5)
- Anthropic vision: <https://platform.claude.com/docs/en/build-with-claude/vision>
- Anthropic models overview: <https://platform.claude.com/docs/en/models/overview>
- Anthropic pricing: <https://platform.claude.com/docs/en/about-claude/pricing>
- Anthropic batch processing: <https://platform.claude.com/docs/en/build-with-claude/batch-processing>

#!/usr/bin/env python3
"""Stitch transcripts/pNNN.md into a single self-contained index.html.

    .venv/bin/python scripts/build.py            # writes ./index.html
    .venv/bin/python scripts/build.py --out x.html

Pipeline: read every page transcript in PDF order, drop page furniture, join pages
(re-joining paragraphs split across a page break), classify lines into blocks, apply the
cut rule (Vocabulary / EXERCISE / COMPREHENSION / REVISION / handwriting blocks never reach
the page), and render the decided design: sticky strip, collapsed TOC grid, the
Grammatical Tables hoisted under the TOC, striped two-column examples, footnotes per
section, dialogues, light + dark themes, fonts inlined as base64 woff2.
"""
import argparse
import base64
import html
import pathlib
import re
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRANSCRIPTS = ROOT / "transcripts"
FONTS = ROOT / "assets" / "fonts"

LESSON_PAGES = range(9, 386)     # PDF pages holding Lessons 1–30
TABLES_PAGES = range(386, 396)   # Grammatical Tables + Four Spelling Rules

CUT_HEADINGS = re.compile(
    r"^(EXERCISE|COMPREHENSION EXERCISE|REVISION|HANDWRITING EXERCISE|PRONUNCIATION EXERCISE|FUN SECTION)", re.I)
VOCAB_HEADING = re.compile(r"^\d+\.\d+\s+Vocabulary", re.I)
LESSON_RE = re.compile(r"^## (\d+) (.+)$")
SECTION_RE = re.compile(r"^### (\d+)\.(\d+)\s+(.*)$")
OTHER_H3_RE = re.compile(r"^### (.+)$")
CYR = "А-Яа-яЁё"
EXAMPLE_RE = re.compile(rf"^(?P<ru>[^|].*?) — (?P<en>.+)$")
DIALOGUE_RE = re.compile(r"^(?:(?P<num>\d+)\.\s+)?(?P<sp>[A-Z][A-Za-z]{0,2}):\s+(?P<text>.+)$")
DIALOGUE_CONT_RE = re.compile(r"^\s{2,}(?P<sp>[A-Z][A-Za-z]{0,2}):\s+(?P<text>.+)$")
FOOTDEF_RE = re.compile(r"^\[\^(\w+)\]:\s*(.*)$")
FOOTREF_RE = re.compile(r"\[\^(\w+)\]")
GUIDE_RE = re.compile(r"\s?\[(?=[^\]]*[A-Za-z])[^\]А-Яа-яЁё]+\]")
XREF_RE = re.compile(r"(?<![\d.])(\d{1,2})\.(\d{1,2})(?![\d.])")


# ----------------------------------------------------------------------------- reading

def read_pages(pages):
    """Return the joined text of the given PDF pages, furniture stripped."""
    chunks = []
    for p in pages:
        f = TRANSCRIPTS / f"p{p:03d}.md"
        if not f.exists():
            continue
        text = unicodedata.normalize("NFC", f.read_text())
        lines = [l.rstrip() for l in text.splitlines()
                 if not re.match(r"<!-- (header|page):", l)]
        while lines and not lines[-1].strip():
            lines.pop()
        while lines and not lines[0].strip():
            lines.pop(0)
        chunks.append(lines)
    out = []
    for lines in chunks:
        if out and lines and _continues(out[-1], lines[0]):
            out[-1] = out[-1] + " " + lines[0].strip()
            lines = lines[1:]
        elif out:
            out.append("")
        out.extend(lines)
    return out


def _continues(prev, nxt):
    """Does `nxt` (first line of a page) continue the paragraph `prev` ended with?"""
    if not prev.strip() or not nxt.strip():
        return False
    if prev.startswith(("#", "|", "<!--", "[^", "**", "---")) or nxt.startswith(("#", "|", "<!--", "[^", "**", "---", "_УРО")):
        return False
    if " — " in prev or " — " in nxt or DIALOGUE_RE.match(prev) or DIALOGUE_RE.match(nxt) or re.match(r"^\d+[.)]?\s", nxt):
        return False
    if prev.rstrip().endswith((".", "!", "?", ":", "»", ")", "”", "'", "_", ";")):
        return False
    return True


# ----------------------------------------------------------------------------- inline

def inline(s, xrefs=None, lesson=None):
    """Escape and convert inline Markdown: _it_, **bold**, [^n], N.x links."""
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![A-Za-zА-Яа-яЁё0-9])_(?=\S)(.+?)(?<=\S)_(?![A-Za-zА-Яа-яЁё0-9])", r"<i>\1</i>", s)
    s = FOOTREF_RE.sub(lambda m: f'<sup class="fnref">{m.group(1)}</sup>', s)
    if xrefs is not None:
        def link(m):
            key = f"{m.group(1)}.{m.group(2)}"
            return f'<a href="#s{m.group(1)}-{m.group(2)}">{key}</a>' if key in xrefs else m.group(0)
        s = XREF_RE.sub(link, s)
    return s


def strip_guides(s):
    return GUIDE_RE.sub("", s)


# ----------------------------------------------------------------------------- blocks

class Section:
    def __init__(self, lesson, num, title, kind):
        self.lesson, self.num, self.title, self.kind = lesson, num, title, kind
        self.lines = []
        self.cut = kind == "cut"

    @property
    def anchor(self):
        return f"s{self.lesson}-{self.num}" if self.num else None


class Lesson:
    def __init__(self, num, title):
        self.num, self.title, self.ru = num, title, ""
        self.sections = []


def parse_lessons(lines):
    lessons, cur_lesson, cur_sec = [], None, None
    for line in lines:
        m = LESSON_RE.match(line)
        if m:
            cur_lesson = Lesson(int(m.group(1)), m.group(2).strip())
            lessons.append(cur_lesson)
            cur_sec = Section(cur_lesson.num, None, "", "intro")
            cur_lesson.sections.append(cur_sec)
            continue
        if cur_lesson is None:
            continue
        if re.fullmatch(r"_[^_]*[А-ЯЁ][^_]*_", line) and not cur_lesson.ru and cur_sec.kind == "intro" and not any(l.strip() for l in cur_sec.lines):
            cur_lesson.ru = line.strip("_")
            continue
        m = SECTION_RE.match(line)
        if m:
            title = m.group(3).strip()
            kind = "cut" if VOCAB_HEADING.match(f"{m.group(1)}.{m.group(2)} {title}") else "section"
            cur_sec = Section(cur_lesson.num, int(m.group(2)), title, kind)
            cur_lesson.sections.append(cur_sec)
            continue
        m = OTHER_H3_RE.match(line)
        if m:
            kind = "cut" if CUT_HEADINGS.match(m.group(1)) else "section"
            cur_sec = Section(cur_lesson.num, None, m.group(1).strip(), kind)
            cur_lesson.sections.append(cur_sec)
            continue
        if line.startswith("<!-- cut:"):
            # handwriting: everything from here to the next heading is cut
            cur_sec = Section(cur_lesson.num, None, "cut", "cut")
            cur_lesson.sections.append(cur_sec)
            continue
        cur_sec.lines.append(line)
    return lessons


def render_section_body(lines, xrefs, keep_guides):
    """Render a section's lines into HTML. Groups example rows, dialogues, tables, footnotes."""
    out, foots = [], []
    i, n = 0, len(lines)
    para = []

    def flush_para():
        if para:
            out.append(f"<p>{inline(' '.join(para), xrefs)}</p>")
            para.clear()

    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            flush_para(); i += 1; continue
        if s.startswith("<!--"):
            i += 1; continue
        if s == "---":
            flush_para(); i += 1; continue
        if s.startswith("<table"):
            flush_para()
            buf = []
            while i < n:
                buf.append(lines[i])
                if "</table>" in lines[i]:
                    i += 1; break
                i += 1
            out.append('<div class="tbl">' + "\n".join(buf) + "</div>")
            continue
        m = FOOTDEF_RE.match(s)
        if m:
            flush_para()
            foots.append((m.group(1), m.group(2)))
            i += 1; continue
        if s.startswith("|"):
            flush_para()
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip()); i += 1
            out.append(render_table(rows, xrefs))
            continue
        if re.fullmatch(r"\*\*.+\*\*", s):
            flush_para()
            out.append(f"<h4>{inline(s.strip('*'), xrefs)}</h4>")
            i += 1; continue
        m = DIALOGUE_RE.match(line) if not line.startswith(" ") else None
        if m and (m.group("num") or (i + 1 < n and DIALOGUE_CONT_RE.match(lines[i + 1]))) and " — " not in s:
            flush_para()
            items = []
            while i < n and lines[i].strip():
                mm = DIALOGUE_RE.match(lines[i]) if not lines[i].startswith(" ") else DIALOGUE_CONT_RE.match(lines[i])
                if not mm:
                    break
                if mm.groupdict().get("num"):
                    items.append([mm.group("num"), []])
                elif not items:
                    items.append(["", []])
                text = mm.group("text") if keep_guides else strip_guides(mm.group("text"))
                items[-1][1].append((mm.group("sp"), text))
                i += 1
            out.append(render_dialogue(items, xrefs))
            continue
        m = EXAMPLE_RE.match(s)
        if m and re.search(rf"[{CYR}]", m.group("ru")) and not s.startswith("#"):
            flush_para()
            rows = []
            while i < n:
                ss = lines[i].strip()
                mm = EXAMPLE_RE.match(ss)
                if not mm or not re.search(rf"[{CYR}]", mm.group("ru")):
                    break
                ru = mm.group("ru") if keep_guides else strip_guides(mm.group("ru"))
                sub = lines[i].startswith("  ")
                rows.append((ru, mm.group("en"), sub))
                i += 1
            out.append(render_examples(rows, xrefs))
            continue
        # numbered list item
        if re.match(r"^\d+[.)]\s", s) or re.match(r"^\([a-z0-9]+\)\s", s):
            flush_para()
            out.append(f'<p class="li">{inline(s if keep_guides else strip_guides(s), xrefs)}</p>')
            i += 1; continue
        para.append(s if keep_guides else strip_guides_prose(s))
        i += 1
    flush_para()
    if foots:
        out.append('<div class="fn">' + "".join(
            f'<p><sup>{html.escape(k)}</sup> {inline(v, xrefs)}</p>' for k, v in foots) + "</div>")
    return "\n".join(out)


def strip_guides_prose(s):
    # in prose only strip a guide that directly follows a Cyrillic word
    return re.sub(rf"([{CYR}́.,!?])\s?\[(?=[^\]]*[A-Za-z])[^\]А-Яа-яЁё]+\]", r"\1", s)


def render_table(rows, xrefs):
    cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r":?-+:?", c or "-") for c in r)]
    if not cells:
        return ""
    head, body = cells[0], cells[1:]
    has_head = any(head)
    h = "<table>"
    if has_head:
        h += "<thead><tr>" + "".join(f"<th>{inline(c, xrefs)}</th>" for c in head) + "</tr></thead>"
    else:
        body = cells
    h += "<tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c, xrefs)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table>"
    return f'<div class="tbl">{h}</div>'


def render_examples(rows, xrefs):
    h = ['<div class="ex">']
    for ru, en, sub in rows:
        h.append(f'<div class="row{" sub" if sub else ""}"><div class="r">{inline(ru, xrefs)}</div><div class="e">{inline(en, xrefs)}</div></div>')
    h.append("</div>")
    return "".join(h)


def render_dialogue(items, xrefs):
    h = ['<div class="dlg">']
    for num, turns in items:
        h.append('<div class="turns">')
        if num:
            h.append(f'<span class="dn">{num}</span>')
        for sp, text in turns:
            h.append(f'<div class="turn"><span class="sp">{sp}:</span> {inline(text, xrefs)}</div>')
        h.append("</div>")
    h.append("</div>")
    return "".join(h)


# ----------------------------------------------------------------------------- tables block

def render_tables_block(lines):
    """Grammatical Tables pages: every heading starts a card; raw <table> and Markdown tables pass through."""
    cards, cur = [], None
    buf = []

    def flush():
        nonlocal buf
        if cur is not None:
            cur["body"].extend(buf)
        buf = []

    for line in lines:
        if line.startswith("#"):
            flush()
            title = line.lstrip("#").strip()
            if line.startswith("## ") or line.startswith("# "):
                cur = {"title": title, "body": [], "level": 2}
            else:
                cur = {"title": title, "body": [], "level": 3}
            cards.append(cur)
        else:
            buf.append(line)
    flush()
    out = []
    for c in cards:
        body = render_section_body(c["body"], set(), True)
        anchor = "t-" + re.sub(r"[^a-z0-9]+", "-", c["title"].lower()).strip("-")
        out.append(f'<div class="card" id="{anchor}"><h4>{inline(c["title"])}</h4>{body}</div>')
    return "\n".join(out), [(c["title"], "t-" + re.sub(r"[^a-z0-9]+", "-", c["title"].lower()).strip("-")) for c in cards]


# ----------------------------------------------------------------------------- page

def font_css():
    css = (FONTS / "fonts.css").read_text()

    def embed(m):
        data = base64.b64encode((FONTS / m.group(1)).read_bytes()).decode()
        return f"url(data:font/woff2;base64,{data})"
    return re.sub(r"url\(([^)]+\.woff2)\)", embed, css)


CSS = """
:root { --bg:#ffffff; --fg:#17202a; --muted:#5f6b7a; --link:#0b57d0; --accent:#ffd166; --accent-fg:#111;
  --line:#e3e8ee; --line2:#eef1f4; --panel:#f3f5f8; --card:#fff; --strip:#17202a; --strip-fg:#fff; --th:#f3f5f8; --stripe:#fafbfc; --h:#17202a; }
[data-theme=dark] { --bg:#1a1a1a; --fg:#d8d8d0; --muted:#999; --link:#8fb8ff; --accent:#f0c674; --accent-fg:#111;
  --line:#3a3a3a; --line2:#2c2c2c; --panel:#222; --card:#1e1e1e; --strip:#0f0f0f; --strip-fg:#e8e8e0; --th:#2a2a2a; --stripe:#202020; --h:#fff; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:17px/1.6 "PT Sans", system-ui, sans-serif; padding-bottom:140px; }
a { color:var(--link); text-decoration:none; } a:hover { text-decoration:underline; }
.strip { position:sticky; top:0; z-index:10; background:var(--strip); color:var(--strip-fg); border-bottom:1px solid var(--line); display:flex; gap:24px; align-items:center; padding:10px 24px; font-size:13px; }
.strip a { color:var(--strip-fg); opacity:.8; } .strip a:hover { opacity:1; }
.strip .now { margin-left:auto; color:var(--accent); font-variant-numeric:tabular-nums; }
.strip button { background:transparent; color:var(--strip-fg); border:1px solid var(--strip-fg); border-radius:999px; padding:2px 10px; font:inherit; cursor:pointer; opacity:.8; }
.strip button:hover { opacity:1; }
.wrap { max-width:960px; margin:0 auto; padding:0 24px; }
h1 { font:600 44px/1 "Vollkorn", Georgia, serif; margin:40px 0 8px; color:var(--h); }
.sub { color:var(--muted); margin-bottom:24px; }
.toc { display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:8px 24px; margin-bottom:32px; }
.toc details { border-bottom:1px solid var(--line); }
.toc summary { cursor:pointer; padding:6px 0; display:flex; gap:10px; list-style:none; }
.toc summary::-webkit-details-marker { display:none; }
.toc summary .n { background:var(--line); color:var(--fg); font-size:11px; padding:2px 6px; border-radius:3px; align-self:center; font-variant-numeric:tabular-nums; min-width:24px; text-align:center; }
.toc details ol { margin:0 0 8px; padding-left:44px; font-size:13px; color:var(--muted); list-style:none; }
.tables { background:var(--panel); border-radius:12px; padding:20px 24px; margin:0 0 48px; }
.tables h2 { margin:0 0 12px; font:600 22px/1 "Vollkorn", Georgia, serif; color:var(--h); }
.tables .tindex { font-size:13px; margin:0 0 16px; color:var(--muted); }
.tables .tindex a { margin-right:12px; white-space:nowrap; }
.cards { display:grid; grid-template-columns:repeat(auto-fill, minmax(420px, 1fr)); gap:16px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 16px; overflow-x:auto; }
.card h4 { margin:0 0 6px; font-size:13px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
.card p { font-size:14px; margin:6px 0; }
.tbl { overflow-x:auto; margin:8px 0 14px; }
table { border-collapse:collapse; font-size:14px; width:100%; }
th, td { padding:4px 8px; text-align:left; border:1px solid var(--line); vertical-align:top; }
th { background:var(--th); font-weight:500; color:var(--muted); }
tbody tr:nth-child(even) td { background:var(--stripe); }
td:first-child { color:var(--muted); }
h2.lesson { font:600 34px/1.1 "Vollkorn", Georgia, serif; margin:56px 0 4px; color:var(--h); border-bottom:1px solid var(--line); padding-bottom:8px; scroll-margin-top:48px; }
h2.lesson .ru { display:block; font:700 13px/1 "PT Sans", sans-serif; color:var(--muted); letter-spacing:.1em; margin-top:8px; }
h3 { font-size:18px; margin:32px 0 8px; display:flex; gap:10px; align-items:baseline; scroll-margin-top:48px; color:var(--h); }
h3 .num { font:500 12px/1 "IBM Plex Mono", monospace; background:var(--accent); color:var(--accent-fg); padding:3px 6px; border-radius:3px; white-space:nowrap; }
h4 { font-size:14px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); margin:20px 0 6px; }
p { margin:10px 0; } p.li { margin:4px 0 4px 1.5em; text-indent:-1.5em; }
.ex { margin:8px 0 14px; border:1px solid var(--line); border-radius:8px; overflow:hidden; }
.ex .row { display:grid; grid-template-columns:1fr 1fr; gap:24px; padding:6px 12px; border-top:1px solid var(--line2); }
.ex .row:first-child { border-top:0; }
.ex .row:nth-child(even) { background:var(--stripe); }
.ex .row.sub .r { padding-left:1.5em; }
.ex .r { font-weight:500; color:var(--h); } .ex .e { color:var(--muted); }
.fn { font-size:13px; color:var(--muted); background:var(--panel); padding:8px 12px; border-radius:6px; margin-top:12px; }
.fn p { margin:4px 0; }
sup.fnref { color:var(--link); font-size:.7em; }
.dlg { margin:8px 0 14px; }
.dlg .turns { display:grid; grid-template-columns:28px 1fr; margin:6px 0; }
.dlg .dn { color:var(--muted); grid-row:1 / span 20; }
.dlg .turn { grid-column:2; }
.dlg .sp { color:var(--muted); display:inline-block; width:2.2em; }
details.tr summary { cursor:pointer; color:var(--link); font-size:14px; }
.cutnote { color:var(--muted); font-size:13px; font-style:italic; }
"""

JS = """
(function(){
  const root=document.documentElement, btn=document.getElementById('theme');
  function apply(t){ root.setAttribute('data-theme',t); btn.textContent = t==='dark' ? '☀ Light' : '☾ Dark'; }
  let t=null; try{ t=localStorage.getItem('theme'); }catch(e){}
  if(!t) t = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  apply(t);
  btn.onclick=()=>{ t = t==='dark'?'light':'dark'; apply(t); try{ localStorage.setItem('theme',t);}catch(e){} };
  const now=document.getElementById('now'), heads=[...document.querySelectorAll('h2.lesson,h3[id]')];
  const obs=new IntersectionObserver(es=>{ es.forEach(e=>{ if(e.isIntersecting) now.textContent=e.target.dataset.label; }); },{rootMargin:'-40px 0px -80% 0px'});
  heads.forEach(h=>obs.observe(h));
  // open the TOC entry for the lesson in the URL hash
  function openHash(){ const h=location.hash.slice(1); if(!h) return; const m=h.match(/^(?:lesson-|s)(\\d+)/); if(m){ const d=document.getElementById('toc-'+m[1]); if(d) d.open=true; } }
  openHash(); addEventListener('hashchange', openHash);
})();
"""


def build(out_path):
    lines = read_pages(LESSON_PAGES)
    lessons = parse_lessons(lines)
    xrefs = {f"{s.lesson}.{s.num}" for L in lessons for s in L.sections if s.num and not s.cut}

    # ---- TOC
    toc = ['<div class="toc">']
    for L in lessons:
        toc.append(f'<details id="toc-{L.num}"><summary><span class="n">{L.num}</span><a href="#lesson-{L.num}">{inline(L.title)}</a></summary><ol>')
        for s in L.sections:
            if s.num and not s.cut:
                toc.append(f'<li><a href="#{s.anchor}">{L.num}.{s.num} {inline(s.title)}</a></li>')
        toc.append("</ol></details>")
    toc.append("</div>")

    # ---- Tables block
    tlines = read_pages(TABLES_PAGES)
    cards_html, card_index = render_tables_block(tlines)
    tindex = " ".join(f'<a href="#{a}">{inline(t)}</a>' for t, a in card_index)
    tables = f'<div class="tables" id="tables"><h2>Grammatical Tables</h2><p class="tindex">{tindex}</p><div class="cards">{cards_html}</div></div>'

    # ---- Lessons
    body = []
    for L in lessons:
        keep_guides = L.num <= 2
        body.append(f'<h2 class="lesson" id="lesson-{L.num}" data-label="Lesson {L.num}">{L.num} {inline(L.title)}<span class="ru">{inline(L.ru)}</span></h2>')
        for s in L.sections:
            if s.cut:
                continue
            if s.kind == "intro":
                body.append(render_section_body(s.lines, xrefs, keep_guides))
                continue
            label = f"{L.num}.{s.num}" if s.num else ""
            title = inline(s.title, xrefs)
            if s.num:
                body.append(f'<h3 id="{s.anchor}" data-label="{label} {html.escape(s.title, quote=True)}"><span class="num">{label}</span>{title}</h3>')
            else:
                body.append(f'<h3 data-label="{html.escape(s.title, quote=True)}">{title}</h3>')
            body.append(render_section_body(s.lines, xrefs, keep_guides))

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Russian Grammar</title>
<style>
{font_css()}
{CSS}
</style>
</head>
<body>
<div class="strip"><a href="#top">↑ Top</a><a href="#tables">Tables</a><span class="now" id="now"></span><button id="theme" type="button">☾ Dark</button></div>
<div class="wrap" id="top">
<h1>Russian Grammar</h1>
<div class="sub">The New Penguin Russian Course (Nicholas J. Brown), trimmed to explanations and examples.</div>
{''.join(toc)}
{tables}
{''.join(body)}
</div>
<script>{JS}</script>
</body>
</html>
"""
    out_path.write_text(page)
    n_sec = sum(1 for L in lessons for s in L.sections if s.num and not s.cut)
    print(f"{out_path}: {len(lessons)} lessons, {n_sec} sections, {len(card_index)} table cards, {out_path.stat().st_size//1024} KB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "index.html"))
    a = ap.parse_args()
    build(pathlib.Path(a.out))

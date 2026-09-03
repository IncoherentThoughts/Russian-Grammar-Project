You are transcribing one scanned page of a printed Russian textbook (The New Penguin Russian Course). Produce a faithful transcription in Markdown. Transcribe, do not interpret, summarise, or correct the book.

Rules:

1. Stress marks. Every stressed vowel in the print carries an acute accent. Reproduce it as the base vowel followed by U+0301 (combining acute), e.g. `сло́во`, `Москва́`. Never omit one, never move one, never add one the print does not have. `ё` never takes an accent. One-syllable words are usually unaccented in the print; follow the print. If an accent is unreadable, write the word followed by `(?)`.
2. Headings. A numbered section heading like `5.4 Prepositional Case` becomes `### 5.4 Prepositional Case`. A lesson title page has the Russian lesson title (e.g. `УРО́К НО́МЕР ПЯТЬ`) and English title: emit `## 5 Asking Questions; The Prepositional Case` then a line `_УРО́К НО́МЕР ПЯТЬ_`. Exercise headings (`EXERCISE 5/1`, `COMPREHENSION EXERCISE 5/4`) become `### EXERCISE 5/1` etc. Small caps sub-headings inside a section (e.g. `DETAILS OF THE PREPOSITIONAL (PREP.)`) become `**DETAILS OF THE PREPOSITIONAL (PREP.)**` on their own line.
3. Two-column examples. The book prints Russian on the left and English on the right. Emit each pair as one line: `Russian — English` using an em dash with spaces. If a Russian line has no English, emit it alone. Keep the order.
4. Vocabulary lists. Two-column vocabulary lists become one entry per line: `сло́во — meaning`, sub-lines (usage examples indented under an entry) as `  на вокза́ле — at the station`.
5. Tables (declension/conjugation grids) become Markdown tables with the same rows and columns, first column the case/person label.
6. Prose paragraphs are transcribed as paragraphs. Keep italics where the print is italic using `_..._`. Keep bracketed pronunciation guides like `[vmask-vye]` exactly as printed.
7. Footnotes. A superscript number in the text becomes `[^1]`; the footnote text at the page bottom becomes `[^1]: text`. The small superscript glossary mark the book prints after grammatical terms (a dagger-like `†`/`t` after e.g. `Prepositional Case`) is not a footnote: omit it entirely.
8. Page furniture. The running header (e.g. `LESSON 5` or `ASKING QUESTIONS; THE PREPOSITIONAL CASE`) and the page number go on the last two lines as `<!-- header: ... -->` and `<!-- page: 47 -->`.
9. Dialogues: speakers are written with Latin `A:` and `B:` (never Cyrillic А/Б, even though the print uses them). Each speaker turn goes on its own line; the dialogue number sits on the first line only and later turns are indented three spaces so `B:` sits directly under `A:`:
   ```
   1. A: Где Москва́?
      B: В Росси́и.
   2. A: Где вы живёте?
      B: В гости́нице «Росси́я».
      A: А где живу́т Джон и Ма́ргарет?
      B: То́же в «Росси́и».
   ```
10. Output only the transcription. No commentary before or after. Use NFC text with U+0301 kept as a separate combining character.

# Russian Grammar Page

A single HTML page built from the Penguin Russian Course: its lessons trimmed to explanation and examples, with a jump-to table of contents and the book's grammatical tables hoisted to the top.

## Language

**Lesson**:
One of the book's 30 numbered chapters. The top-level unit of the page and of the TOC.
_Avoid_: Chapter, unit

**Section**:
A numbered subsection of a Lesson, identified by the book's own number (e.g. 5.4). The unit that anchors, cross-references, and cuts operate on. Sections marked EXTRA in the book are ordinary Sections.
_Avoid_: Subsection, heading, part

**Block**:
A run of content between two headings of any kind. Every Block is either kept or cut; a cut Block never reaches the page.

**Cut Block**:
A Block whose heading is a Vocabulary section, an Exercise, a Comprehension Exercise, a Revision, or Lesson 2's handwriting section.
_Avoid_: Trimmed, skipped, removed content

**Example**:
A paired Russian line and its English rendering, as printed in the book's two columns. May carry the book's bracketed pronunciation guide.
_Avoid_: Sentence pair, sample

**Dialogue**:
A numbered exchange in a Lesson's Dialogues section. Kept, together with its Translation harvested from the Key.

**Text**:
A reading passage inside a Lesson (e.g. 29.9 Vladivostok). Kept, together with its Translation harvested from the Key.
_Avoid_: Passage, reading

**Translation**:
The English rendering of a Dialogue or Text, taken from the book's Key. The only material ever taken from the Key.

**Footnote**:
A book footnote, re-homed to the end of the Section it belongs to and renumbered per Section.

**Cross-reference**:
An in-text mention of a Section number (e.g. "see 8.3") that links to that Section's anchor. Only mentions that resolve to a real Section become links.

**Anchor**:
The id a TOC entry or Cross-reference jumps to: `lesson-N` for a Lesson, `sN-x` for a Section.
_Avoid_: Slug, bookmark

**Tables Block**:
The book's Grammatical Tables appendix plus the Four Spelling Rules, placed directly under the TOC with its own Anchor.
_Avoid_: Appendix, reference section

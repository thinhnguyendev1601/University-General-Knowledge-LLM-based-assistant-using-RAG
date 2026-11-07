"""Structure-aware chunker (struct-v1).

Two modes, picked per document:
  legal   : >= 3 "Điều N." / "Article N:" headings -> one chunk per article (split further only
            if it exceeds the cap). Chapters ("Chương I", "CHAPTER 1") go into section_path.
  heading : handbooks -> short standalone lines are headings; small sections are packed
            together up to the target size.

Never cleans text: every chunk is an exact slice, chunk.text == canonical[start:end]
(the invariant in core/schemas.py). Sizes are in words (~1.3 bge-m3 tokens per word).
"""
from __future__ import annotations

import bisect
import json
import re
from dataclasses import dataclass
from pathlib import Path

from core.schemas import Chunk, make_chunk_id

TARGET_WORDS = 300  # ~400 tokens
CAP_WORDS = 450     # ~600 tokens, hard cap
MIN_WORDS = 60      # heading-mode sections smaller than this get packed with neighbours
SMALL_WORDS = 20    # any piece smaller than this (page footer, lone heading) is folded into a neighbour

_TOC = re.compile(r"\.{4,}|…{2,}|(\.\s){4,}")  # table-of-contents dot leaders
_ARTICLE = re.compile(r"^[ \t]*(Điều|ĐIỀU|Article|ARTICLE)\s+\d+[a-z]?\s*[.:]", re.M)
_CHAPTER = re.compile(r"^[ \t]*(Chương|CHƯƠNG|Chapter|CHAPTER|Phần|PHẦN)\s+([IVXLC]+|\d+)\b.*$", re.M)
_NUMBERED = re.compile(r"^([IVXLC]+|\d+(\.\d+)*)[.)]\s+\S")


@dataclass
class _Sec:
    start: int
    end: int
    path: list[str]


def _words(s: str) -> int:
    return len(s.split())


def _trim(text: str, a: int, b: int) -> tuple[int, int]:
    """Shrink [a, b) so it starts and ends on non-whitespace (still an exact slice)."""
    while a < b and text[a].isspace():
        a += 1
    while b > a and text[b - 1].isspace():
        b -= 1
    return a, b


def _line_at(text: str, pos: int) -> str:
    end = text.find("\n", pos)
    return text[pos: end if end >= 0 else len(text)].strip()


def _chapter_label(text: str, m: re.Match) -> str:
    """'Chương I' alone on its line -> 'Chương I. QUY ĐỊNH CHUNG' (title is on the next line)."""
    label = m.group(0).strip()
    if len(label.split()) <= 2:
        nxt = text[m.end():].lstrip("\n")
        title = _line_at(nxt, 0)
        if title and title.upper() == title and len(title) < 120:
            label = f"{label}. {title}"
    return label[:120]


# ------------------------------------------------------------------ section finding
def _legal_sections(text: str) -> list[_Sec]:
    marks: list[tuple[int, int, str]] = []  # (pos, level, label)
    for m in _CHAPTER.finditer(text):
        if not _TOC.search(m.group(0)):
            marks.append((m.start(), 1, _chapter_label(text, m)))
    for m in _ARTICLE.finditer(text):
        line = _line_at(text, m.start())
        if not _TOC.search(line):
            marks.append((m.start(), 2, line[:120]))
    marks.sort()
    secs, chapter, pending = [], None, None
    first = marks[0][0] if marks else len(text)
    if text[:first].strip():
        secs.append(_Sec(0, first, []))  # preamble (title page, decision text)
    for i, (pos, level, label) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        if level == 1:
            chapter = label
            # chapter heading with no body of its own -> folded into the next article's chunk
            if i + 1 < len(marks) and marks[i + 1][1] == 2 and _words(text[pos:end]) < MIN_WORDS:
                pending = pos
                continue
            secs.append(_Sec(pos, end, [chapter]))
        else:
            start = pending if pending is not None else pos
            pending = None
            secs.append(_Sec(start, end, [p for p in (chapter, label) if p]))
    return secs


def _is_heading(block: str) -> bool:
    s = block.strip()
    if "\n" in s or not (3 <= len(s) <= 80) or _TOC.search(s):
        return False
    if s.isdigit() or not any(c.isalpha() for c in s) or s[-1] in ".,;:)":
        return False
    return bool(_NUMBERED.match(s)) or s.upper() == s or (s[0].isupper() and len(s.split()) <= 8)


def _heading_level(s: str) -> int:
    s = s.strip()
    return 1 if _NUMBERED.match(s) or s.upper() == s else 2


def _heading_sections(text: str) -> list[_Sec]:
    secs, path, cur_start = [], [], 0
    lines = list(re.finditer(r"[^\n]*", text))
    for i, m in enumerate(lines):
        line = m.group(0)
        if not line.strip() or not _is_heading(line):
            continue
        prev_blank = m.start() == 0 or text[:m.start()].endswith("\n\n")
        nxt = text[m.end():m.end() + 2]
        standalone = nxt.startswith("\n\n") or m.end() >= len(text.rstrip())
        # a heading starts after a blank line; it may be followed directly by text only if it is
        # clearly a top-level heading ("III. Survival Tips" + "Get to know your campus")
        if not prev_blank or not (standalone or _heading_level(line) == 1):
            continue
        if text[cur_start:m.start()].strip():
            secs.append(_Sec(cur_start, m.start(), list(path)))
        h = line.strip()
        path = [h] if _heading_level(h) == 1 else (path[:1] + [h])
        cur_start = m.start()
    if text[cur_start:].strip():
        secs.append(_Sec(cur_start, len(text), list(path)))
    # pack small neighbours up to the target (handbooks have many tiny sections)
    packed: list[_Sec] = []
    for s in secs:
        if packed and _words(text[packed[-1].start:packed[-1].end]) < MIN_WORDS \
                and _words(text[packed[-1].start:s.end]) <= TARGET_WORDS:
            packed[-1].end = s.end
        else:
            packed.append(s)
    return packed


# ------------------------------------------------------------------ size control
def _split_big(text: str, a: int, b: int) -> list[tuple[int, int]]:
    """Split [a, b) at paragraph, then line, then word boundaries so no piece exceeds the cap."""
    if _words(text[a:b]) <= CAP_WORDS:
        return [(a, b)]
    for sep in ("\n\n", "\n", " "):
        cuts = [m.end() for m in re.finditer(re.escape(sep), text[a:b])]
        if not cuts:
            continue
        out, s, last = [], a, a
        for c in cuts:
            c += a
            if _words(text[s:c]) > TARGET_WORDS and last > s:
                out.append((s, last))
                s = last
            last = c
        out.append((s, b))
        if len(out) > 1:
            return [p for x, y in out for p in _split_big(text, x, y)]
    return [(a, b)]


def chunk_document(doc_id: str, text: str, lang: str = "en", doc_version: str = "1",
                   page_starts: list[int] | None = None) -> list[Chunk]:
    legal = len(_ARTICLE.findall(text)) >= 3
    secs = _legal_sections(text) if legal else _heading_sections(text)
    mode = "legal" if legal else "heading"
    pieces = [[a, b, sec.path] for sec in secs for a, b in _split_big(text, sec.start, sec.end)]
    # fold tiny pieces forward (the next piece starts earlier); the last one folds backward.
    # Pieces tile the text, so the result is still an exact slice.
    merged: list[list] = []
    carry = None
    for i, (a, b, path) in enumerate(pieces):
        if carry is not None:
            a, carry = carry, None
        if _words(text[a:b]) < SMALL_WORDS and i + 1 < len(pieces):
            carry = a
            continue
        if _words(text[a:b]) < SMALL_WORDS and merged:
            merged[-1][1] = b
            continue
        merged.append([a, b, path])
    out: list[Chunk] = []
    for a, b, path in merged:
        a, b = _trim(text, a, b)
        if b <= a or not any(c.isalnum() for c in text[a:b]):
            continue
        pages = {}
        if page_starts:
            pages = {"page_start": bisect.bisect_right(page_starts, a), "page_end": bisect.bisect_right(page_starts, b - 1)}
        out.append(Chunk(chunk_id=make_chunk_id(doc_id, a, b), doc_id=doc_id, doc_version=doc_version,
                         text=text[a:b], char_start=a, char_end=b, section_path=path, lang=lang,
                         token_count=round(_words(text[a:b]) * 1.3), chunker=f"struct-v1;{mode};target={TARGET_WORDS}w;cap={CAP_WORDS}w",
                         **pages))
    return out


def chunk_file(txt: Path, lang: str = "en", doc_version: str = "1") -> list[Chunk]:
    pj = txt.with_suffix(".pages.json")
    starts = json.loads(pj.read_text(encoding="utf-8")).get("page_starts") if pj.exists() else None
    return chunk_document(txt.stem, txt.read_text(encoding="utf-8"), lang, doc_version, starts)

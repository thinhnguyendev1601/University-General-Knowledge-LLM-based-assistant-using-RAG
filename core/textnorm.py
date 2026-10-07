"""Canonical text normalisation.

RULE: every piece of text that is compared, offset-indexed, or hashed anywhere in the
project (chunks, gold evidence quotes, key facts) goes through these functions first.
Vietnamese makes this important: the same visible character can be stored precomposed
(NFC) or decomposed (NFD), and PDF extractors emit both.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

_WS_RUN = re.compile(r"[ \t\r\f\v]+")
_MANY_NL = re.compile(r"\n{3,}")
_SOFT_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")


def _dehyphenate(m: re.Match) -> str:
    # "regu-\nlation" -> "regulation"; keep real hyphens before capitals ("Vietnam-\nHCM")
    return m.group(1) + m.group(2) if m.group(2).islower() else m.group(0)


def normalize_text(s: str) -> str:
    """Canonical form used for stored document text."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")
    s = s.replace("\u2010", "-").replace("\u2011", "-")
    s = _SOFT_HYPHEN_BREAK.sub(_dehyphenate, s)
    s = _WS_RUN.sub(" ", s)
    s = re.sub(r" ?\n ?", "\n", s)
    s = _MANY_NL.sub("\n\n", s)
    return s.strip()


def collapse_ws(s: str) -> str:
    """Whitespace-insensitive form (all whitespace runs -> one space)."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def match_form(s: str) -> str:
    """Lenient form for fact matching: NFC + casefold + single spaces.
    Diacritics are KEPT on purpose (they change meaning in Vietnamese)."""
    return collapse_ws(s).casefold()


def strip_accents(s: str) -> str:
    """Only for detecting no-diacritics user input or accent-insensitive corpus grep."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


_VI_MARKED = re.compile(
    "[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]"
)


def text_quality(text: str, n_pages: int) -> dict:
    """Cheap sanity numbers to catch scanned / garbled (legacy-font) PDFs early."""
    letters = [c for c in text if c.isalpha()]
    n_letters = max(len(letters), 1)
    vi_marked = len(_VI_MARKED.findall(text))
    return {
        "n_chars": len(text),
        "chars_per_page": round(len(text) / max(n_pages, 1), 1),
        "vi_diacritic_ratio": round(vi_marked / n_letters, 4),
        "replacement_chars": text.count("\ufffd"),
        "non_letter_ratio": round(1 - len(letters) / max(len(text.replace(" ", "").replace("\n", "")), 1), 3),
    }

"""Which institution is a question about?  Detects names, abbreviations, Vietnamese names and
typos, so retrieval can be filtered to that institution's documents (small models confuse
IU / UIT / HCMUS rules when all of them are in the context).

Matching runs on a folded form (NFC, casefold, accents removed, đ->d, punctuation->space):
  - abbreviations (IU, HCMUS, UIT ...)  : exact whole-word match only. They are 1-2 edits apart
    (HCMUS / HCMUT / HCMIU), so fuzzy matching them would pick the WRONG school.
  - long names (>= 12 chars)            : exact, or fuzzy >= 90 for typos
    ("Internatinal University", "Dai hoc Quoc te" without accents).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from rapidfuzz import fuzz


@dataclass(frozen=True)
class Institution:
    id: str
    name_en: str
    name_vi: str
    doc_prefixes: tuple[str, ...]  # doc_id prefixes in data/manifest.csv
    abbrevs: tuple[str, ...] = ()
    names: tuple[str, ...] = ()  # extra long names / Vietnamese variants
    parent: str | None = None  # member school of a university system
    aliases: tuple[str, ...] = field(default=(), init=False)


INSTITUTIONS: list[Institution] = [
    Institution("iu", "International University - VNU-HCM", "Trường Đại học Quốc tế - ĐHQG-HCM", ("iu-",),
                abbrevs=("IU", "HCMIU", "IU-VNU", "ĐHQT"),
                names=("International University", "Đại học Quốc tế", "ĐH Quốc tế", "Trường Quốc tế",
                       "International University of Ho Chi Minh City"), parent="vnu-hcm"),
    Institution("uit", "University of Information Technology - VNU-HCM", "Trường Đại học Công nghệ Thông tin - ĐHQG-HCM",
                ("uit-",), abbrevs=("UIT", "ĐHCNTT", "ĐH CNTT"),
                names=("University of Information Technology", "Đại học Công nghệ Thông tin"), parent="vnu-hcm"),
    Institution("hcmus", "University of Science - VNU-HCM", "Trường Đại học Khoa học Tự nhiên - ĐHQG-HCM", ("hcmus-",),
                abbrevs=("HCMUS", "KHTN", "ĐH KHTN"),
                names=("University of Science", "Đại học Khoa học Tự nhiên", "Khoa học Tự nhiên"), parent="vnu-hcm"),
    Institution("ussh", "University of Social Sciences and Humanities - VNU-HCM",
                "Trường Đại học Khoa học Xã hội và Nhân văn - ĐHQG-HCM", ("ussh-",),
                abbrevs=("USSH", "HCMUSSH", "XHNV", "KHXH&NV"),
                names=("University of Social Sciences and Humanities", "Đại học Khoa học Xã hội và Nhân văn",
                       "Khoa học Xã hội và Nhân văn"), parent="vnu-hcm"),
    Institution("hcmut", "HCMC University of Technology - VNU-HCM", "Trường Đại học Bách khoa - ĐHQG-HCM", ("hcmut-",),
                abbrevs=("HCMUT", "BK", "ĐHBK"),
                names=("University of Technology", "Đại học Bách khoa", "Bách khoa"), parent="vnu-hcm"),
    Institution("moet", "Ministry of Education and Training (national rules)", "Bộ Giáo dục và Đào tạo (quy chế chung)",
                ("moet-",), abbrevs=("MOET", "Bộ GD&ĐT", "Bộ GDĐT", "BGDĐT"),
                names=("Bộ Giáo dục", "Bộ Giáo dục và Đào tạo", "Ministry of Education")),
    Institution("vnu-hcm", "Vietnam National University, Ho Chi Minh City", "Đại học Quốc gia TP.HCM", ("vnuhcm-",),
                abbrevs=("VNU-HCM", "VNUHCM", "ĐHQG-HCM", "ĐHQG TPHCM", "ĐHQG HCM"),
                names=("Vietnam National University Ho Chi Minh City", "Đại học Quốc gia TP.HCM",
                       "Đại học Quốc gia Thành phố Hồ Chí Minh")),
    Institution("vnu-hn", "Vietnam National University, Hanoi", "Đại học Quốc gia Hà Nội", ("vnu-starter",),
                abbrevs=("VNU-HN", "VNU Hanoi", "ĐHQGHN", "ĐHQG Hà Nội"),
                names=("Vietnam National University Hanoi", "Đại học Quốc gia Hà Nội")),
    Institution("mit", "Massachusetts Institute of Technology", "Viện Công nghệ Massachusetts", ("mit-",),
                abbrevs=("MIT",), names=("Massachusetts Institute of Technology",)),
    Institution("umn", "University of Minnesota", "Đại học Minnesota", ("umn-",),
                abbrevs=("UMN",), names=("University of Minnesota", "Minnesota")),
    Institution("princeton", "Princeton University", "Đại học Princeton", ("princeton-",),
                names=("Princeton University", "Princeton")),
    Institution("gatech", "Georgia Institute of Technology", "Viện Công nghệ Georgia", ("gatech-",),
                abbrevs=("GT",), names=("Georgia Tech", "Georgia Institute of Technology")),
]
BY_ID = {i.id: i for i in INSTITUTIONS}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", unicodedata.normalize("NFC", s).replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").casefold()
    return " ".join(re.sub(r"[^\w]+", " ", s).split())


def institution_of_doc(doc_id: str) -> str | None:
    for inst in INSTITUTIONS:
        if doc_id.startswith(inst.doc_prefixes):
            return inst.id
    return None


@dataclass
class Detection:
    ids: list[str]           # institutions the question is about (empty = not stated)
    matches: dict[str, str]  # id -> the text that matched (for the trace / UI)
    fuzzy: bool = False


def detect(query: str) -> Detection:
    q = fold(query)
    padded = f" {q} "
    hits: dict[str, tuple[str, bool]] = {}
    for inst in INSTITUTIONS:
        for a in inst.abbrevs:
            if f" {fold(a)} " in padded:
                hits.setdefault(inst.id, (a, False))
        for n in (inst.name_en, inst.name_vi, *inst.names):
            fn = fold(n)
            if f" {fn} " in padded:
                hits[inst.id] = (n, False)
            elif len(fn) >= 12 and inst.id not in hits and fuzz.partial_ratio(fn, q) >= 90:
                hits[inst.id] = (n, True)
    # "Đại học Quốc tế - ĐHQG TPHCM" names IU *and* its parent system: keep the member school
    for iid in list(hits):
        hits.pop(BY_ID[iid].parent, None)
    # a long, exact name beats a fuzzy one ("Khoa học Tự nhiên" fuzzy-matches inside "Khoa học Xã hội...")
    exact = {k: v for k, v in hits.items() if not v[1]}
    if exact:
        hits = exact
    return Detection(ids=sorted(hits), matches={k: v[0] for k, v in hits.items()},
                     fuzzy=any(v[1] for v in hits.values()))


def options(indexed_doc_ids: list[str]) -> list[dict]:
    """What the UI shows in the school picker: every institution, flagged by whether we hold documents."""
    covered = {institution_of_doc(d) for d in indexed_doc_ids}
    return [{"id": i.id, "name_en": i.name_en, "name_vi": i.name_vi, "covered": i.id in covered} for i in INSTITUTIONS]

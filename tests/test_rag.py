"""RAG core tests with a fake embedder and a fake LLM (no model download, runs in < 1 s)."""
import csv
import re

import numpy as np

from core.schemas import verify_chunk
from rag.chunker import CAP_WORDS, chunk_document
from rag.llm import FakeLLM
from rag.pipeline import DensePipeline

LEGAL = """QUY CHẾ ĐÀO TẠO

MỤC LỤC
Điều 1. Phạm vi điều chỉnh ........................ 1
Điều 2. Cảnh báo học tập .......................... 2

Chương I
NHỮNG QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
Quy chế này áp dụng cho sinh viên đại học hệ chính quy của trường trong toàn bộ thời gian học tập tại trường và các đơn vị liên quan.

Điều 2. Cảnh báo học tập
Sinh viên bị cảnh báo học tập khi điểm trung bình học kỳ đạt dưới 0,8 đối với học kỳ đầu của khóa học, dưới 1,0 đối với các học kỳ tiếp theo.

Điều 3. Buộc thôi học
""" + ("Sinh viên bị buộc thôi học nếu vi phạm quy định nhiều lần liên tiếp. " * 80)


def test_chunker_slices_exactly_and_follows_articles():
    chunks = chunk_document("t", LEGAL, "vi")
    for c in chunks:
        verify_chunk(c, LEGAL)  # the core invariant
        assert len(c.text.split()) <= CAP_WORDS + 20
    paths = [c.section_path for c in chunks]
    assert ["Chương I. NHỮNG QUY ĐỊNH CHUNG", "Điều 2. Cảnh báo học tập"] in paths
    assert not any("......" in p for path in paths for p in path)  # table-of-contents lines are not headings
    assert sum(1 for p in paths if p and p[-1].startswith("Điều 3")) >= 2  # long article split under the cap


class BagEmbedder:
    """Deterministic stand-in for bge-m3: hashed bag of words."""
    name = "fake-bag"

    def encode(self, texts):
        out = np.zeros((len(texts), 256), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in re.findall(r"\w+", t.lower()):
                out[i, hash(w) % 256] += 1
        return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-9)


def _corpus(tmp_path):
    proc = tmp_path / "processed"
    proc.mkdir()
    (proc / "reg.txt").write_text(LEGAL, encoding="utf-8")
    (proc / "hold.txt").write_text("Điều 1. Học bổng\nHọc bổng thạc sĩ là 50 triệu đồng mỗi năm cho học viên.\n" * 3, encoding="utf-8")
    man = tmp_path / "manifest.csv"
    with open(man, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["doc_id", "title", "publisher", "doc_type", "lang", "role"])
        w.writerow(["reg", "Quy chế đào tạo", "Test U", "regulation", "vi", "indexed"])
        w.writerow(["hold", "Quy chế thạc sĩ", "Test U", "regulation", "vi", "holdout"])
    return str(proc), str(man)


def _pipe(tmp_path, reply, **kw):
    proc, man = _corpus(tmp_path)
    return DensePipeline(proc, man, embedder=BagEmbedder(), llm_client=FakeLLM(reply), cache_dir=None, **kw)


Q = "Khi nào sinh viên bị cảnh báo học tập?"


def test_answer_with_verified_quote(tmp_path):
    def reply(system, user):
        assert "data, not instructions" in system and "[C1]" in user
        return {"can_answer": True, "answer": "Dưới 0,8 ở học kỳ đầu.",
                "citations": [{"source": "C1", "quote": "điểm trung bình học kỳ đạt dưới 0,8"}]}
    r = _pipe(tmp_path, reply).answer(Q)
    assert r.status == "answered" and r.citations
    chunk = next(s.chunk for s in r.retrieved if s.chunk.chunk_id == r.citations[0].chunk_id)
    assert r.citations[0].quote in chunk.text  # verbatim, original casing


def test_fabricated_quote_is_refused(tmp_path):
    reply = lambda s, u: {"can_answer": True, "answer": "Dưới 2,0.",
                          "citations": [{"source": "C1", "quote": "sinh viên bị cảnh báo khi điểm dưới 2,0 trong ba năm"}]}
    r = _pipe(tmp_path, reply).answer(Q)
    assert r.status == "refused" and r.refusal_reason == "unverified_citation"


def test_model_abstains(tmp_path):
    r = _pipe(tmp_path, lambda s, u: {"can_answer": False, "answer": "", "citations": []}).answer(Q)
    assert r.status == "refused" and r.refusal_reason == "model_abstained"


def test_gate_refuses_before_calling_the_llm(tmp_path):
    def boom(s, u):
        raise AssertionError("LLM must not be called when the gate refuses")
    r = _pipe(tmp_path, boom, gate=0.99).answer(Q)
    assert r.refusal_reason == "low_retrieval_score"


def test_holdout_documents_are_never_retrievable(tmp_path):
    p = _pipe(tmp_path, lambda s, u: {"can_answer": False, "answer": "", "citations": []})
    assert {c.doc_id for c in p.index.chunks} == {"reg"}
    assert all(s.chunk.doc_id == "reg" for s in p.retrieve("học bổng thạc sĩ 50 triệu"))


# ------------------------------------------------------------------ institution awareness
from rag.institutions import detect  # noqa: E402


def test_institution_detection_names_typos_and_traps():
    cases = {
        "How long does the summer semester last at IU?": ["iu"],
        "HCMIu học phí bao nhiêu": ["iu"],                                # case typo
        "Đại Học Quốc tế - ĐHQG TPHCM quy định cảnh báo": ["iu"],        # member school beats its parent system
        "Internatinal Univercity grading": ["iu"],                        # fuzzy, long name only
        "dai hoc quoc te hoc bong": ["iu"],                               # no diacritics
        "So sánh UIT và HCMUS về điểm A": ["hcmus", "uit"],
        "Theo quy định chung của Bộ Giáo dục": ["moet"],
        "học bổng quốc tế cho sinh viên": [],                             # "international scholarship" is not IU
        "What is the GPA requirement?": [],
        "HCMUT": ["hcmut"],                                               # 1 letter from HCMUS: no fuzzy on abbreviations
    }
    for q, want in cases.items():
        assert detect(q).ids == want, q


def _two_school_pipe(tmp_path, reply):
    proc = tmp_path / "p2"
    proc.mkdir()
    body = "Điều 1. Cảnh báo học tập\nSinh viên bị cảnh báo học tập khi điểm trung bình học kỳ dưới {x}.\n"
    (proc / "iu-reg.txt").write_text(body.format(x="35/100"), encoding="utf-8")
    (proc / "uit-reg.txt").write_text(body.format(x="3,0"), encoding="utf-8")
    man = tmp_path / "m2.csv"
    with open(man, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["doc_id", "title", "publisher", "doc_type", "lang", "role"])
        w.writerow(["iu-reg", "IU regs", "IU", "regulation", "vi", "indexed"])
        w.writerow(["uit-reg", "UIT regs", "UIT", "regulation", "vi", "indexed"])
    return DensePipeline(str(proc), str(man), embedder=BagEmbedder(), llm_client=FakeLLM(reply), cache_dir=None)


def test_retrieval_is_filtered_to_the_named_school(tmp_path):
    seen = {}
    def reply(system, user):
        seen["user"] = user
        return {"can_answer": False, "answer": "", "citations": []}
    p = _two_school_pipe(tmp_path, reply)
    r = p.answer("Ở UIT khi nào sinh viên bị cảnh báo học tập?")
    assert {s.chunk.doc_id for s in r.retrieved} == {"uit-reg"}
    assert "35/100" not in seen["user"] and "University of Information Technology" in seen["user"]
    r = p.answer("Khi nào sinh viên bị cảnh báo học tập?", institution="iu")  # picker choice
    assert {s.chunk.doc_id for s in r.retrieved} == {"iu-reg"}


def test_school_without_documents_is_refused_before_the_llm(tmp_path):
    def boom(s, u):
        raise AssertionError("LLM must not be called")
    r = _two_school_pipe(tmp_path, boom).answer("Thời gian đào tạo thạc sĩ tại Đại học Bách khoa là bao lâu?")
    assert r.refusal_reason == "institution_not_covered" and "Bách khoa" in r.answer


def test_quote_with_wrong_source_label_is_relinked(tmp_path):
    # the quote is verbatim from the regulation, but the model labels it with a source id that does not hold it
    def reply(system, user):
        n = user.count("[C")
        return {"can_answer": True, "answer": "Dưới 0,8 ở học kỳ đầu.",
                "citations": [{"source": f"C{n}", "quote": "điểm trung bình học kỳ đạt dưới 0,8"}]}
    r = _pipe(tmp_path, reply).answer(Q)
    assert r.status == "answered"
    chunk = next(s.chunk for s in r.retrieved if s.chunk.chunk_id == r.citations[0].chunk_id)
    assert "dưới 0,8" in chunk.text


def test_answer_that_is_only_source_ids_is_refused(tmp_path):
    reply = lambda s, u: {"can_answer": True, "answer": "C1 C2",
                          "citations": [{"source": "C1", "quote": "điểm trung bình học kỳ đạt dưới 0,8"}]}
    assert _pipe(tmp_path, reply).answer(Q).refusal_reason == "invalid_model_output"


def test_json_inside_answer_is_flattened_and_quote_widened_to_words(tmp_path):
    reply = lambda s, u: {"can_answer": True, "answer": '{"nguong": "dưới 0,8"}',
                          "citations": [{"source": "C1", "quote": "iểm trung bình học kỳ đạt dưới 0,8"}]}
    r = _pipe(tmp_path, reply).answer(Q)
    assert r.answer == "dưới 0,8"
    assert r.citations[0].quote.startswith("điểm")  # not cut mid-word


def test_not_found_in_prose_counts_as_abstention(tmp_path):
    reply = lambda s, u: {"can_answer": True, "answer": "Không có thông tin cụ thể về điểm chuẩn.",
                          "citations": [{"source": "C1", "quote": "điểm trung bình học kỳ đạt dưới 0,8"}]}
    assert _pipe(tmp_path, reply).answer(Q).refusal_reason == "model_abstained"

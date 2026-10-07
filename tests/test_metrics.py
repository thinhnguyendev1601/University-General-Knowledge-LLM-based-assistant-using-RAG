from core.schemas import AnswerResult, Chunk, Citation, EvidenceSpan, ScoredChunk, make_chunk_id
from eval.metrics import citation_metrics, fact_present, key_fact_recall, retrieval_metrics, summarize


def sc(doc, a, b, rank, text=None):
    return ScoredChunk(chunk=Chunk(chunk_id=make_chunk_id(doc, a, b), doc_id=doc, text=text or "x" * (b - a), char_start=a, char_end=b), score=1 / rank, rank=rank)


def test_hit_and_rr_are_span_based():
    ev = [EvidenceSpan(doc_id="d", quote="q", char_start=100, char_end=200)]
    retrieved = [sc("d", 0, 90, 1), sc("d", 90, 260, 2), sc("other", 100, 200, 3)]
    m = retrieval_metrics(retrieved, ev, ks=(1, 2, 3))
    assert m["hit@1"] == 0 and m["hit@2"] == 1 and m["hit@3"] == 1
    assert m["rr"] == 0.5


def test_partial_overlap_below_threshold_is_a_miss():
    ev = [EvidenceSpan(doc_id="d", quote="q", char_start=100, char_end=200)]
    m = retrieval_metrics([sc("d", 0, 130, 1)], ev, ks=(1,))  # covers 30% of the span
    assert m["hit@1"] == 0


def test_evidence_recall_multi_span():
    ev = [EvidenceSpan(doc_id="d", quote="a", char_start=0, char_end=50), EvidenceSpan(doc_id="d", quote="b", char_start=500, char_end=550)]
    m = retrieval_metrics([sc("d", 0, 60, 1), sc("d", 900, 950, 2)], ev, ks=(2,))
    assert m["evidence_recall@2"] == 0.5 and m["hit@2"] == 1


def test_fact_matching_alternatives_and_diacritics():
    assert fact_present("2.0|2,0", "Điểm tối thiểu là 2,0 trên thang 4")
    assert fact_present("Cảnh báo học vụ", "sinh viên bị cảnh báo học vụ khi ...")
    assert not fact_present("cảnh báo", "canh bao")  # diacritics matter
    assert key_fact_recall(["120", "tín chỉ"], "cần 120 tín chỉ") == 1.0
    assert key_fact_recall(["120", "tín chỉ"], "cần 120") == 0.5


def test_citation_quote_must_be_inside_cited_chunk():
    ev = [EvidenceSpan(doc_id="d", quote="q", char_start=0, char_end=40)]
    chunk = sc("d", 0, 60, 1, text="Sinh viên phải đạt điểm trung bình tích lũy tối thiểu 2.0 để tốt nghiệp.")
    good = AnswerResult(status="answered", answer="a", retrieved=[chunk], citations=[Citation(chunk_id=chunk.chunk.chunk_id, quote="điểm trung bình tích lũy tối thiểu 2.0")])
    bad = AnswerResult(status="answered", answer="a", retrieved=[chunk], citations=[Citation(chunk_id=chunk.chunk.chunk_id, quote="a made-up sentence")])
    ghost = AnswerResult(status="answered", answer="a", retrieved=[chunk], citations=[Citation(chunk_id="d:999:1000", quote="x")])
    assert citation_metrics(good, ev)["quote_verified_rate"] == 1.0
    assert citation_metrics(bad, ev)["quote_verified_rate"] == 0.0
    assert citation_metrics(ghost, ev)["quote_verified_rate"] == 0.0


def test_summarize_refusal_confusion():
    recs = [
        {"answerable": True, "refused": False, "metrics": {"auto_correct": True, "rr": 1, "key_fact_recall": 1.0, **{f"hit@{k}": 1 for k in (1, 3, 5, 10)}, **{f"evidence_recall@{k}": 1 for k in (1, 3, 5, 10)}}, "latency_ms": 5},
        {"answerable": True, "refused": True, "metrics": {"auto_correct": False, "rr": 0, "key_fact_recall": 0.0, **{f"hit@{k}": 0 for k in (1, 3, 5, 10)}, **{f"evidence_recall@{k}": 0 for k in (1, 3, 5, 10)}}, "latency_ms": 5},
        {"answerable": False, "refused": True, "metrics": {"auto_correct": True}, "latency_ms": 5},
        {"answerable": False, "refused": False, "metrics": {"auto_correct": False}, "latency_ms": 5},
    ]
    s = summarize(recs)
    assert s["false_refusal_rate"] == 0.5 and s["unsupported_answer_rate"] == 0.5
    assert s["refusal_precision"] == 0.5 and s["refusal_recall"] == 0.5

from fastapi import HTTPException

from rag.pipeline import DensePipeline

STATE: dict = {}


def get_pipeline() -> DensePipeline:
    if "pipe" not in STATE:
        raise HTTPException(503, "Dịch vụ hỏi đáp chưa được bật")
    return STATE["pipe"]

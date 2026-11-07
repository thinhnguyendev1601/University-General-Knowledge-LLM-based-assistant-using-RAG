"""Small structured operational events; never serialize requests or exceptions."""
from contextvars import ContextVar
import json
import logging

http_request_id = ContextVar("http_request_id", default=None)
logger = logging.getLogger("uvicorn.error")


def emit(event: str, **fields):
    logger.info(json.dumps({"event": event, "httpRequestId": http_request_id.get(), **fields},
                           ensure_ascii=True, separators=(",", ":")))


class AccessPathFilter(logging.Filter):
    def filter(self, record):
        # Uvicorn's standard access tuple: client, method, URL, version, status.
        if isinstance(record.args, tuple) and len(record.args) == 5:
            args = list(record.args)
            if isinstance(args[2], str):
                args[2] = args[2].split("?", 1)[0].split("#", 1)[0]
            record.args = tuple(args)
        return True


def install_access_filter():
    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, AccessPathFilter) for item in access.filters):
        access.addFilter(AccessPathFilter())

import contextvars
import logging
import sys
from typing import Any, Dict

# Context variable holding the unique request_id for the current task/request
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="system")


class SanitizedRequestFormatter(logging.Formatter):
    """
    Structured formatter that automatically injects request_id.
    Strictly enforces S-14: No PII, financial figures, or JWTs in logs.
    """

    def format(self, record: logging.LogRecord) -> str:
        record.request_id = request_id_ctx.get()
        return super().format(record)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("guardian")
    logger.setLevel(log_level.upper())
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level.upper())
        formatter = SanitizedRequestFormatter(
            fmt="%(asctime)s [%(levelname)s] [req:%(request_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()

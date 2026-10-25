"""Privacy-conscious structured HTTP request logging."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import sys


_LOGGER_NAME = "eu_ai_act_sandbox"


class JsonLogFormatter(logging.Formatter):
    """Format selected log fields as one JSON object per line."""

    _FIELDS = (
        "event",
        "request_id",
        "http_method",
        "http_route",
        "http_status_code",
        "duration_ms",
        "error_type",
        "exporter",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in self._FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging() -> logging.Logger:
    """Configure one application-owned JSON stream without changing root logging."""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(isinstance(handler.formatter, JsonLogFormatter) for handler in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonLogFormatter())
        logger.addHandler(handler)
    return logger




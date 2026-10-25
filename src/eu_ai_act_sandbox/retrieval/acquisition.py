"""Bounded validation of acquired regulatory source payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.message import Message
from html.parser import HTMLParser
import re
from urllib.parse import urlparse
from xml.etree import ElementTree

from .source_registry import RegulatorySource, calculate_content_sha256


DEFAULT_MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
_SUPPORTED_MEDIA_TYPES = frozenset({
    "application/pdf",
    "application/xml",
    "text/xml",
    "text/html",
    "text/plain",
})
_DOCTYPE_OR_ENTITY = re.compile(rb"<!\s*(DOCTYPE|ENTITY)\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class AcquiredDocument:
    """Validated acquisition receipt and payload for the next ingestion stage."""

    source_id: str
    requested_url: str
    resolved_url: str
    http_status: int
    media_type: str
    retrieved_at: datetime
    byte_count: int
    content_sha256: str
    content: bytes


class _HTMLStructureCheck(HTMLParser):
    """Small structural check only; this parser never executes document content."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.seen_html_element = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "html":
            self.seen_html_element = True


def validate_acquired_document(
    *,
    source: RegulatorySource,
    resolved_url: str,
    http_status: int,
    content_type: str,
    retrieved_at: datetime,
    content: bytes,
    max_document_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES,
) -> AcquiredDocument:
    """Validate payload metadata and supported format before parsing or indexing.

    This function accepts data from an acquisition adapter. It does not make
    network requests, follow redirects, persist content, or declare a source
    legally authoritative.
    """
    if not isinstance(source, RegulatorySource):
        raise TypeError("source must be a RegulatorySource")
    _require_text("resolved_url", resolved_url)
    _require_text("content_type", content_type)
    if not isinstance(http_status, int) or isinstance(http_status, bool):
        raise TypeError("http_status must be an integer")
    if not 200 <= http_status < 300:
        raise ValueError("only successful 2xx source responses can be ingested")
    if not isinstance(retrieved_at, datetime):
        raise TypeError("retrieved_at must be a datetime")
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise ValueError("retrieved_at must include a timezone")
    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")
    if not content:
        raise ValueError("content must not be empty")
    if not isinstance(max_document_bytes, int) or isinstance(max_document_bytes, bool):
        raise TypeError("max_document_bytes must be an integer")
    if max_document_bytes < 1:
        raise ValueError("max_document_bytes must be positive")
    if len(content) > max_document_bytes:
        raise ValueError("document exceeds the configured maximum size")

    parsed_url = urlparse(resolved_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc or parsed_url.username or parsed_url.password:
        raise ValueError("resolved_url must be an absolute HTTPS URL without embedded credentials")

    message = Message()
    message["content-type"] = content_type
    media_type = message.get_content_type().lower()
    if media_type not in _SUPPORTED_MEDIA_TYPES:
        raise ValueError(f"unsupported source media type: {media_type}")

    _validate_payload(media_type, content)
    return AcquiredDocument(
        source_id=source.source_id,
        requested_url=source.source_url,
        resolved_url=resolved_url,
        http_status=http_status,
        media_type=media_type,
        retrieved_at=retrieved_at,
        byte_count=len(content),
        content_sha256=calculate_content_sha256(content),
        content=content,
    )


def _validate_payload(media_type: str, content: bytes) -> None:
    if b"\x00" in content:
        raise ValueError("source payload contains a NUL byte")

    if media_type == "application/pdf":
        if not content.startswith(b"%PDF-"):
            raise ValueError("PDF payload is missing the PDF file signature")
        if b"%%EOF" not in content[-2048:]:
            raise ValueError("PDF payload is missing a trailing EOF marker")
        return

    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("textual source payload must be valid UTF-8") from exc

    if not text.strip():
        raise ValueError("textual source payload must contain non-whitespace text")

    if media_type in {"application/xml", "text/xml"}:
        if _DOCTYPE_OR_ENTITY.search(content):
            raise ValueError("XML payloads containing DTD or entity declarations are not accepted")
        try:
            ElementTree.fromstring(content)
        except ElementTree.ParseError as exc:
            raise ValueError("XML payload is not well formed") from exc
    elif media_type == "text/html":
        parser = _HTMLStructureCheck()
        try:
            parser.feed(text)
            parser.close()
        except Exception as exc:
            raise ValueError("HTML payload could not be parsed") from exc
        if not parser.seen_html_element and not re.search(r"<(article|main|body|title)\b", text, re.I):
            raise ValueError("HTML payload does not contain an expected document structure")


def _require_text(field_name: str, value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")

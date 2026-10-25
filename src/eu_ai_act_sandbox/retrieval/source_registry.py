"""Immutable source and document-version contracts for regulatory retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from hashlib import sha256
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5


class SourceAuthority(StrEnum):
    BINDING_LEGAL_TEXT = "BINDING_LEGAL_TEXT"
    OFFICIAL_GUIDANCE = "OFFICIAL_GUIDANCE"
    TECHNICAL_STANDARD = "TECHNICAL_STANDARD"
    PROJECT_AUTHORED = "PROJECT_AUTHORED"
    OTHER = "OTHER"


class SourceType(StrEnum):
    REGULATION = "REGULATION"
    DIRECTIVE = "DIRECTIVE"
    DECISION = "DECISION"
    GUIDELINE = "GUIDELINE"
    TECHNICAL_STANDARD = "TECHNICAL_STANDARD"
    PROJECT_DOCUMENT = "PROJECT_DOCUMENT"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class RegulatorySource:
    """Registered source identity and provenance, separate from retrieved content."""

    source_id: str
    source_url: str
    issuing_authority: str
    document_title: str
    source_type: SourceType
    source_authority: SourceAuthority
    jurisdiction: str
    language: str
    published_on: date | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "source_id", "source_url", "issuing_authority", "document_title",
            "jurisdiction", "language",
        ):
            _require_text(field_name, getattr(self, field_name))
        parsed_url = urlparse(self.source_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError("source_url must be an absolute HTTPS URL")
        if not isinstance(self.source_type, SourceType):
            raise TypeError("source_type must be a SourceType")
        if not isinstance(self.source_authority, SourceAuthority):
            raise TypeError("source_authority must be a SourceAuthority")
        if self.published_on is not None and (
            not isinstance(self.published_on, date) or isinstance(self.published_on, datetime)
        ):
            raise TypeError("published_on must be a date or None")


@dataclass(frozen=True, slots=True)
class DocumentVersion:
    """An immutable content snapshot, addressed by source identity and SHA-256."""

    document_version_id: str
    source_id: str
    content_sha256: str
    retrieved_at: datetime
    legal_version_label: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    supersedes_version_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("document_version_id", "source_id", "content_sha256"):
            _require_text(field_name, getattr(self, field_name))
        if len(self.content_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.content_sha256
        ):
            raise ValueError("content_sha256 must be a lowercase 64-character SHA-256 digest")
        _require_aware_datetime("retrieved_at", self.retrieved_at)
        for field_name in ("effective_from", "effective_to"):
            value = getattr(self, field_name)
            if value is not None and (
                not isinstance(value, date) or isinstance(value, datetime)
            ):
                raise TypeError(f"{field_name} must be a date or None")
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError("effective_to must be on or after effective_from")
        if self.legal_version_label is not None:
            _require_text("legal_version_label", self.legal_version_label)
        if self.supersedes_version_id is not None:
            _require_text("supersedes_version_id", self.supersedes_version_id)
            if self.supersedes_version_id == self.document_version_id:
                raise ValueError("a document version cannot supersede itself")


def calculate_content_sha256(content: bytes) -> str:
    """Return a stable SHA-256 digest for the exact acquired document bytes."""
    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")
    if not content:
        raise ValueError("content must not be empty")
    return sha256(content).hexdigest()


def derive_document_version_id(source_id: str, content_sha256: str) -> str:
    """Derive a stable ID so identical source content has the same version identity."""
    _require_text("source_id", source_id)
    if not isinstance(content_sha256, str) or len(content_sha256) != 64 or any(
        char not in "0123456789abcdef" for char in content_sha256
    ):
        raise ValueError("content_sha256 must be a lowercase 64-character SHA-256 digest")
    identifier = uuid5(NAMESPACE_URL, f"eu-ai-act-sandbox:{source_id}:{content_sha256}")
    return f"docv_{identifier.hex}"


def create_document_version(
    *,
    source: RegulatorySource,
    content: bytes,
    retrieved_at: datetime,
    legal_version_label: str | None = None,
    effective_from: date | None = None,
    effective_to: date | None = None,
    supersedes_version_id: str | None = None,
) -> DocumentVersion:
    """Create version metadata without persisting or fetching the source document."""
    if not isinstance(source, RegulatorySource):
        raise TypeError("source must be a RegulatorySource")
    digest = calculate_content_sha256(content)
    version_id = derive_document_version_id(source.source_id, digest)
    return DocumentVersion(
        document_version_id=version_id,
        source_id=source.source_id,
        content_sha256=digest,
        retrieved_at=retrieved_at,
        legal_version_label=legal_version_label,
        effective_from=effective_from,
        effective_to=effective_to,
        supersedes_version_id=supersedes_version_id,
    )


def _require_aware_datetime(field_name: str, value: datetime) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone")


def _require_text(field_name: str, value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")

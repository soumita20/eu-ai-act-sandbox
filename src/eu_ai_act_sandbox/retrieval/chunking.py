"""Deterministic, structure-aware chunking for normalized legal text."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import re

from .parsing import ParsedDocument, ParsedSection
from .source_registry import DocumentVersion, RegulatorySource, SourceAuthority


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?;:])\s+(?=[A-Z0-9(])")


@dataclass(frozen=True, slots=True)
class RegulatoryChunk:
    """A retrievable passage with immutable source and legal metadata."""

    chunk_id: str
    source_id: str
    document_version_id: str
    article_reference: str | None
    text: str
    text_hash: str
    chunk_index: int
    parent_reference: str | None
    source_authority: SourceAuthority
    language: str
    effective_from: date | None
    effective_to: date | None
    source_coordinates: tuple[str, ...]


def chunk_regulatory_document(
    *,
    parsed_document: ParsedDocument,
    source: RegulatorySource,
    document_version: DocumentVersion,
    target_chars: int = 1800,
    overlap_chars: int = 160,
) -> tuple[RegulatoryChunk, ...]:
    """Create stable chunks while keeping legal sections intact where possible.

    Adjacent sections from the same article are grouped up to target_chars.
    Oversized sections are split at sentence boundaries, then word boundaries.
    Overlap is applied only to those forced splits.
    """
    if not isinstance(parsed_document, ParsedDocument):
        raise TypeError("parsed_document must be a ParsedDocument")
    if not isinstance(source, RegulatorySource):
        raise TypeError("source must be a RegulatorySource")
    if not isinstance(document_version, DocumentVersion):
        raise TypeError("document_version must be a DocumentVersion")
    if parsed_document.source_id != source.source_id:
        raise ValueError("parsed document and source IDs do not match")
    if document_version.source_id != source.source_id:
        raise ValueError("document version and source IDs do not match")
    if parsed_document.content_sha256 != document_version.content_sha256:
        raise ValueError("parsed document and document version hashes do not match")
    if not isinstance(target_chars, int) or isinstance(target_chars, bool) or target_chars < 100:
        raise ValueError("target_chars must be an integer of at least 100")
    if not isinstance(overlap_chars, int) or isinstance(overlap_chars, bool) or not 0 <= overlap_chars < target_chars:
        raise ValueError("overlap_chars must be an integer from 0 up to target_chars - 1")

    prepared = _group_sections(parsed_document.sections, target_chars)
    chunk_texts: list[tuple[str, str | None, str | None, tuple[str, ...]]] = []
    for text, article_reference, parent_reference, coordinates in prepared:
        if len(text) <= target_chars:
            chunk_texts.append((text, article_reference, parent_reference, coordinates))
            continue
        for fragment in _split_oversized(text, target_chars, overlap_chars):
            chunk_texts.append((fragment, article_reference, parent_reference, coordinates))

    chunks = []
    for index, (text, article_reference, parent_reference, coordinates) in enumerate(chunk_texts):
        text_hash = sha256(text.encode("utf-8")).hexdigest()
        stable_seed = f"{source.source_id}\0{document_version.document_version_id}\0{index}\0{text_hash}"
        chunk_id = f"chk_{sha256(stable_seed.encode('utf-8')).hexdigest()[:24]}"
        chunks.append(RegulatoryChunk(
            chunk_id=chunk_id,
            source_id=source.source_id,
            document_version_id=document_version.document_version_id,
            article_reference=article_reference,
            text=text,
            text_hash=text_hash,
            chunk_index=index,
            parent_reference=parent_reference,
            source_authority=source.source_authority,
            language=source.language,
            effective_from=document_version.effective_from,
            effective_to=document_version.effective_to,
            source_coordinates=coordinates,
        ))
    return tuple(chunks)


def _group_sections(
    sections: tuple[ParsedSection, ...], target_chars: int
) -> list[tuple[str, str | None, str | None, tuple[str, ...]]]:
    grouped: list[tuple[str, str | None, str | None, tuple[str, ...]]] = []
    pending: list[ParsedSection] = []
    pending_length = 0
    pending_article: str | None = None

    def flush() -> None:
        nonlocal pending, pending_length, pending_article
        if not pending:
            return
        text = "\n\n".join(section.text for section in pending)
        article = pending_article
        parent = next((section.parent_reference for section in pending if section.parent_reference), None)
        if parent is None and article:
            parent = article
        coordinates = tuple(dict.fromkeys(section.source_coordinate for section in pending))
        grouped.append((text, article, parent, coordinates))
        pending = []
        pending_length = 0
        pending_article = None

    for section in sections:
        text = section.text.strip()
        if not text:
            continue
        article = section.article_reference
        would_exceed = pending and pending_length + 2 + len(text) > target_chars
        article_changed = pending and article != pending_article
        if would_exceed or article_changed:
            flush()
        if not pending:
            pending_article = article
        pending.append(section)
        pending_length += len(text) + (2 if pending_length else 0)
    flush()
    return grouped


def _split_oversized(text: str, target_chars: int, overlap_chars: int) -> list[str]:
    sentences = _SENTENCE_BOUNDARY.split(text)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > target_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(_split_long_sentence(sentence, target_chars))
            continue
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > target_chars:
            pieces.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        pieces.append(current)

    if overlap_chars == 0 or len(pieces) < 2:
        return pieces
    result = [pieces[0]]
    for piece in pieces[1:]:
        previous = pieces[len(result) - 1]
        overlap = previous[-overlap_chars:].lstrip()
        result.append(f"{overlap} {piece}".strip())
    return result


def _split_long_sentence(text: str, target_chars: int) -> list[str]:
    words = text.split()
    result: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > target_chars:
            result.append(current)
            current = word
        else:
            current = candidate
    if current:
        result.append(current)
    return result

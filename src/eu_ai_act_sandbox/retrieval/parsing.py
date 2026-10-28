"""Structure-aware text extraction and normalization for acquired sources."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
import re
from xml.etree import ElementTree

from .acquisition import AcquiredDocument


_STRUCTURAL_REFERENCE_PATTERN = re.compile(r"^(Article \d+[a-z]?|Annex [IVXLCDM]+)$", re.IGNORECASE)
_LEGAL_UNIT_PATTERN = re.compile(
    r"^\s*((?:Article\s+\d+[a-z]?(?:\(\d+\))?|Annex\s+[IVXLCDM]+|\d+(?:\.\d+)*\.?))\b",
    re.IGNORECASE,
)
_WHITESPACE = re.compile(r"[\t\f\v ]+")


@dataclass(frozen=True, slots=True)
class ParsedSection:
    """A normalized passage with its location in the acquired source."""

    section_id: str
    text: str
    sequence: int
    source_coordinate: str
    heading: str | None = None
    article_reference: str | None = None
    parent_reference: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Parser output tied to the exact acquired document digest."""

    source_id: str
    content_sha256: str
    media_type: str
    parser_name: str
    parser_version: str
    sections: tuple[ParsedSection, ...]


def parse_acquired_document(document: AcquiredDocument) -> ParsedDocument:
    """Extract normalized sections from validated HTML, XML, text, or PDF."""
    if not isinstance(document, AcquiredDocument):
        raise TypeError("document must be an AcquiredDocument")

    if document.media_type == "application/pdf":
        raw_sections = _parse_pdf(document.content)
        parser_name, parser_version = _pdf_parser_identity()
    elif document.media_type in {"text/html", "application/xhtml+xml"}:
        raw_sections = _parse_html(document.content)
        parser_name, parser_version = "stdlib.html.parser", "1"
    elif document.media_type in {"application/xml", "text/xml"}:
        raw_sections = _parse_xml(document.content)
        parser_name, parser_version = "stdlib.elementtree", "1"
    elif document.media_type == "text/plain":
        raw_sections = [("text", document.content.decode("utf-8"), "document")]
        parser_name, parser_version = "utf8", "1"
    else:
        raise ValueError(f"no parser is configured for {document.media_type}")

    sections = _normalize_sections(raw_sections)
    if not sections:
        raise ValueError("document parsing produced no usable text sections")
    return ParsedDocument(
        source_id=document.source_id,
        content_sha256=document.content_sha256,
        media_type=document.media_type,
        parser_name=parser_name,
        parser_version=parser_version,
        sections=sections,
    )


class _TextHTMLParser(HTMLParser):
    """Collect visible text and source line numbers without executing markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[tuple[str, int, str | None]] = []
        self._skip_depth = 0
        self._heading_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading_depth += 1
        if tag in {"p", "li", "br", "div", "section", "article", "tr"}:
            self.parts.append(("\n", self.getpos()[0], None))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._heading_depth:
            self._heading_depth -= 1
        if tag in {"p", "li", "br", "div", "section", "article", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append(("\n", self.getpos()[0], None))

    def handle_data(self, data: str) -> None:
        if data.strip() and not self._skip_depth:
            self.parts.append((data, self.getpos()[0], "heading" if self._heading_depth else None))


def _parse_html(content: bytes) -> list[tuple[str, str, str]]:
    parser = _TextHTMLParser()
    parser.feed(content.decode("utf-8"))
    parser.close()
    result: list[tuple[str, str, str]] = []
    for text, line, kind in parser.parts:
        result.append((text, str(line), kind or "text"))
    return result


def _parse_xml(content: bytes) -> list[tuple[str, str, str]]:
    root = ElementTree.fromstring(content)
    result: list[tuple[str, str, str]] = []
    for element in root.iter():
        text = " ".join(part.strip() for part in element.itertext() if part.strip())
        if text:
            tag = element.tag.rsplit("}", 1)[-1]
            result.append((text, f"xml:{tag}", "heading" if tag.lower() in {"title", "heading"} else "text"))
    if not result:
        return []
    # Keep the document-level traversal from duplicating all descendant text.
    leaves = []
    for element in root.iter():
        if len(element) == 0 and (element.text or "").strip():
            tag = element.tag.rsplit("}", 1)[-1]
            leaves.append(((element.text or "").strip(), f"xml:{tag}", "text"))
    return leaves or result


def _parse_pdf(content: bytes) -> list[tuple[str, str, str]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF parsing requires the declared pypdf dependency") from exc

    from io import BytesIO

    reader = PdfReader(BytesIO(content), strict=True)
    if reader.is_encrypted:
        raise ValueError("encrypted PDFs are not accepted by the initial parser")
    sections = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text(extraction_mode="layout") or ""
        if text.strip():
            sections.append((text, f"page:{page_number}", "text"))
    return sections


def _normalize_sections(raw_sections: list[tuple[str, str, str]]) -> tuple[ParsedSection, ...]:
    normalized: list[ParsedSection] = []
    current_heading: str | None = None
    current_article: str | None = None
    for raw_text, coordinate, kind in raw_sections:
        text = _normalize_text(raw_text)
        if not text:
            continue
        if kind == "heading":
            current_heading = text
        for block in re.split(r"\n{2,}", text):
            block = block.strip()
            if not block:
                continue
            reference_match = _LEGAL_UNIT_PATTERN.match(block)
            if reference_match:
                current_heading = block[:240]
            structural_reference = _STRUCTURAL_REFERENCE_PATTERN.fullmatch(block)
            if structural_reference:
                current_article = structural_reference.group(1)
            digest = sha256(f"{coordinate}\0{block}".encode("utf-8")).hexdigest()[:16]
            normalized.append(ParsedSection(
                section_id=f"sec_{digest}",
                text=block,
                sequence=len(normalized),
                source_coordinate=coordinate,
                heading=current_heading,
                article_reference=current_article,
            ))
    return tuple(normalized)


def _normalize_text(text: str) -> str:
    lines = [_WHITESPACE.sub(" ", line).strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    compact: list[str] = []
    previous_blank = True
    for line in lines:
        if not line:
            if not previous_blank:
                compact.append("")
            previous_blank = True
        else:
            compact.append(line)
            previous_blank = False
    return "\n".join(compact).strip()


def _pdf_parser_identity() -> tuple[str, str]:
    try:
        from importlib.metadata import version
        return "pypdf", version("pypdf")
    except Exception:
        return "pypdf", "unknown"

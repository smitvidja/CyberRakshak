"""Bounded, defensive text extraction from citizen-supplied resume files.

Resume bytes are untrusted. Every path here is bounded on file size, page or
paragraph count and character count, verifies the file signature rather than
trusting the filename, and raises a typed reviewable error instead of leaking a
library exception. No raw resume text is ever logged from this module.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader

MAX_RESUME_BYTES = 10 * 1024 * 1024
MAX_PAGES = 15
MAX_PARAGRAPHS = 800
MAX_CHARACTERS = 40_000
# A DOCX is a zip; refuse archives that expand far beyond their compressed size.
MAX_DECOMPRESSION_RATIO = 120
MAX_UNCOMPRESSED_BYTES = 60 * 1024 * 1024

PDF_SIGNATURE = b"%PDF-"
ZIP_SIGNATURE = b"PK\x03\x04"
# Legacy OLE2 container: .doc, and also the disguise a hostile upload would use.
OLE2_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

SUPPORTED_EXTENSIONS = (".pdf", ".docx")


class ResumeExtractionError(Exception):
    """Base class for controlled, citizen-reviewable extraction failures."""

    code = "RESUME_EXTRACTION_FAILED"
    message = "This resume could not be read. Try uploading it again as a PDF or DOCX."


class UnsupportedResumeFormat(ResumeExtractionError):
    code = "RESUME_UNSUPPORTED_FORMAT"
    message = "Upload a PDF or DOCX file. Older .doc files are not supported."


class ResumeSignatureMismatch(ResumeExtractionError):
    code = "RESUME_SIGNATURE_MISMATCH"
    message = "This file's contents do not match its name. Upload the original PDF or DOCX."


class EncryptedResume(ResumeExtractionError):
    code = "RESUME_ENCRYPTED"
    message = "This file is password protected. Remove the password and upload it again."


class ResumeTooLarge(ResumeExtractionError):
    code = "RESUME_TOO_LARGE"
    message = "This file is too large to process. Upload a resume under 10 MB."


class EmptyResumeText(ResumeExtractionError):
    code = "RESUME_NO_TEXT"
    message = "No readable text was found. If this is a scanned resume, upload a text-based PDF or DOCX."


class CorruptResume(ResumeExtractionError):
    code = "RESUME_CORRUPT"
    message = "This file could not be opened. It may be incomplete or damaged."


@dataclass(frozen=True)
class ExtractedResume:
    text: str
    extractor: str
    unit_count: int
    truncated: bool


def _normalize(text: str) -> str:
    # Collapse runs of whitespace but keep line structure: section detection needs lines.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def _extract_pdf(content: bytes) -> ExtractedResume:
    try:
        reader = PdfReader(BytesIO(content), strict=False)
    except Exception as error:  # noqa: BLE001 - any pypdf failure is a controlled corrupt-file case
        raise CorruptResume() from error

    if getattr(reader, "is_encrypted", False):
        # Some PDFs are encrypted with an empty owner password and open fine.
        try:
            if reader.decrypt("") == 0:
                raise EncryptedResume()
        except EncryptedResume:
            raise
        except Exception as error:  # noqa: BLE001
            raise EncryptedResume() from error

    pages = reader.pages[:MAX_PAGES]
    truncated = len(reader.pages) > MAX_PAGES
    chunks: list[str] = []
    total = 0
    for page in pages:
        try:
            piece = page.extract_text() or ""
        except Exception:  # noqa: BLE001 - a single unreadable page must not fail the upload
            piece = ""
        total += len(piece)
        chunks.append(piece)
        if total >= MAX_CHARACTERS:
            truncated = True
            break

    text = _normalize("\n".join(chunks))[:MAX_CHARACTERS]
    if not text:
        raise EmptyResumeText()
    return ExtractedResume(text=text, extractor="pypdf", unit_count=len(pages), truncated=truncated)


def _extract_docx(content: bytes) -> ExtractedResume:
    try:
        archive = zipfile.ZipFile(BytesIO(content))
    except Exception as error:  # noqa: BLE001
        raise CorruptResume() from error

    uncompressed = sum(info.file_size for info in archive.infolist())
    if uncompressed > MAX_UNCOMPRESSED_BYTES or (len(content) and uncompressed / max(len(content), 1) > MAX_DECOMPRESSION_RATIO):
        raise ResumeTooLarge()

    # python-docx is imported lazily so a missing optional dependency cannot break import time.
    try:
        from docx import Document
    except ImportError as error:  # pragma: no cover - dependency is declared
        raise ResumeExtractionError() from error

    try:
        document = Document(BytesIO(content))
    except Exception as error:  # noqa: BLE001
        raise CorruptResume() from error

    lines: list[str] = []
    total = 0
    truncated = False
    for index, paragraph in enumerate(document.paragraphs):
        if index >= MAX_PARAGRAPHS:
            truncated = True
            break
        piece = paragraph.text or ""
        if not piece.strip():
            continue
        lines.append(piece)
        total += len(piece)
        if total >= MAX_CHARACTERS:
            truncated = True
            break

    # Resumes frequently keep skills and dates inside tables.
    if total < MAX_CHARACTERS:
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()]
                if cells:
                    lines.append(" | ".join(cells))
                    total += sum(len(cell) for cell in cells)
            if total >= MAX_CHARACTERS:
                truncated = True
                break

    text = _normalize("\n".join(lines))[:MAX_CHARACTERS]
    if not text:
        raise EmptyResumeText()
    return ExtractedResume(text=text, extractor="python-docx", unit_count=len(lines), truncated=truncated)


def extract_resume_text(content: bytes, file_name: str) -> ExtractedResume:
    """Extract bounded plain text, verifying the signature rather than the name."""
    if not content:
        raise EmptyResumeText()
    if len(content) > MAX_RESUME_BYTES:
        raise ResumeTooLarge()

    name = (file_name or "").lower()
    if name.endswith(".doc") and not name.endswith(".docx"):
        # No safe pure-Python extractor for the legacy OLE2 format is available, so
        # the format is refused honestly instead of returning invented output.
        raise UnsupportedResumeFormat()
    if not name.endswith(SUPPORTED_EXTENSIONS):
        raise UnsupportedResumeFormat()

    if content.startswith(OLE2_SIGNATURE):
        raise UnsupportedResumeFormat()

    if name.endswith(".pdf"):
        if not content.startswith(PDF_SIGNATURE):
            raise ResumeSignatureMismatch()
        return _extract_pdf(content)

    if not content.startswith(ZIP_SIGNATURE):
        raise ResumeSignatureMismatch()
    return _extract_docx(content)

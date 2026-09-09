"""Bounded evidence inspection for Cyber Saathi report preparation.

The inspector is intentionally transient: it validates and reads the upload for
metadata/basic text hints, but does not persist the file. The confirmed complaint
flow remains the only owner of stored evidence.
"""

from __future__ import annotations

import re
import shutil
import struct
import subprocess
from io import BytesIO
from hashlib import sha256
from pathlib import Path

from fastapi import UploadFile
from pypdf import PdfReader

from app.core.errors import APIError
from app.schemas.cyber_saathi import AttachmentAnalysis
from app.services.cyber_saathi_understanding import UnderstandingEngine


MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


async def read_and_analyze_attachment(upload: UploadFile) -> tuple[AttachmentAnalysis, bytes]:
    filename = Path(upload.filename or "").name
    extension = Path(filename).suffix.casefold()
    expected_type = ALLOWED_TYPES.get(extension)
    supplied_type = (upload.content_type or "").casefold()
    if expected_type is None or supplied_type != expected_type:
        raise APIError(
            status_code=422,
            code="UNSUPPORTED_ATTACHMENT_TYPE",
            message="Cyber Saathi accepts PDF, PNG, JPG, or JPEG evidence only.",
        )

    chunks: list[bytes] = []
    size = 0
    while chunk := await upload.read(1024 * 1024):
        size += len(chunk)
        if size > MAX_ATTACHMENT_SIZE:
            raise APIError(
                status_code=422,
                code="ATTACHMENT_TOO_LARGE",
                message="Each Cyber Saathi attachment must be 10 MB or smaller.",
            )
        chunks.append(chunk)
    await upload.seek(0)
    content = b"".join(chunks)
    if not content:
        raise APIError(status_code=422, code="EMPTY_ATTACHMENT", message="The attachment is empty.")
    _validate_signature(expected_type, content)

    preview, media_summary, extraction_method, extraction_status = _inspect_content(expected_type, content)
    analysis_text = " ".join(part for part in (filename, preview) if part)
    extracted = UnderstandingEngine.analyze(analysis_text).entities if analysis_text else []
    return (
        AttachmentAnalysis(
            file_name=filename,
            mime_type=expected_type,
            file_size=size,
            checksum=sha256(content).hexdigest(),
            media_summary=media_summary,
            extraction_method=extraction_method,
            extraction_status=extraction_status,
            extracted_text_preview=preview or None,
            extracted_entities=extracted,
            needs_user_review=True,
        ),
        content,
    )


def _validate_signature(mime_type: str, content: bytes) -> None:
    valid = (
        (mime_type == "application/pdf" and content.startswith(b"%PDF-"))
        or (mime_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
        or (mime_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff"))
    )
    if not valid:
        raise APIError(
            status_code=422,
            code="ATTACHMENT_SIGNATURE_MISMATCH",
            message="The file content does not match its extension.",
        )


def _inspect_content(mime_type: str, content: bytes) -> tuple[str, str, str, str]:
    if mime_type == "application/pdf":
        try:
            reader = PdfReader(BytesIO(content), strict=False)
            page_count = len(reader.pages)
            text = " ".join((page.extract_text() or "") for page in reader.pages[:10])
            preview = re.sub(r"\s+", " ", text).strip()[:500]
            status = "completed" if preview else "no_text"
            return preview, f"PDF document · {page_count} page(s)", "pdf_text", status
        except Exception as error:
            raise APIError(
                status_code=422,
                code="UNREADABLE_ATTACHMENT",
                message="The PDF could not be read safely. Export it again and retry.",
            ) from error
    if mime_type == "image/png" and len(content) >= 24:
        width, height = struct.unpack(">II", content[16:24])
        preview, method, status = _ocr_image(content)
        return preview, f"PNG image · {width} × {height} pixels", method, status
    dimensions = _jpeg_dimensions(content)
    if dimensions:
        preview, method, status = _ocr_image(content)
        return preview, f"JPEG image · {dimensions[0]} × {dimensions[1]} pixels", method, status
    return "", "JPEG image · dimensions unavailable", "metadata_only", "unavailable"


def _ocr_image(content: bytes) -> tuple[str, str, str]:
    executable = shutil.which("tesseract")
    if executable is None:
        return "", "metadata_only", "unavailable"
    try:
        completed = subprocess.run(
            [executable, "stdin", "stdout", "--dpi", "300", "-l", "eng+hin"],
            input=content,
            capture_output=True,
            check=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return "", "metadata_only", "unavailable"
    preview = re.sub(r"\s+", " ", completed.stdout.decode("utf-8", errors="ignore")).strip()[:500]
    return preview, "tesseract_ocr", "completed" if preview else "no_text"


def _jpeg_dimensions(content: bytes) -> tuple[int, int] | None:
    position = 2
    while position + 9 < len(content):
        if content[position] != 0xFF:
            position += 1
            continue
        marker = content[position + 1]
        position += 2
        if marker in {0xD8, 0xD9}:
            continue
        if position + 2 > len(content):
            break
        length = int.from_bytes(content[position : position + 2], "big")
        if length < 2 or position + length > len(content):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = int.from_bytes(content[position + 3 : position + 5], "big")
            width = int.from_bytes(content[position + 5 : position + 7], "big")
            return width, height
        position += length
    return None

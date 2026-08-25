from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


class StorageError(Exception):
    pass


class UnsupportedFileTypeError(StorageError):
    pass


class FileTooLargeError(StorageError):
    pass


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    file_url: str
    file_size: int
    checksum: str


class StorageAdapter(Protocol):
    async def store(self, upload_file: UploadFile, prefix: str) -> StoredFile: ...

    def delete(self, storage_key: str) -> None: ...


_ALLOWED_MIME_TYPES = {
    ".doc": {"application/msword"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    },
    ".jpeg": {"image/jpeg"},
    ".jpg": {"image/jpeg"},
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".txt": {"text/plain"},
}


class LocalStorageAdapter:
    def __init__(self, root_path: str, max_file_size: int) -> None:
        self._root = Path(root_path).resolve()
        self._max_file_size = max_file_size

    async def store(self, upload_file: UploadFile, prefix: str) -> StoredFile:
        extension = self._validate_file_type(upload_file)
        storage_key = f"{prefix.strip('/')}/{uuid4().hex}{extension}"
        destination = self._path_for_key(storage_key)
        temporary_path = destination.with_suffix(f"{destination.suffix}.upload")
        destination.parent.mkdir(parents=True, exist_ok=True)

        digest = sha256()
        file_size = 0
        try:
            with temporary_path.open("wb") as destination_file:
                while chunk := await upload_file.read(1024 * 1024):
                    file_size += len(chunk)
                    if file_size > self._max_file_size:
                        raise FileTooLargeError(
                            "The uploaded file exceeds the configured size limit."
                        )
                    digest.update(chunk)
                    destination_file.write(chunk)
            temporary_path.replace(destination)
        except OSError as exc:
            temporary_path.unlink(missing_ok=True)
            raise StorageError("Local evidence storage failed.") from exc
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        finally:
            await upload_file.seek(0)

        return StoredFile(
            storage_key=storage_key,
            file_url=f"local://{storage_key}",
            file_size=file_size,
            checksum=digest.hexdigest(),
        )

    def delete(self, storage_key: str) -> None:
        try:
            self._path_for_key(storage_key).unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError("Local evidence storage failed.") from exc

    def _validate_file_type(self, upload_file: UploadFile) -> str:
        extension = Path(upload_file.filename or "").suffix.lower()
        allowed_mime_types = _ALLOWED_MIME_TYPES.get(extension)
        mime_type = (upload_file.content_type or "").lower()
        if allowed_mime_types is None or mime_type not in allowed_mime_types:
            raise UnsupportedFileTypeError(
                "The uploaded file type is not supported."
            )
        return extension

    def _path_for_key(self, storage_key: str) -> Path:
        candidate = (self._root / storage_key).resolve()
        if not candidate.is_relative_to(self._root):
            raise StorageError("Invalid storage key.")
        return candidate


@lru_cache
def get_storage_adapter() -> StorageAdapter:
    settings = get_settings()
    return LocalStorageAdapter(
        root_path=settings.local_storage_path,
        max_file_size=settings.evidence_max_file_size,
    )

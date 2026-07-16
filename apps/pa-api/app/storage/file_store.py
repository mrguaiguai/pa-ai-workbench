from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import BACKEND_RUNTIME_DIR
from app.config import get_settings


class StoredFile:
    def __init__(self, file_name: str, file_path: str, file_size: int, mime_type: str | None):
        self.file_name = file_name
        self.file_path = file_path
        self.file_size = file_size
        self.mime_type = mime_type


def _upload_root() -> Path:
    upload_dir = Path(get_settings().upload_dir)
    if not upload_dir.is_absolute():
        upload_dir = BACKEND_RUNTIME_DIR / upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _safe_suffix(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if len(suffix) > 16:
        return ""
    return suffix


async def save_upload_file(upload: UploadFile) -> StoredFile:
    original_name = Path(upload.filename or "document").name
    stored_name = f"{uuid4().hex}{_safe_suffix(original_name)}"
    target_path = _upload_root() / stored_name

    file_size = 0
    with target_path.open("wb") as buffer:
        while chunk := await upload.read(1024 * 1024):
            file_size += len(chunk)
            buffer.write(chunk)

    await upload.close()
    return StoredFile(
        file_name=original_name,
        file_path=str(target_path),
        file_size=file_size,
        mime_type=upload.content_type,
    )

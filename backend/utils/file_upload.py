import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from core.config import Settings, get_settings

PDF_MAGIC = b"%PDF-"
ALLOWED_CONTENT_TYPES = ("application/pdf", "application/octet-stream", None)


def ensure_upload_dir(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def sanitize_filename(filename: str) -> str:
    """Strip path components and unsafe characters from an upload filename."""
    name = Path(filename).name.strip()
    name = re.sub(r"[^\w.\- ]", "_", name)
    name = name.strip("._ ") or "document.pdf"
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return name[:200]


def _assert_within_upload_dir(path: Path, upload_dir: Path) -> None:
    if not path.resolve().is_relative_to(upload_dir.resolve()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid upload path"},
        )


async def _write_pdf_file(
    file: UploadFile,
    destination: Path,
    settings: Settings,
) -> None:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Only PDF files allowed"},
        )

    size = 0
    try:
        first_chunk = await file.read(4096)
        if not first_chunk:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Empty file"},
            )
        if not first_chunk.startswith(PDF_MAGIC):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid PDF file"},
            )

        size = len(first_chunk)
        with destination.open("wb") as buffer:
            buffer.write(first_chunk)
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail={"error": "File too large. Max size is 200MB for PDFs."},
                    )
                buffer.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise


async def save_pdf_for_chat(
    chat_id: str,
    file: UploadFile,
    settings: Settings | None = None,
) -> tuple[str, str]:
    """Save a PDF under uploads/<chatId>/ for session-scoped storage."""
    settings = settings or get_settings()
    base_dir = ensure_upload_dir(settings)
    chat_dir = base_dir / chat_id
    chat_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(file.filename or "document.pdf")
    stored_name = f"{uuid.uuid4().hex}-{safe_name}"
    destination = chat_dir / stored_name
    _assert_within_upload_dir(destination, base_dir)

    await _write_pdf_file(file, destination, settings)
    return str(destination), safe_name

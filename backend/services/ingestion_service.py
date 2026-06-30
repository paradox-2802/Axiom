import logging
import os
import re
from pathlib import Path

import pdfplumber
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.ai import get_vector_store
from core.config import get_settings

logger = logging.getLogger(__name__)

_HEADING_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9\s,&\-]{2,60}$")


def _document_title(filename: str) -> str:
    name = filename or "unknown.pdf"
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    return name.strip() or "Financial Document"


def _infer_section_heading(text: str) -> str | None:
    first_line = text.strip().split("\n", 1)[0].strip()
    if not first_line or len(first_line) > 80:
        return None
    if _HEADING_PATTERN.match(first_line) or first_line.isupper():
        return first_line
    return None


async def ingest_pdf(
    path: str,
    filename: str,
    *,
    chat_id: str,
    vector_collection: str,
) -> dict:
    settings = get_settings()
    file_path = Path(path)
    document_title = _document_title(filename)

    if not file_path.exists():
        raise FileNotFoundError("Invalid or missing PDF path")

    pages: list[Document] = []
    with pdfplumber.open(file_path) as pdf:
        for index, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            pages.append(
                Document(
                    page_content=text,
                    metadata={"page": index},
                )
            )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    split_docs = splitter.split_documents(pages)

    enriched_docs: list[Document] = []
    for chunk_index, doc in enumerate(split_docs):
        if not doc.page_content.strip():
            continue
        section = _infer_section_heading(doc.page_content)
        enriched_docs.append(
            Document(
                page_content=doc.page_content,
                metadata={
                    "page": doc.metadata.get("page", 0),
                    "documentTitle": document_title,
                    "sectionHeading": section,
                    "chunkIndex": chunk_index,
                    "filename": filename or "unknown.pdf",
                    "chatId": chat_id,
                    "source": "pdf",
                },
            )
        )

    if not enriched_docs:
        raise ValueError(f"No extractable text in PDF: {filename}")

    vector_store = get_vector_store(settings, collection_name=vector_collection)
    batch_size = settings.INGESTION_BATCH_SIZE
    for i in range(0, len(enriched_docs), batch_size):
        await vector_store.aadd_documents(enriched_docs[i : i + batch_size])

    logger.info(
        "Ingested %s for chat %s: %s chunks into %s",
        filename,
        chat_id,
        len(enriched_docs),
        vector_collection,
    )

    try:
        os.remove(file_path)
    except OSError:
        pass

    return {"chunks": len(enriched_docs), "filename": filename, "chatId": chat_id}

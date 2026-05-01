import io
import logging

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def load_pdf(content: bytes, file_name: str = "unknown.pdf") -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError(
            f"Failed to open PDF '{file_name}': {exc}"
        ) from exc

    text = ""
    for page in doc:
        text += page.get_text()

    return text.strip()


def load_txt(content: bytes) -> str:
    """Decode plain text bytes as UTF-8."""
    return content.decode("utf-8").strip()


def load_gdoc(content: bytes) -> str:
    """Return exported Google Doc plain-text content."""
    return content.decode("utf-8").strip()


def extract_text(content: bytes, mime_type: str, file_name: str = "") -> str:
    """
    Dispatch to the correct loader based on MIME type.

    Args:
        content:   Raw file bytes.
        mime_type: MIME type string.
        file_name: Original file name (used in error messages).

    Returns:
        Extracted plain text string.
    """
    if mime_type == "application/pdf":
        return load_pdf(content, file_name)
    elif mime_type == "text/plain":
        return load_txt(content)
    elif mime_type == "application/vnd.google-apps.document":
        return load_gdoc(content)
    else:
        raise ValueError(f"Unsupported MIME type '{mime_type}' for file '{file_name}'.")
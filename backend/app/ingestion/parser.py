"""
Stage 1a — Ingestion: pull raw text out of an uploaded contract.

Section 3: pdfplumber/PyMuPDF/python-docx, Tesseract OCR only if scanned.
"""
from dataclasses import dataclass

try:
    import docx  # type: ignore
except Exception:  # pragma: no cover - dependency optional in local dev
    docx = None


@dataclass
class ParsedDocument:
    raw_text: str
    page_count: int
    was_scanned: bool  # True if OCR fallback was used


def parse_pdf(file_bytes: bytes) -> ParsedDocument:
    """Best-effort PDF parsing with a safe plain-text fallback when libraries are absent."""
    try:
        import fitz  # PyMuPDF
    except Exception:
        fitz = None

    if fitz is not None:
        try:
            pdf = fitz.open(stream=file_bytes, filetype="pdf")
            texts = [page.get_text("text") for page in pdf]
            raw = "\n\n".join(t for t in texts if t).strip()
            if raw:
                return ParsedDocument(raw_text=raw, page_count=len(texts), was_scanned=False)
        except Exception:
            pass

    # Fallback: treat the PDF as unknown text and preserve a safe raw input.
    try:
        decoded = file_bytes.decode("utf-8")
    except Exception:
        decoded = "".join(chr(b) if 32 <= b < 127 else " " for b in file_bytes)
    return ParsedDocument(raw_text=decoded.strip(), page_count=1, was_scanned=False)


def parse_docx(file_bytes: bytes) -> ParsedDocument:
    """Read .docx text when the dependency is available; otherwise fall back to plain text."""
    if docx is not None:
        try:
            import io
            document = docx.Document(io.BytesIO(file_bytes))
            raw = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
            if raw:
                return ParsedDocument(raw_text=raw, page_count=1, was_scanned=False)
        except Exception:
            pass

    try:
        decoded = file_bytes.decode("utf-8")
    except Exception:
        decoded = "".join(chr(b) if 32 <= b < 127 else " " for b in file_bytes)
    return ParsedDocument(raw_text=decoded.strip(), page_count=1, was_scanned=False)


def parse_document(filename: str, file_bytes: bytes) -> ParsedDocument:
    """Dispatch by extension. Accepts plain-text uploads as an easy runtime fallback."""
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext in {"txt", "md", "rtf"}:
        text = file_bytes.decode("utf-8", errors="replace").strip()
        return ParsedDocument(raw_text=text, page_count=1, was_scanned=False)
    if ext == "pdf":
        return parse_pdf(file_bytes)
    if ext == "docx":
        return parse_docx(file_bytes)
    raise ValueError(f"Unsupported file type: .{ext}")

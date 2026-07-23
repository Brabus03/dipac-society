"""Text extraction for event-report PDFs with graceful fallbacks."""
from pathlib import Path
import subprocess


def extract_pdf_text(file_path):
    """Return all selectable text in a PDF, or an empty string when unavailable."""
    path = Path(file_path)
    try:
        import fitz  # PyMuPDF
        with fitz.open(path) as document:
            return "\n".join(page.get_text("text") for page in document).strip()
    except Exception:
        pass
    try:
        import pdfplumber
        with pdfplumber.open(path) as document:
            return "\n".join((page.extract_text() or "") for page in document.pages).strip()
    except Exception:
        pass
    try:
        result = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, timeout=30, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""

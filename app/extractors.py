from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pypdf import PdfReader
from docx import Document as DocxDocument


@dataclass
class ExtractResult:
    ok: bool
    text: str
    error: Optional[str] = None


def extract_text_from_pdf(path: Path) -> ExtractResult:
    try:
        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t.strip():
                parts.append(t)
        text = "\n\n".join(parts).strip()
        if not text:
            return ExtractResult(
                False, "", "No extractable text found (PDF might be scanned)."
            )
        return ExtractResult(True, text)
    except Exception as e:
        return ExtractResult(False, "", f"PDF extraction failed: {e}")


def extract_text_from_docx(path: Path) -> ExtractResult:
    try:
        doc = DocxDocument(str(path))
        parts = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        text = "\n".join(parts).strip()
        if not text:
            return ExtractResult(False, "", "No extractable text found in DOCX.")
        return ExtractResult(True, text)
    except Exception as e:
        return ExtractResult(False, "", f"DOCX extraction failed: {e}")


def extract_text_from_txt(path: Path) -> ExtractResult:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            return ExtractResult(False, "", "Empty text file.")
        return ExtractResult(True, text)
    except Exception as e:
        return ExtractResult(False, "", f"TXT read failed: {e}")


def extract_text(path: Path) -> ExtractResult:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix == ".docx":
        return extract_text_from_docx(path)
    if suffix in (".txt", ".md"):
        return extract_text_from_txt(path)
    return ExtractResult(
        False, "", f"Unsupported file type: {suffix} (supported: PDF, DOCX, TXT)."
    )

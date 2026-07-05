from __future__ import annotations

from pathlib import Path


def extract_text_from_uploaded_prescription(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md", ".csv"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    return (
        "Image upload received. OCR engine placeholder extracted limited text.\n"
        "Manual review recommended.\n"
        f"Source file: {file_path.name}"
    )

from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Contact:
    name: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""


@dataclass
class ExperienceItem:
    company: str = ""
    role: str = ""
    location: str = ""
    start: str = ""
    end: str = ""
    bullets: List[str] = None

    def __post_init__(self):
        if self.bullets is None:
            self.bullets = []


@dataclass
class Resume:
    contact: Contact
    summary: str = ""
    skills_text: str = ""
    experience: List[ExperienceItem] = None

    def __post_init__(self):
        if self.experience is None:
            self.experience = []

    def to_json(self) -> Dict:
        return {
            "contact": asdict(self.contact),
            "summary": self.summary,
            "skills_text": self.skills_text,
            "experience": [asdict(e) for e in self.experience],
        }


def parse_resume_document(file_path: Optional[str]) -> Resume:
    """MVP: PDF-only parser stub. DOCX and others are not supported.

    Later: implement real PDF parsing into structured JSON.
    """
    if not file_path:
        return Resume(contact=Contact())

    path = Path(file_path)
    if not path.exists():
        return Resume(contact=Contact())

    if path.suffix.lower() != ".pdf":
        # Enforce PDF-only input per requirements
        return Resume(contact=Contact())

    # TODO: Implement PDF parsing (pypdf/pdfminer)
    return Resume(contact=Contact())


def convert_pdf_to_markdown(file_path: Optional[str]) -> str:
    """Convert a PDF resume to Markdown using markitdown.

    - Returns an empty string on any error or when markitdown is unavailable
    - Safe to call in environments without the dependency
    """
    if not file_path:
        return ""
    path = Path(file_path)
    if not path.exists() or path.suffix.lower() != ".pdf":
        return ""
    try:  # pragma: no cover - behavior depends on optional dependency
        from markitdown import MarkItDown  # type: ignore
    except Exception:
        return ""

    try:  # pragma: no cover - library behavior may vary by version
        md = MarkItDown()
        result = md.convert(str(path))

        # Try common return shapes across known versions
        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            for key in ("text_content", "text", "markdown", "content"):
                val = result.get(key)
                if isinstance(val, str) and val.strip():
                    return val

        if isinstance(result, (list, tuple)):
            for item in result:
                if isinstance(item, str) and item.strip():
                    return item
                if isinstance(item, dict):
                    for key in ("text_content", "text", "markdown", "content"):
                        val = item.get(key)
                        if isinstance(val, str) and val.strip():
                            return val
        return ""
    except Exception:
        return ""

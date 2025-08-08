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

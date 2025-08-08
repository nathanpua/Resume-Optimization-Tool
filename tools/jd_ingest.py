from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass
class JobListing:
    source: str
    text: str
    url: Optional[str] = None


def fetch_job_listing(url: Optional[str] = None, raw_text: Optional[str] = None) -> JobListing:
    """Fetch job listing from URL or accept raw text.

    Uses stdlib urllib to avoid external deps.
    """
    if raw_text and raw_text.strip():
        return JobListing(source="raw_text", text=raw_text.strip(), url=None)

    if not url:
        return JobListing(source="empty", text="", url=None)

    parsed = urlparse(url)
    if not parsed.scheme:
        # Not a URL; treat as raw text
        return JobListing(source="raw_text", text=url.strip(), url=None)

    req = Request(url, headers={"User-Agent": "resume-ai/0.1"})
    with urlopen(req, timeout=10) as resp:
        data = resp.read()
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = data.decode("latin-1", errors="ignore")
    return JobListing(source="url", text=text, url=url)

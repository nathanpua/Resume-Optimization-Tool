from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import html
import re


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


def _strip_html(raw: str) -> str:
    # Remove tags and condense whitespace
    no_tags = re.sub(r"<[^>]+>", "\n", raw)
    unescaped = html.unescape(no_tags)
    # Normalize whitespace, but keep newlines to aid title extraction
    unescaped = re.sub(r"\r", "\n", unescaped)
    unescaped = re.sub(r"\n{3,}", "\n\n", unescaped)
    return unescaped


def _slugify(text: str, max_len: int = 60) -> str:
    s = re.sub(r"[^A-Za-z0-9 _\-]+", "", text)
    s = re.sub(r"\s+", "-", s).strip("-_ ")
    s = s.lower()
    return (s[:max_len] or "job")


def derive_job_name(jd_text_html: str, url: Optional[str] = None) -> str:
    """Derive a short folder-friendly job name from JD contents and/or URL.

    Heuristics (best-effort, no external deps):
    - Prefer the <title> tag text when present
    - Else prefer first <h1> text
    - Else pick the shortest non-empty line among the first few lines (likely the header)
    - Try to split into job-title and company via common separators
    - Fallback to URL domain or last path segment
    - Finally fall back to 'job'
    """
    title_match = re.search(r"<title>(.*?)</title>", jd_text_html, flags=re.IGNORECASE | re.DOTALL)
    header_match = re.search(r"<h1[^>]*>(.*?)</h1>", jd_text_html, flags=re.IGNORECASE | re.DOTALL)
    candidate = None
    if title_match:
        candidate = html.unescape(title_match.group(1)).strip()
    elif header_match:
        candidate = html.unescape(header_match.group(1)).strip()
    else:
        stripped = _strip_html(jd_text_html)
        lines = [ln.strip() for ln in stripped.split("\n") if ln.strip()]
        for ln in lines[:15]:
            # Prefer reasonably short header-like lines
            if 5 <= len(ln) <= 100:
                candidate = ln
                break
        if not candidate and lines:
            candidate = lines[0][:100]

    # Try to split into title and company using common separators
    title = None
    company = None
    if candidate:
        parts = re.split(r"\s+[-–—|@]\s+|\s+at\s+|\s+@\s+|\s+\|\s+", candidate, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            title, company = parts[0], parts[1]
        else:
            title = candidate

    if not company and url:
        parsed = urlparse(url)
        host = (parsed.netloc or "").split(":")[0]
        host = host.replace("www.", "")
        # Use second-level domain as company hint, e.g., greenhouse.io/acme → acme
        path_parts = [p for p in (parsed.path or "").split("/") if p]
        company_hint = None
        if len(path_parts) >= 1:
            company_hint = path_parts[0]
        # If company hint is generic like 'jobs', try next
        if company_hint and company_hint.lower() in {"jobs", "careers", "company", "opportunities"} and len(path_parts) >= 2:
            company_hint = path_parts[1]
        company = company or company_hint or host.split(".")[0]

    if title and company:
        return _slugify(f"{title}-{company}")
    if title:
        return _slugify(title)
    if company:
        return _slugify(company)
    if url:
        parsed = urlparse(url)
        last = [p for p in (parsed.path or "").split("/") if p][-1:] or [parsed.netloc or "job"]
        return _slugify(last[0])
    return "job"

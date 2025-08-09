from __future__ import annotations
import re
from typing import List, Tuple


_ITEMIZE_BLOCK_RE = re.compile(r"\\begin\{itemize\}(.*?)\\end\{itemize\}", re.DOTALL)
_ITEM_RE = re.compile(r"\\item\s+(.*)")
_HEADER_RE = re.compile(r"\\resumeheader\s*\{(.*?)\}\s*\{(.*?)\}\s*\{(.*?)\}\s*\{(.*?)\}\s*\{(.*?)\}", re.DOTALL)


def extract_itemize_blocks(tex: str) -> List[Tuple[str, List[str]]]:
    """Return list of (full_block_text, items) for each itemize environment."""
    blocks: List[Tuple[str, List[str]]] = []
    for m in _ITEMIZE_BLOCK_RE.finditer(tex):
        block = m.group(0)
        inner = m.group(1)
        items = [im.group(1).strip() for im in _ITEM_RE.finditer(inner)]
        blocks.append((block, items))
    return blocks


def replace_itemize_block(tex: str, old_block: str, new_items: List[str]) -> str:
    new_inner = "\n".join([f"\\item {s}" for s in new_items])
    new_block = f"\\begin{{itemize}}\n{new_inner}\n\\end{{itemize}}"
    return tex.replace(old_block, new_block, 1)


def set_header_availability(tex: str, availability: str | None) -> str:
    """If availability is None, leave header unchanged. Otherwise, set the 3rd field."""
    m = _HEADER_RE.search(tex)
    if not m:
        return tex
    if availability is None:
        return tex
    name, location, avail, email, link = m.groups()
    new_avail = (availability or "").strip()
    replacement = f"\\resumeheader{{{name}}}{{{location}}}{{{new_avail}}}{{{email}}}{{{link}}}"
    return tex[: m.start()] + replacement + tex[m.end() :]


def escape_latex_text(text: str) -> str:
    """Escape LaTeX special characters in plain text.

    Only escapes characters that are not already escaped. Leaves existing LaTeX
    commands intact by avoiding escaping backslashes themselves.
    """
    if not text:
        return text

    # Unescaped specials: %, $, &, #, _, {, }
    patterns = [
        (r"(?<!\\)%", r"\\%"),
        (r"(?<!\\)\$", r"\\$"),
        (r"(?<!\\)&", r"\\&"),
        (r"(?<!\\)#", r"\\#"),
        (r"(?<!\\)_", r"\\_"),
        (r"(?<!\\)\\{", r"\\{"),
        (r"(?<!\\)\\}", r"\\}"),
    ]

    # Tilde and caret have no simple escapes in text mode
    # Replace unescaped ~ and ^ with text macros
    patterns.extend([
        (r"(?<!\\)~", r"\\textasciitilde{}"),
        (r"(?<!\\)\^", r"\\textasciicircum{}"),
    ])

    escaped = text
    for pattern, repl in patterns:
        escaped = re.sub(pattern, repl, escaped)
    return escaped


_ANGLE_CONTENT_RE = re.compile(r"<\s*([^<>]+?)\s*>")
_MD_BOLD_RE = re.compile(r"\*\*([^\n]*?)\*\*")
_MD_ITALIC_RE = re.compile(r"(?<!\*)\*([^\n*]+?)\*(?!\*)")
_MD_UNDER_BOLD_RE = re.compile(r"__([^\n_]+?)__")
_MD_UNDER_ITALIC_RE = re.compile(r"(?<!_)_([^\n_]+?)_(?!_)")


def sanitize_llm_bullet(text: str) -> str:
    """Normalize raw LLM bullet text before LaTeX escaping.

    - Unwraps angle-bracket placeholders: "<SQL>" -> "SQL", removes empty "<>"
    - Strips Markdown emphasis wrappers: **bold**, *italic*, __bold__, _italic_
    - Leaves inner content verbatim so numbers and symbols remain
    - Run before LaTeX escaping
    """
    if not text:
        return text
    s = text
    # Remove empty placeholders first
    s = s.replace("<>", "")
    # Unwrap single-level <...> markers
    # Apply repeatedly in case of multiple occurrences
    for _ in range(5):
        if "<" not in s:
            break
        s_new = _ANGLE_CONTENT_RE.sub(r"\1", s)
        if s_new == s:
            break
        s = s_new

    # Remove common Markdown emphasis wrappers
    # Apply a few times to handle nested/multiple occurrences
    for _ in range(3):
        s_new = _MD_BOLD_RE.sub(r"\1", s)
        s_new = _MD_UNDER_BOLD_RE.sub(r"\1", s_new)
        s_new = _MD_ITALIC_RE.sub(r"\1", s_new)
        s_new = _MD_UNDER_ITALIC_RE.sub(r"\1", s_new)
        if s_new == s:
            break
        s = s_new
    return s.strip()

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

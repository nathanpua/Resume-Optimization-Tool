from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class CoverageReport:
    required_present: List[str]
    required_missing: List[str]
    preferred_present: List[str]
    preferred_missing: List[str]
    before_counts: Dict[str, int]
    after_counts: Dict[str, int]
    changes: List[str]


_WORD_RE = re.compile(r"[A-Za-z0-9\-\+/#\.]+")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _WORD_RE.findall(text or "")]


def _count_terms(text: str, terms: List[str]) -> Dict[str, int]:
    tokens = _tokenize(text)
    joined = " ".join(tokens)
    counts: Dict[str, int] = {}
    for term in terms:
        t = (term or "").strip().lower()
        if not t:
            continue
        # simple substring count for now
        counts[term] = joined.count(t)
    return counts


def compute_keyword_coverage(before_tex: str, after_tex: str, keywords: Dict[str, List[str]]) -> CoverageReport:
    required = list(dict.fromkeys(keywords.get("required", [])))
    preferred = list(dict.fromkeys(keywords.get("preferred", [])))

    before_counts = _count_terms(before_tex, required + preferred)
    after_counts = _count_terms(after_tex, required + preferred)

    required_present = [k for k in required if after_counts.get(k, 0) > 0]
    required_missing = [k for k in required if after_counts.get(k, 0) == 0]
    preferred_present = [k for k in preferred if after_counts.get(k, 0) > 0]
    preferred_missing = [k for k in preferred if after_counts.get(k, 0) == 0]

    changes: List[str] = []
    for k in (required + preferred):
        b = before_counts.get(k, 0)
        a = after_counts.get(k, 0)
        if a > b:
            changes.append(f"Increased '{k}' from {b} to {a}")
        elif a < b:
            changes.append(f"Decreased '{k}' from {b} to {a}")

    return CoverageReport(
        required_present=required_present,
        required_missing=required_missing,
        preferred_present=preferred_present,
        preferred_missing=preferred_missing,
        before_counts=before_counts,
        after_counts=after_counts,
        changes=changes,
    )

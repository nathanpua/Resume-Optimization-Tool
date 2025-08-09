from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List

from tools.latex import compile_pdf
from .env import load_dotenv
from .lm_google import GoogleLMClient
from .tex_edit import extract_itemize_blocks, replace_itemize_block, set_header_availability
from .coverage import compute_keyword_coverage
from tools.jd_ingest import fetch_job_listing


def optimize_resume(
    job_input_text: str,
    job_input_url: str,
    resume_path: str,
    out_dir: str,
    preferences: Dict[str, Any],
) -> Dict[str, Any]:
    """Preserve base TeX format, change only bullets using Gemini 2.0 Flash, and compile PDF.

    - Base template: preferences["input_tex"] or repo root `Nathan_Pua_Resume.tex`.
    - Only edits contents of itemize blocks; updates header availability only when provided.
    - Returns a report with keyword coverage before/after and per-block change justifications.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Load environment and set up LLM
    load_dotenv()
    model_name = (preferences or {}).get("model") or "gemini-2.0-flash"
    llm = GoogleLMClient(model=model_name)

    # Determine base TeX input
    input_tex_path = (preferences or {}).get("input_tex")
    base_tex_path = Path(input_tex_path) if input_tex_path else Path.cwd() / "Nathan_Pua_Resume.tex"
    if not base_tex_path.exists():
        tex_path = out / "resume.tex"
        tex_path.write_text("% Base template not found. Place your .tex and pass --input-tex\n", encoding="utf-8")
        pdf_path = compile_pdf(tex_path)
        return {
            "outputs": {"tex": str(tex_path), "pdf": pdf_path},
            "preferences": preferences,
            "notes": "Base template missing; wrote placeholder.",
            "job_input_present": bool(job_input_text or job_input_url),
            "resume_present": bool(resume_path),
        }

    # Fetch JD text: prefer URL when provided
    if job_input_url:
        jd = fetch_job_listing(url=job_input_url, raw_text=None)
        jd_text = jd.text
    else:
        jd = fetch_job_listing(url=None, raw_text=job_input_text)
        jd_text = jd.text

    before_tex = base_tex_path.read_text(encoding="utf-8")

    # Update availability only when provided
    if (preferences or {}).get("availability") is not None:
        before_tex = set_header_availability(before_tex, preferences.get("availability"))

    # Extract bullets
    blocks = extract_itemize_blocks(before_tex)

    # Extract keywords and plan
    keywords = llm.extract_keywords(jd_text or "")
    target_keywords: List[str] = (keywords.get("required", []) + keywords.get("preferred", []))[:40]

    # Rewrite bullets per block
    new_bullets_per_block: List[List[str]] = []
    per_block_changes: List[Dict[str, Any]] = []
    for _, items in blocks:
        rewritten = llm.rewrite_bullets({"bullets": items}, target_keywords=target_keywords)
        if not rewritten:
            rewritten = items
        if len(rewritten) < len(items):
            rewritten = rewritten + items[len(rewritten) :]
        elif len(rewritten) > len(items):
            rewritten = rewritten[: len(items)]
        new_bullets_per_block.append(rewritten)
        old_text = " \n".join(items).lower()
        new_text = " \n".join(rewritten).lower()
        added = [k for k in target_keywords if k.lower() in new_text and k.lower() not in old_text]
        per_block_changes.append({
            "old_items": items,
            "new_items": rewritten,
            "added_keywords": added,
        })

    # Apply replacements keeping base format unchanged
    after_tex = before_tex
    for (full_block, _items), new_items in zip(blocks, new_bullets_per_block):
        after_tex = replace_itemize_block(after_tex, full_block, new_items)

    # Compute coverage before/after
    coverage = compute_keyword_coverage(before_tex, after_tex, keywords)

    # Write outputs
    tex_path = out / "resume.tex"
    tex_path.write_text(after_tex, encoding="utf-8")
    pdf_path = compile_pdf(tex_path)

    return {
        "outputs": {"tex": str(tex_path), "pdf": pdf_path},
        "preferences": preferences,
        "notes": "Edited bullets only; preserved base formatting.",
        "job_input_present": bool(job_input_text or job_input_url),
        "resume_present": bool(resume_path),
        "coverage": {
            "required_present": coverage.required_present,
            "required_missing": coverage.required_missing,
            "preferred_present": coverage.preferred_present,
            "preferred_missing": coverage.preferred_missing,
            "before_counts": coverage.before_counts,
            "after_counts": coverage.after_counts,
            "changes": coverage.changes,
        },
        "change_justifications": per_block_changes,
        "jd_source": {"url": job_input_url or None, "text_length": len(jd_text or "")},
    }

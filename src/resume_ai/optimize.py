from __future__ import annotations
from pathlib import Path
import os
from typing import Any, Dict, List, Optional, Callable

from tools.latex import compile_pdf
from tools.resume_parse import convert_pdf_to_markdown
from .env import load_dotenv
from .lm_openrouter import OpenRouterClient
from .tex_edit import (
    extract_itemize_blocks,
    replace_itemize_block,
    set_header_availability,
    escape_latex_text,
    sanitize_llm_bullet,
)
from .coverage import compute_keyword_coverage
from tools.jd_ingest import fetch_job_listing


def optimize_resume(
    job_input_text: str,
    job_input_url: str,
    resume_path: str,
    out_dir: str,
    preferences: Dict[str, Any],
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Preserve base TeX format, change only bullets using an OpenRouter model, and compile PDF.

    - Base template: preferences["input_tex"] or repo root `Nathan_Pua_Resume.tex`.
    - Only edits contents of itemize blocks; updates header availability only when provided.
    - Returns a report with keyword coverage before/after and per-block change justifications.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    def _notify(stage: str) -> None:
        try:
            if progress_callback is not None:
                progress_callback(stage)
        except Exception:
            pass

    # Load environment and set up LLM
    _notify("loading_env")
    load_dotenv()
    # Model selection rules (OpenRouter-only):
    # - If preferences.model is provided, use it as-is
    # - Else use OPENROUTER_MODEL or default to DeepSeek v3 free
    requested_model = (preferences or {}).get("model")
    if not requested_model:
        requested_model = os.getenv("OPENROUTER_MODEL") or "deepseek/deepseek-chat-v3-0324:free"

    # Provider selection: OpenRouter only
    llm = OpenRouterClient(model=requested_model)
    _notify("model_selected")

    # Determine base TeX input
    _notify("reading_base_tex")
    input_tex_path = (preferences or {}).get("input_tex")
    base_tex_path = Path(input_tex_path) if input_tex_path else Path.cwd() / "Nathan_Pua_Resume.tex"
    if not base_tex_path.exists():
        tex_path = out / "resume.tex"
        # Write a minimal compilable TeX so smoke tests pass and users can preview pipeline
        tex_path.write_text(
            r"""\documentclass[letterpaper,10pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\begin{document}
\section*{Resume}
\begin{itemize}
\item Placeholder bullet A
\item Placeholder bullet B
\end{itemize}
\end{document}
""",
            encoding="utf-8",
        )
        _notify("compiling_pdf")
        pdf_path = compile_pdf(tex_path)
        return {
            "outputs": {"tex": str(tex_path), "pdf": pdf_path},
            "preferences": preferences,
            "notes": "Base template missing; wrote placeholder.",
            "job_input_present": bool(job_input_text or job_input_url),
            "resume_present": bool(resume_path),
        }

    # Fetch JD text: prefer URL when provided
    _notify("fetching_jd")
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

    # Convert resume PDF to Markdown (optional context for LLM)
    _notify("parsing_resume_pdf")
    resume_md = convert_pdf_to_markdown(resume_path) if resume_path else ""

    # Extract keywords and plan (clip JD to avoid oversized payloads)
    _notify("extracting_keywords")
    jd_text_for_llm = (jd_text or "")
    if len(jd_text_for_llm) > 20000:
        jd_text_for_llm = jd_text_for_llm[:20000]
    keywords = llm.extract_keywords(jd_text_for_llm)

    # Fallback on error + empty keywords
    if not ((keywords.get("required") or []) or (keywords.get("preferred") or [])):
        last_status = getattr(llm, "last_status", "")
        if last_status == "error":
            # Align with lm_openrouter.py env var naming and default to Kimi K2
            fallback_model = os.getenv("OPENROUTER_MODEL_FALLBACK", "moonshotai/kimi-k2")
            if fallback_model and fallback_model != requested_model:
                llm = OpenRouterClient(model=fallback_model)
                requested_model = fallback_model
                keywords = llm.extract_keywords(jd_text_for_llm)
    target_keywords: List[str] = (keywords.get("required", []) + keywords.get("preferred", []))[:40]

    # Rewrite bullets
    new_bullets_per_block: List[List[str]] = []
    per_block_changes: List[Dict[str, Any]] = []
    rewrite_mode = (preferences or {}).get("rewrite_mode", "per_block")
    if rewrite_mode not in ("single_call", "per_block"):
        rewrite_mode = "per_block"

    if rewrite_mode == "single_call":
        _notify("rewriting_bullets single-call")
        try:
            sections = [{"id": i, "bullets": items} for i, (_full, items) in enumerate(blocks)]
            mapping = llm.rewrite_bullets_multi(sections, target_keywords=target_keywords, resume_markdown=resume_md or None)
        except Exception:
            mapping = {}
        # If invalid/empty, fall back to per-block
        if not mapping or not isinstance(mapping, dict):
            # Log via llm stats already; proceed with per-block
            rewrite_mode = "per_block"

        if rewrite_mode == "single_call":
            for i, (_full, items) in enumerate(blocks):
                rewritten = list(mapping.get(i, items) or [])
                if not rewritten:
                    rewritten = items
                if len(rewritten) < len(items):
                    rewritten = rewritten + items[len(rewritten) :]
                elif len(rewritten) > len(items):
                    rewritten = rewritten[: len(items)]
                rewritten = [escape_latex_text(sanitize_llm_bullet(s)) for s in rewritten]
                new_bullets_per_block.append(rewritten)
                old_text = " \n".join(items).lower()
                new_text = " \n".join(rewritten).lower()
                added = [k for k in target_keywords if k.lower() in new_text and k.lower() not in old_text]
                per_block_changes.append({
                    "old_items": items,
                    "new_items": rewritten,
                    "added_keywords": added,
                })
            _notify("rewriting_complete")

    if rewrite_mode == "per_block":
        _notify("rewriting_bullets 0/0")
        total_blocks = len(blocks)
        for idx, (_, items) in enumerate(blocks):
            _notify(f"rewriting_bullets {idx+1}/{total_blocks}")
            rewritten = llm.rewrite_bullets({"bullets": items}, target_keywords=target_keywords, resume_markdown=resume_md or None)
            if not rewritten:
                rewritten = items
            if len(rewritten) < len(items):
                rewritten = rewritten + items[len(rewritten) :]
            elif len(rewritten) > len(items):
                rewritten = rewritten[: len(items)]
            rewritten = [escape_latex_text(sanitize_llm_bullet(s)) for s in rewritten]
            new_bullets_per_block.append(rewritten)
            old_text = " \n".join(items).lower()
            new_text = " \n".join(rewritten).lower()
            added = [k for k in target_keywords if k.lower() in new_text and k.lower() not in old_text]
            per_block_changes.append({
                "old_items": items,
                "new_items": rewritten,
                "added_keywords": added,
            })
        _notify("rewriting_complete")

    # Apply replacements keeping base format unchanged
    after_tex = before_tex
    for (full_block, _items), new_items in zip(blocks, new_bullets_per_block):
        after_tex = replace_itemize_block(after_tex, full_block, new_items)

    # Compute coverage before/after
    _notify("computing_coverage")
    coverage = compute_keyword_coverage(before_tex, after_tex, keywords)

    # Write outputs
    _notify("writing_outputs")
    tex_path = out / "resume.tex"
    tex_path.write_text(after_tex, encoding="utf-8")
    _notify("compiling_pdf")
    pdf_path = compile_pdf(tex_path)

    # LLM diagnostics for report
    llm_provider = "openrouter"
    llm_configured = bool(os.getenv("OPENROUTER_API_KEY"))
    llm_stats = {
        "provider": llm_provider,
        "model": requested_model,
        "configured": llm_configured,
        "calls_made": getattr(llm, "calls_made", None),
        "last_status": getattr(llm, "last_status", None),
        "last_error": getattr(llm, "last_error", None),
    }

    _notify("done")
    return {
        "outputs": {"tex": str(tex_path), "pdf": pdf_path},
        "preferences": preferences,
        "notes": "Edited bullets only; preserved base formatting.",
        "job_input_present": bool(job_input_text or job_input_url),
        "resume_present": bool(resume_path),
        "llm": llm_stats,
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

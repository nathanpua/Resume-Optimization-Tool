from __future__ import annotations
from pathlib import Path
import os
from typing import Any, Dict, List, Optional, Callable

from tools.latex import compile_pdf
from tools.resume_parse import convert_pdf_to_markdown
from .env import load_dotenv
from .lm_google import GoogleLMClient
from .lm_openai import OpenAIClient
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
    """Preserve base TeX format, change only bullets using Gemini 2.0 Flash, and compile PDF.

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
    # Model selection rules (prefer OpenRouter when available):
    # - If preferences.model is provided, use it
    # - Else when OPENROUTER_API_KEY is set: OPENROUTER_MODEL or default to DeepSeek v3 free
    # - Else fall back to GOOGLE_MODEL or OPENAI_MODEL or gemini-2.0-flash
    requested_model = (preferences or {}).get("model")
    if not requested_model:
        if os.getenv("OPENROUTER_API_KEY"):
            requested_model = os.getenv("OPENROUTER_MODEL") or "deepseek/deepseek-chat-v3-0324:free"
        else:
            requested_model = (
                os.getenv("GOOGLE_MODEL")
                or os.getenv("OPENAI_MODEL")
                or "gemini-2.0-flash"
            )

    # Provider selection:
    # - Prefer OpenRouter when API key present and model looks like provider/model or openrouter/*
    # - Else use OpenAI when model contains 'gpt'
    # - Else use Google
    model_lc = (requested_model or "").lower()
    have_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
    use_openrouter = have_openrouter and ("/" in model_lc or model_lc.startswith("openrouter/") or model_lc in ("openrouter", "openrouter/auto"))
    use_openai = (not use_openrouter) and ("gpt" in model_lc)

    if use_openrouter:
        llm = OpenRouterClient(model=requested_model)
    elif use_openai:
        llm = OpenAIClient(model=requested_model)
    else:
        llm = GoogleLMClient(model=requested_model)
    _notify("model_selected")

    # Determine base TeX input
    _notify("reading_base_tex")
    input_tex_path = (preferences or {}).get("input_tex")
    base_tex_path = Path(input_tex_path) if input_tex_path else Path.cwd() / "Nathan_Pua_Resume.tex"
    if not base_tex_path.exists():
        tex_path = out / "resume.tex"
        tex_path.write_text("% Base template not found. Place your .tex and pass --input-tex\n", encoding="utf-8")
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

    # Fallbacks by provider on error + empty keywords
    if not ((keywords.get("required") or []) or (keywords.get("preferred") or [])):
        last_status = getattr(llm, "last_status", "")
        if last_status == "error":
            if use_openrouter:
                # Align with lm_openrouter.py env var naming and default to Kimi K2
                fallback_model = os.getenv("OPENROUTER_MODEL_FALLBACK", "moonshotai/kimi-k2")
                if fallback_model and fallback_model != requested_model:
                    llm = OpenRouterClient(model=fallback_model)
                    requested_model = fallback_model
                    keywords = llm.extract_keywords(jd_text_for_llm)
            elif use_openai:
                fallback_model = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4o-mini")
                if fallback_model and fallback_model != requested_model:
                    llm = OpenAIClient(model=fallback_model)
                    requested_model = fallback_model
                    keywords = llm.extract_keywords(jd_text_for_llm)
    target_keywords: List[str] = (keywords.get("required", []) + keywords.get("preferred", []))[:40]

    # Rewrite bullets per block
    _notify("rewriting_bullets 0/0")
    new_bullets_per_block: List[List[str]] = []
    per_block_changes: List[Dict[str, Any]] = []
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
        # Sanitize placeholders like <SQL> or <> then escape LaTeX specials
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
    llm_provider = "openrouter" if use_openrouter else ("openai" if use_openai else "google")
    if use_openrouter:
        llm_configured = bool(os.getenv("OPENROUTER_API_KEY"))
    elif use_openai:
        llm_configured = bool(os.getenv("OPENAI_API_KEY"))
    else:
        llm_configured = bool(os.getenv("GOOGLE_API_KEY"))
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

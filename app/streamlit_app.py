from __future__ import annotations

import base64
import io
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st
import time
import threading
import shutil

# Ensure local imports work when running `streamlit run app/streamlit_app.py`
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from resume_ai.optimize import optimize_resume  # type: ignore  # noqa: E402
from resume_ai.env import load_dotenv  # type: ignore  # noqa: E402
from tools.jd_ingest import fetch_job_listing, derive_job_name  # type: ignore  # noqa: E402

# ---------- Config ----------
# Ensure .env at repo root is loaded for UI and backend
try:
    load_dotenv(str(REPO_ROOT / ".env"))
except Exception:
    pass
MAX_RESUME_PDF_BYTES = int(os.getenv("UI_MAX_RESUME_PDF_MB", "15")) * 1024 * 1024
MAX_TEX_BYTES = int(os.getenv("UI_MAX_TEX_MB", "1")) * 1024 * 1024
MAX_JD_TEXT_CHARS = int(os.getenv("UI_MAX_JD_TEXT_CHARS", "20000"))
WARN_JD_TEXT_CHARS = int(os.getenv("UI_WARN_JD_TEXT_CHARS", "18000"))
MAX_URL_CHARS = int(os.getenv("UI_MAX_URL_CHARS", "2048"))
OUT_BASE_DIR = REPO_ROOT / "out"
TMP_DIR = OUT_BASE_DIR / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_file(uploaded, suffix: str, max_bytes: int) -> Optional[Path]:
    if uploaded is None:
        return None
    if hasattr(uploaded, "size") and uploaded.size and uploaded.size > max_bytes:
        raise ValueError(f"File exceeds size limit ({max_bytes // (1024*1024)} MB)")
    # Use a random name to avoid collisions
    name = f"{uuid.uuid4().hex}{suffix}"
    dest = TMP_DIR / name
    # Streamlit provides a BytesIO-like object
    with open(dest, "wb") as f:
        f.write(uploaded.getbuffer())
    return dest


def build_job_name(jd_url: str, jd_text: str, override: str) -> str:
    if override and override.strip():
        return override.strip()
    jd = fetch_job_listing(url=jd_url or None, raw_text=jd_text or None)
    return derive_job_name(jd.text or "", url=jd.url) or "job"


def read_file_bytes(path: Path) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def embed_pdf(path: Path):
    pdf_bytes = read_file_bytes(path)
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="900px" style="border:none;"></iframe>',
        unsafe_allow_html=True,
    )


def render_report(result: dict):
    llm = result.get("llm", {}) or {}
    coverage = result.get("coverage", {}) or {}
    justifications = result.get("change_justifications", []) or []
    jd_source = result.get("jd_source", {}) or {}

    st.subheader("Report")
    with st.expander("LLM and Model Info", expanded=True):
        cols = st.columns(4)
        cols[0].metric(label="Provider", value=str(llm.get("provider", "-")))
        cols[1].metric(label="Model", value=str(llm.get("model", "-")))
        cols[2].metric(label="Configured", value=str(llm.get("configured", False)))
        cols[3].metric(label="Calls Made", value=str(llm.get("calls_made", "-")))
        if llm.get("last_status") == "error" or llm.get("last_error"):
            st.error(f"Last error: {llm.get('last_error', '')}")

    with st.expander("Coverage Summary", expanded=True):
        req_present = coverage.get("required_present", []) or []
        req_missing = coverage.get("required_missing", []) or []
        pref_present = coverage.get("preferred_present", []) or []
        pref_missing = coverage.get("preferred_missing", []) or []

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Required Present", len(req_present))
        c2.metric("Required Missing", len(req_missing))
        c3.metric("Preferred Present", len(pref_present))
        c4.metric("Preferred Missing", len(pref_missing))

        if req_missing or pref_missing:
            st.markdown("**Missing Keywords**")
            chips = req_missing + pref_missing
            if chips:
                st.write(
                    ", ".join(sorted(set(str(x) for x in chips if str(x).strip())))
                )

    with st.expander("Changes by Section", expanded=False):
        for idx, change in enumerate(justifications):
            old_items = change.get("old_items", []) or []
            new_items = change.get("new_items", []) or []
            added = change.get("added_keywords", []) or []
            st.markdown(f"**Section {idx + 1}**")
            cols = st.columns(2)
            with cols[0]:
                st.caption("Old bullets")
                for it in old_items:
                    st.write(f"- {it}")
            with cols[1]:
                st.caption("New bullets")
                for it in new_items:
                    st.write(f"- {it}")
            if added:
                st.caption("Added keywords")
                st.write(", ".join(added))
            st.divider()

    with st.expander("Job Description Source", expanded=False):
        st.write({"url": jd_source.get("url"), "text_length": jd_source.get("text_length")})


# ---------- UI ----------
st.set_page_config(page_title="Resume AI Optimizer", layout="wide")
st.title("Resume AI Optimizer")
st.caption("Tailor your resume to a job description and view the results.")

# Env guidance (OpenRouter only)
has_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
if not has_openrouter:
    st.warning(
        "No LLM API key detected. Set `OPENROUTER_API_KEY` in `.env`.",
        icon="⚠️",
    )

with st.form("inputs_form"):
    st.subheader("Inputs")
    resume_upload = st.file_uploader("Upload your resume (PDF)", type=["pdf"], accept_multiple_files=False, help="Max size 15 MB")

    input_method = st.radio("Job description input", options=["URL", "Text"], horizontal=True)
    if input_method == "URL":
        jd_url = st.text_input("JD URL", placeholder="https://…", help="Max length 2048 characters")
        jd_text = ""
    else:
        jd_text = st.text_area("JD Text", height=180, placeholder="Paste the job description here…", help="Max 20,000 characters; long text will be truncated by the backend")
        jd_url = ""

    with st.expander("Advanced options", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            # Choose placeholder; prefer OpenRouter defaults
            default_placeholder = os.getenv("OPENROUTER_MODEL") or "deepseek/deepseek-chat-v3-0324:free"
            model = st.text_input(
                "Model (optional)",
                placeholder=default_placeholder,
                help="Enter an OpenRouter model id (e.g., 'z-ai/glm-4.5v', 'openai/gpt-4o-mini') or leave blank to use defaults.",
            )
            job_name_override = st.text_input("Job name (optional)")
        with c2:
            strategy = st.selectbox("Strategy", options=["conservative", "balanced", "bold"], index=1)
            pages = st.selectbox("Pages", options=["auto", "one", "two"], index=0)
        with c3:
            availability = st.text_input("Availability (optional)", placeholder="e.g., Available Jan–Jun 2026")
            reuse_existing = st.checkbox("Reuse existing outputs if present", value=False)
        tex_upload = st.file_uploader("Optional: Upload TeX template (.tex)", type=["tex"], accept_multiple_files=False, help="Max size 1 MB")
        
        # Show default routing note when OpenRouter is configured and model is not specified
        if has_openrouter:
            st.caption("OpenRouter is configured. If no model is provided, defaults to DeepSeek v3 free with Kimi K2 fallback.")

    submitted = st.form_submit_button("Optimize", type="primary")

if submitted:
    # Validations
    errors = []
    if not resume_upload:
        errors.append("Resume PDF is required")
    else:
        if getattr(resume_upload, "type", "") not in ("application/pdf", "application/x-pdf", "binary/octet-stream"):
            # Some browsers provide generic type; also rely on extension which st enforces
            pass
        if hasattr(resume_upload, "size") and resume_upload.size and resume_upload.size > MAX_RESUME_PDF_BYTES:
            errors.append(f"Resume exceeds {MAX_RESUME_PDF_BYTES // (1024*1024)} MB limit")

    if input_method == "URL" and not jd_url:
        errors.append("Provide a JD URL")
    if input_method == "Text" and not jd_text:
        errors.append("Provide JD text")
    if jd_url and len(jd_url) > MAX_URL_CHARS:
        errors.append("JD URL is too long")
    if jd_text and len(jd_text) > MAX_JD_TEXT_CHARS:
        errors.append("JD text exceeds 20,000 character limit")

    if tex_upload is not None and hasattr(tex_upload, "size") and tex_upload.size and tex_upload.size > MAX_TEX_BYTES:
        errors.append("TeX template exceeds 1 MB limit")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    if jd_text and len(jd_text) >= WARN_JD_TEXT_CHARS:
        st.info("JD text is very long; it will be truncated to ~20k characters.")

    # Save files to temp
    try:
        resume_path = save_uploaded_file(resume_upload, ".pdf", MAX_RESUME_PDF_BYTES)
    except Exception as e:  # pragma: no cover - safety
        st.error(str(e))
        st.stop()

    tex_template_path: Optional[Path] = None
    if tex_upload is not None:
        try:
            tex_template_path = save_uploaded_file(tex_upload, ".tex", MAX_TEX_BYTES)
        except Exception as e:
            st.error(str(e))
            st.stop()
    # Default to repo root template if available and no upload provided
    default_root_tex = REPO_ROOT / "Nathan_Pua_Resume.tex"
    if tex_template_path is None and default_root_tex.exists():
        tex_template_path = default_root_tex

    # Compute job folder name and out dir
    job_name = build_job_name(jd_url, jd_text, job_name_override)
    out_dir = OUT_BASE_DIR / job_name

    result: Optional[dict] = None

    if out_dir.exists() and reuse_existing:
        # Try to reuse existing results
        report_path = out_dir / "report.json"
        pdf_path = out_dir / "resume.pdf"
        loaded = None
        if report_path.exists():
            try:
                loaded = json.loads(report_path.read_text(encoding="utf-8"))
            except Exception:
                loaded = None
        if loaded:
            # Ensure outputs paths are accurate
            outputs = loaded.get("outputs", {}) or {}
            if pdf_path.exists():
                outputs["pdf"] = str(pdf_path)
            loaded["outputs"] = outputs
            result = loaded
        else:
            st.info("Existing folder found but no report.json; running optimization instead…")

    if result is None:
        preferences = {
            "strategy": strategy,
            "pages": pages,
            "availability": availability if availability else None,
            "input_tex": str(tex_template_path) if tex_template_path else None,
            "job_name": job_name,
            "model": model if model else None,
        }

        status_placeholder = st.empty()
        start_time = time.time()
        result_holder = {"result": None, "error": None}
        stage_holder = {"stage": "starting"}

        def _run_optimize():
            try:
                result_holder["result"] = optimize_resume(
                    job_input_text=jd_text or "",
                    job_input_url=jd_url or "",
                    resume_path=str(resume_path) if resume_path else "",
                    out_dir=str(out_dir),
                    preferences=preferences,
                    progress_callback=lambda s: stage_holder.__setitem__("stage", s),
                )
            except Exception as exc:
                result_holder["error"] = exc

        worker = threading.Thread(target=_run_optimize, daemon=True)
        worker.start()
        while worker.is_alive():
            elapsed = time.time() - start_time
            stage = stage_holder.get("stage", "working")
            # Map internal codes to friendly labels
            stage_map = {
                "loading_env": "Loading environment",
                "model_selected": "Selecting model",
                "reading_base_tex": "Reading base template",
                "fetching_jd": "Analyzing job description",
                "parsing_resume_pdf": "Parsing resume PDF",
                "extracting_keywords": "Extracting keywords",
                "rewriting_bullets 0/0": "Rewriting bullets",
                "rewriting_complete": "Rewriting complete",
                "computing_coverage": "Computing coverage",
                "writing_outputs": "Writing outputs",
                "compiling_pdf": "Compiling PDF",
                "done": "Done",
            }
            friendly = stage_map.get(stage, stage)
            # If stage includes progress like "rewriting_bullets X/Y", show it directly
            if stage.startswith("rewriting_bullets "):
                friendly = stage.replace("rewriting_bullets", "Rewriting bullets")
            status_placeholder.info(f"{friendly}… elapsed {int(elapsed)}s")
            time.sleep(0.5)
        worker.join()

        if result_holder["error"] is not None:
            st.error(f"Optimization failed: {result_holder['error']}")
            st.stop()

        result = result_holder["result"]
        status_placeholder.success(f"Optimization completed in {time.time() - start_time:.1f}s")

        # Write report.json for consistency with CLI
        try:
            with open(out_dir / "report.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
        except Exception:
            pass

    # Render results
    st.success(f"Done. Outputs in {out_dir}")
    outputs = (result or {}).get("outputs", {}) or {}
    pdf_path_str = outputs.get("pdf")

    st.caption(f"Job folder: {out_dir}")

    tab_pdf, tab_report, tab_diag = st.tabs(["PDF", "Report", "Diagnostics"])

    with tab_pdf:
        col_pdf, col_downloads = st.columns([3, 1])
        with col_pdf:
            st.subheader("Resume PDF")
            if pdf_path_str and Path(pdf_path_str).exists():
                embed_pdf(Path(pdf_path_str))
            else:
                st.info("PDF not available. Install LaTeX tools (`latexmk`, `pdflatex`) and retry.")
        with col_downloads:
            st.subheader("Downloads")
            report_bytes = json.dumps(result, indent=2).encode("utf-8")
            st.download_button(
                label="Download report.json",
                data=report_bytes,
                file_name="report.json",
                mime="application/json",
                use_container_width=True,
            )
            if pdf_path_str and Path(pdf_path_str).exists():
                st.download_button(
                    label="Download resume.pdf",
                    data=read_file_bytes(Path(pdf_path_str)),
                    file_name="resume.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

    with tab_report:
        render_report(result or {})

    with tab_diag:
        st.subheader("LaTeX diagnostics")
        try:
            compile_log = (Path(out_dir) / "resume_compile.log")
            if compile_log.exists():
                st.caption("resume_compile.log (last run)")
                content = compile_log.read_text(encoding="utf-8", errors="ignore")
                st.code(content[-8000:] if len(content) > 8000 else content)
            else:
                st.write("No compile log was generated.")
        except Exception:
            st.write("Could not read compile log.")
        st.caption("PATH")
        st.code(os.getenv("PATH", ""))
        st.caption("which latexmk / pdflatex (current process)")
        st.write({
            "latexmk": shutil.which("latexmk"),
            "pdflatex": shutil.which("pdflatex"),
            "texbin_exists": os.path.isdir("/Library/TeX/texbin"),
        })

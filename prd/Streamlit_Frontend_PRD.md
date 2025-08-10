## Streamlit Frontend PRD: Resume AI Optimizer

### 1) Overview
Build a Streamlit web frontend for the existing Resume AI optimizer so a user can:
- Upload their resume (PDF)
- Provide a job description (JD) by URL or by pasting text
- Run the optimizer and view results inline:
  - Render `resume.pdf` in a PDF viewer
  - Present `report.json` in a clean, human-friendly format
  - Provide download buttons for `resume.pdf` and `report.json`

The frontend will call existing Python APIs in the repo (no new backend service required). Outputs follow the current convention: `out/<job-name>/` with `resume.tex`, `resume.pdf` (if LaTeX is available), and `report.json` written by the optimizer.

### 2) Goals and Non-Goals
- Goals
  - Simple, reliable UI to run the optimizer end-to-end
  - Support JD by URL or text (either is sufficient)
  - Clear visualization of coverage and changes from `report.json`
  - Easy export of `resume.pdf` and `report.json`
  - Minimal setup beyond `streamlit` and current project dependencies
- Non-Goals
  - Multi-user auth, user accounts, or cloud persistence
  - Rewriting optimization logic (will reuse `src/resume_ai/optimize.py` as-is)
  - Complex orchestration/queueing or API server

### 3) Users and Primary Scenarios
- Job seekers tailoring resumes per role
- Recruiters running quick alignment checks

Primary scenarios:
- Upload resume PDF, paste JD text, click Optimize, view tailored PDF + coverage
- Upload resume PDF, paste JD URL, click Optimize, view tailored PDF + coverage

### 4) Functional Requirements
- Inputs
  - Resume upload: PDF file via file uploader
  - JD input: 
    - URL field (https://…)
    - OR a multi-line text area
  - Advanced options (collapsible):
    - `Model` (default: derived by backend; user can override)
    - `Strategy`: `conservative` | `balanced` | `bold` (default `balanced`)
    - `Pages`: `auto` | `one` | `two` (default `auto`)
    - `Availability`: optional header line
    - `Input TeX` template: optional upload or path; if not provided, default `Nathan_Pua_Resume.tex` at repo root
    - `Job name`: optional string to override output folder name; otherwise derived from JD contents/URL
  - Validation
    - Require resume PDF
    - Require at least one JD input (URL or text)
    - If both JD URL and JD text are present, prefer URL
    - Size limits:
      - Resume PDF: max 15 MB (reject above; configurable via env)
      - JD text: max 20,000 characters (warn above 18,000; hard cap at 20,000)
      - JD URL: max 2,048 characters
      - Optional TeX template upload: max 1 MB
- Processing
  - Use in-process call to `optimize_resume` from `src.resume_ai.optimize`
    - `job_input_text`, `job_input_url`, `resume_path` (use a temp path written from upload if needed)
    - `out_dir` base defaults to `out/`
    - `preferences` per existing function signature
  - For JD URL, call path remains internal (function already uses `tools.jd_ingest.fetch_job_listing`)
  - Handle LaTeX availability gracefully: if PDF is `None`, still present TeX output and instructions
- Outputs & UI
  - Show progress indicator while optimizing
  - When done, show a result panel:
    - PDF viewer for `resume.pdf` (inline embed). If not available, show a clear message; do not surface `resume.tex` in the UI
    - Report view (derived from `report.json` returned dict):
      - LLM section: provider, model, configured, last status/error
      - Coverage section:
        - counts: required present/missing; preferred present/missing
        - top changes summary from `coverage.changes`
      - Missing keywords list (chips/pills)
      - Per-block change summaries from `change_justifications` (old vs new bullets and added keywords)
      - JD source metadata: url (if any), text_length
    - Download buttons: `resume.pdf` (if available) and `report.json`
- Session & Caching
  - Use Streamlit session state to hold last inputs and paths
  - If the derived `out/<job-name>/` already exists for same inputs, allow reusing results or overwriting
- Errors & Edge Cases
  - Invalid JD URL -> show descriptive error
  - LLM/API key missing -> show banner with setup steps
  - LaTeX not installed -> show guidance; do not display or offer TeX in UI
  - Oversized JD text -> backend already trims; UI should warn if very large (>20k chars)
  - Resume not a PDF -> block with validation message

### 5) Non-Functional Requirements
- Performance: first run latency dominated by LLM calls; UI should show progress and remain responsive
- Reliability: backend function already handles fallbacks (e.g., OpenAI to fallback model). Surface errors clearly
- Privacy: all processing runs locally except LLM API calls; no cloud storage. Inform users that JD/resume content is sent to selected LLM provider
- Portability: single `streamlit run` command to launch UI

### 6) Technical Design
- Architecture
  - Pure Streamlit app that imports and calls `optimize_resume`
  - No separate API process; everything is in-process Python
- Key dependencies
  - `streamlit`
  - Existing repo dependencies (LLM clients, LaTeX, etc.)
- File I/O
  - Write uploaded resume (PDF) to a temp path under `.streamlit_cache/` or `out/tmp/` before passing to optimizer (or pass empty string if not strictly required)
  - Optimizer writes to `out/<job-name>/` per current implementation
  - Read generated `resume.pdf` and `report.json` from that folder for display
- PDF rendering
  - Embed PDF using HTML iframe with base64 or Streamlit `st.download_button` + inline iframe
  - If PDF is unavailable (LaTeX missing), show clear guidance to install `latexmk`/`pdflatex`; do not display or offer TeX in UI
- Report rendering
  - Use the dict returned by `optimize_resume` (mirrors content written to `report.json`). Expected keys:
    - `outputs`: `{ "tex": str, "pdf": Optional[str] }`
    - `preferences`: dict
    - `notes`: str
    - `job_input_present`: bool
    - `resume_present`: bool
    - `llm`: `{ provider, model, configured, calls_made?, last_status?, last_error? }`
    - `coverage`: `{ required_present[], required_missing[], preferred_present[], preferred_missing[], before_counts{}, after_counts{}, changes[] }`
    - `change_justifications`: list of `{ old_items[], new_items[], added_keywords[] }`
    - `jd_source`: `{ url: Optional[str], text_length: int }`
- Configuration
  - `.env` is auto-loaded by backend `load_dotenv()`
  - Expose model override via UI but default to backend behavior

### 7) UX Flow (Happy Path)
1) User opens the app, sees three sections: Inputs, Advanced (collapsed), and Results
2) Upload resume PDF (required)
3) Provide JD URL or paste text (one required)
4) Click Optimize
5) Show progress indicator while running
6) When complete, show:
   - PDF viewer (or TeX fallback) with download buttons
   - Coverage summary with present/missing counts and missing keyword chips
   - Per-section change summaries (old → new bullets) and added keywords
   - LLM/model info and JD source metadata

### 8) Acceptance Criteria (MVP)
- Given a valid resume PDF and a JD URL, when the user clicks Optimize, the app generates outputs under `out/<job-name>/` and displays:
  - Inline `resume.pdf` if LaTeX is available; else show a clear message
  - Coverage and change summary derived from `report.json`
  - Download buttons for `resume.pdf` (if available) and `report.json`
- Given a valid resume PDF and JD text (no URL), the above behavior still works
- If both URL and text are supplied, URL is used and the UI indicates so
- Validation prevents missing resume or missing JD input
- Errors (network, API, LaTeX) are displayed with actionable guidance

### 9) Risks & Mitigations
- LaTeX unavailable on host → Mitigate with clear instructions and TeX fallback
- Large PDFs or long JDs → Cap JD length (backend trims to ~20k chars); warn in UI
- API rate limits or model errors → Show errors, allow retry; OpenAI fallback already implemented
- File path collisions in `out/<job-name>/` → If overwrite detected, prompt user to confirm or auto-suffix job name

### 10) Implementation Plan
- Milestone 1: Skeleton UI
  - Inputs, validations, call `optimize_resume`, surface raw outputs
- Milestone 2: PDF render + downloads
  - Embed PDF or show TeX fallback; add download buttons
- Milestone 3: Report formatting
  - Coverage chips, justified changes, LLM info panel
- Milestone 4: Polish & caching
  - Session state, overwrite prompts, input persistence, basic theming

### 11) Ops & DevEx
- Start command: `streamlit run app/streamlit_app.py`
- Add `streamlit` to project dependencies
- Optional: pre-commit checks for app code style

### 12) Resolved Decisions
- Allow uploading a TeX template in the UI and route it to `preferences["input_tex"]`. If omitted, default to repo root `Nathan_Pua_Resume.tex`.
- The UI surfaces only `resume.pdf` and `report.json` (view + download). No `resume.tex` display or ZIP export.
- Enforce realistic size limits:
  - Resume PDF ≤ 15 MB
  - JD text ≤ 20,000 chars (warn ≥ 18,000)
  - JD URL ≤ 2,048 chars
  - Optional TeX template upload ≤ 1 MB

# Streamlit Frontend Task List (aligned with PRD)

## Setup
- [ ] Add `streamlit` to dependencies (requirements/poetry) and lock versions
- [ ] Ensure `.env` is respected by backend (`load_dotenv()` already in use)
- [ ] Create app entrypoint `app/streamlit_app.py`
- [ ] Add `make` or npm-style script alias to run: `streamlit run app/streamlit_app.py`

## UI Skeleton
- [ ] Page layout with sections: Inputs, Advanced (collapsed), Results
- [ ] Global notices area for environment/API key guidance
- [ ] Spinner/progress UX while optimization runs

## Inputs
- [ ] Resume uploader (PDF only)
  - [ ] Enforce content type (application/pdf) and extension `.pdf`
  - [ ] Enforce size: ≤ 15 MB (configurable via env)
- [ ] JD inputs
  - [ ] URL text input (https://…)
  - [ ] Multiline JD text area
  - [ ] Validation: require URL or text; if both present, prefer URL
  - [ ] Limits: URL length ≤ 2,048 chars; JD text length ≤ 20,000 chars (warn ≥ 18,000)
- [ ] Advanced options (expand/collapse)
  - [ ] Model select (free text or preset list; optional)
  - [ ] Strategy select: conservative | balanced | bold (default balanced)
  - [ ] Pages select: auto | one | two (default auto)
  - [ ] Availability (optional string)
  - [ ] TeX template upload (optional)
    - [ ] Accept `.tex` only; size ≤ 1 MB
    - [ ] Save to temp path and pass path via `preferences["input_tex"]`
  - [ ] Job name override (optional)

## Validation & Preprocessing
- [ ] Write uploaded files to a temp directory (e.g., `out/tmp/`)
- [ ] Sanitize/normalize file names; avoid collisions
- [ ] Derive job name if not provided (backend also derives; keep UI display consistent)
- [ ] Construct preferences dict mirroring backend signature

## Orchestration
- [ ] Call `optimize_resume(job_input_text, job_input_url, resume_path, out_dir, preferences)`
- [ ] Handle and surface exceptions (network, model, LaTeX compile)
- [ ] Record output folder path for session state reuse

## Results: PDF & Report
- [ ] Read `outputs.pdf` and `outputs.tex` paths from result dict
- [ ] Embed PDF if available
  - [ ] Use iframe with base64 or file URL from `out/<job-name>/resume.pdf`
  - [ ] Provide `Download PDF` button
- [ ] If PDF unavailable
  - [ ] Show clear message to install LaTeX tools (`latexmk`, `pdflatex`)
  - [ ] Do not surface TeX in UI
- [ ] Report view from result dict / `report.json`
  - [ ] LLM panel: provider, model, configured, last status/error
  - [ ] Coverage: required/preferred present/missing counts
  - [ ] Missing keyword chips
  - [ ] Changes table: per-block old→new bullets with added keywords
  - [ ] JD source metadata (url, text length)
  - [ ] Provide `Download report.json` button

## Session State & Caching
- [ ] Preserve last inputs and derived output folder in session state
- [ ] If `out/<job-name>/` exists, prompt to reuse or overwrite

## Error Handling
- [ ] Invalid JD URL: user-friendly error
- [ ] Missing API key(s): banner with setup steps
- [ ] File validation errors: type/size messages
- [ ] Backend errors (LLM or LaTeX): surfaced with retry option

## QA & Testing
- [ ] Manual acceptance against PRD scenarios (URL-only, text-only)
- [ ] Smoke test: small JD text triggers output; report JSON renders
- [ ] Edge: JD text >20k chars -> UI warns, backend trims, still runs
- [ ] Edge: LaTeX unavailable -> PDF missing, guidance shown
- [ ] Edge: Large PDF >15 MB -> upload blocked with message

## Docs
- [ ] Update `README.md` with Streamlit section (install, run, env)
- [ ] Add screenshots/gifs of the UI (optional)

## Nice-to-haves (post-MVP)
- [ ] Preset model dropdowns based on env defaults
- [ ] Dark/light theme polish
- [ ] Persist recent runs list in session (non-durable)

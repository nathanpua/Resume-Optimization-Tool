# AI Agent for ATS‑Friendly Resume Optimization

MVP tool to generate ATS‑friendly LaTeX/PDF from a resume and job description. See `prd/AI_Resume_Optimizer_PRD.md` and `prd/AI_Resume_Optimizer_Task_List.md`.

## Quick start (recommended)
```bash
python main.py optimize \
  --jd-text "Senior Data Analyst role requiring SQL, Python, dashboards, and GCP" \
  --job-name demo \
  --out out
```

or with a job URL:
```bash
python main.py optimize \
  --jd-url "https://example.com/job/123" \
  --job-name demo \
  --out out
```

Outputs are written to `out/<job-name>/`, including `resume.tex`, `resume.pdf`, and a `report.json`.

## Alternate CLI entrypoint
```bash
python -m resume_ai.cli optimize --jd-text "Sample JD" --out out
```

## Options
- `--jd-url`: Job description URL
- `--jd-text`: Job description raw text
- `--input-tex`: Path to input TeX template to preserve and edit (defaults to `Nathan_Pua_Resume.tex` in repo root)
- `--out`: Base output directory (default: `out`)
- `--job-name`: Folder name under the output directory; if omitted, derived from JD contents/URL
- `--model`: LLM model id (overrides env), e.g. `gemini-2.0-flash`, `gpt-4o-mini`
- `--strategy`: Optimization strategy: `conservative` | `balanced` | `bold` (default: `balanced`)
- `--pages`: Target page count policy: `auto` | `one` | `two` (default: `auto`)
- `--availability`: Availability line to show in header; omitted if not provided
- `--resume`: Optional original resume path (PDF)

## Environment
Set API keys in `.env` (auto‑loaded):
- `GOOGLE_API_KEY` for Gemini models
- `OPENAI_API_KEY` for GPT models

Optional environment variables:
- `GOOGLE_MODEL` / `OPENAI_MODEL`: default model ids
- `OPENAI_FALLBACK_MODEL`: used if a GPT call fails (default: `gpt-4o-mini`)

## Notes
- LaTeX compilation artifacts are kept next to the generated `resume.tex` inside `out/<job-name>/`.
- Keyword extraction and bullet rewriting use the selected model; see `src/resume_ai/prompts.py` and LLM clients in `src/resume_ai/lm_google.py`, `src/resume_ai/lm_openai.py`.

## Streamlit UI (Frontend)

Run a web UI to upload your resume, provide a JD (URL or text), and view/download outputs.

### Install
```bash
pip install -r requirements.txt
```

Ensure a TeX distribution is installed (for PDF generation):
- macOS: MacTeX (adds binaries under `/Library/TeX/texbin`)
- Minimal (BasicTeX) users: you may need extra packages. See Troubleshooting.

Set environment in `.env` (auto-loaded by backend):
- `GOOGLE_API_KEY` or `OPENAI_API_KEY`
- Optional: `TEXBIN=/Library/TeX/texbin` (if PATH issues)

### Run
```bash
streamlit run app/streamlit_app.py
```

### UI features
- Upload resume (PDF ≤ 15 MB)
- Provide JD by URL (≤ 2048 chars) or text (≤ 20,000 chars)
- Optional: upload TeX template (≤ 1 MB) or default to `Nathan_Pua_Resume.tex`
- Advanced options: model, strategy, pages, availability, job name, reuse outputs
- Results tabs: PDF viewer, Report (coverage and changes), Diagnostics (compile log)
- Downloads: `report.json` and `resume.pdf` (if LaTeX available)

### Troubleshooting PDF generation
- If the PDF tab says "PDF not available":
  1) Check Diagnostics tab:
     - `resume_compile.log` (tail of compile output)
     - PATH and `which latexmk/pdflatex`
  2) On macOS, set in `.env`:
     - `TEXBIN=/Library/TeX/texbin`
  3) Install missing LaTeX packages flagged by the log (BasicTeX example):
```bash
/Library/TeX/texbin/tlmgr update --self
/Library/TeX/texbin/tlmgr install geometry inputenc fontenc lmodern microtype enumitem hyperref titlesec parskip
```

## How it works (Architecture)

- **Entry points**
  - CLI: `main.py` and `src/resume_ai/cli.py` call `src/resume_ai/optimize.optimize_resume`.
  - Streamlit: `app/streamlit_app.py` provides a UI and also calls `optimize_resume` in‑process.
- **Core optimizer**: `src/resume_ai/optimize.py`
  - Loads env (`src/resume_ai/env.py`).
  - Picks model/provider: `src/resume_ai/lm_google.py` (Gemini) or `src/resume_ai/lm_openai.py` (GPT) based on model name.
  - Fetches JD text via `tools/jd_ingest.py`.
  - Reads base TeX (`--input-tex` or `Nathan_Pua_Resume.tex`).
  - Extracts keywords from the JD, rewrites only LaTeX `\item` bullets (`src/resume_ai/tex_edit.py`).
  - Computes keyword coverage before/after (`src/resume_ai/coverage.py`).
  - Writes `resume.tex` and compiles PDF via `tools/latex.py`.
  - Returns a report dict; CLI/UI also write `out/<job-name>/report.json`.

### End‑to‑end flow
1) Ingest JD (URL or raw text) → `tools/jd_ingest.fetch_job_listing`
2) Choose model/provider → `optimize.py` uses `GOOGLE_*` or `OPENAI_*` env and optional `--model`
3) Read & minimally edit TeX:
   - Optionally set header availability → `tex_edit.set_header_availability`
   - Extract `itemize` blocks → `tex_edit.extract_itemize_blocks`
   - Rewrite bullets per block using LLM → `lm_google`/`lm_openai`
   - Sanitize text for LaTeX → `tex_edit.sanitize_llm_bullet` + `tex_edit.escape_latex_text`
   - Replace only the original `itemize` blocks → `tex_edit.replace_itemize_block`
4) Compute coverage deltas → `coverage.compute_keyword_coverage`
5) Write outputs and compile PDF → `tools.latex.compile_pdf`

### Outputs
- Folder: `out/<job-name>/`
  - `resume.tex`: final LaTeX
  - `resume.pdf`: compiled PDF (may be `None` if LaTeX not installed)
  - `report.json`: end‑to‑end metadata including:
    - `outputs`: `{ tex, pdf }`
    - `llm`: `{ provider, model, configured, calls_made, last_status, last_error }`
    - `coverage`: present/missing terms, counts, change notes
    - `change_justifications`: per‑block old/new bullets + added keywords
    - `jd_source`: `{ url, text_length }`

## Execution flows

### CLI flow
```bash
python main.py optimize \
  --jd-url "https://…" \
  --resume ./inputs/resume.pdf \
  --out ./out \
  --strategy balanced --pages auto --availability "Available from Oct 2025"
```
Notes:
- If `--job-name` is omitted, a slug is derived from the JD content/URL.
- If `--input-tex` is omitted, the optimizer tries `Nathan_Pua_Resume.tex` in repo root; otherwise writes a placeholder TeX.

### Streamlit flow
```bash
streamlit run app/streamlit_app.py
```
- Upload resume (PDF), provide JD (URL or text), adjust options, then Optimize.
- Results view shows PDF (if available), coverage, changes, diagnostics, and downloads.

## Configuration

- `.env` (auto‑loaded):
  - `GOOGLE_API_KEY` and/or `OPENAI_API_KEY`
  - Optional: `GOOGLE_MODEL` / `OPENAI_MODEL` (defaults to `gemini-2.0-flash` if none provided)
  - Optional: `OPENAI_FALLBACK_MODEL` (used when a GPT call fails; default `gpt-4o-mini`)
  - Optional (macOS LaTeX): `TEXBIN=/Library/TeX/texbin`

## Module map

- `src/resume_ai/optimize.py`: Orchestrates the full pipeline.
- `src/resume_ai/env.py`: Minimal `.env` loader.
- `src/resume_ai/lm_google.py`: Gemini client (JSON‑aware).
- `src/resume_ai/lm_openai.py`: GPT client (with certifi fallback).
- `src/resume_ai/tex_edit.py`: TeX parsing and safe text transforms.
- `src/resume_ai/coverage.py`: Keyword coverage comparison.
- `tools/jd_ingest.py`: JD fetching, title/company slug derivation.
- `tools/latex.py`: `latexmk`/`pdflatex` wrapper with diagnostics log.

## Templates

- `templates/ats_nathan.tex`: opinionated single‑column ATS template with `\resumeheader`.
- `templates/ats_simple.tex`: minimal skeleton for experimentation.
- You can pass a custom `.tex` via `--input-tex` or upload in Streamlit.

## Development & tests

- Run unit tests:
```bash
pytest -q
```
- Notable tests:
  - `tests/test_tex_edit.py`: itemize extraction/replacement and header availability behavior.
  - `tests/test_smoke.py`: smoke test that the optimizer writes a TeX file.

## Serena MCP (project assistant)

This repo is initialized for Serena MCP. The project config is created at `.serena/project.yml` and enables code navigation and edits inside Cursor.

- To (re)activate in Cursor: use “Activate project” and choose `LmPlayground`.
- You can ask the assistant to: search code, edit files, run tests, or update docs.


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

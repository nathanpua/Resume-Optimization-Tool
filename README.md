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

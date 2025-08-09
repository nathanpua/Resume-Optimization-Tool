## Usage: AI Resume Optimizer (LaTeX + Gemini)

### Prerequisites
- Python 3.10+
- LaTeX tools on PATH: `latexmk` and `pdflatex` (e.g., TeX Live)
- Google Generative Language API key

### Setup
1) Clone/open this repo.
2) Copy environment template and set values:
```bash
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY=... (and optional GOOGLE_MODEL)
```
3) Ensure LaTeX tools are available:
```bash
latexmk -v   # should print version
pdflatex -v  # should print version
```

### Inputs
- Base TeX file (format to preserve): by default the program reads `Nathan_Pua_Resume.tex` at the repo root. You can override with `--input-tex /path/to/your.tex`.
- Job description: pass text via `--jd-text` or a URL via `--jd-url`.
- Availability (optional): pass `--availability "..."` to add/replace the availability header arg. If omitted, the template remains unchanged.

### Run (from repo root)
Use `PYTHONPATH` to point at `src` so the module runs without installation.

- Minimal run with pasted JD text:
```bash
PYTHONPATH="src:." python -m resume_ai.cli optimize \
  --jd-text "Own the ML platform on GCP; Python, Vertex AI, BigQuery; MLOps, CI/CD, Kubernetes" \
  --out ./out
```

- Run with JD URL and a custom TeX input file:
```bash
PYTHONPATH="src:." python -m resume_ai.cli optimize \
  --jd-url "https://company.com/jobs/123" \
  --input-tex ./Nathan_Pua_Resume.tex \
  --out ./out
```

- Include availability in the header (only shown when provided):
```bash
PYTHONPATH="src:." python -m resume_ai.cli optimize \
  --jd-text "Senior Data/ML Engineer; GCP; Vertex AI; MLOps; cost optimization" \
  --input-tex ./Nathan_Pua_Resume.tex \
  --availability "Available Jan 2026 - Jun 2026" \
  --out ./out
```

### Outputs
- `out/resume.tex`: Your TeX with the exact original formatting, but bullets inside `itemize` blocks rewritten and aligned to the JD.
- `out/resume.pdf`: Generated if `latexmk`/`pdflatex` are installed and on PATH.
- `out/report.json`: Coverage and changes report, including:
  - required/preferred keywords present/missing
  - before/after keyword counts
  - per-block change justifications (keywords added)

### Notes
- The program edits only bullets in `itemize` blocks to preserve formatting.
- Availability is only updated when `--availability` is provided; separators remain per your header macro.
- LLM model: defaults to `gemini-2.0-flash`. You can set `GOOGLE_MODEL` in `.env` or leave default.

### Troubleshooting
- PDF is null in `report.json`:
  - Ensure `latexmk` and `pdflatex` are installed and in your PATH.
- No keyword changes detected:
  - Verify `GOOGLE_API_KEY` is set in `.env` and network access is available.
  - Provide a richer JD (`--jd-text` or `--jd-url`).
- Different template filename:
  - Use `--input-tex /absolute/path/to/your_resume.tex`.

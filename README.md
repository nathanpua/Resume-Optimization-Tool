# AI Agent for ATS‑Friendly Resume Optimization

MVP CLI to generate ATS‑friendly LaTeX from a resume and JD. See `prd/AI_Resume_Optimizer_PRD.md` and `prd/AI_Resume_Optimizer_Task_List.md`.

## Quick start
```bash
python -m resume_ai.cli optimize --jd-text "Sample JD" --resume ./inputs/resume_sample.pdf --out ./out
```

Outputs a minimal `resume.tex` in `out/` (PDF compilation and full pipeline to be added).

## Execution Task List: AI Agent for ATS‑Friendly Resume Optimization

### Conventions
- Timeboxes are indicative; parallelize where possible.
- Deliverables should be demoable with CLI and sample inputs.

---

### Phase 0 — Project Setup (Day 0–1)
1. Repo scaffolding: `src/`, `templates/`, `tools/`, `tests/`, `inputs/`, `out/`, `prd/`.
2. Python toolchain: `pyproject.toml` or `requirements.txt`; set versions.
3. Choose LLM & embeddings providers; configure env (`.env.example`).
4. Add logging baseline and structured event schema.
5. Create sample artifacts: 3 JDs + 3 resumes for tests.

### Phase 1 — Parsing & Normalization (Day 2–4)
6. Implement JD fetcher: URL -> text; raw text pass‑through.
7. Implement resume parsers: PDF (pypdf, pdfminer.six), DOCX (python‑docx/mammoth).
8. Define core data model; normalize dates, roles, locations.
9. Unit tests: JD parser, resume parser, normalization edge cases.

### Phase 2 — Keyword Intelligence (Day 5–7)
10. Implement keyword extractor with weighting (frequency, TF‑IDF, sections).
11. Build taxonomy map (O*NET/ESCO + curated synonyms); add embeddings (FAISS/Chroma).
12. Compute required vs preferred terms; semantic expansion.
13. Tests: precision/recall on curated JD/resume pairs.

### Phase 3 — Gap Analysis & Planning (Day 8–9)
14. Compare JD terms to resume; compute coverage by section and overall.
15. Detect impact signals (metrics, scale) and seniority cues.
16. Plan edits: sections to modify, keywords to target, bullets to rewrite.
17. Output plan JSON for traceability.

### Phase 4 — Rewriting Engine (Day 10–12)
18. Prompt library: bullets (CAR), summary, skills, tense rules.
19. Implement function‑calling tools for bullet rewriting with guardrails.
20. Implement missing‑metrics clarification with safe placeholders.
21. Tests: hallucination guards, tense consistency, keyword integration.

### Phase 5 — LaTeX Generation (Day 13–15)
22. Create `ats_simple` LaTeX template; add Jinja2 rendering.
23. Implement one‑ vs two‑page auto‑fit (spacing, pruning rules).
24. Escape LaTeX specials and normalize ASCII punctuation.
25. Tests: compile stability across diverse inputs.

### Phase 6 — Compilation & QA (Day 16–18)
26. Integrate `tectonic` (fallback `pdflatex`/`latexmk`).
27. Implement ATS‑sim checks: keyword coverage, section detection, parseability.
28. Integrate grammar/style (LanguageTool server API).
29. Iteration loop: fix issues until thresholds met; cap iterations.
30. Tests: ATS thresholds, grammar zero critical, retry behavior.

### Phase 7 — Explainability & Reporting (Day 19–20)
31. Generate diff of bullets/summary; highlight added/removed keywords.
32. Produce coverage report JSON + human‑readable Markdown.
33. Bundle outputs: `.pdf`, `.tex`, `report.json`, `changes.md` into `out/`.

### Phase 8 — Variants & Strategy (Day 21–22)
34. Implement strategies: conservative, balanced, bold (knobs on keyword density, tone).
35. Generate up to 3 variants per JD; name systematically.
36. Tests: ensure variants differ meaningfully and meet ATS thresholds.

### Phase 9 — CLI & API (Day 23–24)
37. CLI command `resume-ai optimize` with flags (jd-url/text, resume, out, strategy, pages).
38. Python API `optimize_resume` and `optimize_batch`.
39. Usage docs and examples in `README.md`.

### Phase 10 — Performance & Reliability (Day 25–26)
40. Profiling; parallelize I/O and tool calls; cache embeddings.
41. Add timeouts, circuit breakers, and structured retries.
42. Fuzz tests with malformed PDFs/DOCX/JDs.

### Phase 11 — Privacy & Security (Day 27)
43. Local‑first default; optional cloud provider gating.
44. PII redaction in logs; secure temp file handling; data deletion command.

### Phase 12 — Release Prep (Day 28–30)
45. Golden dataset validation; record baseline metrics.
46. Package distribution (pipx/poetry); version bump v1.0.0.
47. Quickstart guide and demo video script.
48. Draft changelog and PRD link in repo docs.

---

### Deliverables Checklist
- Parsers (PDF/DOCX), JD ingestion, normalization
- Keyword extractor + taxonomy + embeddings
- Gap analysis + planning output
- Rewriting tools + guardrails
- LaTeX template + renderer
- PDF compilation + ATS‑sim + grammar checks
- Explainability reports + variants
- CLI & API + docs
- Tests, benchmarks, telemetry, and privacy controls

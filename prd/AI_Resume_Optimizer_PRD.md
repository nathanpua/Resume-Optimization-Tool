## PRD: AI Agent for ATS‑Friendly Resume Optimization (LaTeX Output)

### Document metadata
- **Owner**: Product & Engineering
- **Last updated**: 2025‑08‑08
- **Status**: Draft for implementation
- **Version**: v1.0

## 1) Overview
An AI agent that tailors a user’s resume to a specific job listing, optimizing for recruiter appeal and ATS (Applicant Tracking System) parsing. The agent ingests a job description (JD) and an existing resume, performs gap analysis and keyword alignment, rewrites content, and generates an ATS‑friendly LaTeX resume PDF. The system provides transparent diffs, coverage metrics, and multiple output variants.

## 2) Goals and Non‑Goals
### Goals
- **Generate tailored, ATS‑friendly resumes** from a base resume and a target JD.
- **Maximize keyword coverage** while preserving truthfulness and readability.
- **Automate LaTeX generation and PDF compilation**, producing clean, single‑column layouts.
- **Provide explainability**: show keyword coverage, changes/diffs, and rationales.
- **Support rapid iteration** with configurable strategies (conservative, balanced, bold).

### Non‑Goals
- Building a general career coaching platform.
- Guaranteeing interview outcomes.
- Hosting a public resume database or job application tracker (out of scope for v1).

## 3) Success Metrics
- **Keyword coverage**: ≥ 80% required JD terms; ≥ 65% overall.
- **Grammar/style**: 0 critical issues (LanguageTool or equivalent).
- **ATS parseability**: 100% of test PDFs have detectable section headers and extractable text.
- **User satisfaction**: ≥ 4.4/5 post‑generation rating.
- **Turnaround time**: ≤ 40 seconds end‑to‑end on typical inputs.
- **Adoption**: ≥ 60% users generate ≥ 2 variants per JD.

## 4) Target Users & Personas
- **Early‑Career Candidate**: Needs one‑page resume aligned to first job.
- **Experienced IC**: Two‑page resume, wants tailored bullets per JD quickly.
- **Career Switcher**: Emphasis on transferable skills, projects, certifications.
- **Recruiter/Reviewer** (secondary): Wants clearly organized, skimmable resumes.

## 5) Key Use Cases & User Stories
- As a candidate, I paste a JD URL and upload my resume (PDF/DOCX) to get a tailored PDF.
- As a candidate, I want a coverage report showing which JD keywords are addressed.
- As a candidate, I want alternative variants (e.g., leadership‑emphasis vs keyword‑emphasis).
- As a candidate, I want clear diffs of bullet changes to maintain accuracy.
- As a candidate, I want a one‑ or two‑page output depending on my seniority.

## 6) Functional Requirements
1. **Input ingestion**
   - Accept JD as URL or raw text.
   - Accept resume as PDF or DOCX; parse to structured JSON.
2. **Normalization**
   - Standardize fields: title, company, responsibilities, qualifications, skills/stack.
   - Normalize dates and seniority signals.
3. **Keyword extraction & taxonomy mapping**
   - Extract 30–50 terms; detect required vs preferred.
   - Map terms to synonyms (O*NET/ESCO, curated list) and embeddings for semantic match.
4. **Gap analysis**
   - Compare JD terms vs resume; identify coverage gaps by section.
   - Detect impact signals (metrics, scope, scale) and seniority indicators.
5. **Content rewriting**
   - Rewrite summary, skills, and experience bullets using CAR (Context‑Action‑Result).
   - Insert JD keywords naturally; avoid stuffing and preserve truthfulness.
   - Request clarifications for missing metrics (configurable fallback placeholders).
6. **Resume layout and generation**
   - Render structured resume to LaTeX using single‑column, ATS‑friendly template.
   - Auto‑fit to one page (early‑career) or two pages (senior), adjust spacing.
7. **Compilation**
   - Compile LaTeX to PDF via `tectonic` (preferred) or `pdflatex`.
8. **Quality checks**
   - ATS‑sim parseability checks, keyword coverage scoring, grammar/style checks.
   - Consistency checks (tense, dates, capitalization, punctuation).
9. **Explainability & reporting**
   - Provide a diff of bullets and summary.
   - Provide keyword coverage table and missing terms.
10. **Variants**
   - Generate up to 3 variants per JD: conservative, balanced, bold.
11. **Export**
   - Output `.tex`, `.pdf`, and a JSON report in an `out` directory.

## 7) Non‑Functional Requirements
- **Performance**: Sub‑40s for typical resumes and JDs; streaming progress updates.
- **Reliability**: Deterministic LaTeX builds; retries on transient compile errors.
- **Security/Privacy**: Local‑first processing; opt‑in cloud; redact PII for telemetry.
- **Maintainability**: Modular tools; versioned templates; observable logs.
- **Accessibility**: PDF text is selectable and screen‑reader friendly.

## 8) Constraints & ATS Best Practices
- Single column; standard section headers; no tables, columns, images, icons, or color‑dependent meaning.
- Avoid headers/footers with critical info; keep contact details in body text.
- Fonts: `helvet`/`lmodern`; no exotic ligatures; T1 encoding; UTF‑8 input.
- Use ASCII punctuation when possible; escape LaTeX special chars.
- Consistent dates (e.g., Jan 2023 -- Mar 2025); include location or "Remote".
- File naming: `Firstname_Lastname_TargetRole_Resume.pdf`.

## 9) User Flow (Happy Path)
1. User provides JD URL/text and uploads resume.
2. System fetches JD and parses resume to JSON.
3. Extracts & ranks keywords; maps synonyms; computes coverage.
4. Plans edits; optionally prompts for missing metrics.
5. Rewrites summary, skills, bullets; reorders sections if needed.
6. Renders LaTeX; compiles to PDF; runs checks.
7. If thresholds unmet, iterates with targeted fixes.
8. Outputs PDF, `.tex`, diff, and coverage report; optionally generate variants.

## 10) System Architecture
### Components
- **LLM Orchestrator (Agent)**: Plans, calls tools, maintains state.
- **Tools/Functions**: Fetch JD, parse resume, keyword extraction, rewrite bullets, LaTeX render, PDF compile, ATS‑sim check, grammar/style, version diff.
- **Storage**: Working directory with `inputs/`, `out/`, `logs/`, and template assets.

### Tool/Function Interfaces (schemas)
```json
{
  "name": "fetch_job_listing",
  "description": "Fetches job listing text from a URL or parses raw text.",
  "parameters": {
    "type": "object",
    "properties": {
      "url": {"type": "string"},
      "raw_text": {"type": "string"}
    }
  }
}
```
```json
{
  "name": "parse_resume_document",
  "description": "Parses PDF/DOCX resume to structured JSON.",
  "parameters": {
    "type": "object",
    "properties": {
      "file_path": {"type": "string"},
      "format_hint": {"type": "string", "enum": ["pdf", "docx"]}
    },
    "required": ["file_path"]
  }
}
```
```json
{
  "name": "extract_keywords",
  "description": "Extracts and ranks keywords from job text.",
  "parameters": {
    "type": "object",
    "properties": {
      "text": {"type": "string"},
      "max_terms": {"type": "integer", "default": 50}
    },
    "required": ["text"]
  }
}
```
```json
{
  "name": "rewrite_bullets",
  "description": "Rewrites experience bullets with JD-aligned, quantified statements.",
  "parameters": {
    "type": "object",
    "properties": {
      "experience_item": {"type": "object"},
      "target_keywords": {"type": "array", "items": {"type": "string"}},
      "ask_for_missing_metrics": {"type": "boolean", "default": true}
    },
    "required": ["experience_item", "target_keywords"]
  }
}
```
```json
{
  "name": "generate_latex",
  "description": "Renders structured resume JSON with a LaTeX template.",
  "parameters": {
    "type": "object",
    "properties": {
      "resume_json": {"type": "object"},
      "template_name": {"type": "string", "default": "ats_simple"},
      "output_tex_path": {"type": "string"}
    },
    "required": ["resume_json", "output_tex_path"]
  }
}
```
```json
{
  "name": "compile_pdf",
  "description": "Compiles LaTeX to PDF with tectonic or latexmk.",
  "parameters": {
    "type": "object",
    "properties": {
      "tex_path": {"type": "string"},
      "engine": {"type": "string", "enum": ["tectonic", "pdflatex"], "default": "tectonic"}
    },
    "required": ["tex_path"]
  }
}
```
```json
{
  "name": "ats_sim_check",
  "description": "Evaluates ATS readiness and keyword coverage.",
  "parameters": {
    "type": "object",
    "properties": {
      "pdf_path": {"type": "string"},
      "job_keywords": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["pdf_path", "job_keywords"]
  }
}
```

### Data Model (core JSON)
```json
{
  "contact": {
    "name": "string",
    "title": "string",
    "email": "string",
    "phone": "string",
    "location": "string",
    "links": [{"label": "GitHub", "url": "string"}]
  },
  "summary": "string",
  "skills": [
    {"group": "Languages", "items": ["Python", "Go"]},
    {"group": "Frameworks", "items": ["FastAPI", "React"]}
  ],
  "experience": [
    {
      "company": "string",
      "role": "string",
      "location": "string",
      "start": "YYYY-MM",
      "end": "YYYY-MM or Present",
      "bullets": ["string", "string"],
      "tech": ["Python", "AWS"],
      "achievements": [{"metric": "string", "value": "number", "unit": "%"}]
    }
  ],
  "projects": [
    {
      "name": "string",
      "link": "string",
      "bullets": ["string"],
      "tech": ["string"]
    }
  ],
  "education": [
    {
      "institution": "string",
      "degree": "string",
      "location": "string",
      "graduation": "YYYY",
      "highlights": ["string"]
    }
  ],
  "certifications": ["AWS SAA", "PMP"]
}
```

## 11) Detailed Behavior
### Keyword extraction & ranking
- Preserve exact JD phrasing and add common synonyms.
- Compute weights using frequency, section importance, and semantic similarity.

### Bullet rewriting rules
- CAR structure; strong action verbs; quantify outcomes.
- Present tense for current role; past tense otherwise.
- Avoid first‑person pronouns; no confidential details.

### Page length policy
- 0–7 years experience: 1 page; otherwise 2 pages.
- Auto‑compaction with `enumitem`, margin tuning, and bullet pruning if needed.

### Error handling
- Missing text in PDF → fallback to OCR prompt or ask user.
- LaTeX compile errors → escape special characters; retry with sanitized text.
- JD fetch failure → ask for pasted text.

## 12) LaTeX Template Spec (ats_simple)
- Single column; `article` class; 10pt.
- `geometry[margin=0.7in]`, `T1`, `utf8`, `helvet` (sans‑serif default), `hyperref`, `enumitem`.
- Section macro `\sectionhead{}` for consistent spacing.
- No tables/columns/images; simple `itemize` lists.

Example skeleton (for reference):
```latex
\documentclass[10pt]{article}
\usepackage[margin=0.7in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[scaled]{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage{hyperref}
\hypersetup{hidelinks}
\usepackage{enumitem}
\setlist[itemize]{left=0pt..1.2em, itemsep=2pt, topsep=2pt, parsep=0pt}

\newcommand{\sectionhead}[1]{\vspace{6pt}\textbf{\large #1}\vspace{2pt}\par}

\begin{document}
% Contact, Summary, Skills, Experience, Projects, Education, Certifications
\end{document}
```

## 13) API & CLI
### Programmatic API
- `optimize_resume(job_input: str|url, resume_path: str, out_dir: str, preferences: dict) -> {tex, pdf, report}`
- `optimize_batch(jobs: List[Job], resume_path: str, strategy: str) -> List[{tex, pdf, report}]`

### CLI
```bash
resume-ai optimize \
  --jd-url "https://company.com/jobs/123" \
  --resume ./inputs/resume.pdf \
  --out ./out \
  --strategy balanced \
  --pages auto
```

## 14) Quality, Testing, and Evaluation
- **Unit tests**: parsers, keyword extraction, LaTeX rendering, ATS checks.
- **Golden files**: Sample JDs and resumes with expected outputs.
- **PDF validation**: text extraction matches expected structure.
- **ATS‑sim**: coverage ≥ thresholds; fail build otherwise (configurable).
- **Style/grammar**: no critical issues; report minor suggestions.
- **Performance**: benchmark suite; budget per stage.

## 15) Telemetry & Logging
- Event logs for tool calls (timing, success/failure).
- Anonymized coverage stats (if opted‑in).
- Error traces for LaTeX and parsers.

## 16) Privacy, Security, and Compliance
- Local‑first; optional encrypted cloud processing.
- PII redaction for logs; user‑controlled data deletion.
- No third‑party data sharing without consent.

## 17) Risks & Mitigations
- **Keyword stuffing** → enforce readability constraints; cap density.
- **Hallucinated metrics** → require user confirmation for inferred numbers.
- **LaTeX build failures** → sanitize text; retry; fallback engine.
- **ATS variance across systems** → use conservative template; cross‑validate.
- **Parsing failures for PDFs** → support DOCX; better OCR path (later).

## 18) Rollout Plan & Timeline (indicative)
- Week 1–2: Parsers, keyword extraction, base LaTeX template.
- Week 3: Rewriting flows, ATS‑sim checks, grammar.
- Week 4: CLI/API; reports; variants.
- Week 5: Testing, benchmarks, docs, sample datasets.

## 19) Acceptance Criteria
- Given a JD URL and a PDF resume, the system outputs:
  - A tailored `.pdf` and `.tex` that compile without errors.
  - Coverage report showing ≥ 80% required terms and ≥ 65% overall.
  - Zero critical grammar/style issues.
  - A diff summarizing bullet and summary changes.
- Build completes within 40 seconds on reference hardware.

## 20) Open Questions
- Should we support multi‑language resumes in v1 or v2?
- Preferred default strategy for variants (balanced vs conservative)?
- Do we include cover letter generation in v1?

## 21) Glossary
- **ATS**: Applicant Tracking System; parses resumes to structured text.
- **CAR**: Context‑Action‑Result, a bullet structure pattern.
- **JD**: Job Description/Listing.

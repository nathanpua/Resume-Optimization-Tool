## PRD: Single-Call Multi-Section Bullet Rewrite

### Objective
- **Reduce repetition** and **improve global coherence** by rewriting all sections’ bullets in a single LLM call.
- **Preserve structure**: keep the number of bullets per section and original section order.
- **Remain robust**: fall back to current per-block flow on errors or oversize payloads.

### Current Behavior (Baseline)
- 1 call extracts keywords from JD.
- N calls (one per `itemize` block) rewrite bullets independently, sharing only the same keyword list and optional resume excerpt.
- Post-processing: sanitize text for LaTeX, enforce bullet count parity, replace blocks, compile PDF, compute coverage.

### Proposed Behavior
- Keep keyword extraction as-is (1 call).
- Rewrite all sections in a single call using a new multi-section prompt that:
  - Receives every section’s current bullets with a stable `id`.
  - Receives the shared keyword list and an optional resume Markdown excerpt.
  - Instructs the LLM to distribute keywords across sections and avoid repetition.
- Response is strict JSON with rewritten bullets per section by `id`.
- Post-processing remains: sanitize, enforce counts, replace blocks, compile, coverage.

### Scope
- **In**: Prompt, client, and orchestrator changes; optional UI toggle; docs/tests.
- **Out**: Provider changes (we’re OpenRouter-only already) and JD extraction logic.

### Data Contract
- Input (to LLM):
  - `keywords`: up to 40 strings (already clipped in `optimize.py`).
  - `resume_context_section`: optional string, truncated to ≤ 5,000 chars.
  - `sections`: array of `{ id: int, bullets: string[] }`.
- Output (from LLM):
```json
{
  "sections": [
    { "id": 0, "bullets": ["...", "..."] },
    { "id": 1, "bullets": ["...", "..."] }
  ]
}
```
- Post-parse guarantees:
  - For each `id`, enforce bullet count to match original (pad with originals or truncate).
  - Apply `sanitize_llm_bullet` and `escape_latex_text` to each bullet.

### Design Changes
- `src/resume_ai/prompts.py`
  - Add `BULLET_REWRITE_MULTI_PROMPT` describing global rewrite, distribution of keywords, anti-repetition rules, count preservation, and strict JSON output with `sections[{id, bullets}]`.

- `src/resume_ai/lm_openrouter.py`
  - Add `rewrite_bullets_multi(sections, target_keywords, resume_markdown) -> Dict[int, List[str]]`:
    - Build prompt from `BULLET_REWRITE_MULTI_PROMPT`.
    - Call `_call_json` with increased `OPENROUTER_MAX_TOKENS_JSON` (document recommended 1200–2000). Fallback to `_call`.
    - Parse JSON; if fails, attempt `_extract_json_block`; else return `{}`.
    - Return `{ id: bullets }` mapping.

- `src/resume_ai/optimize.py`
  - Preferences: support `preferences["rewrite_mode"] in {"single_call", "per_block"}`. Default to `single_call` (or keep `per_block` first if we want conservative rollout; see Rollout).
  - When `single_call`:
    - Build `sections = [{"id": i, "bullets": items}]` for all blocks.
    - `rewritten_map = llm.rewrite_bullets_multi(sections, target_keywords, resume_md)`.
    - For each block `i`, get `rewritten_map.get(i, items)`; enforce bullet count; sanitize; accumulate.
  - Fallbacks:
    - If multi-call returns empty/invalid, log in `llm.last_status/last_error` and use existing per-block loop.

- `app/streamlit_app.py` (optional)
  - Advanced option: `Rewrite mode` select with values `single_call` (recommended) and `per_block`; pass to `preferences`.

### Prompt Constraints (summary)
- Distribute keywords across sections to maximize overall coverage.
- Avoid repeating identical bullets and limit keyword repetition across sections.
- Preserve bullet counts per section; use 15–24 words per bullet; ATS-friendly phrasing.
- Never fabricate metrics or technologies not present in the resume.
- Return strictly valid JSON for `sections[{id, bullets}]`.

### Risks & Mitigations
- **Token/response size**: Large resumes could exceed limits.
  - Mitigate by truncating resume excerpt (≤ 5,000 chars) and falling back to per-block.
- **Invalid JSON or missing sections**: Model may return malformed JSON or omit sections.
  - Mitigate with JSON block extraction; on failure, fallback to per-block rewrite for robustness.
- **Latency variability**: Single larger call vs multiple small calls.
  - Typically neutral or better; still fewer round trips overall.

### Acceptance Criteria
- Single call returns valid JSON mapping bullets for ≥ 90% of sections on typical inputs.
- Bullet counts per section are preserved after enforcement.
- Repetitive keywords across sections are measurably reduced vs per-block baseline (spot-checks, heuristic assertions in tests).
- On any failure, system falls back to per-block and completes without crashing.

### Test Plan
- Unit
  - Valid JSON: verify mapping and count enforcement.
  - Invalid JSON: ensure fallback to per-block is triggered.
  - Repetition heuristic: synthetic sections to check keyword distribution (non-flaky string containment checks).
- Integration
  - End-to-end with `rewrite_mode = single_call` produces `resume.tex` and `report.json`.
  - Coverage computed and change justifications populated.

### Rollout
- Phase 1 (safe): default `per_block`, add `single_call` as opt-in via preferences/UI.
- Phase 2: default `single_call` after validation; keep `per_block` as fallback path.

### Implementation Checklist
- `prompts.py`: add `BULLET_REWRITE_MULTI_PROMPT`.
- `lm_openrouter.py`: add `rewrite_bullets_multi(...)` with robust JSON parsing.
- `optimize.py`: add `rewrite_mode` preference, single-call path, and fallback.
- `app/streamlit_app.py`: optional mode toggle; plumb preference.
- Docs: README update for new mode and `OPENROUTER_MAX_TOKENS_JSON` guidance.
- Tests: new unit and integration coverage.

### Milestones
- **M1**: Prompt + client method + unit tests (multi prompt, parser, fallbacks).
- **M2**: Orchestrator path + integration smoke test (single_call mode).
- **M3**: UI toggle + README/docs + default mode decision.



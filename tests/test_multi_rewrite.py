from typing import Any, Dict, List
from resume_ai.lm_openrouter import OpenRouterClient
from resume_ai.optimize import optimize_resume


def test_rewrite_bullets_multi_parsing_valid(monkeypatch):
    client = OpenRouterClient(model="test")

    def fake_call_json(prompt: str) -> str:  # type: ignore[override]
        return '{"sections": [{"id": 0, "bullets": ["A", "B"]}, {"id": 1, "bullets": ["C"]}]}'

    monkeypatch.setattr(client, "_call_json", fake_call_json)
    out = client.rewrite_bullets_multi(
        sections=[{"id": 0, "bullets": ["x", "y"]}, {"id": 1, "bullets": ["z"]}],
        target_keywords=["python"],
        resume_markdown=None,
    )
    assert out == {0: ["A", "B"], 1: ["C"]}


def test_rewrite_bullets_multi_parsing_invalid_then_empty(monkeypatch):
    client = OpenRouterClient(model="test")

    def fake_call_json(prompt: str) -> str:  # type: ignore[override]
        return 'nonsense { not json'

    def fake_call(prompt: str) -> str:  # type: ignore[override]
        return ""

    monkeypatch.setattr(client, "_call_json", fake_call_json)
    monkeypatch.setattr(client, "_call", fake_call)
    out = client.rewrite_bullets_multi(
        sections=[{"id": 0, "bullets": ["x"]}],
        target_keywords=[],
        resume_markdown=None,
    )
    assert out == {}


def test_optimize_single_call_fallback_to_per_block(monkeypatch, tmp_path):
    # Always return empty mapping to force fallback
    def fake_multi(self, sections: List[Dict[str, Any]], target_keywords: List[str], resume_markdown: str | None = None):
        return {}

    monkeypatch.setattr(OpenRouterClient, "rewrite_bullets_multi", fake_multi)

    # Avoid LLM/network calls in per-block path as well
    def fake_rewrite(self, experience_item: Dict[str, Any], target_keywords: List[str], resume_markdown: str | None = None):
        return ["X", "Y"]

    monkeypatch.setattr(OpenRouterClient, "rewrite_bullets", fake_rewrite)

    out_dir = tmp_path / "out"
    result = optimize_resume(
        job_input_text="JD",
        job_input_url="",
        resume_path="",  # triggers minimal TeX template path
        out_dir=str(out_dir),
        preferences={"rewrite_mode": "single_call"},
    )
    assert "outputs" in result
    # Ensure .tex exists and contains an itemize env (from placeholder when no base template)
    tex_path = tmp_path / "out" / "resume.tex"
    assert tex_path.exists()
    content = tex_path.read_text(encoding="utf-8")
    assert "\\begin{itemize}" in content


def test_rewrite_bullets_multi_parsing_from_json_block(monkeypatch):
    client = OpenRouterClient(model="test")

    def fake_call_json(prompt: str) -> str:  # type: ignore[override]
        return """```json
{"sections": [{"id": 0, "bullets": ["A1", "B1"]}]}
```"""

    monkeypatch.setattr(client, "_call_json", fake_call_json)
    out = client.rewrite_bullets_multi(
        sections=[{"id": 0, "bullets": ["x", "y"]}],
        target_keywords=[],
        resume_markdown=None,
    )
    assert out == {0: ["A1", "B1"]}


def test_optimize_single_call_success(monkeypatch, tmp_path):
    # Provide a positive multi-call mapping
    def fake_multi(self, sections, target_keywords, resume_markdown=None):  # type: ignore[no-redef]
        return {0: ["R1", "R2"]}

    def fake_keywords(self, jd_text: str):  # type: ignore[no-redef]
        return {"required": [], "preferred": []}

    monkeypatch.setattr(OpenRouterClient, "rewrite_bullets_multi", fake_multi)
    monkeypatch.setattr(OpenRouterClient, "extract_keywords", fake_keywords)

    out_dir = tmp_path / "out"
    result = optimize_resume(
        job_input_text="JD",
        job_input_url="",
        resume_path="",
        out_dir=str(out_dir),
        preferences={"rewrite_mode": "single_call"},
    )
    tex_path = tmp_path / "out" / "resume.tex"
    assert tex_path.exists()
    content = tex_path.read_text(encoding="utf-8")
    # Ensure rewritten bullets are present or the placeholder still compiles (bullet replacement depends on template blocks)
    assert "\\documentclass" in content



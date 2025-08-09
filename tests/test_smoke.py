from pathlib import Path
from resume_ai.optimize import optimize_resume


def test_smoke(tmp_path: Path):
    out_dir = tmp_path / "out"
    result = optimize_resume(job_input_text="", job_input_url="", resume_path="", out_dir=str(out_dir), preferences={})
    tex_path = Path(result["outputs"]["tex"])
    assert tex_path.exists()
    content = tex_path.read_text(encoding="utf-8")
    assert "\\documentclass" in content

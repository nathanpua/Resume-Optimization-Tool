from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Optional


def compile_pdf(tex_path: str | Path) -> Optional[str]:
    """Compile a .tex file to PDF using latexmk/pdflatex if available.
    Returns path to PDF or None if compilation not available.
    """
    tex_path = Path(tex_path)
    pdf_path = tex_path.with_suffix(".pdf")

    # Try latexmk (preferred)
    try:
        result = subprocess.run(
            [
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-silent",
                str(tex_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
        if result.returncode == 0 and pdf_path.exists():
            return str(pdf_path)
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        pass

    # Fallback: pdflatex (two runs)
    for _ in range(2):
        try:
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    str(tex_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
                check=False,
                cwd=str(tex_path.parent),
            )
        except FileNotFoundError:
            break
        except subprocess.TimeoutExpired:
            break
    if pdf_path.exists():
        return str(pdf_path)

    # No compilation available
    return None

from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Optional


def compile_pdf(tex_path: str | Path) -> Optional[str]:
    """Try to compile a .tex file with 'tectonic' if available.
    Returns path to PDF or None if compilation not available.
    """
    tex_path = Path(tex_path)
    pdf_path = tex_path.with_suffix(".pdf")

    # Try tectonic
    try:
        result = subprocess.run(
            ["tectonic", str(tex_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        if result.returncode == 0 and pdf_path.exists():
            return str(pdf_path)
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        pass

    # Fallback: no compilation
    return None

from __future__ import annotations
import subprocess
from pathlib import Path
import os
import shutil
from typing import Optional


def _build_env_with_texbin() -> dict:
    """Return a subprocess env with PATH augmented for common TeX bin locations.

    This helps environments (e.g., Streamlit on macOS) where PATH may not include
    TeX binaries like latexmk/pdflatex. Honors TEXBIN env if provided.
    """
    env = os.environ.copy()
    path_value = env.get("PATH", "")
    candidates = [
        os.getenv("TEXBIN"),
        "/Library/TeX/texbin",  # macOS TeX Live / MacTeX default
        "/usr/texbin",  # legacy macOS path
        "/usr/local/texlive/2024/bin/universal-darwin",
        "/opt/homebrew/texlive/2024/bin/universal-darwin",
        "/usr/local/texlive/2023/bin/universal-darwin",
        "/opt/homebrew/texlive/2023/bin/universal-darwin",
    ]
    for cand in candidates:
        if not cand:
            continue
        try:
            if os.path.isdir(cand) and cand not in path_value:
                path_value = f"{cand}{os.pathsep}{path_value}" if path_value else cand
                # Prepend the first valid candidate; that's typically sufficient
                break
        except Exception:
            # Be conservative: ignore any FS errors here
            pass
    env["PATH"] = path_value
    return env


def _resolve_cmd(name: str, env: dict) -> str:
    """Resolve a binary path using shutil.which against the provided env PATH."""
    found = shutil.which(name, path=env.get("PATH"))
    return found or name


def compile_pdf(tex_path: str | Path) -> Optional[str]:
    """Compile a .tex file to PDF using latexmk/pdflatex if available.
    Returns path to PDF or None if compilation not available.
    """
    tex_path = Path(tex_path)
    pdf_path = tex_path.with_suffix(".pdf")
    abs_tex_path = tex_path.resolve()

    # Build env with TeX binaries discoverable
    env = _build_env_with_texbin()

    # Prepare compile log next to the .tex file
    compile_log_path = abs_tex_path.parent / "resume_compile.log"
    def _append_log(header: str, result: subprocess.CompletedProcess | None = None):
        try:
            with open(compile_log_path, "a", encoding="utf-8", errors="ignore") as log:
                log.write(f"\n==== {header} ====\n")
                if result is not None:
                    log.write(f"cmd: {' '.join(result.args) if isinstance(result.args, list) else str(result.args)}\n")
                    log.write(f"returncode: {result.returncode}\n")
                    if result.stdout:
                        try:
                            log.write(result.stdout.decode("utf-8", errors="ignore"))
                        except Exception:
                            pass
                    if result.stderr:
                        try:
                            log.write("\n--- stderr ---\n")
                            log.write(result.stderr.decode("utf-8", errors="ignore"))
                        except Exception:
                            pass
        except Exception:
            # Best effort logging only
            pass

    # Try latexmk (preferred). Ensure all artifacts are written next to the tex file.
    try:
        result = subprocess.run(
            [
                _resolve_cmd("latexmk", env),
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-silent",
                "-outdir=.",
                abs_tex_path.name,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
            cwd=str(abs_tex_path.parent),
            env=env,
        )
        _append_log("latexmk run", result)
        if result.returncode == 0 and pdf_path.exists():
            return str(pdf_path)
    except FileNotFoundError:
        _append_log("latexmk not found")
    except subprocess.TimeoutExpired:
        _append_log("latexmk timeout")

    # Fallback: pdflatex (two runs). Also constrain output directory.
    for _ in range(2):
        try:
            result = subprocess.run(
                [
                    _resolve_cmd("pdflatex", env),
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-output-directory=.",
                    abs_tex_path.name,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
                check=False,
                cwd=str(abs_tex_path.parent),
                env=env,
            )
            _append_log("pdflatex run", result)
        except FileNotFoundError:
            _append_log("pdflatex not found")
            break
        except subprocess.TimeoutExpired:
            _append_log("pdflatex timeout")
            break
    if pdf_path.exists():
        return str(pdf_path)

    # No compilation available
    _append_log("pdf not generated")
    return None

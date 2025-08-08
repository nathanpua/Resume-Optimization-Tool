from pathlib import Path
from typing import Any, Dict
from tools.latex import compile_pdf
from src.resume_ai.env import load_dotenv
from src.resume_ai.lm_google import GoogleLMClient
from src.resume_ai.tex_edit import extract_itemize_blocks, replace_itemize_block, set_header_availability
from tools.jd_ingest import fetch_job_listing


def _write_nathan_style(tex_path: Path, context: Dict[str, Any]) -> None:
    """Render a minimal Nathan-style LaTeX with placeholders.
    This mirrors formatting choices in Nathan_Pua_Resume.tex.
    """
    template = r"""
\documentclass[10pt]{article}
\usepackage[letterpaper, left=0.5in, right=0.5in, top=0.5in, bottom=0.5in]{geometry}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{titlesec}
\usepackage{parskip}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\setlength{\baselineskip}{11pt}
\hypersetup{colorlinks=true, linkcolor=black, filecolor=black, urlcolor=black}
\titleformat{\section}{\large\bfseries\uppercase}{}{0em}{}[\titlerule]
\titleformat{\subsection}{\bfseries}{}{0em}{}
\titlespacing*{\section}{0pt}{8pt}{4pt}
\titlespacing*{\subsection}{0pt}{4pt}{2pt}
\setlist{nosep, leftmargin=1em, itemsep=0pt, parsep=0pt, topsep=0pt}

\newcommand{\resumeheader}[5]{\begin{center}{\Large\bfseries #1}\\[0.1em]#2 \textbar\ #3 \textbar\ \href{mailto:#4}{#4} \textbar\ \href{#5}{#5}\end{center}\vspace{0.3em}}
\newcommand{\resumeentry}[4]{\subsection{#1 \hfill #3}\textit{#2}\\[-0.1em]#4\vspace{0.2em}}
\newcommand{\educationentry}[4]{\subsection{#1 \hfill #3}\textit{#2}\\[-0.1em]#4\vspace{0.2em}}
\newcommand{\projectentry}[2]{\subsection{#1}#2\vspace{0.2em}}

\begin{document}
\resumeheader{%s}{%s}{%s}{%s}{%s}

\section{Education}
%s

\section{Experience}
%s

\section{Projects}
%s

\section{Technical Skills}
%s

\section{Certifications \& Achievements}
%s
\end{document}
""".strip()

    def safe(text: str) -> str:
        return (text or "").replace("&", "\\&").replace("%", "\\%")

    content = template % (
        safe(context.get("name", "Firstname Lastname")),
        safe(context.get("location", "City, Country")),
        safe(context.get("availability", "Available Immediately")),
        safe(context.get("email", "email@example.com")),
        safe(context.get("link", "https://example.com")),
        safe(context.get("education_block", "")),
        safe(context.get("experience_block", "")),
        safe(context.get("projects_block", "")),
        safe(context.get("skills_block", "")),
        safe(context.get("certs_block", "")),
    )
    tex_path.write_text(content, encoding="utf-8")


def optimize_resume(job_input: str, resume_path: str, out_dir: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Nathan-style LaTeX and compile to PDF if possible (latexmk/pdflatex)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    tex_path = out / "resume.tex"

    # Minimal context placeholder; will be replaced by parsed and optimized content
    context = {
        "name": "Firstname Lastname",
        "location": "Singapore",
        "availability": "Available Jan 2026 - Jun 2026",
        "email": "email@example.com",
        "link": "https://example.com",
        "education_block": "Bachelor of Science\\\\ University Name \\ Jul 2020 - May 2024",
        "experience_block": "\\resumeentry{Software Engineer}{Company}{Jan 2023 - Present}{\\begin{itemize}\\item Built X to achieve Y\\end{itemize}}",
        "projects_block": "\\projectentry{Project Name}{\\begin{itemize}\\item Did X with Y\\end{itemize}}",
        "skills_block": "\\textbf{Programming:} Python, Go, SQL\\\\ \\textbf{Tools:} AWS, Docker",
        "certs_block": "\\textbf{Certifications:} AWS SAA",
    }

    _write_nathan_style(tex_path, context)
    pdf_path = compile_pdf(tex_path)

    return {
        "outputs": {
            "tex": str(tex_path),
            "pdf": pdf_path,
        },
        "preferences": preferences,
        "notes": "Generated Nathan-style LaTeX; PDF compiled if latexmk/pdflatex available.",
        "job_input_present": bool(job_input),
        "resume_present": bool(resume_path),
    }

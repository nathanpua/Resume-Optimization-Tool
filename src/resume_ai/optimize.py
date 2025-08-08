from pathlib import Path
from typing import Any, Dict


def _write_minimal_latex(tex_path: Path, context: Dict[str, Any]) -> None:
    template = r"""
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

{\LARGE %s} \hfill %s\\
%s \;|\; %s \;|\; %s \\
\vspace{6pt}

\sectionhead{Summary}
%s

\sectionhead{Skills}
%s

\sectionhead{Experience}
\textbf{%s} \hfill %s --- %s\\
%s -- %s\\
\begin{itemize}
  \item %s
  \item %s
\end{itemize}

\end{document}
""".strip()

    # Very basic safe replacements; real implementation will sanitize thoroughly
    def safe(text: str) -> str:
        return (text or "").replace("&", "\\&").replace("%", "\\%")

    content = template % (
        safe(context.get("name", "Firstname Lastname")),
        safe(context.get("title", "Software Engineer")),
        safe(context.get("email", "email@example.com")),
        safe(context.get("phone", "+1 (000) 000-0000")),
        safe(context.get("location", "City, ST")),
        safe(context.get("summary", "Results-oriented engineer with experience in...")),
        safe(context.get("skills_text", "Languages: Python, Go; Cloud: AWS")),
        safe(context.get("role", "Senior Software Engineer")),
        safe(context.get("company", "Company")),
        safe(context.get("exp_location", "Remote")),
        safe(context.get("start", "Jan 2023")),
        safe(context.get("end", "Present")),
        safe(context.get("bullet1", "Led X to achieve Y% improvement.")),
        safe(context.get("bullet2", "Built Z using A, B, C.")),
    )

    tex_path.write_text(content, encoding="utf-8")


def optimize_resume(job_input: str, resume_path: str, out_dir: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
    """MVP placeholder: generate minimal LaTeX and return paths.

    Later this will:
    - ingest JD/resume, do analysis, rewrite, render multiple variants, compile.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # For MVP, create a single minimal .tex file
    tex_path = out / "resume.tex"

    context = {
        "name": "Firstname Lastname",
        "title": "Target Role",
        "email": "email@example.com",
        "phone": "+1 000 000 0000",
        "location": "Remote",
        "summary": "Tailored summary will appear here.",
        "skills_text": "Languages: Python, Go; Cloud: AWS, GCP",
        "role": "Software Engineer",
        "company": "Acme Corp",
        "exp_location": "Remote",
        "start": "Jan 2023",
        "end": "Present",
        "bullet1": "Implemented feature X improving Y by 30%.",
        "bullet2": "Built service with FastAPI on AWS.",
    }

    _write_minimal_latex(tex_path, context)

    return {
        "outputs": {
            "tex": str(tex_path),
            "pdf": None,  # compilation will be integrated later
        },
        "preferences": preferences,
        "notes": "MVP generated minimal LaTeX only.",
        "job_input_present": bool(job_input),
        "resume_present": bool(resume_path),
    }

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.resume_ai.optimize import optimize_resume
from tools.jd_ingest import fetch_job_listing, derive_job_name


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="resume-ai-main",
        description="Run the Resume AI optimizer with a job URL or raw text and generate LaTeX/PDF outputs",
    )

    # Job inputs
    parser.add_argument("optimize", nargs="?", default="optimize", help="optimize command (default: optimize)")
    parser.add_argument("--jd-url", dest="jd_url", default=None, help="Job description URL")
    parser.add_argument("--jd-text", dest="jd_text", default=None, help="Job description raw text")

    # Template and output
    parser.add_argument(
        "--input-tex",
        dest="input_tex",
        default=None,
        help="Path to input TeX template to preserve and edit (defaults to Nathan_Pua_Resume.tex at repo root)",
    )
    parser.add_argument("--out", dest="out_dir", default="out", help="Base output directory (default: out)")
    parser.add_argument("--job-name", dest="job_name", default=None, help="Folder name under output directory")

    # Model and optimization preferences
    parser.add_argument(
        "--model",
        dest="model",
        default=None,
        help="LLM model id (overrides GOOGLE_MODEL/OPENAI_MODEL), e.g. 'gemini-2.0-flash' or 'gpt-4o-mini'",
    )
    parser.add_argument(
        "--strategy",
        dest="strategy",
        default="balanced",
        choices=["conservative", "balanced", "bold"],
        help="Optimization strategy",
    )
    parser.add_argument(
        "--pages",
        dest="pages",
        default="auto",
        choices=["auto", "one", "two"],
        help="Target page count policy",
    )
    parser.add_argument(
        "--availability",
        dest="availability",
        default=None,
        help="Availability line to show in header; omitted if not provided",
    )

    # Optional resume file path (not strictly required by optimizer)
    parser.add_argument("--resume", dest="resume_path", required=False, default="", help="Path to resume (PDF only)")

    args = parser.parse_args()

    if args.optimize != "optimize":
        parser.print_help()
        return 0

    # Compute output directory -> out/<job-name>
    base_output_directory = Path(args.out_dir)
    job_folder_name = args.job_name
    if not job_folder_name:
        # Fetch JD to extract a meaningful folder name (title/company)
        job_listing = fetch_job_listing(url=args.jd_url, raw_text=args.jd_text)
        job_folder_name = derive_job_name(job_listing.text or "", url=job_listing.url)

    out_dir = base_output_directory / (job_folder_name or "job")
    out_dir.mkdir(parents=True, exist_ok=True)

    result = optimize_resume(
        job_input_text=args.jd_text or "",
        job_input_url=args.jd_url or "",
        resume_path=args.resume_path or "",
        out_dir=str(out_dir),
        preferences={
            "strategy": args.strategy,
            "pages": args.pages,
            "availability": args.availability,
            "input_tex": args.input_tex,
            "job_name": job_folder_name,
            "model": args.model,
        },
    )

    # Write JSON report into the output folder
    report_path = out_dir / "report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote outputs to {out_dir}")
    if isinstance(result, dict):
        outputs = result.get("outputs", {})
        if outputs:
            print(f"TeX: {outputs.get('tex')}")
            print(f"PDF: {outputs.get('pdf')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



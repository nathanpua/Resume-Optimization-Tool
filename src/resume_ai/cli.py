import argparse
import json
from pathlib import Path
from .optimize import optimize_resume
from tools.jd_ingest import fetch_job_listing, derive_job_name


def main():
    parser = argparse.ArgumentParser(
        prog="resume-ai",
        description="AI Agent: Tailor a resume to a job description and generate LaTeX/PDF",
    )
    parser.add_argument("optimize", nargs="?", default=None, help="optimize command")
    parser.add_argument("--jd-url", dest="jd_url", default=None, help="Job description URL")
    parser.add_argument("--input-tex", dest="input_tex", default=None, help="Path to input TeX template to preserve and edit")
    parser.add_argument("--jd-text", dest="jd_text", default=None, help="Job description raw text")
    parser.add_argument("--job-name", dest="job_name", default=None, help="Folder name for outputs (defaults to sanitized job text)")
    parser.add_argument("--model", dest="model", default='moonshotai/kimi-k2:free', help="OpenRouter model id (e.g., 'z-ai/glm-4.5v', 'openrouter/auto')")
    parser.add_argument("--resume", dest="resume_path", required=False, help="Path to resume (PDF only)")
    parser.add_argument("--out", dest="out_dir", default="out", help="Output directory")
    parser.add_argument("--strategy", dest="strategy", default="balanced", choices=["conservative", "balanced", "bold"], help="Optimization strategy")
    parser.add_argument("--pages", dest="pages", default="auto", choices=["auto", "one", "two"], help="Target page count policy")
    parser.add_argument("--availability", dest="availability", default=None, help="Availability line to show in header; omitted if not provided")
    parser.add_argument(
        "--rewrite-mode",
        dest="rewrite_mode",
        default="per_block",
        choices=["per_block", "single_call"],
        help="Bullet rewrite mode: optimize each section independently (per_block) or all sections in one call (single_call)",
    )

    args = parser.parse_args()

    if args.optimize is None or args.optimize != "optimize":
        parser.print_help()
        return 0

    # Compute output directory -> out/<job-name>
    # If no explicit job_name, derive from the actual JD contents (title/company) when possible
    base_out_dir = Path(args.out_dir)
    job_name = args.job_name
    if not job_name:
        # Fetch JD to extract a meaningful name
        jd = fetch_job_listing(url=args.jd_url, raw_text=args.jd_text)
        job_name = derive_job_name(jd.text or "", url=jd.url)
    out_dir = base_out_dir / (job_name or "job")
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
            "job_name": job_name,
            "model": args.model,
            "rewrite_mode": args.rewrite_mode,
        },
    )

    report_path = out_dir / "report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote outputs to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

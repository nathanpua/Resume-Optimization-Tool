import argparse
import json
from pathlib import Path
from .optimize import optimize_resume


def main():
    parser = argparse.ArgumentParser(
        prog="resume-ai",
        description="AI Agent: Tailor a resume to a job description and generate LaTeX/PDF",
    )
    parser.add_argument("optimize", nargs="?", default=None, help="optimize command")
    parser.add_argument("--jd-url", dest="jd_url", default=None, help="Job description URL")
    parser.add_argument("--input-tex", dest="input_tex", default=None, help="Path to input TeX template to preserve and edit")
    parser.add_argument("--jd-text", dest="jd_text", default=None, help="Job description raw text")
    parser.add_argument("--resume", dest="resume_path", required=False, help="Path to resume (PDF only)")
    parser.add_argument("--out", dest="out_dir", default="out", help="Output directory")
    parser.add_argument("--strategy", dest="strategy", default="balanced", choices=["conservative", "balanced", "bold"], help="Optimization strategy")
    parser.add_argument("--pages", dest="pages", default="auto", choices=["auto", "one", "two"], help="Target page count policy")
    parser.add_argument("--availability", dest="availability", default=None, help="Availability line to show in header; omitted if not provided")

    args = parser.parse_args()

    if args.optimize is None or args.optimize != "optimize":
        parser.print_help()
        return 0

    out_dir = Path(args.out_dir)
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
        },
    )

    report_path = out_dir / "report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote outputs to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

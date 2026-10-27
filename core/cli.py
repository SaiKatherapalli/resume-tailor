"""
Command line tool.

    resume-tailor tailor  JOB.txt   [--bank FILE] [--out FILE] [--pdf] [--show]
    resume-tailor import  RESUME    [--out FILE]
    resume-tailor check   BANK.yaml

argparse is built into Python, so no extra library is needed.
"""

import argparse
import sys
from pathlib import Path

import yaml

from core.career_bank import CareerBankError, load_career_bank
from core.chains import split_keywords
from core.latex import compile_pdf, find_compiler
from core.llm import LLMNotConfiguredError
from core.resume_import import import_resume
from core.schemas import bank_to_chunks
from core.tailor import TailorResult, tailor_resume

DEFAULT_BANK = "data/career_bank.yaml"


# ------------------------------------------------------------------ commands


def cmd_tailor(args: argparse.Namespace) -> None:
    bank = load_career_bank(args.bank)
    job_description = read_text(args.job)

    def progress(node: str, update: dict) -> None:
        if node != "validate":
            print(f"  [{node}] done")
            return
        r = update["report"]
        print(f"  [validate] {'OK' if r.ok else f'{len(r.issues)} problem(s), retrying...'}")

    print("Tailoring...")
    result = tailor_resume(job_description, bank, on_step=progress)
    if args.show:
        show_resume(result)
    show_report(result, bank)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.tex, encoding="utf-8")
    print(f"\nSaved: {out}")

    if args.pdf:
        if not find_compiler():
            raise SystemExit("No LaTeX compiler found. Install Tectonic or MiKTeX, or drop --pdf.")
        pdf = out.with_suffix(".pdf")
        pdf.write_bytes(compile_pdf(result.tex))
        print(f"Saved: {pdf}")


def cmd_import(args: argparse.Namespace) -> None:
    print("Reading resume with the LLM...")
    bank = import_resume(read_text(args.resume))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(bank.model_dump(), sort_keys=False, allow_unicode=True, width=120), "utf-8")
    print(f"Saved: {out}")
    print(f"Jobs: {[e.id for e in bank.experiences]}, bullets: {len(bank_to_chunks(bank))}")
    print("Open the file and check it before using it.")


def cmd_check(args: argparse.Namespace) -> None:
    bank = load_career_bank(args.bank)
    print(f"OK: {bank.name}")
    for e in bank.experiences:
        print(f"  {e.id}: {len(e.bullets)} bullets, shows {e.max_bullets}")
    print(f"  skills: {len(bank.all_skills())}, degrees: {len(bank.education)}")


# ------------------------------------------------------------------ output helpers


def show_resume(result: TailorResult) -> None:
    resume = result.resume
    print("\nSUMMARY:\n ", resume.summary)
    print("\nSKILLS:")
    for row in resume.skills:
        print(f"  {row.category}: {', '.join(row.items)}")
    for exp in resume.experiences:
        print(f"\n== {exp.experience_id} ==")
        for b in exp.bullets:
            print(f"  - {b.text}   {b.source_ids}")


def show_report(result: TailorResult, bank) -> None:
    report = result.report
    have, missing = split_keywords(bank, result.analysis.keywords)
    print(f"\nJob: {result.analysis.job_title}")
    print(f"Keywords you have: {have}")
    print(f"Keywords you don't: {missing}")
    print(f"Result: {'OK' if report.ok else 'NOT fully grounded'} after {result.attempts} attempt(s)")
    for issue in report.issues:
        print("  PROBLEM:", issue)
    for fix in report.fixes:
        print("  FIXED:  ", fix)
    print(f"Keyword coverage: {report.keyword_coverage:.0%}")


def read_text(path: str) -> str:
    p = Path(path)
    if not p.is_file():
        raise SystemExit(f"File not found: {p}")
    return p.read_text(encoding="utf-8")


# ------------------------------------------------------------------ entry point


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="resume-tailor", description="Tailor your resume to a job.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("tailor", help="tailor your resume to a job description")
    p.add_argument("job", help="job description text file")
    p.add_argument("--bank", default=DEFAULT_BANK, help=f"career bank YAML (default: {DEFAULT_BANK})")
    p.add_argument("--out", default="output/tailored.tex", help="where to save the .tex")
    p.add_argument("--pdf", action="store_true", help="also compile a PDF")
    p.add_argument("--show", action="store_true", help="print the tailored resume")
    p.set_defaults(func=cmd_tailor)

    p = sub.add_parser("import", help="turn a resume file into a career bank YAML")
    p.add_argument("resume", help="resume file (LaTeX or plain text)")
    p.add_argument("--out", default="data/imported_career_bank.yaml")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("check", help="check a career bank YAML is valid")
    p.add_argument("bank", nargs="?", default=DEFAULT_BANK)
    p.set_defaults(func=cmd_check)
    return parser


def main(argv: list[str] | None = None) -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console: print LLM unicode safely
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (CareerBankError, LLMNotConfiguredError) as e:
        raise SystemExit(f"Error: {e}") from None


if __name__ == "__main__":
    main()

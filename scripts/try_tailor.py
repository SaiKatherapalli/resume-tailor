"""Run the full graph: job description -> tailored, validated resume.

Run:  python scripts/try_tailor.py data/job_descriptions/backend_java.txt
"""

import sys
from pathlib import Path

from core.career_bank import load_career_bank
from core.chains import build_chains, split_keywords
from core.embeddings import LocalEmbeddings
from core.graph import build_graph
from core.latex import compile_pdf, find_compiler, render_resume
from core.retrieval import BulletIndex
from core.schemas import bank_to_chunks

jd_path = sys.argv[1] if len(sys.argv) > 1 else "data/job_descriptions/backend_java.txt"
bank = load_career_bank("data/career_bank.yaml")
index = BulletIndex.build(bank_to_chunks(bank), LocalEmbeddings())

graph = build_graph(build_chains())
job_description = Path(jd_path).read_text(encoding="utf-8")

# stream() shows each node as it finishes, so we can watch the loop happen
state = {"job_description": job_description, "bank": bank, "index": index}
for step in graph.stream(state, stream_mode="updates"):
    for node, update in step.items():
        state.update(update)
        if node == "validate":
            r = update["report"]
            result = "OK" if r.ok else f"{len(r.issues)} problem(s)"
            print(f"[validate] attempt {state['attempts']}: {result}")
            for issue in r.issues:
                print("    PROBLEM:", issue)
        else:
            print(f"[{node}] done")

analysis, report = state["analysis"], state["best"]
resume = report.resume
have, missing = split_keywords(bank, analysis.keywords)

print("\nJOB:", analysis.job_title)
print("KEYWORDS YOU HAVE:   ", have)
print("KEYWORDS YOU DON'T:  ", missing)
print("\nSUMMARY:\n", resume.summary)
print("\nSKILLS:")
for row in resume.skills:
    print(f"  {row.category}: {', '.join(row.items)}")
for exp in resume.experiences:
    print(f"\n== {exp.experience_id} ==")
    for b in exp.bullets:
        print(f"  - {b.text}   {b.source_ids}")

print("\nFINAL:", "OK" if report.ok else f"{len(report.issues)} problem(s) left")
for fix in report.fixes:
    print("  FIXED:  ", fix)
print(f"  Keyword coverage: {report.keyword_coverage:.0%}  unused: {report.unused_keywords}")

# Save as LaTeX, and as PDF if a LaTeX compiler is installed
out_dir = Path("output")
out_dir.mkdir(exist_ok=True)
tex = render_resume(bank, resume)
(out_dir / "tailored.tex").write_text(tex, encoding="utf-8")
print("\nSaved: output/tailored.tex")
if find_compiler():
    (out_dir / "tailored.pdf").write_bytes(compile_pdf(tex))
    print("Saved: output/tailored.pdf")
else:
    print("No LaTeX compiler found, so no PDF. Install Tectonic or MiKTeX.")

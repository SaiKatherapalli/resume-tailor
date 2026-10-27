"""Import a resume file into a career bank YAML.

Run:  python scripts/import_resume.py baseResume.txt data/imported_career_bank.yaml
Then open the output, check it, and copy it to data/career_bank.yaml.
"""

import sys
from pathlib import Path

import yaml

from core.resume_import import import_resume
from core.schemas import bank_to_chunks

src, dest = Path(sys.argv[1]), Path(sys.argv[2])

bank = import_resume(src.read_text(encoding="utf-8"))
text = yaml.safe_dump(bank.model_dump(), sort_keys=False, allow_unicode=True, width=120)
dest.write_text(text, encoding="utf-8")

print(f"Saved: {dest}")
print(f"Jobs: {[e.id for e in bank.experiences]}")
print(f"Bullets: {len(bank_to_chunks(bank))}, Degrees: {len(bank.education)}")
print("Now open the file and check it before using it.")

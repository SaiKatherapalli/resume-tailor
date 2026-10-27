"""Load the career bank YAML file and check it with our schemas."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from core.schemas import CareerBank


class CareerBankError(ValueError):
    """The career bank file is missing or has wrong data."""


def parse_career_bank(text: str) -> CareerBank:
    """YAML text -> checked CareerBank object."""
    try:
        data = yaml.safe_load(text)  # safe_load: reads data only, never runs code
    except yaml.YAMLError as e:
        raise CareerBankError(f"Invalid YAML: {e}") from e

    try:
        return CareerBank.model_validate(data)
    except ValidationError as e:
        raise CareerBankError(f"Career bank has wrong data:\n{e}") from e


def load_career_bank(path: str | Path) -> CareerBank:
    """YAML file -> checked CareerBank object."""
    path = Path(path)
    if not path.exists():
        raise CareerBankError(f"File not found: {path}")
    return parse_career_bank(path.read_text(encoding="utf-8"))

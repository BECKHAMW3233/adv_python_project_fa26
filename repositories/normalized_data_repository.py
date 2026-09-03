"""NormalizedDataRepository -- read/write normalized CSV or JSON files."""

from __future__ import annotations

import csv
import dataclasses
from pathlib import Path
from typing import Sequence


def write_csv(records: Sequence[object], path: Path) -> None:
    """Write a sequence of dataclass records to a CSV file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = [field.name for field in dataclasses.fields(records[0])]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(dataclasses.asdict(record))

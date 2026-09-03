"""NormalizedDataRepository -- read/write normalized CSV or JSON files."""

from __future__ import annotations

import csv
import dataclasses
import hashlib
import json
import typing
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


def _coerce(value: str, field_type: object) -> object:
    origin = typing.get_origin(field_type)
    if origin is not None:
        args = typing.get_args(field_type)
        if type(None) in args and value == "":
            return None
        non_none_args = [a for a in args if a is not type(None)]
        if non_none_args:
            field_type = non_none_args[0]
    if field_type is bool:
        return value == "True"
    if field_type is int:
        return int(value)
    if field_type is float:
        return float(value)
    return value


def read_csv(record_type: type, path: Path) -> list:
    """Read a CSV previously written by write_csv back into a list of `record_type` instances,
    coercing each field from its resolved type hint (str/int/float/bool/Optional)."""
    hints = typing.get_type_hints(record_type)
    fields = dataclasses.fields(record_type)
    records = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            kwargs = {field.name: _coerce(row[field.name], hints[field.name]) for field in fields}
            records.append(record_type(**kwargs))
    return records


def compute_file_hash(path: Path) -> str:
    """SHA-256 hex digest of a file's contents, used to detect source-file changes."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_manifest(path: Path) -> dict[str, str]:
    """Read the conversion manifest (source filename -> content hash). Returns {} if missing or unreadable."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_manifest(path: Path, hashes: dict[str, str]) -> None:
    """Write the conversion manifest, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hashes, indent=2, sort_keys=True), encoding="utf-8")

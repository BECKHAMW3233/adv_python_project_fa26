"""Tests for pipeline.needs_conversion -- first run, unchanged sources, changed source, and
missing normalized output. Module-level path constants are monkeypatched to point at
tmp_path fixtures rather than the real project's source_data/normalized_data."""

from __future__ import annotations

import pipeline
from repositories.normalized_data_repository import compute_file_hash, write_manifest


def _setup(tmp_path, monkeypatch, *, source_content=b"source-a"):
    source_file = tmp_path / "source.xlsx"
    source_file.write_bytes(source_content)
    normalized_file = tmp_path / "normalized.csv"
    normalized_file.write_text("course_id\n")
    manifest_path = tmp_path / ".manifest.json"

    monkeypatch.setattr(pipeline, "SOURCE_FILES", (source_file,))
    monkeypatch.setattr(pipeline, "NORMALIZED_FILES", (normalized_file,))
    monkeypatch.setattr(pipeline, "MANIFEST_PATH", manifest_path)
    return source_file, normalized_file, manifest_path


def test_missing_normalized_output_triggers_conversion(tmp_path, monkeypatch):
    source_file, normalized_file, manifest_path = _setup(tmp_path, monkeypatch)
    normalized_file.unlink()
    needs_conversion, reason = pipeline.needs_conversion(force_refresh=False)
    assert needs_conversion is True
    assert "missing" in reason


def test_first_run_no_manifest_triggers_conversion(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    needs_conversion, _reason = pipeline.needs_conversion(force_refresh=False)
    assert needs_conversion is True


def test_unchanged_source_does_not_trigger_conversion(tmp_path, monkeypatch):
    source_file, _normalized_file, manifest_path = _setup(tmp_path, monkeypatch)
    write_manifest(manifest_path, {source_file.name: compute_file_hash(source_file)})
    needs_conversion, _reason = pipeline.needs_conversion(force_refresh=False)
    assert needs_conversion is False


def test_changed_source_triggers_conversion_and_names_the_file(tmp_path, monkeypatch):
    source_file, _normalized_file, manifest_path = _setup(tmp_path, monkeypatch)
    write_manifest(manifest_path, {source_file.name: "deliberately-wrong-hash"})
    needs_conversion, reason = pipeline.needs_conversion(force_refresh=False)
    assert needs_conversion is True
    assert source_file.name in reason


def test_force_refresh_triggers_conversion_even_when_unchanged(tmp_path, monkeypatch):
    source_file, _normalized_file, manifest_path = _setup(tmp_path, monkeypatch)
    write_manifest(manifest_path, {source_file.name: compute_file_hash(source_file)})
    needs_conversion, reason = pipeline.needs_conversion(force_refresh=True)
    assert needs_conversion is True
    assert "refresh requested" in reason

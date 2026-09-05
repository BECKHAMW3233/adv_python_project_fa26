"""Tests for services/normalizer.py -- course ID normalization, whitespace/punctuation
handling, and numeric conversion."""

from __future__ import annotations

import pytest

from services.normalizer import (
    is_valid_course_id,
    normalize_course_id,
    normalize_credits,
    normalize_hours,
    normalize_text,
    split_course_ids,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("CIS110", "CIS110"),
        ("CIS 110", "CIS110"),
        ("COM-231", "COM231"),
        ("elc 117", "ELC117"),
    ],
)
def test_normalize_course_id_variants_collapse_to_same_form(raw, expected):
    assert normalize_course_id(raw) == expected


def test_normalize_text_collapses_irregular_whitespace_and_punctuation_spacing():
    assert normalize_text("  Multiple   \n\n  spaces\tand\ttabs  ") == "Multiple spaces and tabs"
    assert normalize_text(None) == ""
    assert normalize_text(123) == ""


@pytest.mark.parametrize(
    "raw, expected",
    [
        (3, 3),
        (0, 0),
        (None, 0),
        ("not a number", 0),
        (True, 0),
    ],
)
def test_normalize_credits_coerces_blank_and_non_numeric_to_zero(raw, expected):
    assert normalize_credits(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("6", 6),
        ("6.0", 6),
        (None, None),
        ("", None),
        ("not a number", None),
    ],
)
def test_normalize_hours_parses_or_returns_none(raw, expected):
    assert normalize_hours(raw) == expected


def test_split_course_ids_handles_commas_ampersands_and_line_breaks():
    assert split_course_ids("BUS 137, BUS 234") == ["BUS137", "BUS234"]
    assert split_course_ids("BUS153 & OMT 156") == ["BUS153", "OMT156"]
    assert split_course_ids("NET 125, NET 126,\nSEC 110") == ["NET125", "NET126", "SEC110"]
    assert split_course_ids("") == []


def test_is_valid_course_id_accepts_canonical_form_only():
    assert is_valid_course_id("CIS110") is True
    assert is_valid_course_id("CIS 110") is False
    assert is_valid_course_id("cis110") is False
    assert is_valid_course_id("") is False

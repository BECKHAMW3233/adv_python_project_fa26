"""Normalized-record schema / data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MOSCourseEquivalency:
    mos_code: str
    mos_title: str
    branch: str
    skill_level: str
    course_id: str
    course_title: str
    credits: int
    course_level: str
    source_file: str
    source_sheet: str
    status: str
    notes: str


@dataclass
class WorksheetIssue:
    source_file: str
    source_sheet: str
    message: str


@dataclass
class TrainingEquivalency:
    training_id: str
    branch: str
    training_name: str
    training_alias: str
    course_id: str
    course_credits: int | None
    source_total_hours: int | None
    verification_required: bool
    condition: str
    source_file: str
    source_table: str
    status: str
    notes: str


@dataclass
class TrainingTableIssue:
    source_file: str
    source_table: str
    message: str


@dataclass
class ProgramRequirement:
    program_code: str
    program_title: str
    credential_type: str
    catalog_year: str
    program_total_credits: float | None
    requirement_group: str
    requirement_type: str
    course_id: str
    course_credits: int
    choice_group_id: str
    choice_group_target_credits: float | None
    source_file: str
    source_row: int
    raw_rule_text: str
    status: str
    notes: str


@dataclass
class ProgramWorkbookIssue:
    source_file: str
    source_row: int
    message: str


@dataclass
class ValidationIssue:
    severity: str  # "warning" | "error"
    source: str  # "mos" | "training" | "program"
    identifier: str
    message: str


@dataclass
class CreditProfileEntry:
    """One course's potential-credit contribution to a veteran's combined MOS + training profile."""

    course_id: str
    credits: int
    sources: str  # "; "-joined description of every source that granted credit for this course


@dataclass
class MatchedCourse:
    course_id: str
    credits: int
    requirement_type: str
    weight: int
    ranking_points: int


@dataclass
class ProgramRecommendation:
    program_code: str
    program_title: str
    credential_type: str
    matched_courses: list[MatchedCourse]
    surplus_courses: list[MatchedCourse]  # qualify but weren't counted -- their pick group's target is already met
    applicable_matched_credits: int
    major_required_credits_matched: int
    recommendation_score: int
    match_percentage: float | None
    program_total_credits: float | None
    estimated_credits_remaining: float | None
    explanation: str

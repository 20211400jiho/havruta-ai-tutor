import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parents[1] / "resources" / "curriculum_catalog.json"
# Subjects withdrawn from the service. Their catalog data and tutoring code stay
# so they can be re-enabled by removing them here.
DISABLED_SUBJECTS = frozenset({"영어"})
DISABLED_SUBJECT_MESSAGE = "현재 제공하지 않는 과목입니다."


def is_subject_enabled(subject: str | None) -> bool:
    return (subject or "").strip() not in DISABLED_SUBJECTS


@lru_cache(maxsize=1)
def load_curriculum_catalog() -> dict:
    if not CATALOG_PATH.is_file():
        raise RuntimeError(f"RAG 교육과정 카탈로그를 찾을 수 없습니다: {CATALOG_PATH}")
    with CATALOG_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def unit_matches_school_level(unit_code: str | None, school_level: str | None) -> bool:
    """2022 achievement codes start with 9 (middle) or 10/12 (high school).

    Source rows labelled with the other school level are hidden from selection
    instead of being shown under the wrong level (e.g. 고1 국어 under 중1).
    """
    code = (unit_code or "").strip()
    if school_level == "중학교":
        return code.startswith("9")
    if school_level == "고등학교":
        return code.startswith(("10", "12"))
    return True


def _without_mismatched_units(subject_item: dict) -> dict:
    levels = []
    for level in subject_item.get("school_levels", []):
        grades = []
        for grade in level.get("grades", []):
            units = [unit for unit in grade.get("units", [])
                     if unit_matches_school_level(unit.get("code"), level.get("name"))]
            if units:
                grades.append({**grade, "units": units})
        if grades:
            levels.append({**level, "grades": grades})
    return {**subject_item, "school_levels": levels}


def get_subject_catalog(subject: str) -> dict | None:
    normalized_subject = subject.strip()
    if not is_subject_enabled(normalized_subject):
        return None
    catalog = load_curriculum_catalog()
    for item in catalog.get("subjects", []):
        if item.get("name") != normalized_subject:
            continue
        result = _without_mismatched_units(deepcopy(item))
        result["curriculum_year"] = catalog.get("curriculum_year")
        result["source"] = catalog.get("source")
        result["standard_count"] = sum(
            len(unit.get("standards", []))
            for level in result.get("school_levels", [])
            for grade in level.get("grades", [])
            for unit in grade.get("units", [])
        )
        return result
    return None


def is_valid_curriculum_selection(
    subject: str,
    school_level: str | None,
    grade: str | None,
    unit_code: str | None,
) -> bool:
    """Validate a client selection against the server-owned 2022 curriculum catalog."""
    if not all((school_level, grade, unit_code)):
        return False
    subject_catalog = get_subject_catalog(subject)
    if subject_catalog is None:
        return False
    return any(
        unit.get("code") == unit_code
        for level in subject_catalog.get("school_levels", [])
        if level.get("name") == school_level
        for grade_item in level.get("grades", [])
        if grade_item.get("name") == grade
        for unit in grade_item.get("units", [])
    )

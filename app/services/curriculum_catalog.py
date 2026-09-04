import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parents[1] / "resources" / "curriculum_catalog.json"


@lru_cache(maxsize=1)
def load_curriculum_catalog() -> dict:
    if not CATALOG_PATH.is_file():
        raise RuntimeError(f"RAG 교육과정 카탈로그를 찾을 수 없습니다: {CATALOG_PATH}")
    with CATALOG_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def get_subject_catalog(subject: str) -> dict | None:
    normalized_subject = subject.strip()
    catalog = load_curriculum_catalog()
    for item in catalog.get("subjects", []):
        if item.get("name") != normalized_subject:
            continue
        result = deepcopy(item)
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

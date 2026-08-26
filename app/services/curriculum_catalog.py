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

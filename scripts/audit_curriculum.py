"""Read-only catalog distribution audit; counts are mappings, NOT unique documents."""
import json
from app.rag.curriculum import load_curriculum_catalog


def audit(catalog):
    subjects, flags = [], []
    for subject in catalog.get("subjects", []):
        mappings = 0
        unit_count = 0
        scopes = []
        for level in subject.get("school_levels", []):
            for grade in level.get("grades", []):
                scope_count = 0
                for unit in grade.get("units", []):
                    unit_count += 1
                    for standard in unit.get("standards", []):
                        count = standard.get("document_count", 0)
                        mappings += count
                        scope_count += count
                        code = standard["code"]
                        suspect = (level["name"] == "중학교" and code.startswith(("10", "12"))) or (level["name"] == "고등학교" and code.startswith("9"))
                        if suspect:
                            flags.append({"subject": subject["name"], "school_level": level["name"],
                                          "grade": grade["name"], "code": code, "mapping_count": count,
                                          "action": "manual_review_required"})
                scopes.append({"school_level": level["name"], "grade": grade["name"], "mapping_count": scope_count})
        subjects.append({"subject": subject["name"], "mapping_count": mappings, "unit_scopes": unit_count, "scopes": scopes})
    return {"source": "versioned curriculum catalog", "count_unit": "document-standard mappings (duplicates possible)",
            "does_not_measure": "unique document counts, correctness, full curriculum coverage, or absence of bias",
            "subjects": subjects, "school_code_review_candidates": flags}


if __name__ == "__main__":
    print(json.dumps(audit(load_curriculum_catalog()), ensure_ascii=False, indent=2))

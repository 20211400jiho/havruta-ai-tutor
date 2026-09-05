"""Measure curriculum-standard retrieval integrity and print a JSON report."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from time import perf_counter

from app.database.config import settings
from app.services.rag_service import search_chroma


BASE_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = BASE_DIR / "app" / "resources" / "curriculum_catalog.json"


def evaluation_cases(per_subject: int) -> list[dict]:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    cases: list[dict] = []
    for subject in catalog["subjects"]:
        candidates: list[dict] = []
        seen: set[str] = set()
        for school_level in subject["school_levels"]:
            for grade in school_level["grades"]:
                for unit in grade["units"]:
                    for standard in unit["standards"]:
                        if standard["code"] in seen:
                            continue
                        seen.add(standard["code"])
                        candidates.append({
                            "subject": subject["name"],
                            "school_level": school_level["name"],
                            "grade": grade["name"],
                            "unit_code": unit["code"],
                            "unit_title": unit["title"],
                            "standard_code": standard["code"],
                            "query": standard["title"],
                        })
        if not candidates:
            continue
        positions = sorted({
            round(index * (len(candidates) - 1) / max(1, per_subject - 1))
            for index in range(per_subject)
        })
        cases.extend(candidates[position] for position in positions)
    return cases


def evaluate(top_k: int, per_subject: int) -> dict:
    cases = evaluation_cases(per_subject)
    details = []
    subject_counts = defaultdict(lambda: {"total": 0, "hits": 0})
    started = perf_counter()
    for case in cases:
        query_started = perf_counter()
        results = search_chroma(
            case["query"],
            top_k,
            subject=case["subject"],
            curriculum_year=settings.rag_curriculum_year,
            unit_code=case["unit_code"],
            school_level=case["school_level"],
            grade=case["grade"],
        )
        elapsed_ms = round((perf_counter() - query_started) * 1000, 1)
        hit = any(
            f"[{case['standard_code']}]" in str(result.metadata.get("achievement_standard_2022") or "")
            for result in results
        )
        aligned = bool(results) and all(
            result.metadata.get("curriculum_alignment") in {"source", "achievement_standard"}
            for result in results
        )
        subject_counts[case["subject"]]["total"] += 1
        subject_counts[case["subject"]]["hits"] += int(hit)
        details.append({**case, "hit_at_k": hit, "aligned": aligned, "result_count": len(results), "latency_ms": elapsed_ms})
    total_hits = sum(item["hit_at_k"] for item in details)
    aligned_cases = sum(item["aligned"] for item in details)
    total_ms = round((perf_counter() - started) * 1000, 1)
    return {
        "curriculum_year": settings.rag_curriculum_year,
        "collection": settings.chroma_collection,
        "top_k": top_k,
        "total_cases": len(details),
        "hit_rate_at_k": round(total_hits / len(details), 4) if details else 0,
        "alignment_rate": round(aligned_cases / len(details), 4) if details else 0,
        "average_latency_ms": round(sum(item["latency_ms"] for item in details) / len(details), 1) if details else 0,
        "total_runtime_ms": total_ms,
        "by_subject": {
            subject: {**counts, "hit_rate": round(counts["hits"] / counts["total"], 4)}
            for subject, counts in subject_counts.items()
        },
        "cases": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--per-subject", type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.top_k, args.per_subject), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

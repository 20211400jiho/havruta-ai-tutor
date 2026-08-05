import argparse
from pathlib import Path
from typing import Dict, List, Tuple

from app.services.rag_indexer import extract_records_from_file


def find_json_folders(data_dir: Path) -> Dict[Path, List[Path]]:
    folders: Dict[Path, List[Path]] = {}
    for file_path in sorted(data_dir.rglob("*.json")):
        folders.setdefault(file_path.parent, []).append(file_path)
    return folders


def format_percent(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.00%"
    return f"{numerator / denominator * 100:.2f}%"


def inspect_folder(folder: Path, files: List[Path], data_dir: Path) -> Tuple[int, int, int, int, List[str]]:
    tested = min(len(files), 20)
    tested_files = files[:tested]
    extracted_docs = 0
    failed_files = 0
    errors: List[str] = []

    for file_path in tested_files:
        try:
            records = extract_records_from_file(file_path, data_dir)
        except Exception as exc:
            failed_files += 1
            errors.append(f"{file_path.name}: {exc}")
            continue
        extracted_docs += len(records)

    return len(files), tested, extracted_docs, failed_files, errors


def print_folder_report(rows: List[Dict[str, object]]) -> None:
    header = ["폴더 경로", "전체 JSON", "테스트 JSON", "추출 문서", "실패 파일", "성공률", "상태"]
    widths = [40, 10, 11, 11, 10, 10, 10]
    fmt = " | ".join(f"{{:<{w}}}" for w in widths)

    print(fmt.format(*header))
    print("-" * (sum(widths) + 3 * (len(widths) - 1)))
    for row in rows:
        print(
            fmt.format(
                row["folder"],
                str(row["total_json"]),
                str(row["tested_json"]),
                str(row["extracted_docs"]),
                str(row["failed_files"]),
                row["success_rate"],
                row["status"],
            )
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="data 하위 폴더별 JSON 추출 테스트 스크립트")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="JSON 데이터 폴더",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    if not data_dir.exists() or not data_dir.is_dir():
        print(f"유효한 data 폴더를 찾을 수 없습니다: {data_dir}")
        return

    folders = find_json_folders(data_dir)
    if not folders:
        print(f"JSON 파일을 찾을 수 없습니다: {data_dir}")
        return

    rows: List[Dict[str, object]] = []
    problem_folders: List[str] = []
    total_folders = len(folders)
    normal_folders = 0

    for folder in sorted(folders):
        total_json, tested_json, extracted_docs, failed_files, errors = inspect_folder(folder, folders[folder], data_dir)
        success_rate = format_percent(tested_json - failed_files, tested_json)
        status = "정상"
        if extracted_docs == 0 or failed_files > 0:
            status = "[문제 있음]"
            problem_folders.append(str(folder.relative_to(data_dir)))
        else:
            normal_folders += 1

        rows.append(
            {
                "folder": str(folder.relative_to(data_dir)),
                "total_json": total_json,
                "tested_json": tested_json,
                "extracted_docs": extracted_docs,
                "failed_files": failed_files,
                "success_rate": success_rate,
                "status": status,
            }
        )

    print("JSON 추출 테스트 결과")
    print(f"데이터 루트: {data_dir}")
    print(f"검사한 폴더 수: {total_folders}")
    print()
    print_folder_report(rows)
    print()
    print("요약")
    print(f"전체 폴더 수: {total_folders}")
    print(f"정상 폴더 수: {normal_folders}")
    print(f"문제 있는 폴더 수: {len(problem_folders)}")
    if problem_folders:
        print("문제 있는 폴더 목록:")
        for folder in problem_folders:
            print(f"- {folder}")


if __name__ == "__main__":
    main()

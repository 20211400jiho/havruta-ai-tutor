import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set

TEXT_KEYS = [
    "text_description",
    "text_qa",
    "text_an",
    "description",
    "question",
    "answer",
    "solution",
    "content",
    "text",
]

TEXT_RELATED_PATTERNS = [
    "text",
    "description",
    "question",
    "answer",
    "solution",
    "content",
    "qa",
    "an",
]


def collect_keys(data: Any, parent_key: Optional[str] = None) -> Set[str]:
    keys: Set[str] = set()
    if isinstance(data, dict):
        for key, value in data.items():
            keys.add(key)
            keys.update(collect_keys(value, key))
    elif isinstance(data, list):
        for item in data:
            keys.update(collect_keys(item, parent_key))
    return keys


def text_related_keys(all_keys: Set[str]) -> List[str]:
    found: Set[str] = set()
    for key in all_keys:
        lowered = key.lower()
        if any(pattern in lowered for pattern in TEXT_RELATED_PATTERNS):
            found.add(key)
    return sorted(found)


def find_key_existence(all_keys: Set[str], keys: List[str]) -> Dict[str, bool]:
    return {key: key in all_keys for key in keys}


def get_payload_type(payload: Any) -> str:
    if isinstance(payload, dict):
        return "dict"
    if isinstance(payload, list):
        return "list"
    return type(payload).__name__


def get_info_keys(value: Any) -> Optional[List[str]]:
    if isinstance(value, dict):
        return sorted(value.keys())
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return sorted(first.keys())
        return [f"first_item_type={type(first).__name__}"]
    return None


def inspect_file(file_path: Path) -> None:
    print(f"\n=== 파일: {file_path} ===")
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"JSON 읽기 실패: {exc}")
        return

    try:
        payload = json.loads(raw_text)
    except Exception as exc:
        print(f"JSON 파싱 실패: {exc}")
        return

    payload_type = get_payload_type(payload)
    if isinstance(payload, dict):
        top_keys = sorted(payload.keys())
    else:
        top_keys = []

    raw_data_info = payload.get("raw_data_info") if isinstance(payload, dict) else None
    source_data_info = payload.get("source_data_info") if isinstance(payload, dict) else None
    learning_data_info = payload.get("learning_data_info") if isinstance(payload, dict) else None

    all_keys = collect_keys(payload)
    related_keys = text_related_keys(all_keys)
    existence = find_key_existence(all_keys, TEXT_KEYS)

    print(f"상위 타입: {payload_type}")
    print(f"상위 keys: {top_keys}")
    print(f"raw_data_info keys: {get_info_keys(raw_data_info)}")
    print(f"source_data_info keys: {get_info_keys(source_data_info)}")
    print(f"learning_data_info type: {get_payload_type(learning_data_info)}")
    if isinstance(learning_data_info, dict):
        print(f"learning_data_info keys: {sorted(learning_data_info.keys())}")
    elif isinstance(learning_data_info, list):
        if learning_data_info:
            first_keys = get_info_keys(learning_data_info)
            print(f"learning_data_info 첫 번째 item keys: {first_keys}")
        else:
            print("learning_data_info 첫 번째 item keys: []")
    else:
        print("learning_data_info keys: None")

    print(f"파일 전체에서 발견되는 텍스트 관련 키 목록: {related_keys}")
    print("키 존재 여부:")
    for key, exists in existence.items():
        print(f"  {key}: {exists}")

    preview = raw_text[:1500].replace("\n", "\\n")
    print("JSON 일부 미리보기:")
    print(preview)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Hub JSON 구조를 확인하는 디버그 스크립트입니다.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="JSON 데이터 폴더",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="확인할 JSON 파일 수",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    files = sorted(data_dir.rglob("*.json"))
    if not files:
        print(f"JSON 파일을 찾을 수 없습니다: {data_dir}")
        return

    print(f"찾은 JSON 파일 수: {len(files)}")
    for file_path in files[: args.count]:
        inspect_file(file_path)


if __name__ == "__main__":
    main()

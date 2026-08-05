import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import chromadb
from sentence_transformers import SentenceTransformer

COLLECTION_NAME = "havruta_math_all"
DB_DIR = Path(__file__).resolve().parents[2] / "app" / "database" / "chroma_db"
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"

SUBJECT_KEYS = ["subject_name", "subject", "subject_nm", "과목"]
GRADE_KEYS = ["grade_name", "grade", "grade_nm", "학년"]
LEVEL_KEYS = ["school_level", "school_name", "school", "학교급"]
YEAR_KEYS = ["curriculum_year", "revision_year", "개정연도"]
DESCRIPTION_KEYS = ["text_description", "description", "explanation"]
QUESTION_KEYS = ["text_qa", "question", "qa"]
ANSWER_KEYS = ["text_an", "answer", "solution"]
CLASS_NUM_KEYS = ["class_num", "unit_num", "chapter_num", "단원번호"]
CLASS_NAME_KEYS = ["class_name", "unit_name", "chapter_name", "단원명"]
ACHIEVE_2015_KEYS = ["achievement_2015", "achievement2015", "성취기준2015"]
ACHIEVE_2022_KEYS = ["achievement_2022", "achievement2022", "성취기준2022"]

KEY_CANDIDATES = {
    "subject": SUBJECT_KEYS,
    "grade": GRADE_KEYS,
    "school_level": LEVEL_KEYS,
    "curriculum_year": YEAR_KEYS,
    "description": DESCRIPTION_KEYS,
    "question": QUESTION_KEYS,
    "answer": ANSWER_KEYS,
    "class_num": CLASS_NUM_KEYS,
    "class_name": CLASS_NAME_KEYS,
    "achievement_2015": ACHIEVE_2015_KEYS,
    "achievement_2022": ACHIEVE_2022_KEYS,
}


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


def find_first_value(data: Any, keys: List[str], depth: int = 3) -> Optional[Any]:
    if depth < 0 or data is None:
        return None
    if isinstance(data, dict):
        for key in keys:
            if key in data and data[key] not in (None, ""):
                return data[key]
        for value in data.values():
            if isinstance(value, (dict, list)):
                found = find_first_value(value, keys, depth - 1)
                if found is not None:
                    return found
    elif isinstance(data, list):
        for item in data:
            found = find_first_value(item, keys, depth - 1)
            if found is not None:
                return found
    return None


def normalize_learning_items(obj: Any) -> List[Any]:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        return [obj]
    return []


def join_string_if_list(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(safe_str(item) for item in value if item not in (None, ""))
    return safe_str(value)


def safe_id(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-\.]+", "_", text)


def extract_records_from_file(file_path: Path, data_dir: Path) -> List[Dict[str, Any]]:
    try:
        raw_text = file_path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)
    except Exception:
        raise

    if not isinstance(payload, dict):
        return []

    raw = payload.get("raw_data_info", {}) or {}
    source = payload.get("source_data_info", {}) or {}
    learning_data = payload.get("learning_data_info", {}) or {}

    records = normalize_learning_items(learning_data)
    extracted: List[Dict[str, Any]] = []
    rel_path = str(file_path.relative_to(data_dir)).replace("\\", "/")

    for index, learning_item in enumerate(records):
        if not isinstance(learning_item, dict):
            continue

        description = safe_str(learning_item.get("text_description", "")).strip()
        question = safe_str(learning_item.get("text_qa", "")).strip()
        answer = safe_str(learning_item.get("text_an", "")).strip()

        if not any([description, question, answer]):
            # fallback helper keys if the primary keys are missing
            description = description or safe_str(find_first_value(learning_item, ["description", "explanation", "content", "text"], depth=2)).strip()
            question = question or safe_str(find_first_value(learning_item, ["question", "qa", "query", "problem"], depth=2)).strip()
            answer = answer or safe_str(find_first_value(learning_item, ["answer", "solution", "response"], depth=2)).strip()

        if not any([description, question, answer]):
            continue

        subject = safe_str(raw.get("subject", "")).strip()
        grade = safe_str(raw.get("grade", "")).strip()
        school_level = safe_str(raw.get("school", "")).strip()
        curriculum_year = safe_str(raw.get("revision_year", "")).strip()
        semester = safe_str(raw.get("semester", "")).strip()

        achievement_2009 = join_string_if_list(source.get("2009_achievement_standard", "")).strip()
        achievement_2015 = join_string_if_list(source.get("2015_achievement_standard", "")).strip()
        achievement_2022 = join_string_if_list(source.get("2022_achievement_standard", "")).strip()

        learning_name = safe_str(learning_item.get("learning_data_name", file_path.stem)).strip()
        class_num = safe_str(learning_item.get("class_num", "")).strip()
        class_name = safe_str(learning_item.get("class_name", "")).strip()

        document = (
            f"과목: {subject}\n"
            f"학년: {grade}\n"
            f"학교급: {school_level}\n"
            f"학기: {semester}\n"
            f"단원번호: {class_num}\n"
            f"단원명: {class_name}\n"
            f"설명: {description}\n"
            f"질문: {question}\n"
            f"정답: {answer}\n"
            f"성취기준2009: {achievement_2009}\n"
            f"성취기준2015: {achievement_2015}\n"
            f"성취기준2022: {achievement_2022}"
        )

        doc_id = safe_id(f"{rel_path}#{index}")

        metadata = {
            "file": file_path.name,
            "source_path": rel_path,
            "learning_name": learning_name,
            "subject": subject,
            "grade": grade,
            "school_level": school_level,
            "semester": semester,
            "curriculum_year": curriculum_year,
            "class_num": class_num,
            "class_name": class_name,
        }

        extracted.append({
            "id": doc_id,
            "document": document,
            "metadata": metadata,
        })

    return extracted


def get_chroma_client(reset: bool = False) -> chromadb.api.client.Client:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DB_DIR))
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"기존 컬렉션 삭제 완료: {COLLECTION_NAME}")
        except Exception:
            print(f"삭제할 기존 컬렉션 없음: {COLLECTION_NAME}")
    return client


def get_collection(client: chromadb.api.client.Client) -> chromadb.api.models.Collection:
    return client.get_or_create_collection(name=COLLECTION_NAME)


def index_documents(data_dir: Path, reset: bool = False, batch_size: int = 64) -> None:
    data_dir = data_dir.resolve()
    files = sorted(data_dir.rglob("*.json"))
    total_files = len(files)
    if total_files == 0:
        print(f"JSON 파일을 찾을 수 없습니다: {data_dir}")
        return

    print(f"발견된 JSON 파일 수: {total_files}")

    client = get_chroma_client(reset=reset)
    collection = get_collection(client)

    model = SentenceTransformer(EMBEDDING_MODEL)
    documents: List[str] = []
    ids: List[str] = []
    metadatas: List[Dict[str, str]] = []
    failed_files = 0
    skipped_files = 0
    success_documents = 0
    stored_documents = 0
    processed_files = 0
    skip_reasons: List[str] = []

    def flush_batch() -> None:
        nonlocal documents, ids, metadatas, stored_documents
        if not documents:
            return
        embeddings = model.encode(documents, batch_size=batch_size, show_progress_bar=True, convert_to_numpy=True)
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings.tolist(),
        )
        stored_documents += len(ids)
        documents.clear()
        ids.clear()
        metadatas.clear()

    for file_path in files:
        processed_files += 1
        try:
            extracted = extract_records_from_file(file_path, data_dir)
        except Exception as exc:
            failed_files += 1
            skipped_files += 1
            if len(skip_reasons) < 10:
                skip_reasons.append(f"[스킵] {file_path.name} / 이유: JSON 파싱 또는 읽기 실패 ({exc})")
            if processed_files % 100 == 0 or processed_files == total_files:
                print(f"JSON 읽는 중: {processed_files}/{total_files}")
            continue

        if not extracted:
            skipped_files += 1
            if len(skip_reasons) < 10:
                skip_reasons.append(f"[스킵] {file_path.name} / 이유: description, question, answer 모두 비어 있음")
        else:
            for item in extracted:
                ids.append(item["id"])
                documents.append(item["document"])
                metadatas.append(item["metadata"])
            success_documents += len(extracted)

        if processed_files % 100 == 0 or processed_files == total_files:
            print(f"JSON 읽는 중: {processed_files}/{total_files}")

        if len(documents) >= batch_size:
            flush_batch()

    flush_batch()

    try:
        client.persist()
    except Exception:
        pass

    print("인덱싱 결과")
    print(f"발견된 JSON 파일 수: {total_files}")
    print(f"성공적으로 추출한 문서 수: {success_documents}")
    print(f"스킵한 파일 수: {skipped_files}")
    print(f"ChromaDB 저장 문서 수: {stored_documents}")
    if skip_reasons:
        print("\n최초 스킵된 파일 이유:")
        for reason in skip_reasons:
            print(reason)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Training RAG 인덱서")
    parser.add_argument("--reset", action="store_true", help="기존 Chroma 컬렉션을 초기화합니다.")
    parser.add_argument("--batch-size", type=int, default=64, help="임베딩 배치 크기")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[2] / "data", help="JSON 데이터 폴더")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    index_documents(data_dir=args.data_dir, reset=args.reset, batch_size=args.batch_size)


if __name__ == "__main__":
    main()

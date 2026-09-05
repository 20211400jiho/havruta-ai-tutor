"""배포 시작 전에 Chroma 볼륨의 무결성을 빠르게 검사한다."""

import os
from pathlib import Path

from app.database.config import settings


REQUIRED_SUBJECTS = {"국어", "영어", "수학", "사회", "사회문화", "과학", "도덕", "기술가정", "정보"}


def main() -> None:
    if os.getenv("CHROMA_REQUIRED", "false").lower() not in {"1", "true", "yes"}:
        print("Chroma preflight skipped (CHROMA_REQUIRED=false).")
        return

    import chromadb

    chroma_dir = Path(settings.chroma_dir).resolve()
    sqlite_file = chroma_dir / "chroma.sqlite3"
    if not sqlite_file.is_file():
        raise SystemExit(f"Chroma preflight failed: {sqlite_file} not found")

    collection_name = settings.chroma_collection
    collection = chromadb.PersistentClient(path=str(chroma_dir)).get_collection(collection_name)
    count = collection.count()
    if count < 300_000:
        raise SystemExit(f"Chroma preflight failed: expected >=300000 rows, got {count}")

    missing = []
    for subject in sorted(REQUIRED_SUBJECTS):
        result = collection.get(where={"subject": {"$eq": subject}}, limit=1, include=[])
        if not result.get("ids"):
            missing.append(subject)
    if missing:
        raise SystemExit(f"Chroma preflight failed: missing subjects={','.join(missing)}")

    print(f"Chroma preflight passed: collection={collection_name}, rows={count}, subjects=9")


if __name__ == "__main__":
    main()

import argparse
from pathlib import Path

from app.services.rag_indexer import index_documents


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="전체 JSON 데이터를 ChromaDB로 인덱싱합니다.")
    parser.add_argument("--reset", action="store_true", help="기존 Chroma 컬렉션을 초기화합니다.")
    parser.add_argument("--batch-size", type=int, default=64, help="임베딩 배치 크기")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data", help="JSON 데이터 폴더")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    index_documents(data_dir=args.data_dir, reset=args.reset, batch_size=args.batch_size)


if __name__ == "__main__":
    main()

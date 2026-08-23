from app.services.rag_service import load_local_rows


def load_high1_math() -> list[dict]:
    return load_local_rows()


if __name__ == "__main__":
    rows = load_high1_math()
    print(f"로드된 데이터 개수: {len(rows)}")
    for row in rows[:3]:
        print(row)

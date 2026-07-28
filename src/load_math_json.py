from pathlib import Path
import json
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def load_high1_math() -> pd.DataFrame:
    rows = []

    json_files = list(DATA_DIR.glob("*.json"))

    if not json_files:
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {DATA_DIR}")

    for file_path in json_files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw = data.get("raw_data_info", {})
        source = data.get("source_data_info", {})
        learning = data.get("learning_data_info", {})

        subject = raw.get("subject_name", raw.get("subject", "수학"))
        grade = raw.get("grade_name", raw.get("grade", "1학년"))

        achievement_2015 = " ".join(source.get("achievement_2015", []))
        achievement_2022 = " ".join(source.get("achievement_2022", []))

        row = {
            "id": learning.get("learning_data_name", file_path.stem),
            "file": file_path.name,
            "subject": subject,
            "grade": grade,
            "achievement_2015": achievement_2015,
            "achievement_2022": achievement_2022,
            "description": learning.get("text_description", ""),
            "question": learning.get("text_qa", ""),
            "answer": learning.get("text_an", ""),
        }

        rows.append(row)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = load_high1_math()

    print("로드된 데이터 개수:", len(df))
    print()
    print(df.head())
    print()
    print("컬럼 목록:")
    print(df.columns.tolist())
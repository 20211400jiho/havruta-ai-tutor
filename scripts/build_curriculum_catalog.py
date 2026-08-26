"""Build the RAG curriculum selector catalog from the persisted Chroma collection.

The source dataset stores the useful 2022 curriculum unit information inside each
document's ``성취기준2022`` line.  The legacy ``class_num``/``class_name``
metadata describes the data format (usually ``텍스트``), so it must not be used
as a learning unit.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
STANDARD_PATTERN = re.compile(r"\[([^\]]+)]\s*([^\[]+)")
SUPPORTED_SUBJECTS = (
    "국어",
    "영어",
    "수학",
    "사회",
    "사회문화",
    "과학",
    "도덕",
    "기술가정",
    "정보",
)


UNIT_TITLES = {
    "국어": {
        "01": "듣기·말하기",
        "02": "읽기",
        "03": "쓰기",
        "04": "문법",
        "05": "문학",
        "06": "매체",
        "12화언01": "화법과 언어",
        "12독작01": "독서와 작문",
    },
    "영어": {"01": "영어 이해", "02": "영어 표현"},
    "수학": {
        "9수01": "수와 연산",
        "9수02": "변화와 관계",
        "9수03": "도형과 측정",
        "9수04": "자료와 가능성",
        "10공수1-01": "다항식",
        "10공수1-02": "방정식과 부등식",
        "10공수1-03": "경우의 수",
        "10공수2-01": "도형의 방정식",
        "10공수2-02": "집합과 명제",
        "10공수2-03": "함수와 그래프",
    },
    "과학": {
        "9과01": "과학과 지속가능한 삶",
        "9과02": "생물의 구성과 다양성",
        "9과03": "열",
        "9과04": "물질의 상태와 입자",
        "9과05": "힘",
        "9과06": "기체의 성질",
        "9과07": "태양계",
        "9과08": "물질의 특성",
        "9과09": "지구계와 지권",
        "9과10": "빛과 파동",
        "9과11": "원소와 원자",
        "9과12": "식물과 에너지",
        "9과13": "동물과 에너지",
        "9과14": "전기와 자기",
        "9과15": "별과 우주",
        "9과16": "화학 반응의 규칙",
        "9과17": "날씨와 기후",
        "9과18": "해양과 기후변화",
        "9과19": "운동과 에너지",
        "9과20": "자극과 반응",
        "9과21": "생식과 발생",
        "9과22": "재해·재난과 안전",
        "9과23": "과학과 진로",
        "10통과1-01": "과학의 기초",
        "10통과1-02": "물질과 규칙성",
        "10통과1-03": "시스템과 상호작용",
        "10통과2-02": "환경과 에너지",
        "10통과2-03": "과학과 미래 사회",
    },
    "도덕": {
        "9도01": "자신과의 관계",
        "9도02": "타인과의 관계",
        "9도03": "사회·공동체와의 관계",
        "9도04": "자연·초월과의 관계",
    },
    "기술가정": {
        "9기가01": "인간 발달과 가족",
        "9기가02": "생활환경과 지속가능한 선택",
        "9기가03": "기술의 이해와 문제 해결",
        "9기가04": "기술 시스템",
        "12기가01": "생활문화와 지속가능한 삶",
        "12기가02": "생활 설계와 자립",
        "12기가03": "성인기 발달과 가족",
        "12기가04": "공학의 이해와 진로",
        "12기가05": "공학 설계와 미래 기술",
        "12기가06": "디지털·생명 공학",
    },
    "사회문화": {
        "12사문01": "사회·문화 현상의 탐구",
        "12사문02": "개인과 사회 구조",
        "12사문03": "문화와 일상생활",
        "12사문04": "사회 불평등과 복지",
    },
    "정보": {
        "9정01": "컴퓨팅 시스템",
        "9정02": "데이터",
        "9정03": "알고리즘과 프로그래밍",
        "9정04": "인공지능",
        "9정05": "디지털 문화",
        "12정01": "컴퓨팅 시스템과 네트워크",
        "12정02": "데이터",
        "12정03": "알고리즘과 프로그래밍",
        "12정05": "디지털 사회와 보안",
    },
    "사회": {
        "9사(지리)01": "세계화와 지역 이해",
        "9사(지리)02": "아시아",
        "9사(지리)03": "유럽",
        "9사(지리)04": "아프리카",
        "9사(지리)05": "아메리카",
        "9사(지리)06": "오세아니아와 극지방",
        "9사(지리)07": "대한민국의 위치와 지역",
        "9사(지리)08": "우리나라의 자연환경",
        "9사(지리)09": "중부 지역",
        "9사(지리)10": "남부 지역",
        "9사(지리)11": "북한과 접경지역",
        "9사(지리)12": "자원과 지속가능한 발전",
        "9사(일사)01": "사회화와 자아 정체성",
        "9사(일사)02": "문화와 미디어",
        "9사(일사)03": "정치와 민주주의",
        "9사(일사)04": "정치 과정과 시민 참여",
        "9사(일사)05": "법과 재판",
        "9사(일사)06": "인권과 기본권",
        "9사(일사)07": "정부와 국가기관",
        "9사(일사)08": "경제생활과 기업",
        "9사(일사)09": "시장과 가격",
        "9사(일사)10": "국민경제와 국제 거래",
        "9사(일사)11": "국제 사회와 세계시민",
        "9사(일사)12": "사회 변동과 사회문제",
        "10통사1-01": "통합적 관점",
        "10통사1-02": "행복한 삶",
        "10통사1-03": "자연환경과 인간",
        "10통사1-04": "문화와 다양성",
        "10통사1-05": "생활공간과 사회",
        "10통사2-01": "인권과 헌법",
        "10통사2-02": "정의와 불평등",
        "10통사2-03": "시장경제와 지속가능발전",
        "10통사2-04": "세계화와 평화",
        "10통사2-05": "미래와 지속가능한 삶",
    },
}


def extract_standards(content: str) -> list[tuple[str, str]]:
    line = next(
        (line.partition(":")[2].strip() for line in content.splitlines() if line.startswith("성취기준2022:")),
        "",
    )
    return [
        (code.strip(), " ".join(title.split()).strip(" ."))
        for code, title in STANDARD_PATTERN.findall(line)
        if code.strip().startswith(("9", "10", "12")) and title.strip()
    ]


def unit_code(standard_code: str) -> str:
    return standard_code.rsplit("-", 1)[0]


def unit_title(subject: str, code: str) -> str:
    subject_titles = UNIT_TITLES.get(subject, {})
    if code in subject_titles:
        return subject_titles[code]
    if subject == "국어" and code.startswith(("9국", "10공국")):
        domain_match = re.search(r"(\d{2})$", code)
        if domain_match and domain_match.group(1) in subject_titles:
            return subject_titles[domain_match.group(1)]
    if subject == "영어":
        domain_match = re.search(r"(\d{2})$", code)
        if domain_match and domain_match.group(1) in subject_titles:
            return subject_titles[domain_match.group(1)]
    return f"성취기준 영역 {code}"


def grade_sort_key(value: str) -> tuple[int, str]:
    match = re.search(r"\d+", value)
    return (int(match.group()) if match else 99, value)


def build_catalog(collection, batch_size: int = 2_000) -> dict:
    # (subject, school level, grade, unit, standard) -> document count
    counts: Counter = Counter()
    # Some sources contain minor punctuation variations; keep the most common title.
    titles: dict[tuple[str, str], Counter] = defaultdict(Counter)

    for offset in range(0, collection.count(), batch_size):
        response = collection.get(
            limit=batch_size,
            offset=offset,
            include=["documents", "metadatas"],
        )
        for content, metadata in zip(
            response.get("documents") or [],
            response.get("metadatas") or [],
            strict=False,
        ):
            subject = str(metadata.get("subject") or "").strip()
            if subject not in SUPPORTED_SUBJECTS:
                continue
            school_level = str(metadata.get("school_level") or "").strip()
            grade = str(metadata.get("grade") or "공통").strip()
            if school_level not in {"중학교", "고등학교"}:
                continue
            for standard_code, standard_title in extract_standards(content or ""):
                code = unit_code(standard_code)
                counts[(subject, school_level, grade, code, standard_code)] += 1
                titles[(subject, standard_code)][standard_title] += 1

    subjects = []
    for subject in SUPPORTED_SUBJECTS:
        school_levels = []
        levels = sorted({key[1] for key in counts if key[0] == subject}, key=lambda value: value != "중학교")
        for school_level in levels:
            grades = []
            grade_names = sorted(
                {key[2] for key in counts if key[:2] == (subject, school_level)},
                key=grade_sort_key,
            )
            for grade in grade_names:
                units = []
                unit_codes = sorted(
                    {key[3] for key in counts if key[:3] == (subject, school_level, grade)}
                )
                for code in unit_codes:
                    standards = []
                    standard_codes = sorted(
                        {
                            key[4]
                            for key in counts
                            if key[:4] == (subject, school_level, grade, code)
                        }
                    )
                    for standard_code in standard_codes:
                        title = titles[(subject, standard_code)].most_common(1)[0][0]
                        standards.append(
                            {
                                "code": standard_code,
                                "title": title,
                                "document_count": counts[
                                    (subject, school_level, grade, code, standard_code)
                                ],
                            }
                        )
                    units.append(
                        {
                            "code": code,
                            "title": unit_title(subject, code),
                            "document_count": sum(item["document_count"] for item in standards),
                            "standards": standards,
                        }
                    )
                grades.append({"name": grade, "units": units})
            school_levels.append({"name": school_level, "grades": grades})
        subjects.append({"name": subject, "school_levels": school_levels})

    return {
        "curriculum_year": "2022",
        "source": "ChromaDB 성취기준2022 필드",
        "subjects": subjects,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chroma-dir", default=str(BASE_DIR / "chroma_db"))
    parser.add_argument("--collection", default="havruta_math_all")
    parser.add_argument(
        "--output",
        default=str(BASE_DIR / "app" / "resources" / "curriculum_catalog.json"),
    )
    args = parser.parse_args()

    import chromadb

    collection = chromadb.PersistentClient(path=args.chroma_dir).get_collection(args.collection)
    catalog = build_catalog(collection)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output} ({len(catalog['subjects'])} subjects)")


if __name__ == "__main__":
    main()

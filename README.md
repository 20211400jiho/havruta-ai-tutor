# AITraining RAG 백엔드

AI Training JSON 데이터를 읽어 ChromaDB에 인덱싱하고 검색 테스트를 실행하는 RAG backend 구조입니다.

## 폴더 구조

```
AITraining/
├── app/
│   ├── __init__.py
│   ├── database/
│   │   └── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rag_indexer.py
│   │   └── rag_retriever.py
│   └── routers/
│       └── __init__.py
├── data/
├── scripts/
│   ├── index_all.py
│   └── test_search.py
├── requirements.txt
├── .gitignore
└── README.md
```

## 설명

- `data/` 폴더 아래 하위 폴더를 포함해 모든 `.json` 파일을 재귀적으로 읽습니다.
- AI Hub 교육과정 라벨링 JSON 구조를 분석해 주요 필드(`subject`, `grade`, `description`, `question`, `answer` 등)를 추출합니다.
- 텍스트를 하나의 passage 형태로 연결하고 `intfloat/multilingual-e5-base` 모델로 임베딩합니다.
- 임베딩 결과는 `app/database/chroma_db`에 저장되는 ChromaDB 컬렉션 `havruta_math_all`에 인덱싱됩니다.
- 현재 GPT API는 연결하지 않았고, 이 프로젝트는 Retriever 단계입니다.

## data 폴더 사용 방법

- `data/` 아래에 AI Hub JSON 데이터 폴더를 그대로 위치시키면 됩니다.
- 기존 하위 폴더 구조를 유지하세요.
- 예: `data/TL_06.중학교 1학년_03.수학_01.텍스트/*.json`

## 가상환경 생성

Windows PowerShell에서:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 전체 인덱싱 명령

```powershell
.\.venv\Scripts\python.exe scripts/index_all.py --reset --batch-size 64
```

- 데이터가 많거나 메모리/시간 문제가 있으면 `--batch-size 16`로 낮추세요.

## 검색 테스트 명령

```powershell
.\.venv\Scripts\python.exe scripts/test_search.py
```

## ChromaDB 저장 위치

- `app/database/chroma_db`

## 참고

- 현재는 Retriever 단계이며 GPT API 연결은 아직 구현되지 않았습니다.

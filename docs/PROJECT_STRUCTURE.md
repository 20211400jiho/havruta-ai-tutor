# RAG 중심 프로젝트 구조

프론트엔드·백엔드 최상위 분리를 되돌리고, 자료·RAG 핵심·API·화면이 한눈에 보이도록 정리했다. 기능과 API 동작은 유지하며 코드 이동과 import·경로만 변경했다.

```text
havruta-ai-tutor/
├── app/                       # 애플리케이션
│   ├── rag/                   # RAG 핵심
│   │   ├── retriever.py        # 자료 인덱싱·임베딩·벡터/어휘 검색
│   │   ├── tutor.py            # 프롬프트·대화 흐름·OpenAI 응답
│   │   └── curriculum.py       # 과목·학년·단원 카탈로그
│   ├── resources/             # 교육과정 카탈로그 JSON
│   ├── routers/               # 인증·학습·RAG·채팅 API
│   ├── services/              # 노트·퀴즈·공동 학습·실시간 연결
│   ├── models/                # DB 테이블
│   ├── schemas/               # 요청 데이터 검증
│   ├── database/              # 환경변수·DB 연결
│   └── utils/                 # JWT·비밀번호 처리
├── data/                      # RAG 원본 샘플
├── chroma_db/                 # 기존 벡터 인덱스 (Git 제외)
├── scripts/                   # 카탈로그 생성·마이그레이션·RAG 평가
├── tests/                     # 자동 테스트
├── web/                       # React 화면·API 클라이언트
├── docs/                      # 설계·사용·배포 문서
├── main.py                    # FastAPI 시작점
├── .env.example               # 환경변수 예시
├── requirements*.txt          # 기본·AI·테스트 의존성
├── Dockerfile                 # 서버 이미지
└── railway.json               # 서버 배포 설정
```

## RAG 처리 흐름

```text
data/ · chroma_db/
        ↓
app/rag/retriever.py   자료 인덱싱 → 검색·재정렬
        ↓
app/rag/tutor.py       검색 근거 + 이전 대화 → OpenAI 응답
        ↓
app/routers/          API 응답·학습 기록 처리
        ↓
web/src/              학생에게 대화·근거 표시
```

`app/rag/curriculum.py`와 `app/resources/curriculum_catalog.json`이 과목·학년·단원 선택을 지원한다. 기존 검색·생성 코드 안의 인덱싱, 임베딩, 프롬프트를 별도 파일로 세분화하지 않아 기능 변경을 최소화했다.

## 실행

저장소 루트에서 기존 가상환경을 활성화하고 서버를 실행한다.

```bash
source .venv/bin/activate
uvicorn main:app --reload --reload-dir app
```

웹은 새 터미널의 저장소 루트에서 실행한다.

```bash
npm --prefix web run dev
```

실제 비밀 설정은 루트 `.env`에 있으며 Git에서 제외된다. `CHROMA_DIR` 상대 경로는 저장소 루트 기준, Railway의 절대 볼륨 경로는 기존 그대로다. `.venv/`와 대용량 `chroma_db/`도 기존 위치를 유지했다.

## 변경 범위

- `backend/`의 Python 코드·자료·테스트·실행 설정을 루트로 복귀.
- `frontend/`를 `web/`로 변경.
- `app/services/`의 RAG 검색·튜터·카탈로그를 `app/rag/`로 이동.
- import, Docker 빌드 제외 경로, Railway 설정, 문서 링크를 새 경로에 맞춤.

이 구조를 배포할 때는 서버 루트 `/`, 웹 루트 `/web`을 사용한다. 이전 폴더 분리 버전에서 전환하는 절차는 [배포 경로 전환 안내](RAILWAY_DEPLOYMENT.md)를 따른다.

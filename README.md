# Havruta AI Tutor

중·고등학생이 **자신의 설명 → AI의 질문·피드백 → 생각 수정**을 반복하는 RAG 기반 하브루타 학습 웹앱입니다. 단순 정답 제공보다, 근거를 설명하고 배운 내용을 새로운 상황에 적용하는 과정을 돕는 캡스톤 프로젝트입니다.

[웹앱](https://frontend-production-8c41.up.railway.app) · [API 문서](https://backend-production-98f3.up.railway.app/docs) · [발표 자료](docs/PRESENTATION_GUIDE.md) · [배포 안내](docs/RAILWAY_DEPLOYMENT.md)

> 배포 주소의 이용 가능 여부는 서비스 운영 상태에 따라 달라집니다. Git 저장소만 복제하면 운영 DB나 전체 ChromaDB 자료까지 내려받아지는 것은 아닙니다.

## 주요 기능

| 영역 | 구현 내용 |
| --- | --- |
| 계정 | 이메일 가입·로그인, 중1~고3 학년 선택, Argon2 비밀번호 해싱, JWT 인증 |
| 개인 학습 | 과목·학교급·학년·단원 선택, 중단 학습의 대화·진행 확인, 저장 후 나가기·이어하기·처음부터 다시 학습 |
| 대화와 진행 | 최근 대화와 학습 상태 반영, 개념·근거·생각 수정·적용·정리의 5단계 AI 확인 |
| 복습 | 정리노트, RAG 기반 3·5·10문항 퀴즈, 선택지별 오답 이유·정답 해설, 지난 답안 다시 보기 |
| 친구와 학습 | 초대 코드로 스터디룸 참여, WebSocket 채팅, 공동 하브루타 분석 |
| 학습 관리 | 홈 학습 플래너, 최근 학습 기록, 노트·퀴즈·스터디룸 삭제, 다크 모드 |

퀴즈 생성과 단원 선택은 실제 보유 자료에 영향을 받습니다. 표시되는 AI 확인은 잠정적인 학습 기록이며, 객관적 성적이나 학습효과의 증명이 아닙니다.

## 시스템 구성

```mermaid
flowchart LR
    Student["학생 · React/Vite"] -->|HTTP · JWT| API["FastAPI"]
    Student -->|WebSocket · 인증| Chat["스터디룸 채팅"]
    API --> Tutor["튜터 · 대화 상태 관리"]
    Tutor --> Search["과목·학년·단원 필터 검색"]
    Search --> Chroma[("ChromaDB")]
    Search --> Rank["검색 후보 BM25·RRF 재정렬"]
    Rank --> Tutor
    Tutor -->|검색 근거 + 대화 이력 + 프롬프트| LLM["OpenAI"]
    LLM --> Validate["구조화 응답·평가 근거 검증"]
    Validate --> API
    API --> DB[("MySQL · 계정/학습 기록")]
    Chat --> DB
    Chat <--> Redis[("Redis Pub/Sub")]
```

- **RAG**: ChromaDB 의미 검색으로 후보를 찾고, 후보 내 BM25 점수와 순위를 이용해 재정렬합니다. 전체 자료를 별도로 BM25 검색하는 구조는 아닙니다.
- **LLM**: 검색 자료와 최근 대화를 바탕으로 설명·후속 질문·학습 항목 평가를 생성합니다.
- **애플리케이션 로직**: 인증·접근 권한, 검색 범위, 대화 상태, 학생 발언 인용 및 출처 ID 검증, 기록 저장을 담당합니다. 질문 중복·단계 불일치에 대한 규칙 기반 보완도 남아 있습니다.
- **장애 대응**: Chroma 검색을 사용할 수 없으면 관계형 DB의 어휘 검색으로 대체합니다. OpenAI 생성 실패 시에는 기본 안내를 제공하며, 정상적인 AI 평가와 구분합니다.
- 개인 AI 대화는 HTTP, 친구 간 실시간 채팅은 WebSocket입니다. OpenAI 키는 백엔드에서만 사용합니다.

## 코드 탐색

```text
havruta-ai-tutor/
├── app/
│   ├── rag/
│   │   ├── retriever.py     # 인덱싱·벡터/어휘 검색
│   │   ├── reranker.py      # 검색 후보 재정렬
│   │   ├── tutor.py         # 프롬프트·OpenAI 호출·응답 검증
│   │   ├── dialogue.py      # 대화 의도·학습 단계·후속 질문 관리
│   │   └── curriculum.py    # 과목·학년·단원 카탈로그
│   ├── routers/            # 인증·학습·채팅 API
│   ├── services/           # 노트·퀴즈·실시간 연결
│   ├── models/             # 관계형 DB 모델
│   ├── schemas/            # 요청·응답 스키마
│   ├── database/           # 환경설정·DB 연결
│   ├── resources/          # 교육과정 카탈로그
│   └── utils/              # 인증 유틸리티
├── web/                    # React 화면·API 클라이언트
├── data/                   # Git에 포함된 수학 JSON 샘플 10건
├── scripts/                # 데이터 확인·카탈로그 생성·평가 도구
├── tests/                  # API·RAG·대화 상태 회귀 테스트
├── docs/                   # 설계·발표·배포 문서
├── main.py                 # FastAPI 진입점
├── .env.example            # 비밀 값 없는 환경설정 예시
├── requirements*.txt       # 기본·AI·개발 의존성
├── Dockerfile              # 백엔드 이미지
└── railway.json            # 백엔드 배포 설정
```

전체 흐름은 [프로젝트 구조](docs/PROJECT_STRUCTURE.md), 화면 코드는 [프런트엔드 안내](web/README.md)를 참고하세요.

## 로컬 실행

Python 3.11과 Node.js 22 환경을 기준으로 안내합니다. 아래는 **SQLite와 소량 샘플을 사용하는 개발 실행**이며, 운영 환경의 전체 과목 검색을 재현하지 않습니다.

### 1. 백엔드

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
test -f .env || cp .env.example .env
```

`.env`에서 `JWT_SECRET_KEY`를 임의의 충분히 긴 값으로 바꿉니다. OpenAI 대화를 사용하려면 `OPENAI_API_KEY`를 설정합니다. API 사용에는 별도 비용이 발생할 수 있습니다.

```bash
DATABASE_URL=sqlite:///./havruta-local.db RAG_PROVIDER=lexical REDIS_URL= \
  python -m uvicorn main:app --reload --reload-dir app
```

기본 API 문서: <http://127.0.0.1:8000/docs>. 키가 없으면 AI 생성 대신 기본 안내가 표시됩니다. Redis 없는 로컬 실행에서는 프로세스 내부 채팅 연결만 사용합니다.

### 2. 프런트엔드 — 새 터미널

```bash
cd web
npm ci
test -f .env || cp .env.example .env
npm run dev -- --host 127.0.0.1
```

브라우저에서 <http://127.0.0.1:5173>을 엽니다. 프런트엔드 환경변수에 OpenAI 키나 DB 비밀번호를 넣지 마세요.

### 3. 전체 RAG·운영 DB 사용

- MySQL 접속 정보는 루트 `.env`의 `DATABASE_URL` 또는 `DB_*` 항목으로 설정합니다. 위 SQLite 명령의 환경변수 덮어쓰기 없이 서버를 실행해야 합니다.
- ChromaDB 검색에는 `requirements-ai.txt`의 추가 패키지, 별도 Chroma 인덱스, 임베딩 모델 캐시가 필요합니다.
- 기본 설정은 임베딩 모델의 로컬 파일만 사용하므로, 패키지 설치만으로 모델과 학습 자료가 준비되지는 않습니다.
- `CHROMA_DIR`, `CHROMA_COLLECTION`, `EMBEDDING_MODEL`은 인덱스를 만든 환경과 일치시켜야 합니다.
- `chroma_db/`는 Git과 Docker 빌드에서 제외합니다. 운영 환경에서는 영속 볼륨에 별도로 준비합니다.

자세한 환경변수는 [.env.example](.env.example), MySQL·Redis·볼륨 설정은 [운영 설명서](docs/PROJECT_MANUAL.md)와 [Railway 배포 안내](docs/RAILWAY_DEPLOYMENT.md)를 참고하세요.

## 검증 명령

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests/test_assessment_repair.py tests/test_dialogue_state.py tests/test_learning_report.py
npm --prefix web run lint
npm --prefix web test
npm --prefix web run build
```

위 Python 명령은 평가 응답 복구·대화 상태·학습 진행의 **선별 회귀 검사**입니다. 전체 테스트, 실제 OpenAI 응답 품질 평가, 배포 환경 검증을 대신하지 않습니다. 외부 API를 사용하는 평가 도구는 비용·데이터 변경 여부를 확인한 후 별도로 실행하세요.

퀴즈 해설·재학습 회귀 검사는 `python -m pytest tests/test_quiz_review.py tests/test_session_relearning.py`로 실행합니다.
`cd web` 후 `node tests/browser-smoke.mjs`는 macOS Chrome의 격리된 프로필에서 실제 화면 흐름을 검사합니다.
이 브라우저 검사는 API 응답을 모의하므로 운영 계정 생성·데이터 변경·외부 AI 호출을 하지 않습니다. 다른 Chrome 경로는 `CHROME_PATH`로 지정합니다.

### 퀴즈 해설·중단 학습 저장 정책

- 새 퀴즈는 보기 순서를 섞은 뒤 선택지별 설명도 같은 순서로 저장합니다. 다른 문항에서 가져온 보기인지, 정답의 조건을 바꾼 보기인지를 근거로 설명하며 별도의 LLM 호출은 하지 않습니다.
- 기존 퀴즈는 저장된 정답·해설을 이용해 선택한 답과 비교합니다. 저장되지 않은 오답의 제작 의도를 추측하지 않습니다. 채점 전 문제 조회 API에는 정답과 해설을 포함하지 않습니다.
- 기존 MySQL DB를 업그레이드할 때는 배포 전 `python -m scripts.migrate_schema`가 필요합니다. Railway의 기존 pre-deploy 단계에서 실행되며, `quiz_questions.option_explanations`를 nullable JSON으로 추가합니다. 기존 행은 유지됩니다.
- ‘저장하고 나가기’는 `paused` 상태만 저장하며 완료 기록·정리노트를 만들지 않습니다. 전송한 대화와 AI 확인 근거는 유지됩니다. 보내지 않은 입력은 저장하지 않으며, 나갈 때 안내합니다.
- ‘이어서 학습’은 같은 세션의 질문·힌트·진행 상태를 복원합니다. ‘처음부터 다시’는 같은 학습 범위의 **새 세션**을 만들고 0/5부터 시작하며 원본 대화·완료 기록을 삭제하지 않습니다.
- AI 확인 2/5 같은 표시는 수집된 학습목표 확인 기록이지 이해도 40%나 검증된 학습 성과를 의미하지 않습니다.
- 남은 항목 중심으로 질문하며 4/5에서는 마지막 정리를 예고합니다. 검증된 5개 항목을 모두 채우면 마지막 답변·완료 기록·정리노트를 한 트랜잭션으로 저장하고 채팅을 종료합니다. 저장 실패 시 마지막 답변과 완료 처리도 함께 롤백됩니다.
- 완료 화면은 학생이 설명한 핵심과 다음 복습을 보여주며, 해당 정리노트 열기·같은 과목/학년/단원의 퀴즈로 이동·다른 단원 시작을 제공합니다. 퀴즈는 사용자가 문항 수를 선택하고 직접 생성합니다. 중간 수동 종료는 미확인 항목을 그대로 기록합니다.
- 완료 처리는 세션 행 잠금과 기존 기록 재사용으로 중복 생성을 방지합니다. 사용자가 삭제한 노트는 완료 요청 재시도로 복원하지 않습니다. 예전 5/5 미종료 세션은 이어서 학습을 누르면 마무리합니다.

### 입력창 위 학습 도움 버튼

- 입력창 위의 옵션은 ‘힌트’ 버튼 하나로 통일합니다. 정답 대신 단서·작은 질문을 요청하며, 입력 중인 답변은 제출하거나 지우지 않습니다.
- 버튼은 같은 메시지 API에 `help_action: "hint"`를 보냅니다. 이전 클라이언트·저장 기록과 직접 입력한 요청의 호환성을 위해 서버의 `example`·`simplify` 처리는 유지합니다. 도움 요청은 학생의 정답 제출이나 학습목표 체크 근거에서 제외하며, 기존 JSON 메타데이터에 저장하므로 별도 DB 변경은 필요하지 않습니다.
- 대화 횟수로 강제 전환하던 자동 힌트는 사용하지 않습니다. 버튼 선택이나 ‘모르겠어요’ 같은 명시적 도움 요청일 때만 힌트를 줍니다. 이전 대화 기록에 남아 있는 자동 힌트는 삭제하지 않습니다.
- 구조화 응답의 `answer_status`는 방금 질문에 대한 답변 자체의 잠정적 상태이며, `assessment`는 학습단계 확인입니다. 맞힌 계산이라도 단계 전체가 미완료일 수 있습니다. 학생 인용·실제 검색 출처로 확인된 `correct` 답변을 기초 `scaffold` 질문으로 되돌리려 하면 이유 연결 질문으로 바꿉니다. 이 신호만으로 학습목표를 체크하지 않습니다.
- JSON 스키마에는 기존 응답 필드와 `answer_status`, `missing_requirement`를 모두 필수로 전달합니다. 부분 확인 시 추가로 필요한 내용을 명시하고 질문의 요구와 맞지 않으면 최대 한 번 재검토합니다. 이전 저장 응답에 새 키가 없어도 Python 기본값으로 읽을 수 있습니다. 출력 형식 검증은 수학적 정확성 자체의 보장이 아닙니다.
- 예시와 쉬운 설명 요청은 힌트로 덮어쓰지 않습니다. AI 응답 실패 시 설명을 만들어낸 것처럼 표시하지 않고 이전 질문과 학습목표를 유지합니다.
- 응답 대기 중에는 버튼을 비활성화하고 중복 전송을 막습니다. 실패한 요청의 임시 메시지는 되돌리고 작성 중인 답변은 유지합니다.
- `python -m pytest tests/test_tutor_help_actions.py`와 `cd web && node tests/browser-smoke.mjs`로 서버 분류·학습 상태 보존·실제 버튼 흐름을 검사합니다. 브라우저 검사는 모의 API를 사용합니다.

## 데이터와 평가의 한계

- 전체 ChromaDB와 운영 사용자 기록은 이 저장소에 포함되지 않습니다. `data/`의 10건 샘플과 운영 자료를 혼동하지 마세요.
- 카탈로그에는 국어·영어·수학·사회·사회문화·과학·도덕·기술가정·정보를 다루지만, 모든 단원에 충분한 자료가 있다는 뜻은 아닙니다.
- 검색 점수는 문서 정렬용 내부 값이지 답변의 정답 확률이 아닙니다. 사용자 화면의 정확도 퍼센트로 표현하지 않습니다.
- 출처 ID·학생 발언 인용 검증만으로 답변의 사실성이나 추론 정확성을 보장할 수 없습니다.
- 재정렬·대화 상태 관리가 구현되어 있어도, 정확도 향상률이나 학습효과는 별도 비교 평가 없이는 주장하지 않습니다.

## 문서 바로가기

| 목적 | 문서 |
| --- | --- |
| 구조 파악 | [프로젝트 구조](docs/PROJECT_STRUCTURE.md) · [아키텍처](docs/ARCHITECTURE.md) |
| 사용·운영 | [프로젝트 설명서](docs/PROJECT_MANUAL.md) · [Railway 배포](docs/RAILWAY_DEPLOYMENT.md) |
| 구현 개선과 한계 | [검색·대화 개선 기록](docs/RAG_DIALOGUE_IMPROVEMENTS.md) |
| 발표 준비 | [발표 자료](docs/PRESENTATION_GUIDE.md) · [기술 질의응답](docs/PRESENTATION_QA_TECH.md) |
| 교수 피드백 대응 | [캡스톤 1주차 대응](docs/CAPSTONE_WEEK1_RESPONSE.md) |

상세 문서에는 작성 당시의 구현·검증 기록이 포함됩니다. 현재 동작을 확인할 때는 관련 코드와 설정도 함께 확인하세요.

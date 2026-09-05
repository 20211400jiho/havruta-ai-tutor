# Backend — FastAPI 서버

인증, 학습방, 하브루타 대화, RAG 검색, 노트·퀴즈·통계, 그룹 채팅을 담당합니다.

| 위치 | 역할 |
|---|---|
| `main.py` | 앱 생성, 라우터 연결, 시작·종료 처리 |
| `app/routers/` | REST API와 그룹 채팅 WebSocket 진입점 |
| `app/schemas/` | 요청 데이터 형식 검증 |
| `app/dependencies.py` | 현재 사용자 인증 및 DB 의존성 |
| `app/services/` | 튜터·RAG·노트·퀴즈 등 기능 로직 |
| `app/models/` | SQLAlchemy 테이블 모델 |
| `app/database/` | 환경변수, DB 엔진·세션 |
| `app/utils/security.py` | 비밀번호 해싱과 JWT |
| `app/resources/` | 교육과정 선택 카탈로그 |
| `app/paths.py` | 실행 위치에 의존하지 않는 경로 기준 |
| `data/` | 수학 RAG 샘플 JSON 10건 |
| `scripts/` | DB 마이그레이션, RAG 점검·평가, 스모크 테스트 |
| `tests/` | 격리된 SQLite 기반 API·튜터 테스트 |

저장소 루트에서 실행합니다. 기존 루트 `.venv`를 그대로 사용할 수 있습니다.

```bash
source .venv/bin/activate
cd backend
pip install -r requirements-dev.txt
test -f .env || cp .env.example .env
# .env에 개발용 DB 연결과 JWT 설정을 입력한 다음 실행
python -m scripts.migrate_schema
uvicorn main:app --reload --reload-dir app
```

`backend/.env`는 현재 작업 디렉터리와 관계없이 읽습니다. 실제 환경변수는 `.env`보다 우선합니다. `CHROMA_DIR=chroma_db`는 저장소 루트의 인덱스를 가리키며, 절대 경로를 지정하면 그대로 사용합니다. `.env`와 인덱스는 Git에 포함하지 않습니다.

`backend/`에서 `python -m pytest -q`로 테스트합니다. 독립 Docker 빌드는 저장소 루트에서 `docker build -t havruta-backend ./backend`로 실행합니다. Railway 설정은 [배포 문서](../docs/RAILWAY_DEPLOYMENT.md)를 참고하세요.

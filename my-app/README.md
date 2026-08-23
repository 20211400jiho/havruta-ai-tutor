# Havruta AI Tutor Frontend

FastAPI 백엔드와 연결되는 React/Vite 프런트엔드입니다. 화면에 표시되는 계정, 학습방, 세션, 노트, 퀴즈, 학습 통계는 REST API 또는 WebSocket에서 가져옵니다.

## 실행

```bash
npm install
cp .env.example .env
npm run dev -- --host 127.0.0.1
```

기본 주소는 <http://127.0.0.1:5173>입니다. 백엔드는 기본적으로 <http://127.0.0.1:8000>을 사용합니다.

## 환경변수

| 이름 | 설명 |
|---|---|
| `VITE_API_URL` | FastAPI 공개 또는 로컬 주소 |
| `VITE_WS_URL` | WebSocket 서버 주소. 생략하면 API 주소에서 계산 |

## 검증

```bash
npm run lint
npm run build
```

`dist/`와 `node_modules/`는 생성물이므로 Git에 포함하지 않습니다.

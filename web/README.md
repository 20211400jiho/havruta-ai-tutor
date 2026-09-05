# Havruta AI Tutor Frontend

FastAPI 백엔드와 연결되는 React/Vite 프런트엔드입니다. 화면에 표시되는 계정, 학습방, 세션, 노트, 퀴즈, 학습 통계는 REST API 또는 WebSocket에서 가져옵니다.

## 실행

저장소 루트에서 `cd web`로 이동한 뒤 실행합니다.

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

## 코드 탐색

| 위치 | 역할 |
|---|---|
| `src/main.jsx`, `src/App.jsx` | React 시작점과 화면 전환 |
| `src/*View.jsx`, `src/Home.jsx` | 로그인·학습·방·노트·퀴즈·통계 등 화면 |
| `src/Sidebar.jsx`, `src/CurriculumSelector.jsx` | 메뉴와 교육과정 선택 UI |
| `src/api.js` | REST 요청, JWT 전달, WebSocket 주소 구성 |
| `src/clientStorage.js` | 토큰·테마·진행 중 세션의 브라우저 저장 |
| `src/*.css`, `src/assets/`, `public/` | 스타일·이미지·정적 파일 |
| `Dockerfile`, `nginx.conf.template`, `railway.json` | 빌드와 배포 |

AI 개인 대화는 REST, 학습방의 사용자 간 채팅은 WebSocket을 사용합니다. OpenAI 키와 DB 접속 정보는 백엔드에서만 관리합니다. 독립 Docker 빌드는 저장소 루트에서 `docker build -t havruta-web ./web`로 실행합니다.

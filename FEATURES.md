# 기능 목록

- ✅ 구현 완료 (동작 확인 또는 테스트 통과)
- 🔁 구현했지만 실기기 확인 필요 (Windows/Linux 원격 등)

## 세션 · 폴더

| 기능 | 위치 | 상태 |
|---|---|---|
| 폴더 목록 (Claude + Codex 병합) | `agent/server.py` `/folders` | ✅ |
| 폴더별 세션 목록 | 동일 | ✅ |
| 새 Claude 세션 (`--remote-control`, bridge URL) | `/launch` + `agent/launcher_posix.py` | ✅ |
| Windows ConPTY 실행 | `agent/launcher_win.py` | 🔁 |
| 이어가기 / 포크 / 이미 실행 중이면 붙기 | 동일 | ✅ |
| 큰 transcript 이어가기 타임아웃 | 동일 | ✅ |
| 로그인 만료·조직 차단 즉시 실패 | 동일 | ✅ |
| 세션 중지 / 삭제 / 폴더 삭제 | 동일 | ✅ |
| 폴더 탐색기 · 새 폴더 | 동일 | ✅ |
| 대화 미리보기 | 동일 | ✅ |
| 폴더 내 검색 / 전체 머신 검색 | 동일 | ✅ |
| 세션 이름 · 계정 기록 | `.remocon-session-*.json` (기존 파일 자동 승계) | ✅ |

## 에이전트 · 모델

| 기능 | 위치 | 상태 |
|---|---|---|
| Codex 세션 (app-server, 데스크톱 앱 연동) | `agent/codex.py` | ✅ |
| Codex 가져오기 중복 숨김 | `REMOCON_SHOW_IMPORTED_CODEX` (예전 변수도 인식) | ✅ |
| Codex 프로젝트 목록 | 동일 | ✅ |
| 이미지 첨부 | `~/.remocon/uploads` | ✅ |
| 모델 · effort 선택, 기본값 저장 | 동일 | ✅ |
| 되감기 · 에이전트 전환 (handoff) | 동일 | ✅ |
| 터미널 핸드오프 (브라우저 쪽 PC에 창 열기) | `host/terminal.py`: macOS Terminal(`REMOCON_TERMINAL_APP`), Windows Terminal/cmd, Linux 7종 | ✅ |
| 매니저(오케스트레이션) 세션 | `~/.remocon/manager` | ✅ |
| 오케스트레이션 스킬 | `skills/remocon-orchestrate` | ✅ |

## 계정

| 기능 | 위치 | 상태 |
|---|---|---|
| 머신별 다중 로그인, 활성 계정 전환 | `agent/accounts.py` (활성 계정 파일 자동 승계) | ✅ |
| 웹에서 로그인 (OAuth URL + 코드 붙여넣기, 조직 선택) | 동일 | ✅ |
| 계정 생성 / 삭제 / 로그아웃 | 동일 | ✅ |
| 예전 계정 세션을 현재 계정으로 옮기기 | 동일 | ✅ |

## 머신 · 배포 · 상주

| 기능 | 위치 | 상태 |
|---|---|---|
| 머신 등록 / 이름 변경 / 제거 | 동일 | ✅ |
| enroll 스크립트 (Windows / Linux) | `hub/enroll.py` + **macOS** 추가, 키 종류 ed25519/ecdsa/rsa | ✅ |
| SSH 원격 배포 (Windows / Linux) | `remocon deploy` (`hub/deploy.py`) + **macOS 대상** | 🔁 |
| 원격 자동 시작 | 원격에서 `remocon service install agent` 실행 — 수동 설치와 같은 코드 | 🔁 |
| Windows 서비스 (pywin32) | `host/winservice.py`, `--winservice` | 🔁 |
| SSH 터널 자동 재연결 | 허브 프로세스 안의 `TunnelManager`, 머신 추가·삭제가 바로 반영, 재시도 간격 점점 늘림 | ✅ |
| 스킬 자동 동기화 | 허브 안에서 `skillSync.intervalMin` 주기 + `remocon skills-sync` | ✅ |
| 허브 상주 | macOS launchd / Linux systemd / Windows 작업 스케줄러 (`remocon service install up`) | ✅ |

## UI

| 기능 | 위치 | 상태 |
|---|---|---|
| 단일 HTML (CSS·JS 인라인) | `web/index.html` + `assets/app.css` + `assets/app.js` | ✅ |
| 한/영 토글, 고정 폴더 · 즐겨찾기 | `remocon.*` (같은 origin이면 자동 이전) | ✅ |
| 모바일 레이아웃 | `docs/DESIGN.md` 기준 디자인 | ✅ |

## 편의 기능

- `remocon` CLI 하나로 모든 역할 실행: `up` / `hub` / `agent` / `deploy` / `service` / `doctor` / `open` / `init --import`
- `remocon doctor`: python·claude·codex·ssh·키·포트·서비스 상태를 한 번에 점검
- `remocon init --import csm.config.json`: 기존 csm 설정(비밀키, 머신, 기본값) 그대로 이전 — 원격 에이전트 재배포 불필요
- 설정·로그·업로드를 모든 OS에서 `~/.remocon` 한 곳에 모음
- `GET /api/status`: 버전 + 터널 상태 (UI 상태 표시용)
- 정적 파일 경로 탈출 차단

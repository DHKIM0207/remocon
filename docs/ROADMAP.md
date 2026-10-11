# 로드맵

## 0.1 — 뼈대 (현재)

- [x] 기본 기능 구현, 패키지 구조 정리 (`agent/`, `hub/`, `host/`)
- [x] `remocon` CLI, `pip install` 가능한 패키지
- [x] 허브·터널·스킬 동기화를 한 프로세스로 합침
- [x] macOS / Linux / Windows 자동 시작 (`remocon service`)
- [x] UI를 HTML / CSS / JS 파일로 분리
- [ ] 실기기 확인: Windows 원격 배포, Linux 원격 배포, macOS 원격 배포
- [ ] Windows·Linux에서 허브(`remocon up`) 실행 확인

## 0.2 — 디자인 개편

기준: [DESIGN.md](DESIGN.md) (원본 레퍼런스: [design/spotify-reference.md](design/spotify-reference.md))

- [x] `web/assets/tokens.css`: DESIGN.md의 색·그림자·모서리·간격·글꼴 토큰 (어두운 테마만)
- [x] 버튼·입력·카드·대화상자를 알약/원형 형태와 무채색 표면으로 교체, 그린은 기능에만
- [ ] `app.js`를 ES 모듈로 나누기: `api.js`, `i18n.js`, `sidebar.js`, `sessions.js`,
      `accounts.js`, `machines.js`, `dialogs.js` (인라인 `onclick` → 이벤트 위임)
- [ ] 레이아웃: 머신 → 폴더 → 세션 3단 구조, 모바일은 단계별 화면 전환
- [x] 세션 카드: 실행 중 표시, 에이전트, 모델, 계정, 마지막 활동을 한 줄 배지로
- [x] 머신 상태 표시: 머신별 연결 점(터널 상태) + 하단 상태 바(진행 중 작업, 머신·터널 수, 버전)
- [x] 모바일: 하단 탭 바(폴더/세션/검색/계정/설정), 헤더 아이콘화
- [x] 이모지 → 단색 SVG 아이콘 (`assets/icons.js`), 세션 카드당 그린 버튼 1개
- [ ] 에이전트 버전, 마지막 응답 시각 표시
- [ ] 명령 팔레트 (⌘K / Ctrl+K): 폴더·세션 바로 찾기, 새 세션
- [ ] 접근성: 키보드 이동, 포커스 표시, 대비

## 0.3 — 편의성

- [ ] 머신 추가 마법사: OS 선택 → enroll 스크립트 복사 → 배포 진행 로그를 실시간 표시
- [ ] 배포 로그·에이전트 로그를 UI에서 보기
- [ ] 에이전트 버전이 허브와 다르면 "업데이트" 버튼 (재배포)
- [ ] 세션 상태 실시간 갱신 (SSE): 폴링 대신 푸시
- [ ] 알림: 세션 종료·실패 시 브라우저 알림
- [ ] 허브 접속 보호: 허브를 LAN에 열 때 로그인 토큰 (현재는 127.0.0.1 전용)
- [ ] `remocon update`: 허브 업데이트 후 모든 에이전트 재배포

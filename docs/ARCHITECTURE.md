# 구조

```
브라우저 ──HTTP──▶ hub (127.0.0.1:8765)
                    ├─ 웹 UI (web/)
                    ├─ 머신 레지스트리 (~/.remocon/config.json)
                    ├─ /api/m/<id>/… 프록시 (머신별 bearer 비밀키를 붙임)
                    ├─ TunnelManager ──ssh -L──▶ 원격 agent (각 머신 127.0.0.1:8766)
                    └─ skill sync 루프
                   agent (로컬, 127.0.0.1:8766)
                    ├─ ~/.claude 읽기: 폴더·세션·검색·미리보기
                    ├─ ~/.codex 읽기 + codex app-server
                    ├─ launcher (PTY/ConPTY) → claude --remote-control
                    └─ 계정(CLAUDE_CONFIG_DIR), 스킬, 업로드, 터미널 열기
```

브라우저에는 비밀키가 가지 않습니다. 허브만 각 에이전트의 비밀키를 갖고, 에이전트는
`127.0.0.1`에만 바인드합니다. 원격 에이전트에는 SSH 터널로만 접근합니다.

## 소스 배치

```
src/remocon/
  cli.py            remocon 명령 (up/hub/agent/init/service/deploy/skills-sync/open/doctor)
  paths.py          ~/.remocon 경로, 예전 .csm-* 파일 승계
  config.py         설정 로드·생성·원자적 저장·csm 설정 가져오기
  agent/
    server.py       에이전트 HTTP API (라우트 목록은 FEATURES.md)
    claude_store.py Claude 세션 저장소 읽기
    codex.py        Codex rollout 읽기 + app-server
    accounts.py     다중 로그인
    skills.py       스킬 파일 목록·읽기·쓰기
    launcher_posix.py / launcher_win.py   세션 하나를 붙잡는 독립 스크립트
  hub/
    server.py       UI 호스트 + 레지스트리 + 프록시 + 머신 관리
    tunnels.py      SSH 터널 관리 (허브 프로세스 안)
    deploy.py       SSH 원격 배포
    enroll.py       새 머신용 1회성 스크립트 (Windows/Linux/macOS)
    skillsync.py    스킬 수렴 (mtime 기준 최신본)
  host/
    proc.py         분리 실행(detached) 옵션, pythonw
    terminal.py     OS별 터미널 창 열기
    service.py      launchd / systemd / 작업 스케줄러 등록
    winservice.py   pywin32 서비스 래퍼 (독립 스크립트)
  web/
    index.html, assets/app.css, assets/app.js
```

## 역할

| 역할 | 명령 | 어디서 |
|---|---|---|
| `up` | `remocon up` | 브라우저를 여는 메인 PC (허브 + 로컬 에이전트) |
| `hub` | `remocon hub` | 허브만 따로 둘 때 |
| `agent` | `remocon agent` | 그 외 모든 머신 (`remocon deploy`가 설치) |

`remocon service install <role>`이 OS에 맞는 자동 시작을 등록합니다. `remocon deploy`는
원격 머신에서 이 명령을 그대로 실행하므로, 손으로 설치한 머신과 배포한 머신이 같은
상태가 됩니다.

## 크로스플랫폼 원칙

- 서버 쪽은 표준 라이브러리만 씁니다. Windows에서만 `pywinpty`가 필요하고, 서비스로
  돌리려면 `pywin32`를 추가합니다.
- 경로는 모든 OS에서 `~/.remocon` 하나로 통일합니다 (`REMOCON_HOME`으로 바꿀 수 있음).
- OS별 분기는 `host/` 아래에만 둡니다. agent·hub 코드는 `host`의 함수를 부릅니다.
- 원격 명령은 OpenSSH만 씁니다. Windows 10 이상, macOS, Linux에 기본으로 들어 있습니다.

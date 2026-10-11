# 📡 Remocon

여러 컴퓨터에 흩어진 **Claude Code**와 **OpenAI Codex** 세션을 브라우저 탭 하나에서
다루는 자체 호스팅 리모컨입니다. Windows, macOS, Linux 어디서든 허브를 띄우고, SSH로
닿는 어느 머신이든 에이전트로 붙일 수 있습니다.

## 빠른 시작

Python 3.10 이상이 필요합니다.

```bash
pip install -e .
```

```bash
remocon up --open
```

브라우저에서 `http://127.0.0.1:8765`가 열립니다. 로그인할 때 자동으로 시작되게 하려면:

```bash
remocon service install up
```

설치가 잘 되었는지 점검하려면:

```bash
remocon doctor
```

## 다른 머신 붙이기

1. 웹 UI의 **＋ 머신**에서 대상 OS의 enroll 스크립트를 복사해 그 머신에서 한 번 실행합니다
   (SSH 서버를 켜고 허브의 공개키를 등록합니다).
2. 같은 창에서 호스트와 SSH 사용자를 입력하면 배포가 시작됩니다. CLI로도 할 수 있습니다:

```bash
remocon deploy workpc 192.168.1.50 alice
```

배포는 코드를 `~/.remocon/app`에 올리고, 원격에서 `remocon service install agent`를 실행해
자동 시작까지 등록합니다. 허브는 설정이 바뀐 것을 보고 SSH 터널을 직접 엽니다.

## 기존 csm 설정 가져오기

```bash
remocon init --import /path/to/csm.config.json
```

비밀키와 머신 목록을 그대로 가져오므로 원격 에이전트는 기존 것과 계속 통신합니다.
세션 이름, 세션별 계정, 활성 계정 기록(`~/.claude/.csm-*`)은 처음 읽을 때 자동으로 복사됩니다.
기존 `com.csm.*` launchd 작업은 포트가 겹치니 먼저 내려 주세요.

## 명령

| 명령 | 설명 |
|---|---|
| `remocon up [--open]` | 허브 + 로컬 에이전트 |
| `remocon hub` / `remocon agent` | 하나만 실행 |
| `remocon service install\|uninstall\|status [up\|hub\|agent]` | 자동 시작 (launchd / systemd / 작업 스케줄러) |
| `remocon deploy ID HOST USER [--ssh-port N] [--python EXE] [--winservice]` | 원격 에이전트 설치·갱신 |
| `remocon skills-sync` | `~/.claude/skills`를 모든 머신에서 최신본으로 맞추기 |
| `remocon init [--import F] [--force]` | 설정 파일 만들기 |
| `remocon open` | 웹 UI 열기 |
| `remocon doctor` | 환경 점검 |

## 파일 위치

모든 OS에서 `~/.remocon` 하나에 모입니다 (`REMOCON_HOME`으로 변경 가능).

```
~/.remocon/config.json   비밀키, 포트, 머신 목록, UI 설정
~/.remocon/logs/         허브·에이전트·배포·세션 실행 로그
~/.remocon/uploads/      Codex에 첨부한 이미지
~/.remocon/manager/      매니저 세션 폴더
~/.remocon/app/          원격 배포된 코드
```

## 개발

```bash
python -m pytest
```

기능 목록은 [FEATURES.md](FEATURES.md), 구조는 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), 앞으로의 계획(디자인 개편 포함)은
[docs/ROADMAP.md](docs/ROADMAP.md)에 있습니다.

## 라이선스

MIT. [LICENSE](LICENSE)를 참고하세요.

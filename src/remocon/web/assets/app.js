// One-time carry-over of the legacy csm.* per-browser state (pins,
// starred folders/sessions, language) when the hub keeps the same origin.
try{
  if(!localStorage.getItem("remocon.migrated")){
    for(let i=0;i<localStorage.length;i++){
      const k=localStorage.key(i);
      if(k&&k.startsWith("csm.")&&localStorage.getItem("remocon."+k.slice(4))===null)
        localStorage.setItem("remocon."+k.slice(4), localStorage.getItem(k));
    }
    localStorage.setItem("remocon.migrated","1");
  }
}catch(e){}

// ---- i18n (ko/en). Korean source strings are the keys; t() falls back to ko. ----
let LANG=localStorage.getItem("remocon.lang")||"en";  // default: English (toggle persists)
const EN={
"🎯 매니저 세션 열기":"🎯 Open manager session",
"전 머신을 총괄하는 매니저 세션 열기":"Open the manager session (oversees all machines)",
"초기화 — 세션 종료 후 새로 시작":"Reset — end the session and start fresh",
"삭제 — 매니저 세션 기록 삭제":"Delete — remove the manager session history",
"노드 / 폴더":"Nodes / Folders","＋ 머신":"＋ Machine","← 노드":"← Nodes",
"머신 추가":"Add machine",
"새 컴퓨터에서 1회 실행 (SSH키·OpenSSH·Python 준비):":"Run once on the new computer (sets up SSH key · OpenSSH · Python):",
"🪟 Windows — 관리자 PowerShell:":"🪟 Windows — elevated PowerShell:",
"🐧 Linux — 터미널 (sudo 비번 입력):":"🐧 Linux — terminal (sudo will prompt):",
"그 다음 아래 정보로 등록 → 자동 배포 (OS 자동 감지):":"Then register with the details below → auto-deploy (OS auto-detected):",
"닉네임":"Nickname","호스트/IP":"Host/IP","SSH 유저":"SSH user","SSH 포트":"SSH port",
"예: 작업용 데스크탑":"e.g. work desktop","예: 192.168.1.50 또는 tailscale IP":"e.g. 192.168.1.50 or tailscale IP","예: alice":"e.g. alice",
"취소":"Cancel","등록 + 배포":"Register + deploy","클릭해서 복사":"Click to copy",
"폴더 추가":"Add folder","또는 경로 직접 입력 후 Enter":"or type a path and press Enter","추가":"Add",
"선택:":"Selected:","＋ 이 폴더 추가":"＋ Add this folder","⬆ 상위":"⬆ Up","🏠 홈":"🏠 Home","드라이브":"Drives",
"하위 폴더 없음":"No subfolders","이 폴더에 파일이 없습니다":"No files in this folder","세션 있음":"Has sessions",
"대화 미리보기":"Conversation preview","닫기":"Close","이어가기":"Resume","보내기":"Send",
"이미지 첨부 (또는 입력창에 붙여넣기)":"Attach image (or paste into the input)",
"🟢 Codex 메시지… (이미지 붙여넣기 가능, Enter 전송)":"🟢 Message Codex… (paste images, Enter to send)",
"🟢 Codex 응답 대기 중… (최대 몇 분)":"🟢 Waiting for Codex… (may take minutes)",
"새 세션 — 에이전트 선택":"New session — choose agent",
"＋ 새 세션":"＋ New session","🔎 이 폴더에서 세션 검색 (제목·대화 내용)":"🔎 Search sessions in this folder (title · content)",
"불러오는 중…":"Loading…","🔎 검색 중…":"🔎 Searching…","검색 결과 없음":"No results",
"세션이 없습니다. ＋ 새 세션으로 시작하세요.":"No sessions yet. Start one with ＋ New session.",
"개 메시지":" messages","처리 중…":"Working…",
"🟢 Codex 세션 생성 중… 응답까지 최대 1~2분 (앱에도 뜹니다)":"🟢 Creating Codex session… up to 1-2 min for the reply (also appears in the app)","모델":"Model","← 뒤로":"← Back","세션 시작":"Start session","새 Codex 세션":"New Codex session","새 Claude 세션":"New Claude session",
"🟢 Codex 세션이 앱에 뜨려면, 그 폴더를 Codex 데스크톱 앱에서도 프로젝트로 추가해야 합니다. 아래 목록엔 Codex 세션이 있는 폴더만 뜨고, Codex 세션이 없는 폴더는 직접 고르세요.":"🟢 For a Codex session to show in the app, add that folder as a project in the Codex desktop app too. The list below shows only folders that already have Codex sessions; pick a folder without one yourself.","Codex 세션 있음 (앱에 표시됨)":"Has Codex sessions (shown in the app)","세션":"sessions","Codex 프로젝트 (클릭해서 추가)":"Codex projects (click to add)","🟢 새 Codex 세션 — 첫 메시지:":"🟢 New Codex session — first message:",
"Codex 세션 생성 중… (앱에도 뜹니다)":"Creating Codex session… (also appears in the app)",
"Codex 세션 생성됨":"Codex session created","⌨ 터미널":"⌨ Terminal","📋 터미널 명령 복사됨 — 터미널에 붙여넣으세요":"📋 Terminal command copied — paste it into your terminal","아래 명령을 복사해 터미널에서 실행:":"Copy this command and run it in your terminal:","터미널에서 이어가기 (SSH 명령 복사)":"Continue in a terminal (copy SSH command)","터미널에서 인터랙티브로 이어가기":"Continue interactively in a terminal","열기":"Open","👁 미리보기":"👁 Preview","Fork":"Fork","삭제":"Delete","■ 종료":"■ Stop","💬 대화":"💬 Chat",
"📌 고정":"📌 Pin","📌 고정됨":"📌 Pinned","상단 고정":"Pin to top","상단 고정 해제":"Unpin from top",
"폴더 없음 — ＋로 추가":"No folders — add with ＋",
 "🔎 폴더 검색 · Enter로 전체 세션 검색":"🔎 Filter folders · Enter to search all sessions","지우기":"Clear","🔎 전체 세션 검색":"🔎 Search all sessions","닫기":"Close","검색 중…":"Searching…","머신":"machines","건":"","일부만":"partial","결과가 많아 일부만 표시합니다":"Too many matches — showing the most recent","검색할 수 있는 머신이 없습니다":"No reachable machines","종료 중…":"stopping…","이 머신 새로고침":"Refresh this machine","🟧 이미 실행 중인 세션에 연결하는 중…":"🟧 Attaching to the session that is already running…","🟧 큰 대화를 불러오는 중… ":"🟧 Loading a large conversation… ","초":"s","이 머신이 쓰는 계정":"Account this machine uses","이 세션의 계정":"This session's account","이 세션은 다른 계정으로 실행됐습니다":"Started under a different account","종료하고 현재 계정으로 다시 열기":"Stop and reopen under the current account","(으)로 전환":"","이 세션을 종료하고 현재 계정으로 다시 열까요?":"Stop this session and reopen it under the current account?","실행 중인 이 세션을 종료할까요?":"Stop this running session?","종료 실패: ":"Could not stop: ","클로드 계정":"Claude accounts","클로드 계정 전환":"Switch Claude account","로그인 안 됨":"not signed in","사용 중":"in use","사용":"Use","로그인":"Sign in","다시 로그인":"Sign in again","머신 기본":"machine default","계정 없음":"No accounts","새 계정 이름":"New account name","머신":"Machine","로그인할 조직":"Organization to sign in to","원격 제어 막힘":"Remote Control blocked","이 조직은 원격 제어를 막아 두어 이 매니저로 세션을 열 수 없습니다":"This organization blocks Remote Control, so this manager cannot open sessions with it","로그인 대기가 끊겼습니다 — 새 주소를 받아 다시 로그인해 주세요.":"That sign-in is no longer waiting — get a new link and sign in again.","로그인 대기가 끝났습니다 (시간 초과 또는 에이전트 재시작) — 새 주소를 받아 다시 로그인해 주세요.":"That sign-in expired (timeout or agent restart) — get a new link and sign in again.","코드가 틀렸거나 만료됐습니다. 로그인 주소를 다시 받아 주세요.":"The code was wrong or has expired. Get a new sign-in link.","로그인 주소 받기":"Get sign-in link","브라우저에서 선택":"Choose in the browser","조직 ID 직접 입력…":"Enter organization ID…","지금 조직: ":"Current organization: ","다시 로그인 / 조직 변경":"Sign in again / change org","처음 쓰는 조직은 '브라우저에서 선택'으로 한 번 로그인하면 다음부터 목록에 나옵니다.":"Sign in once with 'Choose in the browser' and that organization joins this list.","＋ 추가":"＋ Add","이름을 입력하세요":"Enter a name","만드는 중…":"Creating…","계정 전환됨: ":"Switched to: ","이 계정을 삭제할까요? 세션 기록은 공유라 지워지지 않습니다.":"Delete this account? Session history is shared and is not deleted.","로그인 주소를 받는 중…":"Getting the sign-in link…","아래 주소를 열어 로그인한 뒤, 받은 코드를 붙여넣으세요.":"Open the link, sign in, then paste the code you get back.","여기에 코드 붙여넣기":"Paste the code here","확인":"Submit","브라우저에서 로그인한 뒤 코드를 붙여넣으세요":"Sign in in the browser, then paste the code","코드를 붙여넣으세요":"Paste the code","확인 중…":"Checking…","로그인 완료":"Signed in","모두 펼치기":"Expand all","모두 접기":"Collapse all","노드의 폴더를 고르세요.":"Pick a folder.","📌 추가됨":"📌 added","더보기":"Show more","접기":"Show less",
"이 폴더 세션 전체 삭제":"Delete all sessions in this folder","목록에서 제거(핀 해제)":"Remove from list (unpin)","머신 제거":"Remove machine",
"에이전트 없음":"no agent","개":"","　":" ",
"이 세션을 삭제할까요? 되돌릴 수 없습니다.":"Delete this session? This cannot be undone.",
"실행 중인 세션은 먼저 '종료' 후 삭제하세요":"Stop the running session before deleting",
"삭제됨":"Deleted","삭제 거부: ":"Delete refused: ","오류: ":"Error: ","실패: ":"Failed: ",
"폴더 추가됨":"Folder added","이름 변경됨":"Renamed","제거됨":"Removed",
"매니저 세션 여는 중… (전 머신 총괄)":"Opening manager session…","매니저 세션 초기화 중…":"Resetting manager session…",
"매니저 세션 초기화됨":"Manager session reset","매니저 세션(기존) 열림":"Manager session (existing) opened","매니저 세션 시작됨":"Manager session started",
"현재 매니저 세션을 종료하고 새 세션으로 초기화할까요?":"End the current manager session and start a fresh one?",
"매니저 세션을 삭제할까요? (대화 기록 삭제)":"Delete the manager session? (clears its history)",
"매니저 세션 삭제 중…":"Deleting manager session…","매니저 세션 삭제됨":"Manager session deleted",
"이미지 업로드 중…":"Uploading image…","업로드 실패: ":"Upload failed: ","이미지 첨부됨":"Image attached",
"(이미지)":"(image)","첨부한 이미지를 봐줘":"Please look at the attached image",
"🧑 나":"🧑 You",
"터미널":"Terminal","터미널 세션 여는 중…":"Opening terminal session…",
"🖥 이 맥에 터미널 창이 열렸습니다 (원격은 SSH)":"🖥 Terminal window opened on this mac (remote via SSH)",
"명령을 클립보드에 복사했습니다 — 터미널에 붙여넣으세요":"Command copied — paste it into your terminal","모델 (Codex)":"Model (Codex)","기본값 (config.toml)":"default (config.toml)",
"터미널에서 인터랙티브로 이어가기 (SSH)":"Continue interactively in your terminal (SSH)",
"복사됨! 터미널에 붙여넣으세요:":"Copied! Paste into your terminal:",
"아래 명령을 복사해 터미널에서 실행:":"Copy this command and run it in your terminal:",
"모델 (Claude)":"Model (Claude)","기본값":"Default","모델: 머신 설정":"Model: machine default",
 "노력: 머신 설정":"Effort: machine default","기본 노력 저장됨: ":"Default effort saved: ","노력":"Effort",
"기본 모델 저장됨: ":"Default model saved: ","머신 설정":"machine default",
"🟢 Codex로 전환":"🟢 Switch to Codex","🟧 Claude로 전환":"🟧 Switch to Claude",
"여기서 되감아 새 세션으로 이어가기":"Rewind to here — branch a new session from this point",
"이 시점으로 되감아 새 세션을 만듭니다. 진행할까요?":"Rewind to this point and start a NEW session from here. Proceed?",
"이 대화를 다른 모델의 새 세션으로 이어갑니다. 진행할까요?":"Continue this conversation in a NEW session of the other agent. Proceed?",
"되감는 중… (선택 시점까지 맥락 이전 + 새 세션)":"Rewinding… (carrying context up to here into a new session)",
"모델 전환 중… (맥락 이전 + 새 세션)":"Switching model… (carrying context into a new session)",
"완료 — 새 Codex 세션":"Done — new Codex session","완료 — 새 Claude 세션 (새 탭)":"Done — new Claude session (new tab)",
"🟢 새 Codex 세션 — 첫 메시지:":"🟢 New Codex session — first message:",
"Codex 세션 생성 중… (응답까지 잠시)":"Starting Codex session… (takes a moment)","Codex 세션 생성됨":"Codex session started",
"이 폴더의 파일":"Files in this folder","개 중 ":" total, showing ","개 표시":"","총 ":"",
"실행 중인 세션은":"Stop running sessions first",
"터미널 창을 열었습니다 (원격은 SSH)":"Opened a terminal window (remote via SSH)",
"매니저 세션":"Manager session","머신 · 폴더":"Machines · Folders",
"폴더 검색 · Enter로 전체 세션 검색":"Filter folders · Enter to search all sessions",
"폴더를 고르세요":"Pick a folder",
"왼쪽에서 머신의 폴더를 고르면 세션이 보입니다. 폴더 추가는 머신 옆 ＋, 새 세션은 폴더 안에서.":"Pick a machine's folder on the left to see its sessions. Add folders with ＋ next to a machine; start sessions inside a folder.",
"폴더":"Folders","세션":"Sessions","검색":"Search","계정":"Account","설정":"Settings",
"Windows — 관리자 PowerShell":"Windows — elevated PowerShell","Linux — 터미널 (sudo 비번 입력)":"Linux — terminal (sudo will prompt)",
"macOS — 터미널":"macOS — terminal",
"Codex로 전환":"Switch to Codex","Claude로 전환":"Switch to Claude","포크":"Fork",
"Codex에게 메시지… (이미지 붙여넣기 가능, Enter 전송)":"Message Codex… (paste images, Enter to send)",
"새 세션":"New session","이 폴더 추가":"Add this folder","확인":"OK",
"Codex 세션이 앱에 뜨려면 그 폴더를 Codex 데스크톱 앱에서도 프로젝트로 추가해야 합니다. 아래 목록엔 Codex 세션이 있는 폴더만 뜨고, 없는 폴더는 직접 고르세요.":"For Codex sessions to show up in the Codex desktop app, add the folder there as a project too. The list below only has folders that already have Codex sessions; pick any other folder yourself.",
"전체 새로고침":"Refresh everything","기본 모델 (새 세션·이어가기에 적용)":"Default model (new sessions and resumes)",
"기본 노력 (새 세션·이어가기에 적용)":"Default effort (new sessions and resumes)",
"이 PC에 폴더 추가":"Add a folder on this machine","이름 변경":"Rename","이 머신 새로고침":"Refresh this machine",
"새 세션 시작":"New session","이 폴더 새로고침":"Refresh this folder",
"이 폴더에서 세션 검색 (제목·대화 내용)":"Search sessions in this folder (title · content)",
"전체 세션 검색":"Search all sessions","모두 펼치기":"Expand all","모두 접기":"Collapse all",
"열기":"Open","미리보기":"Preview","대화":"Chat","터미널":"Terminal","종료":"Stop","삭제":"Delete",
"고정":"Pin","고정 해제":"Unpin","터미널 명령 복사":"Copy terminal command",
"메시지":"messages","추가됨":"added","상위":"Up","홈":"Home","새 폴더":"New folder",
"Codex 프로젝트 (클릭해서 추가)":"Codex projects (click to add)",
"사용":"Use","사용 중":"In use","로그인":"Sign in","다시 로그인 / 조직 변경":"Sign in again / change org",
"로그인 안 됨":"Not signed in","머신 기본":"Machine default","계정 없음":"No accounts",
"에이전트":"agent","오프라인":"offline","연결 중":"connecting","연결됨":"connected","끊김":"down",
"머신 연결":"machines","터널":"tunnels","작업 중":"Working",
"새 Claude 세션":"New Claude session","새 Codex 세션":"New Codex session",
"레지스트리 로드 실패":"Couldn't load machines","에이전트 미설치":"agent not installed",
"이 머신이 쓰는 계정":"Account this machine uses","Codex 세션 있음 (앱에 표시됨)":"Has Codex sessions (shown in the app)"
};
const t=s=>LANG==="en"?(EN[s]!==undefined?EN[s]:s):s;
function applyStatic(){
  document.querySelectorAll("[data-i18n]").forEach(e=>e.textContent=t(e.dataset.i18n));
  document.querySelectorAll("[data-i18n-ph]").forEach(e=>e.placeholder=t(e.dataset.i18nPh));
  document.querySelectorAll("[data-i18n-title]").forEach(e=>e.title=t(e.dataset.i18nTitle));
  const lb=document.getElementById("langbtn"); if(lb) lb.textContent=LANG==="ko"?"KO":"EN";
  document.documentElement.lang=LANG;
}
let DEFMODEL="", DEFEFFORT="high";
// Codex sessions are hidden unless ui.showCodex is set: listing them makes the
// agent read every rollout on the machine on every folder click, and here those
// are mostly one-shot `codex exec` calls (482 of 518), not conversations.
let SHOW_CODEX = false;
const cx = () => SHOW_CODEX ? "" : "codex=0";
const withCx = path => { const q = cx(); return q ? path + (path.includes("?") ? "&" : "?") + q : path; };   // effort: claude's own default runs hot for long sessions
function modelOpts(sel,cur){
  if(!sel) return;
  const d=t("기본값")+(DEFMODEL?` (${DEFMODEL})`:"");
  sel.innerHTML=`<option value="">${d}</option><option value="fable">Fable 5.1</option><option value="opus">Opus 5.5</option><option value="sonnet">Sonnet 4.6</option><option value="haiku">Haiku 4.5</option>`;
  sel.value=cur||"";
}
const EFFORTS=["low","medium","high","xhigh","max"];
function effortOpts(sel, prefix){
  if(!sel) return;
  sel.innerHTML=`<option value="">${prefix}${t("노력: 머신 설정")}</option>`+
    EFFORTS.map(e=>`<option value="${e}">${prefix}${e}</option>`).join("");
}
async function setDefaultEffort(v){
  DEFEFFORT=v;
  try{ await fetch("/api/prefs",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({defaultEffort:v})});
       toast(t("기본 노력 저장됨: ")+(v||t("머신 설정")));
  }catch(e){ toast(t("오류: ")+e.message); }
  fillModelSelects();
}
function fillModelSelects(){
  const he=document.getElementById("defeffort");
  if(he){ effortOpts(he,""); he.value=DEFEFFORT; }
  effortOpts(document.getElementById("ag-effort"),"");
  effortOpts(document.getElementById("tx-effort"),"");
  const ae=document.getElementById("ag-effort"); if(ae) ae.value=DEFEFFORT;
  const te=document.getElementById("tx-effort"); if(te) te.value=DEFEFFORT;
  const h=document.getElementById("defmodel");
  if(h){ h.innerHTML=`<option value="">${t("모델: 머신 설정")}</option><option value="fable">Fable 5.1</option><option value="opus">Opus 5.5</option><option value="sonnet">Sonnet 4.6</option><option value="haiku">Haiku 4.5</option>`; h.value=DEFMODEL; }
  modelOpts(document.getElementById("ag-model"));
  modelOpts(document.getElementById("tx-model"));
}
async function saveDefModel(v){
  DEFMODEL=v;
  try{await fetch("/api/prefs",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({defaultModel:v})});toast(t("기본 모델 저장됨: ")+(v||t("머신 설정")));}catch(e){toast(t("오류: ")+e.message);}
  fillModelSelects();
}
async function initLang(){
  try{const r=await(await fetch("/api/prefs")).json();
    if(r.ui&&r.ui.lang){LANG=r.ui.lang;localStorage.setItem("remocon.lang",LANG);}
    if(r.ui&&r.ui.defaultModel!==undefined) DEFMODEL=r.ui.defaultModel||"";
    if(r.ui&&r.ui.defaultEffort!==undefined) DEFEFFORT=r.ui.defaultEffort||"";
    if(r.ui&&r.ui.showCodex!==undefined) SHOW_CODEX=!!r.ui.showCodex;
  }catch(e){}
  applyStatic(); fillModelSelects();
}
async function setLang(l){
  LANG=l; localStorage.setItem("remocon.lang",l);
  try{await fetch("/api/prefs",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({lang:l})});}catch(e){}
  location.reload();
}

const $ = s => document.querySelector(s);
// in-app dialog (replaces native prompt/confirm)
let _dlgRes=null, _dlgPrompt=false;
function uiConfirm(msg,title){ return new Promise(r=>_openDlg(title||"확인",msg,false,r)); }
function uiPrompt(msg,def,title){ return new Promise(r=>_openDlg(title||"입력",msg,true,r,def)); }
function _openDlg(title,msg,isPrompt,res,def){
  _dlgRes=res; _dlgPrompt=isPrompt;
  $("#dlg-title").textContent=title; $("#dlg-msg").textContent=msg;
  $("#dlg-inwrap").style.display=isPrompt?"block":"none";
  const inp=$("#dlg-input"); inp.value=def||"";
  $("#dlg").classList.add("show");
  if(isPrompt) setTimeout(()=>{inp.focus();inp.select();},40);
}
function _dlgClose(v){ $("#dlg").classList.remove("show"); const cb=_dlgRes; _dlgRes=null; if(cb) cb(v); }
function dlgCancel(){ _dlgClose(_dlgPrompt?null:false); }
function dlgOk(){ _dlgClose(_dlgPrompt?$("#dlg-input").value:true); }
document.addEventListener("keydown",e=>{ if(!$("#dlg").classList.contains("show"))return;
  if(e.key==="Enter"){e.preventDefault();dlgOk();} if(e.key==="Escape")dlgCancel(); });
let MACHINES=[], FOLDER=null, FOLDER_MACHINE=null, PK_MID=null, PK_PATH=null, TX=null;
const mById = id => MACHINES.find(m=>m.id===id)||{};
const osIcon = os => ic(os==="windows"?"monitor":os==="macos"?"laptop":os==="linux"?"server":"monitor","sm");
const osName = os => ({windows:"Windows",macos:"macOS",linux:"Linux"})[os]||os||"";
const shortModel = m => (m||"").replace(/^claude-/,"").replace(/-\d{8}$/,"");
function termCmd(m,cwd,sid,agent){
  const r=(agent==="claude")?(sid?`claude --remote-control --resume ${sid}`:"claude --remote-control"):(sid?`codex resume ${sid}`:"codex");
  // ssh 정보(원격 host 또는 self의 tailnet sshHost)가 있으면 ssh 포함 — 어느 PC에서든 붙여넣게
  const host=(m.host&&m.host!=="localhost")?m.host:(m.sshHost||"");
  if(!m.sshUser||!host) return `cd "${cwd}" && ${r}`;
  const port=(m.sshPort&&m.sshPort!==22)?` -p ${m.sshPort}`:"";
  if(m.os==="windows") return `ssh -t${port} ${m.sshUser}@${host} "cd /d \"${cwd}\" && ${r}"`;
  return `ssh -tt${port} ${m.sshUser}@${host} 'bash -lc "cd \"${cwd}\" && exec ${r}"'`;
}
async function copyTermCmd(mid,cwd,sid,agent){
  const m=mById(mid); if(!m) return;
  const cmd=termCmd(m,cwd,sid,agent);
  let ok=false;
  try{ await navigator.clipboard.writeText(cmd); ok=true; }catch(e){
    try{ const ta=document.createElement("textarea"); ta.value=cmd; document.body.appendChild(ta); ta.select(); ok=document.execCommand("copy"); ta.remove(); }catch(e2){}
  }
  if(ok) toast(t("📋 터미널 명령 복사됨 — 터미널에 붙여넣으세요")); else await uiPrompt(t("아래 명령을 복사해 터미널에서 실행:"),cmd);
}
async function openTerm(mid,cwd,sid,model){
  toast(t("터미널 세션 여는 중…"));
  try{
    const r=await(await fetch("/api/terminal",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({mid,cwd,sessionId:sid||"",model:model||""})})).json();
    if(r.ok){ toast(t("터미널 창을 열었습니다 (원격은 SSH)")); return; }
    // fallback (e.g. control couldn't open Terminal): copy the command
    const cmd=r.cmd||termCmd(mById(mid)||{},cwd,sid);
    try{ const ta=document.createElement("textarea"); ta.value=cmd; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); }catch(e){}
    toast(t("명령을 클립보드에 복사했습니다 — 터미널에 붙여넣으세요"));
  }catch(e){ toast(t("오류: ")+e.message); }
}
const cssid = id => id.replace(/[^a-zA-Z0-9_-]/g,"_");
const fkey = (mid,cwd)=>mid+""+cwd;
const isMobile = ()=>window.matchMedia("(max-width:767px)").matches;
function setTab(id){ document.querySelectorAll("#tabbar button").forEach(b=>b.classList.toggle("on", b.id==="tab-"+id)); }
function showNav(){ document.body.classList.remove("content"); document.body.classList.add("nav"); setTab("nav"); }
function showContent(){ if(isMobile()){ document.body.classList.remove("nav"); document.body.classList.add("content"); setTab("content"); } }
// Mobile tab bar: the two panes plus shortcuts into them.
function tabGo(which){
  if(which==="nav") return showNav();
  if(which==="content") return showContent();
  if(which==="search"){ showNav(); setTab("search"); const q=$("#fq"); if(q){ q.focus(); q.select(); } return; }
  if(which==="prefs"){
    // the header's model/effort pickers don't fit a phone header; ask here instead
    const lines=[t("기본 모델 (새 세션·이어가기에 적용)")+": "+($("#defmodel").selectedOptions[0]||{}).text,
                 t("기본 노력 (새 세션·이어가기에 적용)")+": "+($("#defeffort").selectedOptions[0]||{}).text];
    document.body.classList.toggle("show-prefs");
    toast(lines.join(" · "), 3500);
  }
}
// Messages still carry the old UI's leading emoji in their i18n keys; the
// achromatic UI shows them without it.
const plain = s => String(s==null?"":s).replace(/^[\p{Extended_Pictographic}\u2328\u2699\u25A0\uFE0F\s]+/u,"");
function toast(m,ms=2800){ const t=$("#toast"); t.textContent=plain(m); t.classList.add("show"); clearTimeout(t._t); t._t=setTimeout(()=>t.classList.remove("show"),ms); }
const sleep = ms=>new Promise(r=>setTimeout(r,ms));
const esc = s=>(s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmtSize = b=>(b==null?"":b<1024?b+" B":b<1048576?(b/1024).toFixed(1)+" KB":b<1073741824?(b/1048576).toFixed(1)+" MB":(b/1073741824).toFixed(1)+" GB");
const shortPath = p=>{ const a=(p||"").split(/[\\/]/).filter(Boolean); return a.length>2?"…/"+a.slice(-2).join("/"):p; };

// pinned folders per machine (localStorage)
const pins = mid=>{ try{return JSON.parse(localStorage.getItem("remocon.pins."+mid)||"[]")}catch(e){return[]} };
const setPins = (mid,a)=>localStorage.setItem("remocon.pins."+mid, JSON.stringify([...new Set(a)]));
// "pin to top" — folders (per machine) and sessions (global), localStorage
const topF = mid=>{ try{return new Set(JSON.parse(localStorage.getItem("remocon.topf."+mid)||"[]"))}catch(e){return new Set()} };
function toggleTopFolder(mid,cwd){ const s=topF(mid); s.has(cwd)?s.delete(cwd):s.add(cwd); localStorage.setItem("remocon.topf."+mid,JSON.stringify([...s])); loadNodeFolders(mById(mid)); }
const topS = ()=>{ try{return new Set(JSON.parse(localStorage.getItem("remocon.tops")||"[]"))}catch(e){return new Set()} };
function toggleTopSession(mid,cwd,sid){ const s=topS(); s.has(sid)?s.delete(sid):s.add(sid); localStorage.setItem("remocon.tops",JSON.stringify([...s])); const q=$("#ssearch"); loadSessionList(mid,cwd,q?q.value:""); }
const addPin = (mid,cwd)=>setPins(mid,[...pins(mid),cwd]);
const removePin = (mid,cwd)=>setPins(mid, pins(mid).filter(p=>p!==cwd));

async function apiM(mid, path, opts){
  const r = await fetch(`/api/m/${mid}/${path}`, opts);
  const txt = await r.text(); let j; try{ j=JSON.parse(txt);}catch(e){ j={error:txt||r.statusText}; }
  if(!r.ok && j.error) throw new Error(j.error);
  return j;
}

async function loadRegistry(){
  try{ MACHINES=(await (await fetch("/api/machines")).json()).machines; }
  catch(e){ $("#nodes").innerHTML=`<div class="empty sm err">${t("레지스트리 로드 실패")}</div>`; return; }
  renderSidebar();
  renderStatus();
}
function renderSidebar(){
  const host=$("#nodes"); host.innerHTML="";
  for(const m of MACHINES){
    const tun = STATUS.tunnels && STATUS.tunnels[m.id];
    const dot = !m.online ? "bad" : !m.agentReady ? "" : (m.is_self || tun==="up") ? "ok" : tun==="down" ? "bad" : "wait";
    const dotTitle = !m.online ? t("오프라인") : !m.agentReady ? t("에이전트 미설치")
      : (m.is_self || tun==="up") ? t("연결됨") : tun==="down" ? t("끊김") : t("연결 중");
    const status = `<span class="mdot ${dot}" title="${esc(dotTitle)}"></span>`;
    // Shown even when it is the machine's own login: "which account is this
    // machine on" should never be answered by an absence.
    const acctTag = (m.online&&m.agentReady&&ACTIVE_ACCT[m.id]!==undefined)
      ? `<span class="badge acct" title="${t("이 머신이 쓰는 계정")}">${esc(acctLabel(ACTIVE_ACCT[m.id]))}</span>` : "";
    const mj=JSON.stringify(m.id), nmj=JSON.stringify(m.name);
    const plus = (m.online&&m.agentReady)?`<button class="iconbtn sm" title="${t("이 PC에 폴더 추가")}" onclick='openPicker(${mj})'>${ic("plus","sm")}</button>`:"";
    const ref = (m.online&&m.agentReady)?`<button class="iconbtn sm" title="${t("이 머신 새로고침")}" onclick='refreshMachine(${mj},this)'>${ic("refresh","sm")}</button>`:"";
    const ren = `<button class="iconbtn sm" title="${t("이름 변경")}" onclick='renameMachine(${mj},${nmj})'>${ic("pencil","sm")}</button>`;
    const rem = m.is_self?"":`<button class="iconbtn sm del" title="${t("머신 제거")}" onclick='removeMachine(${mj},${nmj})'>${ic("x","sm")}</button>`;
    const g=document.createElement("div"); g.className="nodegrp";
    g.innerHTML=`<div class="nodehead">${status}<span class="os" title="${esc(osName(m.os))}">${osIcon(m.os)}</span><span class="nm">${esc(m.name)}</span>${acctTag}<span class="tools">${ref}${ren}${rem}</span>${plus}</div>
      <div class="nodefolders" id="nf-${cssid(m.id)}"></div>`;
    host.appendChild(g);
    if(m.online&&m.agentReady) loadNodeFolders(m);
    else g.querySelector(".nodefolders").innerHTML=`<div class="empty sm">${m.online?t("에이전트 미설치"):t("오프라인")}</div>`;
  }
}

async function loadNodeFolders(m){
  const nf=$("#nf-"+cssid(m.id));
  let folders=[];
  try{ const r=await apiM(m.id,withCx("folders")); folders=r.folders||[];
       if(r.activeAccount!==undefined) ACTIVE_ACCT[m.id]=r.activeAccount; }
  catch(e){ nf.innerHTML=`<div class="empty sm">${esc(e.message)}</div>`; return; }
  const have=new Set(folders.map(f=>f.cwd));
  for(const p of pins(m.id)) if(!have.has(p)) folders.push({cwd:p,session_count:0,last_activity:0});
  const pinset=new Set(pins(m.id)), topset=topF(m.id);
  folders.forEach(f=>{ f.pinned=pinset.has(f.cwd); f.top=topset.has(f.cwd); });
  folders.sort((a,b)=>((b.top?1:0)-(a.top?1:0)) || ((b.last_activity||0)-(a.last_activity||0))); // pinned-to-top first, then most-recent
  if(!folders.length){ nf.innerHTML=`<div class="empty sm">${t("폴더 없음 — ＋로 추가")}</div>`; return; }
  const mj=JSON.stringify(m.id);
  const row=(f,hidden)=>{
    const when=f.last_activity?new Date(f.last_activity*1000).toLocaleDateString():"";
    const cj=JSON.stringify(f.cwd);
    const act=(m.id===FOLDER_MACHINE && f.cwd===FOLDER)?" active":"";
    const meta=f.session_count?`${f.session_count}${LANG==="en"?" sessions":"개"} · ${when}`:`<span class="pinned">${t("추가됨")}</span>`;
    const trash=f.session_count?`<button class="iconbtn sm del" title="${t("이 폴더 세션 전체 삭제")}" onclick='event.stopPropagation();delFolder(${mj},${cj},${f.session_count})'>${ic("trash","sm")}</button>`:"";
    const unpin=f.pinned?`<button class="iconbtn sm" title="${t("목록에서 제거(핀 해제)")}" onclick='event.stopPropagation();unpinFolder(${mj},${cj})'>${ic("x","sm")}</button>`:"";
    const topBtn=`<button class="iconbtn sm${f.top?" on":""}" title="${f.top?t("상단 고정 해제"):t("상단 고정")}" onclick='event.stopPropagation();toggleTopFolder(${mj},${cj})'>${ic("pin","sm")}</button>`;
    return `<div class="folder${hidden?" hidden":""}${act}" data-fkey="${esc(fkey(m.id,f.cwd))}" title="${esc(f.cwd)}" onclick='openFolder(${mj},${cj})'>
      <div class="fcol"><div class="path"><span class="pname">${esc(shortPath(f.cwd))}</span>${(f.codex_count>0)?`<span class="badge agent codex dotonly" title="${t("Codex 세션 있음 (앱에 표시됨)")}"></span>`:''}${f.live?`<span class="livecount" title="${f.live} live">${f.live}</span>`:''}</div><div class="meta">${meta}</div></div>
      <div class="tools">${topBtn}${trash}${unpin}</div></div>`;
  };
  const rows=folders.map((f,i)=>row(f,i>=3 && !f.top));
  const more = folders.length>3 ? `<div class="more" data-n="${folders.length-3}" onclick="toggleMore(this)">${t("더보기")} (${folders.length-3})</div>` : "";
  nf.innerHTML=rows.join("")+more;
  const head = nf.parentNode && nf.parentNode.querySelector(".nodehead");
  if(head && ACTIVE_ACCT[m.id] !== undefined && !head.querySelector(".badge.acct")){
    head.querySelector(".nm").insertAdjacentHTML("afterend",
      `<span class="badge acct" title="${t("이 머신이 쓰는 계정")}">${esc(acctLabel(ACTIVE_ACCT[m.id]))}</span>`);
  }
  if(FQ) applyFolderFilter();   // folders arrive per machine; keep the active filter
}
// Folder search — filters the already-loaded folder rows of every machine at once.
// Case-insensitive over the full path; a query with spaces requires every term to
// appear, so "work scout" finds D:\workspace\project_scout.
let FQ = "";
function filterFolders(q){
  FQ = (q || "").trim().toLowerCase();
  const box = $("#fsearch");
  if(box) box.classList.toggle("on", !!FQ);
  $("#nodes").classList.toggle("searching", !!FQ);
  applyFolderFilter();
}
function applyFolderFilter(){
  const host = $("#nodes");
  const terms = FQ ? FQ.split(/\s+/).filter(Boolean) : [];
  let total = 0;
  for(const grp of host.querySelectorAll(".nodegrp")){
    let shown = 0;
    for(const row of grp.querySelectorAll(".folder")){
      const path = (row.getAttribute("title") || "").toLowerCase();
      const hit = !terms.length || terms.every(w => path.includes(w));
      row.classList.toggle("nomatch", !hit);
      if(hit) shown++;
    }
    // while searching, hide machines that contribute nothing
    grp.classList.toggle("nomatch", terms.length > 0 && shown === 0);
    total += shown;
  }
  let none = $("#fnone");
  if(terms.length && total === 0){
    if(!none){
      none = document.createElement("div");
      none.id = "fnone"; none.className = "empty sm";
      host.appendChild(none);
    }
    none.textContent = t("검색 결과 없음");
  } else if(none){ none.remove(); }
}

// Re-read one machine's folders. Folder rows carry the live-session counts, so
// this is also how you ask "what is actually running over there right now?"
// without reloading the page and every other machine with it.
async function refreshMachine(mid, btn){
  const m = mById(mid); if(!m) return;
  const svg = btn && btn.querySelector("svg");
  if(btn){ btn.disabled = true; if(svg) svg.classList.add("spin"); }
  try{ await loadNodeFolders(m); }
  finally{ if(btn){ btn.disabled = false; if(svg) svg.classList.remove("spin"); } }
}

function toggleMore(btn){ const nf=btn.parentNode; const ex=nf.classList.toggle("expanded"); btn.textContent= ex?t("접기"):(t("더보기")+" ("+btn.dataset.n+")"); }

async function openFolder(mid,cwd){
  FOLDER=cwd; FOLDER_MACHINE=mid;
  document.querySelectorAll(".folder.active").forEach(e=>e.classList.remove("active"));
  document.querySelectorAll(".folder").forEach(e=>{ if(e.dataset.fkey===fkey(mid,cwd)) e.classList.add("active"); });
  showContent();
  renderFolderView(mid,cwd);
}

let searchTimer=null, searchSeq=0;
function renderFolderView(mid,cwd){
  const m=mById(mid), mj=JSON.stringify(mid), cj=JSON.stringify(cwd);
  const name=(cwd.split(/[\\/]/).filter(Boolean).pop())||cwd;
  $("#main").innerHTML=`<div class="viewhead">
      <div class="vh-text"><div class="eyebrow">${osIcon(m.os)} ${esc(m.name)}</div>
        <h2>${esc(name)}</h2><div class="full">${esc(cwd)}</div></div>
      <div class="vh-actions">
        <button class="iconbtn solid" title="${t("이 폴더 새로고침")}" onclick='openFolder(${mj},${cj})'>${ic("refresh")}</button>
        <button class="primary lg" onclick='newSession(${mj},${cj})'>${ic("plus")}${t("새 세션")}</button></div></div>
    <div class="pill-search"><span class="lead">${ic("search")}</span>
      <input class="searchbox" id="ssearch" placeholder="${t("이 폴더에서 세션 검색 (제목·대화 내용)")}" spellcheck="false"
       oninput='clearTimeout(searchTimer);searchTimer=setTimeout(()=>loadSessionList(${mj},${cj},this.value),300)'></div>
    <div id="slist"><div class="empty">${t("불러오는 중…")}</div></div>`;
  loadSessionList(mid,cwd,"");
}
// ---- Claude accounts -------------------------------------------------------
// An account is a login the agent keeps on that machine; the picker switches
// which one new sessions use. Which machine we are configuring follows the
// folder currently selected in the sidebar, since the accounts live per machine.
let ACCT_MID = "", ACCT_TOKEN = "", ACCT_ORGS = [], ACCT_ROWS = [], ACCT_LOGIN_NAME = "";
// Which account each machine is currently launching with. Filled in from the
// folder and session responses, so no extra round trip just to label things.
const ACTIVE_ACCT = {};
const acctLabel = a => a ? a : t("머신 기본");
function acctMachine(){ return ACCT_MID || FOLDER_MACHINE || (MACHINES.find(m=>m.online&&m.agentReady)||{}).id || ""; }
function acctMsg(t_, bad){ const e=$("#acct-msg"); if(e){ e.textContent=t_||""; e.style.color = bad ? "var(--danger,#f85149)" : "var(--muted)"; } }

async function openAccounts(mid){
  ACCT_MID = mid || acctMachine();
  if(!ACCT_MID){ toast(t("검색할 수 있는 머신이 없습니다")); return; }
  $("#acct").classList.add("show");
  $("#acct-login").style.display = "none";
  $("#acct-org").style.display = "none";
  ACCT_TOKEN = "";
  acctMsg("");
  // Accounts live on the machine that runs the sessions, so which machine we
  // are looking at is part of the question, not a hidden default.
  const sel = $("#acct-machine");
  const usable = MACHINES.filter(m => m.online && m.agentReady);
  if(!usable.some(m => m.id === ACCT_MID)) ACCT_MID = (usable[0] || {}).id || "";
  sel.innerHTML = usable.map(m =>
    `<option value="${esc(m.id)}">${esc(m.name)} · ${esc(osName(m.os))}</option>`).join("");
  sel.value = ACCT_MID;
  $("#acct-list").innerHTML = `<div class="empty sm">${t("불러오는 중…")}</div>`;
  await acctRefresh();
}
function closeAccounts(){ $("#acct").classList.remove("show"); ACCT_TOKEN=""; }

async function acctRefresh(){
  let r;
  try{ r = await apiM(ACCT_MID, "accounts"); }
  catch(e){ $("#acct-list").innerHTML = `<div class="empty sm">${esc(e.message)}</div>`; return; }
  const rows = r.accounts || [];
  ACCT_ORGS = r.orgs || [];
  ACCT_ROWS = rows;
  $("#acct-list").innerHTML = rows.map(a=>{
    const nj = JSON.stringify(a.name);
    const who = a.loggedIn
      ? `${esc(a.email||"")}${a.orgName?` · ${esc(a.orgName)}`:""}${a.subscriptionType?` · ${esc(a.subscriptionType)}`:""}`
      : `<span class="warn">${t("로그인 안 됨")}</span>`;
    const use = a.active
      ? `<span class="badge live">${t("사용 중")}</span>`
      : `<button class="primary" onclick='acctSelect(${nj})'>${t("사용")}</button>`;
    const login = `<button class="ghost" onclick='acctLogin(${nj})'>${a.loggedIn?t("다시 로그인 / 조직 변경"):t("로그인")}</button>`;
    const del = a.isDefault ? "" : `<button class="ghost danger" onclick='acctDelete(${nj})'>${t("삭제")}</button>`;
    const rcBlocked = a.loggedIn && a.remoteControl === false
      ? `<span class="badge acct stale" title="${t("이 조직은 원격 제어를 막아 두어 이 매니저로 세션을 열 수 없습니다")}">${t("원격 제어 막힘")}</span>` : "";
    return `<div class="acct-card${a.active?" active":""}">
      <div class="row1"><span class="title">${esc(a.label)}</span>${a.isDefault?`<span class="badge">${t("머신 기본")}</span>`:""}${rcBlocked}</div>
      <div class="sub">${who}${a.error?` · <span class="err">${esc(a.error)}</span>`:""}</div>
      <div class="actions">${use}${login}${del}</div></div>`;
  }).join("") || `<div class="empty sm">${t("계정 없음")}</div>`;
}

async function acctCreate(){
  const el = $("#acct-new"), name = (el.value||"").trim();
  if(!name){ acctMsg(t("이름을 입력하세요"), true); return; }
  acctMsg(t("만드는 중…"));
  try{
    const r = await apiM(ACCT_MID, "accounts/create", {method:"POST",
      headers:{"Content-Type":"application/json"}, body:JSON.stringify({name})});
    if(r.error) throw new Error(r.error);
    el.value = ""; acctMsg("");
    await acctRefresh();
    acctLogin(name);            // a new account is useless until it has a login
  }catch(e){ acctMsg(e.message, true); }
}

async function acctSelect(name){
  try{
    const r = await apiM(ACCT_MID, "accounts/select", {method:"POST",
      headers:{"Content-Type":"application/json"}, body:JSON.stringify({name})});
    if(r.error) throw new Error(r.error);
    toast(t("계정 전환됨: ") + (name || t("머신 기본")));
    await acctRefresh();
  }catch(e){ acctMsg(e.message, true); }
}

async function acctDelete(name){
  if(!confirm(t("이 계정을 삭제할까요? 세션 기록은 공유라 지워지지 않습니다.") + "\n\n" + name)) return;
  try{
    const r = await apiM(ACCT_MID, "accounts/delete", {method:"POST",
      headers:{"Content-Type":"application/json"}, body:JSON.stringify({name})});
    if(r.error) throw new Error(r.error);
    await acctRefresh();
  }catch(e){ acctMsg(e.message, true); }
}

// Step 1: which organization. claude.com can show its own picker, or the
// sign-in can be pinned to an org this machine has seen (forceLoginOrgUUID).
function acctLogin(name){
  ACCT_LOGIN_NAME = name;
  $("#acct-login").style.display = "none";
  const cur = (ACCT_ROWS.find(a => a.name === name) || {}).orgUuid || "";
  const sel = $("#acct-org-sel");
  sel.innerHTML = `<option value="">${t("브라우저에서 선택")}</option>` +
    ACCT_ORGS.map(o => `<option value="${esc(o.uuid)}">${esc(o.name || o.uuid)}</option>`).join("") +
    `<option value="__uuid">${t("조직 ID 직접 입력…")}</option>`;
  sel.value = "";
  $("#acct-org-uuid").style.display = "none"; $("#acct-org-uuid").value = "";
  $("#acct-org").style.display = "";
  acctMsg(cur ? t("지금 조직: ") + ((ACCT_ORGS.find(o => o.uuid === cur) || {}).name || cur) : "");
}
function acctOrgSel(){
  $("#acct-org-uuid").style.display = $("#acct-org-sel").value === "__uuid" ? "" : "none";
}
async function acctLoginGo(){
  const name = ACCT_LOGIN_NAME;
  let org = $("#acct-org-sel").value;
  if(org === "__uuid") org = ($("#acct-org-uuid").value || "").trim();
  acctMsg(t("로그인 주소를 받는 중…"));
  $("#acct-org").style.display = "none";
  $("#acct-login").style.display = "none";
  try{
    const r = await apiM(ACCT_MID, "accounts/login", {method:"POST",
      headers:{"Content-Type":"application/json"}, body:JSON.stringify({name, org})});
    if(r.error) throw new Error(r.error);
    ACCT_TOKEN = r.token;
    const a = $("#acct-url"); a.href = r.url; a.textContent = r.url;
    $("#acct-login").style.display = "";
    $("#acct-code").value = ""; $("#acct-code").focus();
    acctMsg(t("브라우저에서 로그인한 뒤 코드를 붙여넣으세요"));
  }catch(e){ acctMsg(e.message, true); }
}

async function acctSubmitCode(){
  const code = ($("#acct-code").value||"").trim();
  if(!code){ acctMsg(t("코드를 붙여넣으세요"), true); return; }
  // The waiting `claude auth login` is gone (dialog reopened, machine switched,
  // agent restarted, or 15 minutes passed). Its code can't be used any more,
  // so say that plainly and start a fresh sign-in instead of asking for a code
  // that is already in the box.
  if(!ACCT_TOKEN) return acctRestartLogin(t("로그인 대기가 끊겼습니다 — 새 주소를 받아 다시 로그인해 주세요."));
  acctMsg(t("확인 중…"));
  let r;
  try{
    r = await apiM(ACCT_MID, "accounts/code", {method:"POST",
      headers:{"Content-Type":"application/json"}, body:JSON.stringify({token:ACCT_TOKEN, code})});
  }catch(e){ r = {error: e.message}; }
  if(r && !r.error){
    ACCT_TOKEN = "";
    $("#acct-login").style.display = "none";
    acctMsg(t("로그인 완료"));
    await acctRefresh();
    return;
  }
  const err = (r && r.error) || "";
  if(/unknown or expired login|no longer running/.test(err))
    return acctRestartLogin(t("로그인 대기가 끝났습니다 (시간 초과 또는 에이전트 재시작) — 새 주소를 받아 다시 로그인해 주세요."));
  // claude has exited after a failed exchange; show its own reason
  ACCT_TOKEN = "";
  const why = ((r && r.output) || "").match(/Login failed[^\r\n]*/);
  acctMsg((why ? why[0] + " — " : err + " — ") +
          t("코드가 틀렸거나 만료됐습니다. 로그인 주소를 다시 받아 주세요."), true);
}
function acctRestartLogin(msg){
  ACCT_TOKEN = "";
  acctLogin(ACCT_LOGIN_NAME);   // back to the organization step
  acctMsg(msg, true);
}

// All-machines session search. Each online agent scans its own sessions, so the
// machines work in parallel and nothing but the hits crosses the network.
let GSEQ = 0;
async function searchAllSessions(query){
  const q = (query || "").trim();
  if(!q) return;
  const seq = ++GSEQ;
  showContent();
  const targets = MACHINES.filter(m => m.online && m.agentReady);
  const main = $("#main");
  main.innerHTML = `<div class="viewhead">
      <div class="vh-text"><div class="eyebrow">${ic("search","sm")} ${t("전체 세션 검색")}</div>
        <h2>“${esc(q)}”</h2></div>
      <div class="vh-actions">
        <button class="ghost" id="gtoggle" style="display:none" onclick="toggleAllGroups()">${t("모두 펼치기")}</button>
        <button class="iconbtn solid" title="${t("닫기")}" onclick="clearGlobalSearch()">${ic("x")}</button></div></div>
    <div id="gstatus" class="empty sm"></div><div id="gresults"></div>`;
  const status = $("#gstatus"), host = $("#gresults");
  if(!targets.length){ status.textContent = t("검색할 수 있는 머신이 없습니다"); return; }

  let done = 0, total = 0;
  const tick = () => { if(seq===GSEQ)
    status.textContent = `${done}/${targets.length} ${t("머신")} · ${total}${t("건")}`; };
  tick();

  await Promise.all(targets.map(async m => {
    const box = document.createElement("div");
    box.className = "gmachine";
    box.innerHTML = `<div class="ghead">${osIcon(m.os)} ${esc(m.name)}
      <span class="badge">${t("검색 중…")}</span></div>`;
    host.appendChild(box);
    let r;
    try{ r = await apiM(m.id, `search-all?q=${encodeURIComponent(q)}`); }
    catch(e){ r = {error: e.message}; }
    if(seq !== GSEQ) return;            // a newer search replaced this one
    done++;
    const rows = r.sessions || [];
    total += rows.length;
    const note = r.error ? `<span class="badge">${esc(r.error)}</span>`
      : `<span class="badge">${rows.length}${t("건")}</span>` +
        (r.truncated ? `<span class="badge" title="${t("결과가 많아 일부만 표시합니다")}">${t("일부만")}</span>` : "");
    // A machine with a handful of hits opens on its own; a long one stays shut
    // so the page reads as a summary of where the matches are.
    const open = rows.length > 0 && rows.length <= 3;
    box.classList.toggle("open", open);
    const caret = rows.length ? `<span class="gcaret">${ic("chevron","sm")}</span>` : "";
    box.innerHTML = `<div class="ghead${rows.length ? " clickable" : ""}"
        ${rows.length ? `onclick="toggleGroup(this)"` : ""}>
        ${caret}${osIcon(m.os)} ${esc(m.name)} ${note}</div>
      <div class="gbody">` +
      rows.map(x => `<div class="gpath">${esc(x.cwd || "")}</div>` + sessionRow(x, m.id, x.cwd || "")).join("") +
      `</div>`;
    tick();
  }));
  if(seq === GSEQ){ $("#gtoggle").style.display = total ? "" : "none"; syncGroupToggle(); }
  if(seq === GSEQ && total === 0) status.textContent = t("검색 결과 없음");
}
const groupsWithHits = () =>
  [...document.querySelectorAll("#gresults .gmachine")].filter(g => g.querySelector(".gbody").children.length);
// The button says what the next click will do, so it has to follow the groups —
// including when they are opened one at a time.
function syncGroupToggle(){
  const b = $("#gtoggle"); if(!b) return;
  const groups = groupsWithHits();
  b.textContent = groups.some(g => !g.classList.contains("open")) ? t("모두 펼치기") : t("모두 접기");
}
function toggleGroup(head){ head.parentNode.classList.toggle("open"); syncGroupToggle(); }
function toggleAllGroups(){
  const groups = groupsWithHits();
  const expand = groups.some(g => !g.classList.contains("open"));
  groups.forEach(g => g.classList.toggle("open", expand));
  syncGroupToggle();
}
function clearGlobalSearch(){
  GSEQ++;
  const box = $("#fq"); if(box){ box.value = ""; filterFolders(""); }
  $("#main").innerHTML = `<div class="empty"><div class="big">${t("폴더를 고르세요")}</div></div>`;
}

// One session card. Used by the per-folder list and by the all-machines
// search, which passes each hit's own machine and cwd.
function sessionRow(s, mid, cwd){
  const m=mById(mid), mj=JSON.stringify(mid), cj=JSON.stringify(cwd);

    const when=s.last_activity?new Date(s.last_activity*1000).toLocaleString():"";
    const isCx=s.agent==="codex";
    const agentBadge=isCx?`<span class="badge agent codex">codex</span>`:`<span class="badge agent claude">claude</span>`;
    const modelBadge=s.model?`<span class="badge model" title="${esc(s.model)}">${esc(shortModel(s.model))}</span>`:"";
    // The account a session was started under is recorded at launch; older
    // sessions have none, and a session on the machine's own login is the
    // common case — neither is worth a badge, so only show one when it differs
    // from what the machine is launching with now.
    const cur = ACTIVE_ACCT[mid];
    const stale = !isCx && s.account !== undefined && s.account !== null
                  && cur !== undefined && s.account !== cur;
    const acctBadge = (!isCx && s.account)
      ? `<span class="badge acct${stale?" stale":""}" title="${stale?t("이 세션은 다른 계정으로 실행됐습니다"):t("이 세션의 계정")}">${ic("user","sm")}${esc(s.account)}</span>`
      : (stale ? `<span class="badge acct stale" title="${t("이 세션은 다른 계정으로 실행됐습니다")}">${ic("user","sm")}${esc(t("머신 기본"))}</span>` : "");
    const badges=(s.is_live?`<span class="badge live">live</span>`:"")+agentBadge+modelBadge+acctBadge+`<span class="badge node">${osIcon(m.os)} ${esc(m.name)}</span>`+(s.is_remote_control?`<span class="badge rc">remote</span>`:"");
    const sj=JSON.stringify(s.session_id);
    const snip=s.snippet?`<div class="snippet">…${esc(s.snippet)}</div>`:"";
    const pinBtn=`<button class="iconbtn${s._top?" on":""}" onclick='toggleTopSession(${mj},${cj},${sj})' title="${s._top?t("상단 고정 해제"):t("상단 고정")}">${ic("pin")}</button>`;
    const pinMark=s._top?`<span class="badge" title="${t("상단 고정")}">${ic("pin","sm")}</span>`:"";
    const cls=`session${s.is_live?" is-live":""}`;
    const meta=[`${s.msg_count} ${t("메시지")}`, when, isCx?"":esc(s.git_branch||""), `<code>${s.session_id.slice(0,8)}</code>`].filter(Boolean).join(" · ");
    if(isCx){
      return `<div class="${cls}" data-sid="${esc(s.session_id)}"><div class="row1">${pinMark}<span class="title">${esc(s.title)}</span>${badges}</div>
        <div class="sub">${esc(s.first_prompt||"")}</div>
        <div class="sub meta">${meta}</div>${snip}
        <div class="actions">
          <button class="primary" onclick='openTerm(${mj},${cj},${sj})' title="${t("터미널에서 인터랙티브로 이어가기")}">${ic("terminal")}${t("터미널")}</button>
          <button class="ghost" onclick='preview(${mj},${cj},${sj},"codex")'>${ic("chat","sm")}${t("대화")}</button>
          <span class="sp"></span>${pinBtn}
          <button class="iconbtn del" title="${t("삭제")}" onclick='del(${mj},${cj},${sj},false,"codex")'>${ic("trash")}</button></div></div>`;
    }
    // One green action per card: open a live session, otherwise resume it.
    const main=s.is_live&&s.bridge_url
      ? `<button class="primary" onclick='window.open(${JSON.stringify(s.bridge_url)},"_blank")'>${ic("external","sm")}${t("열기")}</button>`
      : `<button class="primary" onclick='resume(${mj},${cj},${sj},false)'>${ic("play","sm")}${t("이어가기")}</button>`;
    const stopBtn=s.is_live?`<button class="ghost danger" onclick='stopSession(${mj},${cj},${sj})'>${ic("stop","sm")}${t("종료")}</button>`:"";
    return `<div class="${cls}" data-sid="${esc(s.session_id)}"><div class="row1">${pinMark}<span class="title">${esc(s.title)}</span>${badges}</div>
      <div class="sub">${esc(s.first_prompt||"")}</div>
      <div class="sub meta">${meta}</div>${snip}
      <div class="actions">${main}
        ${stale?`<button class="ghost" title="${t("종료하고 현재 계정으로 다시 열기")}" onclick='switchAccount(${mj},${cj},${sj})'>${ic("user","sm")}${esc(acctLabel(cur))}${t("(으)로 전환")}</button>`:""}
        <button class="ghost" onclick='preview(${mj},${cj},${sj})'>${ic("eye","sm")}${t("미리보기")}</button>
        <button class="ghost" onclick='resume(${mj},${cj},${sj},true)'>${ic("fork","sm")}${t("포크")}</button>
        ${stopBtn}<span class="sp"></span>
        <button class="iconbtn" onclick='copyTermCmd(${mj},${cj},${sj},"claude")' title="${t("터미널 명령 복사")}">${ic("terminal")}</button>
        ${pinBtn}<button class="iconbtn del" title="${t("삭제")}" onclick='del(${mj},${cj},${sj},${s.is_live})'>${ic("trash")}</button></div></div>`;
}

async function loadSessionList(mid,cwd,query){
  const sl=$("#slist"); if(!sl) return;
  const seq=++searchSeq;
  sl.innerHTML=`<div class="empty">${query?t("🔎 검색 중…"):t("불러오는 중…")}</div>`;
  let sessions;
  try{
    const path=query?`search?cwd=${encodeURIComponent(cwd)}&q=${encodeURIComponent(query)}`:withCx(`sessions?cwd=${encodeURIComponent(cwd)}`);
    const resp=await apiM(mid,path);
    sessions=resp.sessions;
    if(resp.activeAccount!==undefined) ACTIVE_ACCT[mid]=resp.activeAccount;
  }catch(e){ if(seq===searchSeq) sl.innerHTML=`<div class="empty">${esc(e.message)}</div>`; return; }
  if(seq!==searchSeq) return; // a newer query superseded this one
  const m=mById(mid), mj=JSON.stringify(mid), cj=JSON.stringify(cwd);
  if(!sessions.length){ sl.innerHTML=`<div class="empty">${query?t("검색 결과 없음"):t("세션이 없습니다. ＋ 새 세션으로 시작하세요.")}</div>`; return; }
  const tset=topS();
  sessions.forEach(s=>s._top=tset.has(s.session_id));
  sessions.sort((a,b)=>(b._top?1:0)-(a._top?1:0)); // pinned sessions to the top (otherwise keep API order)
  sl.innerHTML=sessions.map(s=>sessionRow(s,mid,cwd)).join("");
}

function txRender(d,agent){
  const bot=agent==="codex"?`<span class="badge agent codex">Codex</span>`:`<span class="badge agent claude">Claude</span>`;
  $("#tx-title").textContent=d.title||t("대화 미리보기"); $("#tx-meta").textContent=(LANG==="en"?`${d.total} total · ${d.messages.length} recent`:`총 ${d.total}개 · 최근 ${d.messages.length}개`)+(d.model?` · 🧠 ${shortModel(d.model)}`:"");
  TX.msgs=d.messages;
  $("#tx-body").innerHTML=d.messages.length?d.messages.map((x,i)=>`<div class="msg ${x.role}"><div class="who">${x.role==="user"?(LANG==="en"?"You":"나"):bot}${x.ts?" · "+new Date(x.ts).toLocaleString():""}<button class="rw" onclick="rewindTo(${i})" title="${t("여기서 되감아 새 세션으로 이어가기")}">${ic("rewind","sm")}</button></div><div class="bubble">${esc(x.text)}</div></div>`).join(""):`<div class="empty">${t("표시할 대화가 없습니다")}</div>`;
  $("#tx-body").scrollTop=$("#tx-body").scrollHeight;
}
async function preview(mid,cwd,sessionId,agent){
  TX={mid,cwd,sessionId,agent:agent||"claude"};
  $("#tx-foot-claude").style.display = TX.agent==="codex"?"none":"flex";
  modelOpts(document.getElementById("tx-model"));
  $("#tx-foot-codex").style.display = TX.agent==="codex"?"flex":"none";
  $("#tx").classList.add("show"); $("#tx-body").innerHTML=`<div class="empty">${t("불러오는 중…")}</div>`; $("#tx-meta").textContent="";
  try{ const d=await apiM(mid,`transcript?sessionId=${sessionId}${TX.agent==="codex"?"&agent=codex":""}`);
    if(d.error){ $("#tx-body").innerHTML=`<div class="empty">${esc(d.error)}</div>`; return; }
    txRender(d,TX.agent);
  }catch(e){ $("#tx-body").innerHTML=`<div class="empty">${esc(e.message)}</div>`; }
}
function closeTx(){ $("#tx").classList.remove("show"); }
function txResume(fork){ if(!TX) return; const m=(document.getElementById("tx-model")||{}).value||DEFMODEL; const e=(document.getElementById("tx-effort")||{}).value||DEFEFFORT; closeTx(); resume(TX.mid,TX.cwd,TX.sessionId,fork,m,e); }
function renderAttach(){
  const box=$("#tx-attach"), a=(TX&&TX.attachments)||[];
  box.style.display=a.length?"block":"none";
  box.innerHTML=a.map((x,i)=>`${ic("clip","sm")} ${esc(x.name)} <a href="#" onclick="TX.attachments.splice(${i},1);renderAttach();return false">✕</a>`).join(" · ");
}
async function attachImage(file){
  if(!file||!TX) return;
  const b64=await new Promise(res=>{const r=new FileReader();r.onload=()=>res(r.result.split(",",2)[1]);r.readAsDataURL(file);});
  toast(t("이미지 업로드 중…"));
  try{
    const r=await apiM(TX.mid,"upload",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({filename:file.name||"pasted.png",data:b64})});
    if(!r.ok){ toast(t("업로드 실패: ")+(r.error||"")); return; }
    (TX.attachments=TX.attachments||[]).push({name:file.name||"pasted.png",path:r.path});
    renderAttach(); toast(t("이미지 첨부됨"));
  }catch(e){ toast(t("오류: ")+e.message); }
}
function rewindTo(i){ return handoff(TX&&TX.agent, i); }
async function handoff(toAgent, upToIndex){
  if(!TX) return;
  const rewind = (toAgent===TX.agent);
  const ask = rewind ? t("이 시점으로 되감아 새 세션을 만듭니다. 진행할까요?")
                     : t("이 대화를 다른 모델의 새 세션으로 이어갑니다. 진행할까요?");
  if(!await uiConfirm(ask)) return;
  toast(rewind ? t("되감는 중… (선택 시점까지 맥락 이전 + 새 세션)") : t("모델 전환 중… (맥락 이전 + 새 세션)"));
  const payload={sessionId:TX.sessionId,fromAgent:TX.agent,toAgent:toAgent,cwd:TX.cwd};
  if(Number.isInteger(upToIndex)){ payload.upToIndex=upToIndex; const m=(TX.msgs||[])[upToIndex]; if(m&&m.ts) payload.upToTs=m.ts; }
  try{
    const r=await apiM(TX.mid,"handoff",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    if(!r.ok&&!r.token){ toast(t("실패: ")+(r.error||"unknown")); return; }
    if(toAgent==="codex"){
      toast(t("완료 — 새 Codex 세션"));
      openFolder(TX.mid,TX.cwd); preview(TX.mid,TX.cwd,r.sessionId,"codex"); return;
    }
    for(let i=0;i<40;i++){ await sleep(1500); const st=await apiM(TX.mid,`launch?token=${r.token}`);
      if(st.state==="ready"){ toast(t("완료 — 새 Claude 세션 (새 탭)")); window.open(st.url,"_blank"); closeTx(); openFolder(TX.mid,TX.cwd); return; }
      if(st.state==="failed"){ toast(t("실패: ")+(st.error||"unknown")); return; } }
    toast(t("시간 초과 — auth/trust 확인 필요"));
  }catch(e){ toast(t("오류: ")+e.message); }
}
async function txSend(){
  const inp=$("#tx-input"); const msg=(inp.value||"").trim();
  const imgs=((TX&&TX.attachments)||[]).map(a=>a.path);
  if((!msg&&!imgs.length)||!TX) return;
  inp.value=""; inp.disabled=true; inp.placeholder=t("🟢 Codex 응답 대기 중… (최대 몇 분)"); showLoading(t("🟢 Codex 응답 대기 중…"));
  $("#tx-body").insertAdjacentHTML("beforeend",`<div class="msg user"><div class="who">${LANG==="en"?"You":"나"}</div><div class="bubble">${esc(msg||t("(이미지)"))}${imgs.length?` · ${imgs.length} img`:""}</div></div>`);
  $("#tx-body").scrollTop=$("#tx-body").scrollHeight;
  try{
    const r=await apiM(TX.mid,"run",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({agent:"codex",cwd:TX.cwd,resumeId:TX.sessionId,prompt:msg||t("첨부한 이미지를 봐줘"),images:imgs})});
    if(!r.ok){ toast(t("실패: ")+(r.error||"unknown")); }
    TX.attachments=[]; renderAttach();
    const d=await apiM(TX.mid,`transcript?sessionId=${TX.sessionId}&agent=codex`);
    if(!d.error) txRender(d,"codex");
  }catch(e){ toast(t("오류: ")+e.message); }
  hideLoading(); inp.disabled=false; inp.placeholder=t("Codex에게 메시지… (이미지 붙여넣기 가능, Enter 전송)"); inp.focus();
}
function showLoading(msg){ const m=$("#loading-msg"); if(m) m.textContent=plain(msg||t("처리 중…")); const l=$("#loading"); if(l) l.style.display="flex"; setBusy(plain(msg||t("처리 중…"))); }
function hideLoading(){ const l=$("#loading"); if(l) l.style.display="none"; setBusy(""); }
// ---- status bar: what's running, machines, tunnels, version ----------------
let STATUS = {tunnels:{}};
function setBusy(msg){ const b=$("#st-busy"); if(!b) return; b.hidden=!msg; $("#st-busy-msg").textContent=msg||""; }
async function loadStatus(){
  try{ STATUS=await (await fetch("/api/status")).json(); }catch(e){ return; }
  renderStatus();
  // tunnel state shows as each machine's dot; repaint just the dots
  for(const m of MACHINES){
    const head=document.querySelector(`#nf-${cssid(m.id)}`)?.parentNode?.querySelector(".mdot");
    if(!head || m.is_self || !m.agentReady) continue;
    const tun=STATUS.tunnels[m.id];
    head.className="mdot "+(tun==="up"?"ok":tun==="down"?"bad":"wait");
  }
}
function renderStatus(){
  const ready=MACHINES.filter(m=>m.online&&m.agentReady).length;
  const st=$("#st-machines"); if(st) st.innerHTML=`${ic("server","sm")} ${ready}/${MACHINES.length} ${t("머신 연결")}`;
  const tun=Object.values(STATUS.tunnels||{}), up=tun.filter(x=>x==="up").length;
  const tt=$("#st-tunnels"); if(tt) tt.innerHTML=tun.length?`<span class="mdot ${up===tun.length?"ok":"bad"}"></span>${up}/${tun.length} ${t("터널")}`:"";
  const v=$("#st-ver"); if(v && STATUS.version) v.textContent=`Remocon ${STATUS.version}`;
}
let AG=null;
function newSession(mid,cwd){ AG={mid,cwd}; const pe=$("#ag-path"); if(pe) pe.textContent=cwd; agBack(); $("#agpick").classList.add("show"); if(!SHOW_CODEX) agPick('claude'); }
function agBack(){   // step 1로
  $("#ag-step1").style.display="grid"; $("#ag-step2").style.display="none";
  $("#ag-title").textContent=t("새 세션");
}
function agPick(kind){   // step 2로
  if(!AG) return; AG.kind=kind;
  $("#ag-step1").style.display="none"; $("#ag-step2").style.display="block";
  const isCx=kind==="codex";
  $("#ag-claude-row").style.display=isCx?"none":"flex";
  $("#ag-codex-row").style.display=isCx?"flex":"none";
  $("#ag-title").textContent=isCx?t("새 Codex 세션"):t("새 Claude 세션");
  if(!isCx) modelOpts(document.getElementById("ag-model"));
}
function agStart(){
  $("#agpick").classList.remove("show"); if(!AG) return;
  if(AG.kind==="claude") launchIn(AG.mid,AG.cwd);
  else newCodexSession(AG.mid,AG.cwd,(document.getElementById("ag-cxmodel")||{}).value||"");
}
async function newCodexSession(mid,cwd,model){
  const first=await uiPrompt(t("🟢 새 Codex 세션 — 첫 메시지:")); if(!first) return;
  showLoading(t("🟢 Codex 세션 생성 중… 응답까지 최대 1~2분 (앱에도 뜹니다)"));
  try{
    const r=await apiM(mid,"run",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({agent:"codex",cwd,prompt:first,model:model||undefined})});
    if(!r.ok){ toast(t("실패: ")+(r.error||"unknown")); return; }
    toast(t("Codex 세션 생성됨")); openFolder(mid,cwd);
    preview(mid,cwd,r.sessionId,"codex");
  }catch(e){ toast(t("오류: ")+e.message); }
  finally{ hideLoading(); }
}

// picker = ADD FOLDER to a node (pin); session is created later from the folder
async function openPicker(mid,start){
  const m=mById(mid); if(!m.agentReady) return toast("에이전트가 없는 노드입니다");
  PK_MID=mid; $("#pk-title").textContent=`폴더 추가 · ${m.name}`; $("#pk-path").value="";
  $("#picker").classList.add("show"); loadCodexProjects(mid); await pkNav(start||null);
}
async function loadCodexProjects(mid){
  const box=$("#pk-codex"); box.style.display="none"; box.innerHTML="";
  try{
    const r=await apiM(mid,"codex/projects");
    const ps=(r&&r.projects)||[];
    if(!ps.length) return;
    box.style.display="block";
    box.innerHTML=`<div class="lbl" style="margin-bottom:6px">${t("Codex 프로젝트 (클릭해서 추가)")} · ${ps.length}</div>`+
      ps.map(o=>{
        const path=o.cwd||o; const live=o.has_sessions;
        const name=(path.split(/[\\/]/).filter(Boolean).pop())||path;
        const tag=live?`<span class="badge live">${t("세션")}</span>`:"";
        return `<div class="cxproj" onclick='pkGo(${JSON.stringify(path)})' title="${esc(path)}">
          <span class="badge agent codex dotonly"></span>
          <div style="flex:1;min-width:0"><div class="nm">${esc(name)}</div><div class="pp">${esc(path)}</div></div>
          ${tag}${ic("plus","sm")}
        </div>`;
      }).join("");
  }catch(e){}
}
function pkGo(path){ addAndOpen(PK_MID,path); }   // 칩 클릭 = 그 codex 프로젝트 폴더를 바로 추가
function closePicker(){ $("#picker").classList.remove("show"); }
async function pkMkdir(){
  if(!PK_PATH) return;
  const name=await uiPrompt(t("새 폴더 이름")+`\n${PK_PATH}`,"");
  if(name===null) return;            // 취소
  if(!name.trim()) return;
  try{
    const d=await apiM(PK_MID,"mkdir",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({parent:PK_PATH,name:name.trim()})});
    if(d&&d.error){ toast(t("실패: ")+d.error); return; }
    toast(t("폴더 생성됨")); await pkNav((d&&d.path)||PK_PATH);   // 새 폴더 안으로 이동
  }catch(e){ toast(t("오류: ")+e.message); }
}
async function pkNav(path){
  $("#pk-list").innerHTML=`<div class="empty">${t("불러오는 중…")}</div>`;
  let d; try{ d=await apiM(PK_MID,`browse${path?`?path=${encodeURIComponent(path)}`:""}`); }
  catch(e){ $("#pk-list").innerHTML=`<div class="empty">${esc(e.message)}</div>`; return; }
  PK_PATH=d.path; $("#pk-cur").textContent=d.path;
  // breadcrumb: each path segment is clickable
  const win=d.path.includes("\\");
  let crumbHtml="";
  if(d.path && !d.path.startsWith("내 PC")){
    const sep=win?"\\":"/";
    const parts=d.path.split(/[\\/]/).filter(Boolean);
    let acc=win?"":"/";
    const segs=[];
    if(!win) segs.push({label:"/",path:"/"});
    for(const p of parts){
      acc = win ? (acc?acc+sep+p:p+sep) : (acc==="/"?"/"+p:acc+sep+p);
      const full = win&&acc.endsWith(":\\")===false&&/^[A-Za-z]:$/.test(acc)?acc+"\\":acc;
      segs.push({label:p,path:full});
    }
    crumbHtml=segs.map((s,i)=>`<a href="#" onclick='pkNav(${JSON.stringify(s.path)});return false'>${esc(s.label)}</a>`).join(`<span class="sep">${esc(sep)}</span>`);
  } else { crumbHtml=`<code>${esc(d.path)}</code>`; }
  $("#pk-crumbs").innerHTML=`<button class="iconbtn solid sm" title="${t("상위")}" onclick='pkNav(${d.parent?JSON.stringify(d.parent):"null"})' ${d.parent?"":"disabled"}>${ic("up","sm")}</button>
    <button class="iconbtn solid sm" title="${t("홈")}" onclick='pkNav(${JSON.stringify(d.home)})'>${ic("home","sm")}</button>
    <button class="ghost" onclick="pkMkdir()" ${d.path&&!d.path.startsWith("내 PC")?"":"disabled"} title="${t("이 폴더 안에 새 폴더 만들기")}">${ic("plus","sm")}${t("새 폴더")}</button>
    <span style="width:6px"></span>${crumbHtml}`;
  // drive side list (Windows targets)
  const dv=$("#pk-drives"), drv=d.drives||[];
  if(drv.length){
    dv.style.display="block";
    dv.innerHTML=`<div class="sec-title" style="margin:6px 8px">${t("드라이브")}</div>`+drv.map(x=>{
      const on=d.path.toUpperCase().startsWith(x.toUpperCase().slice(0,2));
      return `<div class="direntry${on?" on":""}" onclick='pkNav(${JSON.stringify(x)})'>${ic("drive","sm")} ${esc(x.replace("\\\\",""))}</div>`;
    }).join("");
  } else dv.style.display="none";
  const items=d.entries||[], files=d.files||[];
  const dirsHtml=items.length?items.map(e=>`<div class="direntry" onclick='pkNav(${JSON.stringify(e.path)})'>${ic("folder","sm")}<span style="flex:1">${esc(e.name)}</span>${e.has_sessions?`<span class="dotg" title="${t("세션 있음")}"></span>`:""}</div>`).join(""):`<div class="empty sm">${t("하위 폴더 없음")}</div>`;
  const filesHtml=files.length
    ? `<div class="sec-title" style="margin:12px 12px 4px">${t("이 폴더의 파일")} (${d.file_count}${d.file_count>files.length?` / ${files.length}`:""})</div>`+files.map(f=>`<div class="fileentry">${ic("file","sm")}<span style="flex:1">${esc(f.name)}</span><span class="fsize">${fmtSize(f.size)}</span></div>`).join("")
    : `<div class="empty sm" style="margin-top:10px">${t("이 폴더에 파일이 없습니다")}</div>`;
  $("#pk-list").innerHTML=dirsHtml+filesHtml;
}
function addAndOpen(mid,cwd){ addPin(mid,cwd); closePicker(); loadNodeFolders(mById(mid)); openFolder(mid,cwd); toast(t("폴더 추가됨")); }
function pickHere(){ if(PK_PATH) addAndOpen(PK_MID,PK_PATH); }
function pickTyped(){ const p=$("#pk-path").value.trim(); if(p) addAndOpen(PK_MID,p); }
function unpinFolder(mid,cwd){ removePin(mid,cwd); loadNodeFolders(mById(mid)); if(FOLDER_MACHINE===mid&&FOLDER===cwd){ FOLDER=null; $("#main").innerHTML=`<div class="empty">목록에서 제거됨.</div>`; } }

async function launchIn(mid,cwd){
  const name=await uiPrompt("새 세션 이름 (선택 — 비우면 자동 생성)","");
  if(name===null) return; // 취소
  const body={cwd}; if(name.trim()) body.name=name.trim();
  const m=(document.getElementById("ag-model")||{}).value||DEFMODEL; if(m) body.model=m;
  const ef=(document.getElementById("ag-effort")||{}).value||DEFEFFORT; if(ef) body.effort=ef;
  doLaunch(mid,body);
}
function resume(mid,cwd,sessionId,fork,model,effort){ const b={cwd,resumeId:sessionId,fork}; const m=model!==undefined?model:DEFMODEL; if(m) b.model=m; const e=effort!==undefined?effort:DEFEFFORT; if(e) b.effort=e; doLaunch(mid,b); }
async function doLaunch(mid,body){
  showLoading(t("🟧 Claude 세션 여는 중… (trust 자동승인 + bridge 대기)"));
  try{
    const r=await apiM(mid,"launch",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    if(r.error){ toast(t("실패: ")+r.error); return; }
    // The agent decides how long this may take (a resume of a large transcript
    // needs minutes, not 45s); wait that long plus a margin, never less.
    const limit = Math.max(45, r.timeout || 45) + 15;
    const t0 = Date.now();
    if(r.attached) showLoading(t("🟧 이미 실행 중인 세션에 연결하는 중…"));
    while((Date.now()-t0)/1000 < limit){
      await sleep(1500);
      const st=await apiM(mid,`launch?token=${r.token}`);
      if(st.state==="ready"){ toast("열렸습니다 → 새 탭"); window.open(st.url,"_blank"); if(FOLDER_MACHINE===mid&&FOLDER) openFolder(mid,FOLDER); loadNodeFolders(mById(mid)); return; }
      if(st.state==="failed"){ toast(t("실패: ")+(st.error||"unknown")); return; }
      const sec = Math.round((Date.now()-t0)/1000);
      if((r.timeout||45) > 45 && sec > 20)
        showLoading(t("🟧 큰 대화를 불러오는 중… ") + sec + "/" + (r.timeout) + t("초"));
    }
    toast("시간 초과 — auth/trust 확인 필요");
  }catch(e){ toast(t("오류: ")+e.message); }
  finally{ hideLoading(); }
}
// Stopping is a signal, not a wait: the agent returns as soon as it has sent it,
// but claude takes a moment to actually go. Mark the card immediately so the
// click has an answer, then settle the lists in the background — nothing here
// holds up the next thing the user wants to do.
function markStopping(sessionId, on){
  const card = document.querySelector(`.session[data-sid="${CSS.escape(sessionId)}"]`);
  if(!card) return;
  card.querySelectorAll("button").forEach(b => b.disabled = on);
  card.style.opacity = on ? ".6" : "";
  const live = card.querySelector(".badge.live");
  if(live && on){ live.textContent = t("종료 중…"); live.classList.add("stopping"); }
}

async function settleAfterStop(mid, cwd, sessionId){
  for(let i = 0; i < 15; i++){
    await sleep(1000);
    // "is it still running" only needs the pidfiles, not a re-read of every
    // transcript in the folder — the old poll took seconds per tick.
    try{ if(!(await apiM(mid, `alive?sessionId=${encodeURIComponent(sessionId)}`)).alive) break; }
    catch(e){ continue; }
  }
  const m = mById(mid);
  if(m) loadNodeFolders(m);                 // the machine's live count in the sidebar
  // only redraw the list if it is still the one on screen
  if(FOLDER === cwd && FOLDER_MACHINE === mid){
    const q = $("#ssearch");
    loadSessionList(mid, cwd, q ? q.value : "");
  }
}

// Move a session onto the account the machine is launching with now. Claude
// cannot change the login of a running process, so the only honest way is to
// stop it and resume the same transcript under the new one — which is exactly
// what resume already does, the conversation being on disk either way.
async function switchAccount(mid,cwd,sessionId){
  const cur = ACTIVE_ACCT[mid];
  if(!await uiConfirm(t("이 세션을 종료하고 현재 계정으로 다시 열까요?") + "\n\n" + acctLabel(cur))) return;
  markStopping(sessionId, true);
  try{
    const r = await apiM(mid,"stop",{method:"POST",headers:{"Content-Type":"application/json"},
                                     body:JSON.stringify({sessionId})});
    if(!r.ok && r.reason !== "not live") throw new Error(r.reason || "stop failed");
  }catch(e){ toast(t("오류: ")+e.message); markStopping(sessionId, false); return; }
  for(let i = 0; i < 15; i++){          // resume refuses while the old one holds the session
    await sleep(1000);
    try{ if(!(await apiM(mid, `alive?sessionId=${encodeURIComponent(sessionId)}`)).alive) break; }
    catch(e){ /* keep waiting */ }
  }
  resume(mid, cwd, sessionId, false);   // picks up the machine's current account
}

async function stopSession(mid,cwd,sessionId){
  if(!await uiConfirm(t("실행 중인 이 세션을 종료할까요?"))) return;
  markStopping(sessionId, true);
  try{
    const r = await apiM(mid,"stop",{method:"POST",headers:{"Content-Type":"application/json"},
                                     body:JSON.stringify({sessionId})});
    if(!r.ok){ toast(t("종료 실패: ")+(r.reason||"")); markStopping(sessionId, false); return; }
  }catch(e){ toast(t("오류: ")+e.message); markStopping(sessionId, false); return; }
  toast(t("종료 중…"));
  settleAfterStop(mid, cwd, sessionId);     // deliberately not awaited
}
async function delFolder(mid,cwd,count){
  if(!await uiConfirm(`이 폴더의 세션 ${count}개를 모두 삭제할까요?\n${cwd}\n실행 중(live)은 건너뜁니다. 되돌릴 수 없습니다.`)) return;
  try{ const r=await apiM(mid,"folder/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({cwd})});
    toast(`삭제 ${r.deleted} · 건너뜀(live) ${r.skipped_live}`); loadNodeFolders(mById(mid));
    if(FOLDER_MACHINE===mid&&FOLDER===cwd) openFolder(mid,cwd); }catch(e){ toast(t("오류: ")+e.message); }
}
async function del(mid,cwd,sessionId,isLive,agent){
  if(isLive) return toast(t("실행 중인 세션은 먼저 '종료' 후 삭제하세요"));
  if(!await uiConfirm(t("이 세션을 삭제할까요? 되돌릴 수 없습니다."))) return;
  try{ const r=await apiM(mid,`session?sessionId=${sessionId}${agent==="codex"?"&agent=codex":""}`,{method:"DELETE"});
    if(r.ok){ toast(t("삭제됨")); openFolder(mid,cwd); loadNodeFolders(mById(mid)); } else toast(t("삭제 거부: ")+(r.reason||"")); }catch(e){ toast(t("오류: ")+e.message); }
}

// ---- orchestration manager ----
async function openManager(reset){
  if(reset && !await uiConfirm(t("현재 매니저 세션을 종료하고 새 세션으로 초기화할까요?"))) return;
  toast(reset ? t("매니저 세션 초기화 중…") : t("매니저 세션 여는 중… (전 머신 총괄)"));
  try{
    const r = await (await fetch("/api/manager"+(reset?"?fresh=1":""))).json();
    if(r.bridgeUrl){ window.open(r.bridgeUrl,"_blank"); toast(reset?t("매니저 세션 초기화됨"):(r.reused?t("매니저 세션(기존) 열림"):t("매니저 세션 시작됨"))); }
    else toast(t("실패: ")+(r.error||"unknown"));
  }catch(e){ toast(t("오류: ")+e.message); }
}
async function deleteManager(){
  if(!await uiConfirm(t("매니저 세션을 삭제할까요? (대화 기록 삭제)"))) return;
  toast(t("매니저 세션 삭제 중…"));
  try{
    const r = await (await fetch("/api/manager?delete=1")).json();
    toast(r.ok ? t("매니저 세션 삭제됨") : t("실패: ")+(r.error||"unknown"));
    loadRegistry();
  }catch(e){ toast(t("오류: ")+e.message); }
}

// ---- add / rename / remove machine ----
function openAddMachine(){
  $("#enroll-cmd").textContent = `irm http://${location.host}/enroll | iex`;
  $("#enroll-cmd-linux").textContent = `curl -fsSL http://${location.host}/enroll?os=linux | bash`;
  $("#enroll-cmd-mac").textContent = `curl -fsSL http://${location.host}/enroll?os=macos | bash`;
  $("#am-name").value=""; $("#am-host").value=""; $("#am-user").value=""; $("#am-port").value="22";
  $("#addm").classList.add("show"); setTimeout(()=>$("#am-name").focus(),40);
}
function closeAddM(){ $("#addm").classList.remove("show"); }
function copyCmd(el){ try{ navigator.clipboard.writeText(el.textContent); toast("복사됨"); }catch(e){ toast("선택해서 복사하세요"); } }
async function submitAddM(){
  const name=$("#am-name").value.trim(), host=$("#am-host").value.trim(), user=$("#am-user").value.trim(), port=$("#am-port").value.trim()||"22";
  if(!host||!user) return toast("호스트/IP 와 SSH 유저는 필수입니다");
  closeAddM(); toast("등록 + 배포 시작… (수십 초)");
  try{
    const r=await (await fetch("/api/machines/add",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({name:name||host,host,sshUser:user,sshPort:+port})})).json();
    if(r.error) return toast(t("실패: ")+r.error);
    for(let i=0;i<40;i++){ await sleep(3000); await loadRegistry();
      const m=mById(r.id); if(m&&m.agentReady){ try{ await apiM(r.id,"folders"); toast("배포 완료: "+(m.name||r.id)); return; }catch(e){} } }
    toast("배포 진행 중 — 잠시 후 새로고침하세요");
  }catch(e){ toast(t("오류: ")+e.message); }
}
async function renameMachine(id,cur){
  const name=await uiPrompt("새 이름(닉네임)",cur,"이름 변경");
  if(name===null||!name.trim()) return;
  try{ const r=await (await fetch("/api/machines/rename",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id,name:name.trim()})})).json();
    if(r.ok){ toast(t("이름 변경됨")); loadRegistry(); } else toast(t("실패: ")+(r.error||"")); }catch(e){ toast(t("오류: ")+e.message); }
}
async function removeMachine(id,name){
  if(!await uiConfirm(`'${name}' 을(를) 목록에서 제거할까요?\n원격 에이전트·세션은 그대로 남고 등록만 해제됩니다.`)) return;
  try{ const r=await (await fetch("/api/machines/remove",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id})})).json();
    if(r.ok){ toast(t("제거됨")); if(FOLDER_MACHINE===id){ FOLDER=null; $("#main").innerHTML='<div class="empty">머신이 제거되었습니다.</div>'; } loadRegistry(); } else toast("실패"); }catch(e){ toast(t("오류: ")+e.message); }
}

applyIcons();
if(isMobile()) showNav();   // a phone starts on the folder list
initLang().then(()=>loadRegistry()).then(loadStatus);
setInterval(loadStatus, 15000);

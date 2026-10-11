"""Skill folder sync primitives, operating on a base dir.

A "skill" is a subdirectory of a skills root (e.g. ~/.claude/skills/<name>/ on a
machine, or <repo>/skills/<name>/ canonical). We list with content hashes +
mtime (to compare machines and judge which is newest), read (base64) to
transfer, and write to apply.

Secret/credential/encrypted files are EXCLUDED from listing, hashing, transfer,
and overwrite — we compare/sync the skill STRUCTURE + code only, never secrets.
"""

from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

# files that hold credentials / tokens / keys / encrypted blobs -> never sync/compare
_SECRET = re.compile(
    r"(credential|token|secret|password|api[_-]?key|\.env|\.key$|\.pem$|\.p12$|"
    r"\.pfx$|\.gpg$|\.age$|\.enc$|\.crypt$|id_rsa|id_ed25519)",
    re.I,
)


def is_secret(rel: str) -> bool:
    return bool(_SECRET.search(rel))


def _iter_skill_dirs(base: Path):
    if not base.is_dir():
        return
    for d in sorted(base.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            yield d


def _skill_files(d: Path):
    """Yield (rel, Path) for non-secret regular files in a skill dir."""
    for f in sorted(d.rglob("*")):
        if f.is_file():
            rel = f.relative_to(d).as_posix()
            if is_secret(rel) or "/." in ("/" + rel):
                continue
            yield rel, f


def list_skills(base: Path) -> list[dict]:
    """[{name, hash, fileCount, mtime, files:[{rel,sha,size}]}] per skill.
    `hash` is over structure+content of non-secret files; `mtime` = newest file."""
    out = []
    for d in _iter_skill_dirs(base):
        files = []
        h = hashlib.sha256()
        mtime = 0.0
        for rel, f in _skill_files(d):
            data = f.read_bytes()
            sha = hashlib.sha256(data).hexdigest()
            files.append({"rel": rel, "sha": sha, "size": len(data)})
            h.update(rel.encode()); h.update(sha.encode())
            try:
                mtime = max(mtime, f.stat().st_mtime)
            except OSError:
                pass
        out.append({"name": d.name, "hash": h.hexdigest()[:16], "fileCount": len(files),
                    "mtime": mtime, "files": files})
    return out


def read_skills(base: Path, names: list | None = None) -> dict:
    """{name: {rel: base64}} for non-secret files (for transfer/apply).
    If `names` is given, only those skills are read (keeps payloads small)."""
    want = set(names) if names else None
    res = {}
    for d in _iter_skill_dirs(base):
        if want is not None and d.name not in want:
            continue
        files = {rel: base64.b64encode(f.read_bytes()).decode() for rel, f in _skill_files(d)}
        res[d.name] = files
    return res


def write_skills(base: Path, payload: dict) -> dict:
    """Write {name: {rel: base64}} into base/<name>/<rel>, skipping secret files.
    Overwrites managed files; never deletes existing files/skills. Traversal-safe."""
    base.mkdir(parents=True, exist_ok=True)
    written, names = 0, []
    for name, files in (payload or {}).items():
        if not name or "/" in name or "\\" in name or name.startswith("."):
            continue
        sd = base / name
        sd.mkdir(parents=True, exist_ok=True)
        names.append(name)
        for rel, b64 in (files or {}).items():
            if is_secret(rel):
                continue
            parts = rel.replace("\\", "/").split("/")
            if any(p in ("", "..", ".") for p in parts):
                continue
            target = sd.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(b64))
            written += 1
    return {"ok": True, "written": written, "names": names}

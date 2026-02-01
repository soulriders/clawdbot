import os
from pathlib import Path
import time
import random
import string

# --- 설정: 새로운 목표 경로 ---
ROOT_DIR = r"E:\antimoltbot"

# --- 파일 내용 정의 (새로운 경로 반영) ---

CONTENT_HELPER = r'''"""AntimoltbotClient — file-based inbox/outbox helper
This module implements the protocol defined in `antimoltbot/PROTOCOL.md`.
Created: 2026-01-30 (KST)
"""
from __future__ import annotations
import os
import time
import random
import string
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Literal

ProtocolType = Literal["error_report", "fix_instruction", "ack_read", "ack_applied", "status"]

def now_iso_kst() -> str:
    from datetime import timedelta
    kst = timezone(timedelta(hours=9))
    return datetime.now(tz=kst).isoformat(timespec="seconds")

def ts_compact(dt: Optional[datetime] = None) -> str:
    if dt is None: dt = datetime.now()
    return dt.strftime("%Y%m%d_%H%M%S")

def gen_task_id(dt: Optional[datetime] = None, short_len: int = 2) -> str:
    if dt is None: dt = datetime.now()
    short = "".join(random.choices(string.ascii_uppercase + string.digits, k=short_len))
    return f"T{dt.strftime('%Y%m%d-%H%M%S')}-{short}"

def atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding=encoding, newline="\n") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def load_template(base: Path, name: str) -> str:
    tpath = base / "templates" / name
    return tpath.read_text(encoding="utf-8")

def build_filename(ptype: ProtocolType, task_id: str, dt: Optional[datetime] = None) -> str:
    return f"{ts_compact(dt)}__{task_id}__{ptype}.md"

def fill_frontmatter(*, ptype: ProtocolType, task_id: str, iteration: int, agent: str, summary: str, extra: Optional[dict[str, str]] = None) -> str:
    safe_summary = summary.replace('"', '')
    lines = [
        "---",
        f"type: {ptype}",
        f"taskId: {task_id}",
        f"timestamp: {now_iso_kst()}",
        f"iteration: {iteration}",
        f"agent: {agent}",
        f"summary: \"{safe_summary}\"",
    ]
    if extra:
        for k, v in extra.items():
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)

@dataclass
class AntimoltbotClient:
    base: Path
    @property
    def inbox(self) -> Path: return self.base / "inbox"
    @property
    def outbox(self) -> Path: return self.base / "outbox"
    @property
    def workspace(self) -> Path: return self.base / "workspace"

    # 기본 경로를 E:\antimoltbot 으로 변경
    def __init__(self, base: str | Path = r"E:\antimoltbot"):
        self.base = Path(base)

    def send_error_report(self, *, task_desc: str, repro_steps: str, code_snippet: str, error_message: str, stacktrace: str = "", iteration: int = 1) -> str:
        task_id = gen_task_id()
        fm = fill_frontmatter(ptype="error_report", task_id=task_id, iteration=iteration, agent="antigravity", summary=task_desc[:120])
        body = f"""
# Error Report
## 목표 / 작업 설명
{task_desc}
## 재현 방법
{repro_steps}
## 관련 코드
```python
{code_snippet}
```
## 에러 메시지
```text
{error_message}
```
## 스택 트레이스 / 로그
```text
{stacktrace}
```""".lstrip("\n")
        filename = build_filename("error_report", task_id)
        atomic_write(self.inbox / filename, fm + "\n\n" + body)
        return task_id

    def send_ack_applied(self, *, task_id: str, iteration: int, applied_summary: str, test_result: str) -> Path:
        fm = fill_frontmatter(ptype="ack_applied", task_id=task_id, iteration=iteration, agent="antigravity", summary=applied_summary[:120])
        body = f"""
# ACK (Applied)
## 적용 내용
{applied_summary}
## 재실행/테스트 결과
```text
{test_result}
```""".lstrip("\n")
        filename = build_filename("ack_applied", task_id)
        path = self.inbox / filename
        atomic_write(path, fm + "\n\n" + body)
        return path

    def wait_for_fix_instruction(self, *, task_id: str, timeout_s: int = 120, poll_s: float = 1.0) -> Optional[Path]:
        deadline = time.time() + timeout_s
        pattern = f"*__{task_id}__fix_instruction.md"
        while time.time() < deadline:
            matches = sorted(self.outbox.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            if matches: return matches[0]
            time.sleep(poll_s)
        return None

    def read_fix_instruction(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

if __name__ == "__main__":
    client = AntimoltbotClient()
    print(f"AntimoltbotClient initialized at {client.base}")
'''

CONTENT_WRITE_ATOMIC_PY = r'''#!/usr/bin/env python3
"""Atomic-ish writer for Antimoltbot protocol files."""
from __future__ import annotations
import os
from pathlib import Path
import argparse

def write_atomic(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding=encoding, newline="\n") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--content", required=True)
    args = ap.parse_args()
    write_atomic(Path(args.path), args.content)
    print(f"WROTE: {args.path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''

CONTENT_LINT_PS1 = r'''param([string]$Base = "E:\antimoltbot")
$ErrorActionPreference = "Stop"
function Fail($msg) { Write-Host "FAIL: $msg" -ForegroundColor Red; exit 1 }
$inbox = Join-Path $Base "inbox"; $outbox = Join-Path $Base "outbox"
if (-not (Test-Path $inbox)) { Fail "missing inbox/" }
if (-not (Test-Path $outbox)) { Fail "missing outbox/" }
$files = @(Get-ChildItem -LiteralPath $inbox -File -Filter "*.md" -ErrorAction SilentlyContinue) + @(Get-ChildItem -LiteralPath $outbox -File -Filter "*.md" -ErrorAction SilentlyContinue)
$re = '^[0-9]{8}_[0-9]{6}__T[0-9]{8}-[0-9]{6}-[A-Za-z0-9]+__(error_report|fix_instruction|ack_read|ack_applied|status)\.md$'
foreach ($f in $files) {
  if ($f.Name -notmatch $re) { Fail "bad filename: $($f.Name)" }
  $text = Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8
  if (-not ($text.StartsWith("---"))) { Fail "missing YAML frontmatter start in $($f.Name)" }
}
Write-Host "OK" -ForegroundColor Green
exit 0
'''

CONTENT_TEMPLATE_ERROR = r'''---
type: error_report
taskId: TYYYYMMDD-HHMMSS-XX
timestamp: {{TIMESTAMP}}
iteration: 1
agent: antigravity
summary: "(Summary)"
---
# Error Report
## 목표
...
## 에러 메시지
...
'''

CONTENT_TEMPLATE_FIX = r'''---
type: fix_instruction
taskId: {{TASK_ID}}
timestamp: {{TIMESTAMP}}
iteration: {{ITERATION}}
agent: codex
risk: low
summary: "Fix summary"
---
# Fix Instruction
## 1) 원인 분석
## 2) 수정안
## 3) 테스트 방법
'''

# --- 실행 로직 ---

def create_file(path_str, content):
    p = Path(path_str)
    # create parent if needed, but usually redundant with strict loop below
    p.parent.mkdir(parents=True, exist_ok=True)
    # write
    p.write_text(content, encoding='utf-8')
    print(f"Created: {p}")

def main():
    root = Path(ROOT_DIR)
    
    print(f"🚀 Migrating Antimoltbot to: {root}")

    # Directories
    for d in ["inbox", "outbox", "backup", "current", "docs", "templates", "tools", "workspace"]:
        (root / d).mkdir(parents=True, exist_ok=True)

    # Files
    create_file(root / "workspace/antigravity_helper.py", CONTENT_HELPER)
    create_file(root / "tools/write_atomic.py", CONTENT_WRITE_ATOMIC_PY)
    create_file(root / "tools/protocol_lint.ps1", CONTENT_LINT_PS1)
    create_file(root / "templates/error_report.md", CONTENT_TEMPLATE_ERROR)
    create_file(root / "templates/fix_instruction.md", CONTENT_TEMPLATE_FIX)
    
    print("\n✅ Migration complete!")
    print(f"New system root: {ROOT_DIR}")

if __name__ == "__main__":
    main()

"""Board —— 协作黑板状态机（单写者）。

状态机：idle → working → done | error
- init: idle → working（working 期间拒绝新 init，抛 BoardBusyError）
- complete: working → done
- fail: working → error
- 黑板文件唯一写者：本模块。写入用原子替换（tmp + rename）。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class BoardBusyError(RuntimeError):
    """已有任务在跑，拒绝新 init。"""


class Board:
    STATUSES = ("idle", "working", "blocked", "done", "error")

    def __init__(self, root: Path) -> None:
        self.path = Path(root) / "task_board.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ---- 内部 ----

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"status": "idle"}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"status": "error", "error": "黑板文件损坏"}

    def _save(self, state: dict[str, Any]) -> dict[str, Any]:
        state["updated_at"] = time.time()
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)  # 原子替换，避免并发读看到半截文件
        return state

    def _must_be(self, state: dict[str, Any], status: str | tuple[str, ...]) -> None:
        if state.get("status") not in (status if isinstance(status, tuple) else (status,)):
            raise RuntimeError(f"黑板状态为 {state.get('status')!r}，期望 {status!r}")

    # ---- 公开操作 ----

    def init(self, task: str, workspace: str) -> dict[str, Any]:
        state = self._load()
        if state.get("status") in ("working", "blocked"):
            raise BoardBusyError(f"已有任务在执行: {state.get('task')!r}")
        self._must_be(state, ("idle", "done", "error"))  # done/error 视为可重置
        self._save(
            {
                "status": "working",
                "task": task,
                "workspace": workspace,
                "pid": None,
                "created_at": time.time(),
            }
        )
        return self.read()

    def read(self) -> dict[str, Any]:
        return self._load()

    def complete(self, result: str) -> dict[str, Any]:
        state = self._load()
        self._must_be(state, ("working", "blocked"))
        state.update({"status": "done", "result": result})
        return self._save(state)

    def fail(self, error: str) -> dict[str, Any]:
        state = self._load()
        self._must_be(state, ("working", "blocked"))
        state.update({"status": "error", "error": error})
        return self._save(state)

    def block(self, request_id: str, message: str) -> dict[str, Any]:
        """working → blocked：DSH 在请求权限/澄清。"""
        state = self._load()
        self._must_be(state, "working")
        state.update({"status": "blocked", "request_id": request_id, "request_message": message})
        return self._save(state)

    def respond(self, allow: bool) -> dict[str, Any]:
        """blocked → working：应答权限请求后继续。"""
        state = self._load()
        self._must_be(state, "blocked")
        state.update({"status": "working"})
        return self._save(state)

    def attach_pid(self, pid: int) -> dict[str, Any]:
        state = self._load()
        self._must_be(state, "working")
        state["pid"] = pid
        return self._save(state)

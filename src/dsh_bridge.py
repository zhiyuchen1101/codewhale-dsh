"""dsh-bridge —— 把 DeepSeek Harness 作为 codewhale 子 agent 的 MCP 薄壳。

薄壳原则：只翻译协议（MCP 工具 ↔ DSH headless 进程），不跑 Agent、不决策。
黑板（Board）是唯一状态源；DSH 进程是唯一工人。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from fastmcp import FastMCP

from board import Board, BoardBusyError
from token_stats import session_path, sum_usage

BRIDGE_ROOT = Path(os.environ.get("DSH_BRIDGE_ROOT", str(Path.home() / ".codewhale-dsh")))
RUN_DIR = BRIDGE_ROOT / "run"

# 驱动选择：acp（默认，流式/可取消）| headless（fallback，零依赖）
DRIVER = os.environ.get("DSH_DRIVER", "acp")

board = Board(BRIDGE_ROOT)
_ACTIVE_PROCS: dict[str, subprocess.Popen] = {}  # run_id → acp_client 进程（respond/cancel 用）


def _dsh_bin() -> str:
    found = shutil.which("dsh")
    if not found:
        raise RuntimeError("dsh 不在 PATH 中，请先安装 DeepSeek Harness")
    return found


def _api_key() -> str:
    """优先环境变量，否则读 ~/.dsh/.credentials.yaml（DSH 凭据）。"""
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key
    try:
        import yaml
        cred = yaml.safe_load(Path.home().joinpath(".dsh", ".credentials.yaml").read_text(encoding="utf-8"))
        return cred.get("DEEPSEEK_API_KEY", "") or ""
    except (ImportError, OSError, AttributeError):
        return ""


def _fmt(state: dict) -> str:
    return json.dumps(state, ensure_ascii=False, default=str)


def _spawn(task: str, workspace: str) -> int:
    """后台启动 DSH，返回 pid。输出落到 run/ 目录。"""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    out_path = RUN_DIR / f"{run_id}.out"
    err_path = RUN_DIR / f"{run_id}.err"
    exit_path = RUN_DIR / f"{run_id}.exit"
    ws = Path(workspace).expanduser()
    ws.mkdir(parents=True, exist_ok=True)

    if DRIVER == "headless":
        cmd = (
            f"cd {shlex_quote(str(ws))} && "
            f"{shlex_quote(_dsh_bin())} --profile headless {shlex_quote(task)} "
            f"> {shlex_quote(str(out_path))} 2> {shlex_quote(str(err_path))}; "
            f"echo $? > {shlex_quote(str(exit_path))}"
        )
    else:  # acp：Node acp_client，行协议喂任务，chunk 落 out，done/error 写 exit
        client_cmd = [
            "node", str(Path(__file__).resolve().parent / "acp_client.mjs"),
        ]
        env = dict(os.environ)
        key = _api_key()
        if key:
            env["DEEPSEEK_API_KEY"] = key
        proc = subprocess.Popen(
            client_cmd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=Path(__file__).resolve().parent.parent,
            text=True, bufsize=1,
            env=env,
        )
        proc.stdin.write(json.dumps({"id": run_id, "action": "run", "task": task, "workspace": str(ws)}) + "\n")
        proc.stdin.flush()
        # 读行协议：chunk 写 out，permission_request 转黑板 blocked，done/error 写 exit
        def pump():
            try:
                for line in proc.stdout:
                    ev = json.loads(line)
                    t = ev.get("type")
                    if t == "chunk":
                        with open(out_path, "a", encoding="utf-8") as f:
                            f.write(ev.get("text", ""))
                    elif t == "permission_request":
                        try:
                            board.block(
                                request_id=ev.get("requestId", "?"),
                                message=ev.get("message", "DSH 请求权限")[:500],
                            )
                        except RuntimeError:
                            pass  # 状态非 working 时忽略
                    elif t == "done":
                        with open(exit_path, "w") as f:
                            f.write("0" if ev.get("stopReason") == "end_turn" else "1")
                        if ev.get("stopReason") != "end_turn":
                            with open(err_path, "w") as f:
                                f.write(f"stopReason: {ev.get('stopReason')}")
                        sid = ev.get("sessionId")
                        if sid:
                            with open(RUN_DIR / f"{run_id}.session", "w") as f:
                                f.write(sid)
                    elif t == "error":
                        with open(exit_path, "w") as f:
                            f.write("1")
                        with open(err_path, "w") as f:
                            f.write(ev.get("message", ""))
            except (json.JSONDecodeError, OSError, ValueError):
                pass
            finally:
                try:
                    proc.stdin.close()
                except OSError:
                    pass
        import threading
        threading.Thread(target=pump, daemon=True).start()
        _ACTIVE_PROCS[run_id] = proc

    proc = subprocess.Popen(
        ["/bin/bash", "-c", cmd],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) if DRIVER == "headless" else proc
    # 记下输出路径供 dsh_read 使用
    state = board.read()
    state["run_id"] = run_id
    state["out_path"] = str(out_path)
    state["err_path"] = str(err_path)
    state["exit_path"] = str(exit_path)
    state["driver"] = DRIVER
    board._save(state)
    return proc.pid


def shlex_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def _check_done() -> dict:
    """轮询进程与退出码文件：进程退出且 exit 文件存在 → complete/fail。"""
    state = board.read()
    if state.get("status") != "working":
        return state
    exit_path = Path(state.get("exit_path", ""))
    if exit_path.exists():
        code = exit_path.read_text(encoding="utf-8").strip()
        try:
            rc = int(code)
        except ValueError:
            rc = -1
        if rc == 0:
            result = Path(state.get("out_path", "")).read_text(encoding="utf-8", errors="replace").strip()
            result = _attach_tokens(result, state)
            return board.complete(result=result or "(无输出)")
        err = Path(state.get("err_path", "")).read_text(encoding="utf-8", errors="replace").strip()
        return board.fail(error=f"DSH 退出码 {rc}: {err[:500]}")
    pid = state.get("pid")
    if pid:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            # 进程已退出但 exit 文件还没写好（极短窗口），等下一轮
            pass
        except PermissionError:
            pass
    return state


def _attach_tokens(result: str, state: dict) -> str:
    """ACP 驱动：从 DSH 会话文件读 token 用量，附到结果尾部。"""
    if state.get("driver") != "acp":
        return result
    run_id = state.get("run_id")
    if not run_id:
        return result
    sid_file = RUN_DIR / f"{run_id}.session"
    if not sid_file.exists():
        return result
    sid = sid_file.read_text(encoding="utf-8").strip()
    sessions_root = Path(os.environ.get("DSH_SESSIONS_ROOT", str(Path.home() / "deepseek-harness" / ".sessions")))
    usage = sum_usage(session_path(sessions_root, sid))
    if not any(usage.values()):
        return result
    tokens = (
        f"\n[tokens] input={usage['inputTokens']} output={usage['outputTokens']} "
        f"cache={usage['cacheReadTokens']} reasoning={usage['reasoningTokens']}"
    )
    return result + tokens


mcp = FastMCP("dsh-bridge")


@mcp.tool()
def dsh_init(task: str, workspace: str) -> str:
    """派活给 DSH 子 agent：启动一次 headless 任务。任务未完成时拒绝新任务。"""
    try:
        state = board.init(task=task, workspace=workspace)
        pid = _spawn(task, workspace)
        state = board.attach_pid(pid)
        return _fmt(state)
    except BoardBusyError as e:
        raise ValueError(str(e)) from e


@mcp.tool()
def dsh_status() -> str:
    """查 DSH 任务状态：working / done / error。进程结束自动收账。"""
    return _fmt(_check_done())


@mcp.tool()
def dsh_read() -> str:
    """读 DSH 任务完整结果（done 后可用）。"""
    state = _check_done()
    if state.get("status") != "done":
        return _fmt(state)
    return _fmt({"status": "done", "result": state.get("result")})


@mcp.tool()
def dsh_respond(allow: bool) -> str:
    """应答 DSH 的权限/澄清请求（黑板 blocked 时可用）：allow=true 放行，false 拒绝。"""
    state = board.read()
    if state.get("status") != "blocked":
        raise ValueError(f"当前状态 {state.get('status')!r}，没有待应答的请求")
    run_id = state.get("run_id")
    proc = _ACTIVE_PROCS.get(run_id) if run_id else None
    if proc is None or proc.poll() is not None:
        # 进程已退出：直接恢复黑板，让收账逻辑处理
        return _fmt(board.respond(allow=allow))
    try:
        proc.stdin.write(json.dumps({"id": run_id, "action": "respond", "allow": allow}) + "\n")
        proc.stdin.flush()
    except (OSError, ValueError) as e:
        raise ValueError(f"无法送达应答: {e}") from e
    return _fmt(board.respond(allow=allow))


@mcp.tool()
def dsh_cancel() -> str:
    """中断 DSH 任务：ACP 驱动走优雅 session/cancel，超时兜底 kill。"""
    state = board.read()
    run_id = state.get("run_id")
    proc = _ACTIVE_PROCS.get(run_id) if run_id else None
    if DRIVER == "acp" and proc is not None and proc.poll() is None:
        try:
            proc.stdin.write(json.dumps({"id": run_id, "action": "cancel"}) + "\n")
            proc.stdin.flush()
            proc.wait(timeout=10)
            return _fmt(board.fail(error="已取消（优雅）"))
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        # 兜底：强杀
    pid = state.get("pid")
    if pid:
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass
    return _fmt(board.fail(error="已取消"))


if __name__ == "__main__":
    mcp.run(transport="stdio")

"""dsh-bridge —— 把 DeepSeek Harness 作为 codewhale 子 agent 的 MCP 薄壳。

薄壳原则：只翻译协议（MCP 工具 ↔ DSH 进程），不跑 Agent、不决策。
黑板（Board）是唯一状态源；DSH 进程是唯一工人。
驱动：acp（默认，官方 ACP 协议，流式/思考流/可取消）| headless（fallback）。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

from fastmcp import FastMCP

from board import Board, BoardBusyError
from token_stats import read_session_events, reasoning_texts, session_path, sum_usage

BRIDGE_ROOT = Path(os.environ.get("DSH_BRIDGE_ROOT", str(Path.home() / ".codewhale-dsh")))
RUN_DIR = BRIDGE_ROOT / "run"

# 驱动选择：acp（默认，流式/可取消）| headless（fallback，零依赖）
DRIVER = os.environ.get("DSH_DRIVER", "acp")
# 任务超时兜底：黑板卡在 working 超过此时长即判失败（默认 30 分钟）
TASK_TIMEOUT_SECS = int(os.environ.get("DSH_TASK_TIMEOUT", "1800"))
# DSH 会话日志根（token/思考流数据源）
SESSIONS_ROOT = Path(os.environ.get("DSH_SESSIONS_ROOT", str(Path.home() / "deepseek-harness" / ".sessions")))

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


def shlex_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def _poll_thinking(run_id: str, session_id: str) -> None:
    """轮询 DSH 会话日志，把新增 reasoning-chunks 追加到 <run_id>.thinking（思考流可见）。"""
    thinking_path = RUN_DIR / f"{run_id}.thinking"
    exit_path = RUN_DIR / f"{run_id}.exit"
    sp = session_path(SESSIONS_ROOT, session_id)
    last_len = 0
    while not exit_path.exists():
        try:
            events = read_session_events(sp)
            t = reasoning_texts(events)
            if len(t) > last_len:
                with open(thinking_path, "a", encoding="utf-8") as f:
                    f.write(t[last_len:])
                last_len = len(t)
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
            pass
        time.sleep(0.5)  # 日志 chunk 级实时写入，0.5s 轮询 ≈ 秒级实时


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
        proc = subprocess.Popen(
            ["/bin/bash", "-c", cmd],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # 独立进程组：取消时可 killpg 连子进程一起杀
        )
    else:  # acp：Node acp_client，行协议喂任务
        env = dict(os.environ)
        key = _api_key()
        if key:
            env["DEEPSEEK_API_KEY"] = key
        proc = subprocess.Popen(
            ["node", str(Path(__file__).resolve().parent / "acp_client.mjs")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=Path(__file__).resolve().parent.parent,
            text=True, bufsize=1,
            env=env,
        )
        proc.stdin.write(json.dumps({"id": run_id, "action": "run", "task": task, "workspace": str(ws)}) + "\n")
        proc.stdin.flush()
        _ACTIVE_PROCS[run_id] = proc

        def pump():
            try:
                for line in proc.stdout:
                    ev = json.loads(line)
                    t = ev.get("type")
                    if t == "chunk":
                        with open(out_path, "a", encoding="utf-8") as f:
                            f.write(ev.get("text", ""))
                    elif t == "session_ready":
                        sid = ev.get("sessionId")
                        if sid:
                            state = board.read()
                            state["session_id"] = sid
                            board._save(state)
                            threading.Thread(target=_poll_thinking, args=(run_id, sid), daemon=True).start()
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

        threading.Thread(target=pump, daemon=True).start()

    state = board.read()
    state["run_id"] = run_id
    state["out_path"] = str(out_path)
    state["err_path"] = str(err_path)
    state["exit_path"] = str(exit_path)
    state["driver"] = DRIVER
    board._save(state)
    return proc.pid


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
            # 进程已死但 exit 文件没写（pump 崩溃/被强杀）——不能死等（DSH 审查问题 2）
            return board.fail(error="DSH 进程已退出但未写退出码（pump/子进程异常？）")
        except PermissionError:
            pass
    # 超时兜底：卡在 working 超过 TASK_TIMEOUT_SECS
    created = state.get("created_at") or 0
    if time.time() - created > TASK_TIMEOUT_SECS:
        return board.fail(error=f"任务超时（>{TASK_TIMEOUT_SECS}s），已强制终止")
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
    usage = sum_usage(session_path(SESSIONS_ROOT, sid))
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
    """派活给 DSH 子 agent。任务未完成时拒绝新任务。"""
    try:
        state = board.init(task=task, workspace=workspace)
        try:
            pid = _spawn(task, workspace)
            state = board.attach_pid(pid)
        except Exception as e:
            # 启动失败必须回滚黑板（DSH 审查问题 1）
            board.fail(error=f"启动 DSH 失败: {e}")
            raise
        return _fmt(state)
    except BoardBusyError as e:
        raise ValueError(str(e)) from e


@mcp.tool()
def dsh_status() -> str:
    """查 DSH 任务状态。working 时附思考摘要（思考流可见）。进程结束自动收账。"""
    state = _check_done()
    if state.get("status") == "working":
        run_id = state.get("run_id")
        if run_id:
            tp = RUN_DIR / f"{run_id}.thinking"
            if tp.exists():
                text = tp.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    state["thinking"] = text[-200:]
    return _fmt(state)


@mcp.tool()
def dsh_read() -> str:
    """读 DSH 任务完整结果（done 后可用）。"""
    state = _check_done()
    if state.get("status") != "done":
        return _fmt(state)
    return _fmt({"status": "done", "result": state.get("result")})


@mcp.tool()
def dsh_respond(allow: bool) -> str:
    """应答 DSH 的权限/澄清请求（黑板 blocked 时可用）。"""
    state = board.read()
    if state.get("status") != "blocked":
        raise ValueError(f"当前状态 {state.get('status')!r}，没有待应答的请求")
    run_id = state.get("run_id")
    proc = _ACTIVE_PROCS.get(run_id) if run_id else None
    if proc is None or proc.poll() is not None:
        return _fmt(board.respond(allow=allow))
    try:
        proc.stdin.write(json.dumps({"id": run_id, "action": "respond", "allow": allow}) + "\n")
        proc.stdin.flush()
    except (OSError, ValueError) as e:
        raise ValueError(f"无法送达应答: {e}") from e
    return _fmt(board.respond(allow=allow))


@mcp.tool()
def dsh_cancel() -> str:
    """中断 DSH 任务：ACP 走优雅 session/cancel，超时兜底 killpg。"""
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
        # 兜底：强杀（headless 独立进程组，连子进程一起杀）
    pid = state.get("pid")
    if pid:
        try:
            os.killpg(os.getpgid(pid), 9)
        except (ProcessLookupError, PermissionError):
            try:
                os.kill(pid, 9)
            except (ProcessLookupError, PermissionError):
                pass
    return _fmt(board.fail(error="已取消"))


if __name__ == "__main__":
    mcp.run(transport="stdio")

"""RED→GREEN: dsh_bridge 单元测试（mock DSH 进程，不真跑模型）。

覆盖：
- dsh_init 正常派活
- working 期间 dsh_init 拒绝（BoardBusyError → ValueError）
- _check_done: exit=0 → done + result；exit!=0 → error + stderr
- dsh_cancel → error
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import dsh_bridge as b
from board import Board


@pytest.fixture
def bridge_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DSH_BRIDGE_ROOT", str(tmp_path))
    monkeypatch.setattr(b, "BRIDGE_ROOT", tmp_path)
    monkeypatch.setattr(b, "RUN_DIR", tmp_path / "run")
    monkeypatch.setattr(b, "board", Board(tmp_path))
    return tmp_path


def _fake_spawn_ok(monkeypatch, tmp_path, rc=0, out="完成", err=""):
    """mock _spawn：直接写好 exit/out/err 文件，模拟进程已完成。"""
    run_id = "test0001"
    exit_path = tmp_path / "run" / f"{run_id}.exit"
    out_path = tmp_path / "run" / f"{run_id}.out"
    err_path = tmp_path / "run" / f"{run_id}.err"
    (tmp_path / "run").mkdir(exist_ok=True)
    exit_path.write_text(str(rc))
    out_path.write_text(out)
    err_path.write_text(err)

    def fake_spawn(task, workspace):
        state = b.board.read()
        state["run_id"] = run_id
        state["out_path"] = str(out_path)
        state["err_path"] = str(err_path)
        state["exit_path"] = str(exit_path)
        b.board._save(state)
        return 99999  # 不存在的 pid

    monkeypatch.setattr(b, "_spawn", fake_spawn)
    return exit_path


def test_init_and_status_done(bridge_env, tmp_path, monkeypatch):
    _fake_spawn_ok(monkeypatch, tmp_path)
    r = b.dsh_init(task="任务A", workspace="/tmp")
    assert '"working"' in r
    s = b.dsh_status()
    assert '"done"' in s and "完成" in s


def test_init_rejected_while_working(bridge_env, tmp_path, monkeypatch):
    def fake_spawn(task, workspace):
        return 99999

    monkeypatch.setattr(b, "_spawn", fake_spawn)
    b.dsh_init(task="任务A", workspace="/tmp")
    with pytest.raises(ValueError):
        b.dsh_init(task="任务B", workspace="/tmp")


def test_fail_captures_stderr(bridge_env, tmp_path, monkeypatch):
    _fake_spawn_ok(monkeypatch, tmp_path, rc=1, err="boom: model timeout")
    b.dsh_init(task="任务A", workspace="/tmp")
    s = b.dsh_status()
    assert '"error"' in s and "boom: model timeout" in s


def test_cancel_marks_error(bridge_env, tmp_path, monkeypatch):
    def fake_spawn(task, workspace):
        return 99999

    monkeypatch.setattr(b, "_spawn", fake_spawn)
    b.dsh_init(task="任务A", workspace="/tmp")
    r = b.dsh_cancel()
    assert '"error"' in r and "已取消" in r


# === 阶段 D+ 回归：DSH 审查发现的问题 ===

def _fake_os_module(monkeypatch, kill_impl):
    """替换 dsh_bridge.os 为假模块（只改 kill，其余委托真 os）。"""
    import os as real_os
    import types
    fake = types.ModuleType("fake_os")
    for name in dir(real_os):
        setattr(fake, name, getattr(real_os, name))
    fake.kill = kill_impl
    monkeypatch.setattr(b, "os", fake)
    return fake


def test_stale_process_without_exit_fails(bridge_env, tmp_path, monkeypatch):
    """问题2：进程已死但 exit 文件不存在 → 必须判 fail，不能永久 working。"""
    def fake_spawn(task, workspace):
        # 设置 exit_path 指向一个永远不存在的文件（模拟 pump 异常未写退出码）
        state = b.board.read()
        state["exit_path"] = str(tmp_path / "run" / "never.exit")
        state["out_path"] = str(tmp_path / "run" / "never.out")
        state["err_path"] = str(tmp_path / "run" / "never.err")
        b.board._save(state)
        return 99999  # 不存在的 pid

    monkeypatch.setattr(b, "_spawn", fake_spawn)
    b.dsh_init(task="任务A", workspace="/tmp")
    # 模拟：exit 文件从未生成，进程已死（os.kill 抛 ProcessLookupError）
    _fake_os_module(monkeypatch, lambda pid, sig: (_ for _ in ()).throw(ProcessLookupError()))
    s = b.dsh_status()
    assert '"error"' in s, f"FAIL: 应判 error，实际 {s[:120]}"


def test_init_spawn_failure_rolls_back(bridge_env, tmp_path, monkeypatch):
    """问题1：_spawn 抛异常 → 黑板回滚为 error，不能停在 working。"""
    def broken_spawn(task, workspace):
        raise RuntimeError("spawn 失败")

    monkeypatch.setattr(b, "_spawn", broken_spawn)
    with pytest.raises(RuntimeError):
        b.dsh_init(task="任务A", workspace="/tmp")
    assert b.board.read()["status"] == "error"


def test_timeout_guard_fails_stale_task(bridge_env, tmp_path, monkeypatch):
    """超时兜底：任务超过 DSH_TASK_TIMEOUT 秒仍在 working → 判 fail。"""
    import dsh_bridge as bb
    monkeypatch.setattr(bb, "TASK_TIMEOUT_SECS", 60)
    state = bb.board.init(task="任务A", workspace="/tmp")
    state["exit_path"] = str(tmp_path / "run" / "never.exit")
    state["out_path"] = str(tmp_path / "run" / "never.out")
    state["err_path"] = str(tmp_path / "run" / "never.err")
    # created_at 改成 100 秒前
    import time as _t
    state["created_at"] = _t.time() - 100
    bb.board._save(state)
    # 进程"活着"（kill 不抛错），但超时了
    _fake_os_module(monkeypatch, lambda pid, sig: None)
    s = bb.dsh_status()
    assert '"error"' in s and "超时" in s, f"FAIL: {s[:120]}"

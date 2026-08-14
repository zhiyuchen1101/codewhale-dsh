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

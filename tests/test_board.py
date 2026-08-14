"""RED: 黑板状态机测试 —— 先写测试，再写实现。

状态机：idle → working → done | error
规则：
- init 创建任务并置 working；working 期间拒绝新 init（执行锁）
- complete 置 done；fail 置 error
- 黑板文件单写者（由 Board 实例独占）
"""
from pathlib import Path

import pytest

from src.board import Board, BoardBusyError


@pytest.fixture
def board(tmp_path: Path) -> Board:
    return Board(tmp_path)


def test_board_init_creates_working_status(board: Board):
    board.init(task="跑测试", workspace="/tmp/demo")
    state = board.read()
    assert state["status"] == "working"
    assert state["task"] == "跑测试"
    assert state["workspace"] == "/tmp/demo"


def test_board_rejects_init_while_working(board: Board):
    board.init(task="任务1", workspace="/tmp/a")
    with pytest.raises(BoardBusyError):
        board.init(task="任务2", workspace="/tmp/b")
    state = board.read()
    assert state["task"] == "任务1"


def test_board_complete_transitions_to_done(board: Board):
    board.init(task="跑测试", workspace="/tmp/demo")
    board.complete(result="全部通过")
    state = board.read()
    assert state["status"] == "done"
    assert state["result"] == "全部通过"


def test_board_fail_transitions_to_error(board: Board):
    board.init(task="跑测试", workspace="/tmp/demo")
    board.fail(error="DSH 进程崩溃")
    state = board.read()
    assert state["status"] == "error"
    assert "DSH 进程崩溃" in state["error"]


def test_board_complete_without_init_raises(board: Board):
    with pytest.raises(RuntimeError):
        board.complete(result="x")


def test_board_persists_across_instances(tmp_path: Path):
    b1 = Board(tmp_path)
    b1.init(task="持久化", workspace="/tmp/demo")
    b2 = Board(tmp_path)
    assert b2.read()["status"] == "working"
    assert b2.read()["task"] == "持久化"


def test_board_init_resets_after_error(tmp_path: Path):
    b = Board(tmp_path)
    b.init(task="任务1", workspace="/tmp/a")
    b.fail(error="崩了")
    b.init(task="任务2", workspace="/tmp/b")
    assert b.read()["status"] == "working"
    assert b.read()["task"] == "任务2"


def test_board_init_resets_after_done(tmp_path: Path):
    b = Board(tmp_path)
    b.init(task="任务1", workspace="/tmp/a")
    b.complete(result="ok")
    b.init(task="任务2", workspace="/tmp/b")
    assert b.read()["status"] == "working"
    assert b.read()["task"] == "任务2"


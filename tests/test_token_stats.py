"""token_stats 单元测试：用真实 DSH 会话文件验证解析与累加。"""
from pathlib import Path

import pytest

from src.token_stats import read_session_events, session_path, sum_usage

# 合成 fixture：最小 usage 事件（无真实环境内容）
FIXTURE = Path(__file__).parent / "fixtures" / "session.jsonl.zstd"


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture 未生成（真实会话文件）")
def test_read_session_events_parses():
    events = read_session_events(FIXTURE)
    assert len(events) > 0
    types = {e.get("type") for e in events}
    assert "assistant/message" in types


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture 未生成")
def test_sum_usage_accumulates():
    u = sum_usage(FIXTURE)
    assert u == {"inputTokens": 300, "outputTokens": 30, "cacheReadTokens": 110, "reasoningTokens": 13}


def test_sum_usage_missing_file_returns_zeros(tmp_path):
    u = sum_usage(tmp_path / "nope.zstd")
    assert u == {"inputTokens": 0, "outputTokens": 0, "cacheReadTokens": 0, "reasoningTokens": 0}


def test_session_path_layout():
    p = session_path(Path("/root/.sessions"), "abc-123")
    assert p == Path("/root/.sessions/--tmp--/abc-123/session.jsonl.zstd")

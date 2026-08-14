"""token_stats —— 从 DSH 会话文件（session.jsonl.zstd）统计 token 用量。

数据源：DSH 持久化会话日志，assistant/message 事件带 usage 字段：
  {"type": "assistant/message", ..., "usage": {"inputTokens": N, "outputTokens": N,
   "cacheReadTokens": N, "reasoningTokens": N}}
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    import zstandard
except ImportError:  # pragma: no cover
    zstandard = None


def read_session_events(path: Path) -> list[dict]:
    """解压并解析 session.jsonl.zstd，返回事件列表。"""
    if zstandard is None:
        raise RuntimeError("缺少 zstandard 库：pip install zstandard")
    with open(path, "rb") as fh:
        with zstandard.ZstdDecompressor().stream_reader(fh) as r:
            data = r.read()
    return [json.loads(l) for l in data.decode().splitlines() if l.strip()]


def sum_usage(path: Path) -> dict[str, int]:
    """累加所有 assistant/message 的 usage，返回汇总。"""
    total = {"inputTokens": 0, "outputTokens": 0, "cacheReadTokens": 0, "reasoningTokens": 0}
    try:
        events = read_session_events(path)
    except (OSError, RuntimeError, json.JSONDecodeError):
        return total
    for ev in events:
        if ev.get("type") != "assistant/message":
            continue
        usage = ev.get("data", {}).get("usage") or {}
        for k in total:
            total[k] += int(usage.get(k, 0) or 0)
    return total


def session_path(sessions_root: Path, session_id: str) -> Path:
    """DSH ACP demo 的会话文件路径：<root>/--tmp--/<sessionId>/session.jsonl.zstd"""
    return Path(sessions_root) / "--tmp--" / session_id / "session.jsonl.zstd"

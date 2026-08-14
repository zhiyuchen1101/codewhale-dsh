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


def reasoning_texts(events: list[dict]) -> str:
    """拼接所有 reasoning-chunks 的 texts（DSH 的思考流）。"""
    parts = []
    for ev in events:
        if ev.get("type") != "reasoning-chunks":
            continue
        texts = ev.get("data", {}).get("texts") or []
        parts.extend(t for t in texts if isinstance(t, str))
    return "".join(parts)


class IncrementalZstdReader:
    """增量读 zstd JSONL：维护字节偏移 + 续解，适合追加写入的会话日志。"""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.offset = 0
        self.dobj = None
        self.buf = b""
        self._reset()

    def _reset(self):
        self.offset = 0
        self.dobj = zstandard.ZstdDecompressor().decompressobj()
        self.buf = b""

    def read_new_lines(self) -> list[str]:
        try:
            with open(self.path, "rb") as f:
                f.seek(self.offset)
                chunk = f.read()
                new_offset = f.tell()
            if new_offset == self.offset:
                return []
            self.offset = new_offset
            try:
                out = self.dobj.decompress(chunk)
            except zstandard.ZstdError:
                # 文件被重写（offset 失效）：重置重来
                self._reset()
                with open(self.path, "rb") as f:
                    chunk = f.read()
                self.offset = f.tell()
                out = self.dobj.decompress(chunk)
        except OSError:
            return []
        self.buf += out
        lines = self.buf.split(b"\n")
        self.buf = lines.pop()
        return [l.decode("utf-8", errors="replace") for l in lines if l.strip()]

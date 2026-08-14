#!/usr/bin/env python3
"""dsh-watch —— 鲸鱼观察窗：实时彩色显示 DSH 子 agent 的思考流。

用法：任务运行中，在第二个终端运行：
    ~/codewhale-dsh/.venv/bin/python ~/codewhale-dsh/scripts/dsh_watch.py

实时读黑板状态 + .thinking 文件，ANSI 彩色输出。Ctrl+C 退出。
"""
import json
import os
import sys
import time
from pathlib import Path

BRIDGE_ROOT = Path(os.environ.get("DSH_BRIDGE_ROOT", str(Path.home() / ".codewhale-dsh")))
RUN_DIR = BRIDGE_ROOT / "run"
BOARD = BRIDGE_ROOT / "task_board.json"

C = {
    "blue": "\033[38;5;81m",
    "cyan": "\033[96m",
    "dim": "\033[2m",
    "green": "\033[92m",
    "red": "\033[91m",
    "yellow": "\033[93m",
    "reset": "\033[0m",
}


def board_state() -> dict:
    try:
        return json.loads(BOARD.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> None:
    print(f"{C['cyan']}🐋 DSH 观察窗{C['reset']}  {C['dim']}(Ctrl+C 退出){C['reset']}")
    last = 0
    last_status = None
    while True:
        st = board_state()
        status = st.get("status", "idle")
        run_id = st.get("run_id")
        if status != last_status:
            print(f"\n{C['yellow']}── 状态: {status}{C['reset']}")
            last_status = status
        if status == "working" and run_id:
            tp = RUN_DIR / f"{run_id}.thinking"
            if tp.exists():
                text = tp.read_text(errors="replace")
                if len(text) > last:
                    piece = text[last:]
                    last = len(text)
                    for i in range(0, len(piece), 60):
                        print(f"{C['blue']}{piece[i:i+60].strip()}{C['reset']}", flush=True)
        elif status == "done":
            if last_status != "done":
                print(f"\n{C['green']}✅ 完成{C['reset']}")
                print(f"{C['dim']}{st.get('result', '')[:200]}{C['reset']}")
                last_status = "done"
            time.sleep(3)
        elif status == "error":
            if last_status != "error":
                print(f"\n{C['red']}❌ {st.get('error', '')[:200]}{C['reset']}")
                last_status = "error"
            time.sleep(3)
        elif status == "blocked":
            print(f"\n{C['yellow']}🔔 求助: {st.get('request_message', '')[:200]}{C['reset']}")
            time.sleep(1)
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C['dim']}观察结束{C['reset']}")

"""集成测试 acp_client：起 Node 子进程，喂行协议，验证输出。"""
import json, subprocess, sys, time

def run_acp(env_extra, task, timeout=30):
    env = {"PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin", **env_extra}
    p = subprocess.Popen(
        ["node", "src/acp_client.mjs"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1, env=env,
    )
    p.stdin.write(json.dumps({"id": 1, "action": "run", "task": task, "workspace": "/tmp"}) + "\n")
    p.stdin.flush()
    events = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = p.stdout.readline()
        if not line:
            break
        ev = json.loads(line)
        events.append(ev)
        if ev.get("type") in ("done", "error"):
            break
    p.kill()
    return events

# 1. fake server 测试
print("== fake server ==")
evs = run_acp({"DSH_REPO": ".", "DSH_ACP_SERVER": '["node","tests/fake_acp_server.mjs"]'}, "hello")
kinds = [e["type"] for e in evs]
print("事件:", kinds)
assert "chunk" in kinds and "done" in kinds, f"FAIL: {evs}"
done = [e for e in evs if e["type"] == "done"][0]
assert done["stopReason"] == "end_turn", f"FAIL: {done}"
print("✅ fake server 链路 OK")

# 2. 真实 DSH server 测试（需要 DEEPSEEK_API_KEY + DSH 仓库；缺条件自动跳过）
import os
key = os.environ.get("DEEPSEEK_API_KEY")
if not key:
    import yaml
    try:
        key = yaml.safe_load(open(os.path.expanduser("~/.dsh/.credentials.yaml")))["DEEPSEEK_API_KEY"]
    except (FileNotFoundError, KeyError, ImportError):
        key = None
if not key or not os.path.isdir("~/deepseek-harness"):
    print("== 真实 DSH server ==")
    print("跳过：需要 DEEPSEEK_API_KEY 和 ~/deepseek-harness 仓库")
    sys.exit(0)
print("== 真实 DSH server ==")
evs = run_acp({"DSH_REPO": "~/deepseek-harness", "DEEPSEEK_API_KEY": key}, "只回复两个字：完成", timeout=90)
kinds = [e["type"] for e in evs]
print("事件:", kinds)
for e in evs:
    if e.get("type") == "chunk": print("  chunk:", e["text"])
    if e.get("type") == "done": print("  done:", e["stopReason"])
    if e.get("type") == "error": print("  error:", e["message"][:200])
assert "done" in kinds, f"FAIL: {evs}"
print("✅ 真实 DSH server 链路 OK")

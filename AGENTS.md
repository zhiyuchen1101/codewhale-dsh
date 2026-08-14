# AGENTS.md —— 本项目工作规则（codewhale 自动加载）

## 这是什么

codewhale-dsh：把 DeepSeek Harness 作为 codewhale 的子 agent。
架构：codewhale → MCP → dsh_bridge.py（FastMCP 薄壳）→ board.py（黑板）→ acp_client.mjs（官方 ACP SDK）→ DSH server。
工具：dsh_init / dsh_status / dsh_read / dsh_respond / dsh_cancel。

先读：`MEMORY.md`（状态与坑）· `docs/adr/`（设计决策）· `LOG.md`（最近进展）。

## 协作规则

1. TDD：先写 RED 测试再实现；`make test` 全绿才提交
2. 测试分两堆：`make test`（快）· `make test-acp`（重链路，需 ~/deepseek-harness + key）
3. 大决策先 grill 用户，共识后再动手；改动保持小步
4. 会话结束更新 LOG.md；状态变化更新 MEMORY.md

## Git push 红线（违反即拒绝）

1. **push 前检查**（三条命令全空才允许）：
   ```sh
   git grep -n "/Users/" $(git rev-list --all) | head
   git grep -nE "sk-[A-Za-z0-9]{16,}" $(git rev-list --all) | head
   git ls-files | grep -iE "\.env|credential|secret" | head
   ```
2. **测试全绿**：`make test` 必须通过
3. **未征求用户同意不 push**——尤其 force push / 重写历史 / 删分支；历史重写只在无他人 clone 时做，force push 后验证远程无残留
4. 运行产物（task_board.json / run/ / .sessions / .venv / node_modules）绝不提交
5. fixture 只用合成数据；测试路径用 `~` 展开，不写真实用户名路径
6. commit message 说明为什么，小步可回溯

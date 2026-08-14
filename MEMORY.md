# MEMORY —— 项目记忆

> 每次会话开始先读这里；状态变化后更新。与 docs/adr/（为什么）、LOG.md（发生了什么）配合。

## 一句话定位

DSH 说一切皆可插件——那 DSH 本身，也可以是一个插件。
**codewhale-dsh** = 把 DeepSeek Harness 作为 codewhale 的子 agent（MCP bridge + 黑板 + 官方 ACP）。

## 当前状态（2026-08-15）

- ✅ 最小闭环 / ✅ ACP 流式 / ✅ 求助 L1 / ✅ token 记账
- 5 个 MCP 工具：`dsh_init` `dsh_status` `dsh_read` `dsh_respond` `dsh_cancel`
- 20 测试全绿；Release v0.0.1；CI（GitHub Actions）
- 社区：2 帖 + awesome-dsh-bridges PR #1

## 文件地图

```
src/dsh_bridge.py    FastMCP 薄壳（MCP 工具 + 黑板集成 + 结算）——入口
src/acp_client.mjs   Node ACP 驱动（官方 SDK，行协议）——DSH 引擎的嘴
src/board.py         黑板状态机（单写者，idle→working→blocked→done|error）
src/token_stats.py   会话日志 usage 解析（zstd）
tests/               pytest（20）+ fake_acp_server.mjs（协议模拟）
docs/adr/            架构决策记录（6 条）
docs/ACP.md          ACP 接入施工图
```

## 关键环境事实

- DSH 仓库：`~/deepseek-harness`（`demo:acp` 跑 ACP server，tsx 现场编译）
- 凭据：bridge 自动读 `~/.dsh/.credentials.yaml`（无需环境变量）
- DSH 会话日志：`~/deepseek-harness/.sessions/--tmp--/<sessionId>/session.jsonl.zstd`
- codewhale 注册：`~/.codewhale/mcp.json` 的 `dsh` server（doctor 验证 ok）

## 已知坑（踩过的）

1. **EOF 才 flush**：acp_client 完成任务后必须 `child.stdin.end()` 等 server 退出（最多 3s），否则会话日志不完整、token 读不到
2. **ACP 协议细节**：protocolVersion 是整数 1；无 `notifications/initialized`；`session/prompt` response 直接带 stopReason（无 complete 事件）；thinking 不产生 update
3. **npm 组装堵死**：`dsh-workspace-context`/`dsh-bash`/`dsh-environment`/`dsh-session-title` 未发布 npm → 必须依赖源码仓库（ADR-004）
4. **`session/update` 只在 committed `assistant/message` 时发**——长时间无事件可能是模型在 thinking（demo 配置 v4-pro + max effort 会很慢；测试用 flash + off 配置）
5. **worker 权限模式**：`danger-full-access` 下永远不触发 request_permission；要测求助链路用 `DSH_PERMISSION_MODE=workspace-write` + workspace 外操作
6. **git 安全**：个人路径/凭据绝不进仓库；fixture 用合成数据；测试路径用 `~` 展开

## 协作约定（本项目工作方式）

- TDD：先 RED 再 GREEN（make test 全绿才提交）
- 大决策 grill 后共识（参考 docs/adr/ 的格式）
- 小步提交 + 清晰 commit message（中英皆可）
- 测试分两堆：`make test`（快，20 个）· `make test-acp`（重，需要 DSH 仓库 + key）
- 会话结束更新 LOG.md；状态变化更新本文件

## Git push 规则（红线）

1. **push 前必须检查**：
   - 无个人路径：`git grep -n "/Users/" $(git rev-list --all) | head` 应为空
   - 无凭据：`git grep -nE "sk-[A-Za-z0-9]{16,}" $(git rev-list --all)` 应为空
   - 无 .env / 凭据文件：`git ls-files | grep -iE "\.env|credential|secret"` 应为空
2. **测试全绿才提交**：`make test` 通过（`make test-acp` 视改动范围）
3. **未征求同意不 push**（尤其 force push / 删分支 / 重写历史）——历史重写只在无他人 clone 时可用，filter-branch 后必须 force push 并验证远程无残留
4. **不做**：把运行产物（task_board.json / run/ / .sessions）和 venv/node_modules 提交进去（.gitignore 已覆盖）
5. fixture 一律用合成数据；测试路径用 `~` 展开，不写真实用户名路径
6. commit message 说清楚为什么（小步、可回溯）

## 下一步候选

1. 求助分级 L2/L3（blocked 语义已就位，扩展 request_message 分类）
2. 任务队列（acp_client 行协议已支持多任务，黑板加任务表）
3. npm 包发布（`dsh-bridge` 名字已验证未占用；等启动固化后再做）
4. 社区跟进：帖子的评论、star、PR 认领

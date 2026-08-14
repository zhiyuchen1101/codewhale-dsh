# ACP 接入方案（施工图）

> 状态：调研完成，待实现。目标：把 bridge 的 DSH 驱动层从 `headless` 升级为 DSH 官方 ACP server。

## 为什么

headless 的已知限制（官方文档确认）：一次性任务、无交互、无流式、只能拿最后一条消息。
DSH 官方 ACP server（`@deepseek-ai/dsh-acp`）补齐了这些：

- 流式：`session/update` 每 committed assistant message 发 `agent_message_chunk`（非逐 token，是干净的自动化结果）
- 审批：`session/request_permission` 提供一次性 allow/reject —— **这正是求助机制（L1）的协议基础**
- 多 session：一个连接可管多个任务（队列顺带解决）
- 优雅取消：`session/cancel` 替代 kill -9

## 协议契约（摘自官方 README）

| Method | 行为 |
|---|---|
| `initialize` | 协商版本；只广告 baseline（无 image/audio/MCP 能力） |
| `session/new` | 创建新 agent，绝对路径 `cwd`；空 `mcpServers` 接受，非空拒绝 |
| `session/prompt` | 文本 prompt；每 session 一个 in-flight；整个 agent idle 后返回 `end_turn` |
| `session/cancel` | 只取消指定 session，pending prompt 置 `cancelled` |
| `session/update` | 每 committed message 一个 `agent_message_chunk` |
| `session/request_permission` | bridge 拥有的审批请求，客户端可自动应答 |

## 参考实现

官方 `dsh-subagent-acp`（DSH 把外部 agent 当子 agent 的 client）是现成范本：
`spawn` → ACP `initialize` → `newSession` → `prompt` → 收集 chunks → `SubagentResult.output`。

我们的 bridge 照抄这个模式，方向相反（我们的 client 是 bridge 自己）。

## 改动范围（小）

```
src/dsh_bridge.py
  _spawn():           headless 子进程  →  ACP server 子进程 + JSON-RPC client
  _check_done():      读 exit 文件     →  读 session 生命周期（end_turn / cancelled）
  dsh_status():       加 pending 进度（已收 chunks 数/长度）
  新增 dsh_respond(): 应答 request_permission（allow/reject）→ 求助机制 L1
```

- `board.py` 不变（状态机已覆盖 blocked 语义？—— 需要加 `blocked` 状态，见下）
- 黑板新增状态：`blocked`（等待审批/澄清）→ `dsh_respond` 后回 `working`
- 队列：ACP 一连接多 session，`dsh_init` 支持并发（需评估执行锁策略）

## 验收标准

- [ ] ACP 驱动替代 headless（保留 headless 作为 fallback 配置项）
- [ ] 主会话能看到 DSH 的进度摘要（chunk 数/最新 chunk）
- [ ] request_permission → 黑板 blocked → dsh_respond(allow/reject) 闭环
- [ ] session/cancel 优雅取消（非 kill -9）
- [ ] 测试全绿（mock ACP server：脚本模拟 JSON-RPC 帧）

## 依赖事实

- DSH ACP 入口：`dsh --profile <acp-profile>`（官方 runnable ACP composition 需要 provider/model 配置）
- 协议文档：https://agentclientprotocol.com + `packages/acp/acp/README.md`
- client 参考：`packages/subagent/subagent-acp/README.md`

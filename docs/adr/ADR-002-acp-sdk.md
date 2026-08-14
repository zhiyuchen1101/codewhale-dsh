# ADR-002：驱动走 DSH 官方 ACP 协议 + 官方 SDK

## 背景

DSH 的 headless 模式（`dsh --profile headless "task"`）一次性、无交互、无流式、只能拿最后一条消息。
需要流式吐字、权限求助、优雅取消。最初尝试手写 Python JSON-RPC 客户端直连 DSH 的 ACP server，
结果收不到 `session/update` 事件（协议分发细节问题），浪费了多轮调试。

## 决策

ACP 客户端用官方 `@agentclientprotocol/sdk`（`ClientSideConnection` + `ndJsonStream`），
Node/JS 实现，不手写协议。官方 e2e 测试（`examples/acp-agent/tests/acp.e2e.ts`）证明组合本身可用，
问题在客户端姿势。

关键协议事实（踩坑记录）：
- `protocolVersion` 是整数（1），不是 MCP 的字符串
- ACP 没有 `notifications/initialized`（那是 MCP 的概念）
- `session/prompt` 的 response 直接带 `stopReason`（end_turn），没有 session/complete 事件
- `session/update` 只在 committed `assistant/message` 时发（thinking 不产生事件）

## 后果

- 正向：协议细节全部封装，2.5 秒跑通真实链路；DSH 官方 subagent-acp 是同构参考实现。
- 代价：引入 Node 运行时依赖（项目同时有 Python 和 Node）。
- 注意：prompt 完成后必须 EOF 关闭子进程 stdin（触发 server 的 dispose+flush），
  否则会话日志不落盘、token 统计读不到。

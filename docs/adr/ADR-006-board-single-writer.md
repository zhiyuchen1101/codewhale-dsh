# ADR-006：黑板单写者 + blocked 状态（mcp-bio 血泪复用）

## 背景

用户 mcp-bio 项目的血泪教训：两个进程并发写 `task_board.json` 会互相覆盖（`_writing_by` 互斥锁），
Verifier 太激进会假 pass，Agent 自由度失控会乱跑。DSH 的 ACP 有 `request_permission` 机制
（工具调用审批），天然需要"阻塞-应答"语义。

## 决策

- 黑板单写者：`Board` 模块独占文件，原子替换写（tmp + rename）。
- 状态机：idle → working → blocked → working | done | error；working/blocked 期间 `dsh_init` 拒绝（BUSY）。
- `blocked` 由 ACP 的 `request_permission` 触发（acp_client 转发 → bridge 置黑板），
  `dsh_respond(allow)` 应答后回 working。
- 审批策略默认 `danger-full-access`（桥接场景不打断），`DSH_PERMISSION_MODE` 可切换
  （workspace-write 时真实触发权限请求，已在 e2e 验证）。

## 后果

- 正向：并发安全（单写者 + 原子替换）；求助 L1（权限应答）协议级打通；
  L2/L3（澄清/升级）在 blocked 语义上自然扩展。
- 代价：一次只能跑一个任务（队列是 Roadmap 项，做队列时保留单写者、加任务表）。

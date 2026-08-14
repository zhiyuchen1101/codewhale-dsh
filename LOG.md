# LOG —— 项目日志（会话记录）

> 每次工作会话结束，在此追加一条记录：做了什么 / 验证了什么 / 下一步。
> 格式：日期 · 主题 | 关键动作 | 验证证据 | 遗留事项

---

## 2026-08-15 · 从零到发布：占坑 → 实现 → 验证 → 社区 → 存档

**主题**：codewhale-dsh 立项并发布（单次长会话完成全链路）

**关键动作**：
- 占坑：GitHub 仓库 `zhiyuchen1101/codewhale-dsh` + topics（dsh-plugin/codewhale/mcp/agent-interop）+ Release v0.0.1
- 实现：board 黑板状态机 → FastMCP bridge（5 工具）→ ACP 驱动（官方 SDK）→ 求助 L1 → token 记账
- 验证：fake/真实双链路测试；codewhale TUI 实测完整闭环（派活→轮询→结果+token 账单）
- 社区：codewhale Discussions #5385 + DSH Discussions #1578 + awesome-dsh-bridges PR #1（Outbound 类目）
- 安全：硬编码路径修复 + git 历史重写 + 合成 fixture
- 存档：ADR-001~006 + 本文档 + MEMORY.md + SYSTEM_PROMPT.md

**验证证据**：
- 20 测试全绿（pytest）+ make test-acp 双链路（fake server + 真实 DSH server）
- TUI 实测：dsh_init → dsh_status×4 → dsh_read，结果 `完成\n[tokens] input=38 output=41 cache=7424 reasoning=39`
- 权限求助实测：request_permission → blocked → dsh_respond(allow) → 恢复 → done
- 优雅取消实测：cancel → error(已取消（优雅）)

**决策记录**：见 docs/adr/（6 条）

**遗留事项**：
- 等 DSH 官方补发 npm 包（dsh-workspace-context 等）→ ADR-004 的 b 方案复活
- Roadmap：求助 L2/L3、任务队列、npm 包（dsh-bridge 名字已验证未占用）
- 社区帖子发布后的反应跟进（star/评论/PR）

---

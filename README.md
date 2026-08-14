# codewhale-dsh

**DSH 说一切皆可插件 —— 那 DSH 本身，也可以是一个插件。**

把 DeepSeek Harness 作为 codewhale 的子 agent：派活、盯进度、收结果、求救、记账，全在主会话完成。

## 这是什么

DeepSeek Harness 是 DeepSeek 官方开源的 agent harness（"一切皆插件"，358+ 社区插件）。
codewhale 是你日常使用的 Rust agent harness（fleet / constitution / hooks）。

本项目的方向与 DSH 生态现有的桥接（X → DSH）相反：**DSH 出来，给 codewhale 当工人**。

```
codewhale TUI（Leader，你的日常、你的账本）
  │  MCP（~/.codewhale/mcp.json 注册）
  ▼
dsh-bridge（FastMCP server，薄壳：只翻译协议，不跑 Agent 不决策）
  ├── 同步工具：dsh_init / dsh_status / dsh_read / dsh_respond / dsh_cancel
  ├── 黑板：task_board.json（单写者 + 状态机 + 执行锁）
  └── DSH 进程：dsh --profile headless "task"
```

## 快速开始（开发中）

```sh
make install
# ~/.codewhale/mcp.json 添加：
# "dsh": { "command": "/Users/<you>/codewhale-dsh/.venv/bin/python", "args": ["/Users/<you>/codewhale-dsh/src/dsh_bridge.py"] }
```

## Roadmap（待认领）

- [ ] **最小闭环**（本仓库当前目标）：dsh_init → headless 干活 → dsh_read 收结果
- [ ] **ACP 流式**：DSH 官方 ACP server（packages/acp）接入，主会话实时看进度（**发布后立即开始打磨，欢迎社区一起**）
- [ ] **求助机制**：DSH 卡住 → blocked → 主会话弹求助 → dsh_respond 传回（L1/L2/L3 分级）
- [ ] **token 记账**：读 DSH 会话 JSON 的 total_tokens，进返回结果
- [ ] **任务队列**：多任务排队 + 每任务独立 workspace/会话
- [ ] **迁移 FastMCP 高级特性**：流式进度、多 worker

## 设计铁律

1. 薄壳不挟持：bridge 只翻译协议，不跑 Agent、不决策
2. 单写者：黑板只有一个写者，绝不两个进程写同一个 JSON
3. TDD：先 RED 再 GREEN（make test）
4. 任务隔离：每次任务独立 workspace 和 DSH 会话
5. 结果只出摘要，裁决交给用户（或 codewhale 的 verifier 角色）

## License

MIT

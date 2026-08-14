# codewhale-dsh

**DSH 说：一切皆可插件。那 DSH 本身，也可以是一个插件。**

它没有离开自己的海域——在 codewhale 里，DSH 是游进来的另一条大鲸鱼：带着自己的引擎、自己的插件生态、自己的脾气，和 codewhale 共享同一个终端、同一本账本。

派活、盯进度、收结果、回应它的求助、一本账到底——全在 codewhale 会话里完成。

## 这是什么

DeepSeek Harness 是 DeepSeek 官方的开源 agent harness（"一切皆插件"，358+ 社区插件）。codewhale 是你日常使用的 Rust agent harness（fleet / constitution / hooks）。

DSH 生态里已有的桥接全部指向同一个方向（X → DSH）。本项目指向另一侧：**DSH 游进 codewhale**——不是来做客的 UI，不是借来的工具箱，而是一条带着完整插件树的大鲸鱼，与你并肩干活。

```
codewhale TUI（Leader —— 你的日常、你的账本）
  │  MCP（注册于 ~/.codewhale/mcp.json）
  ▼
dsh-bridge（FastMCP 薄壳 —— 只翻译协议，不跑 Agent 不决策）
  ├── 工具：dsh_init / dsh_status / dsh_read / dsh_cancel
  ├── 黑板：task_board.json（单写者状态机 + 执行锁）
  └── DSH 进程：dsh --profile headless "task"
```

## 快速开始（开发预览）

```sh
make install
```

在 `~/.codewhale/mcp.json` 注册：

```json
{
  "mcpServers": {
    "dsh": {
      "command": "/Users/<you>/codewhale-dsh/.venv/bin/python",
      "args": ["/Users/<you>/codewhale-dsh/src/dsh_bridge.py"]
    }
  }
}
```

然后在 codewhale 会话里说："用 dsh_init 派个任务：……"

## Roadmap（待认领）

- [x] **最小闭环** —— dsh_init → headless 干活 → dsh_read 收结果
- [ ] **ACP 流式** —— 接入 DSH 官方 ACP server（packages/acp），主会话实时看进度（**发布后我们立即开始打磨，欢迎社区一起**）
- [ ] **求助机制** —— DSH 卡住 → 黑板 blocked → 主会话弹求助 → dsh_respond 传回（L1/L2/L3 分级）
- [ ] **token 记账** —— 读 DSH 会话 JSON 的 total_tokens，进返回结果
- [ ] **任务队列** —— 多任务排队，每任务独立 workspace/会话
- [ ] **npm 包** —— 以 npm 可安装二进制发布 dsh-bridge

## 设计铁律

1. 薄壳不挟持：bridge 只翻译协议，不跑 Agent、不决策
2. 单写者：黑板只有一个写者
3. TDD：先 RED 再 GREEN（make test）
4. 任务隔离：每次任务独立 workspace 和 DSH 会话
5. 只出摘要，裁决归你（或 codewhale 的 verifier 角色）

## License

MIT

<p align="center">
  <a href="README.md">English</a> · <b>简体中文</b>
</p>

<h1 align="center">codewhale-dsh</h1>

<p align="center">
  <em>DSH 说：一切皆可插件。那 DSH 本身，也可以是一个插件。</em>
</p>

<p align="center">
  <a href="https://github.com/zhiyuchen1101/codewhale-dsh/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <a href="https://github.com/zhiyuchen1101/codewhale-dsh/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/zhiyuchen1101/codewhale-dsh/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/zhiyuchen1101/codewhale-dsh/releases"><img alt="Release" src="https://img.shields.io/github/v/release/zhiyuchen1101/codewhale-dsh?label=release"></a>
  <img alt="tests" src="https://img.shields.io/badge/tests-12%20passed-green">
  <img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-blue">
</p>

---

它没有离开自己的海域。在 **codewhale** 里，DSH 是游进来的**另一条大鲸鱼**——带着自己的引擎、自己的插件生态（358+ 社区插件）、自己的脾气，与 codewhale 共享同一个终端、同一本账本。

派活、盯进度、收结果、回应它的求助——一本账到底，全在 codewhale 会话里完成。

## 为什么

DSH 生态里已有的桥接全部指向同一个方向（工具 → DSH）。本项目指向另一侧：

> **DSH → codewhale。** 不是来做客的 UI，不是借来的工具箱——一条带着完整插件树的大鲸鱼，与你并肩干活。

## 怎么运作

```
┌────────────────────────────────────────────────────┐
│ codewhale TUI        你的日常 · 你的账本             │
│        │ MCP（mcp.json）                            │
│        ▼                                           │
│ dsh-bridge             FastMCP 薄壳                │
│   工具：dsh_init · dsh_status                      │
│          dsh_read  · dsh_cancel                    │
│   黑板：task_board.json（单写者状态机）              │
│        │ spawn                                     │
│        ▼                                           │
│ DSH headless          自己的引擎与插件树            │
└────────────────────────────────────────────────────┘
```

bridge 只翻译协议——不跑 Agent、不决策。黑板是唯一状态源，DSH 进程是唯一工人。

## 工具

| 工具 | 作用 |
|---|---|
| `dsh_init(task, workspace)` | 派活。busy 时拒绝；`done`/`error` 后自动重置 |
| `dsh_status()` | 查状态；进程退出自动结算 `done`/`error` |
| `dsh_read()` | 读完整结果 |
| `dsh_respond(allow)` | 应答 DSH 的权限/求助请求（`blocked` 状态） |
| `dsh_cancel()` | ACP 优雅取消；超时兜底强杀 |

## 快速开始

```sh
git clone https://github.com/zhiyuchen1101/codewhale-dsh && cd codewhale-dsh
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

## Roadmap

| 状态 | 事项 |
|---|---|
| ✅ | **最小闭环** —— dsh_init → headless 干活 → dsh_read 收结果 |
| ✅ | **ACP 流式** —— 官方 ACP server（packages/acp）：实时吐字、权限转发（blocked + dsh_respond）、优雅取消 |
| 🚧 | **求助分级 L2/L3** —— 更丰富的阻塞原因与升级层级（L1 权限应答已完成） |
| ⬜ | **token 记账** —— 读 DSH 会话 total_tokens，进返回结果 |
| ⬜ | **任务队列** —— 多任务排队，每任务独立 workspace/会话 |
| ⬜ | **npm 包** —— 以可安装二进制发布 dsh-bridge |

## 设计铁律

1. **薄壳不挟持** —— bridge 只翻译协议：不跑 Agent、不决策
2. **单写者** —— 黑板只有一个写者
3. **TDD** —— 先 RED 再 GREEN（`make test`）
4. **任务隔离** —— 每次任务独立 workspace 和 DSH 会话
5. **只出摘要，裁决归人** —— 归你，或 codewhale 的 verifier 角色

## 参与贡献

从 Roadmap 里挑一项，先开 issue 再发 PR。测试必须全绿（`make test`）。欢迎首次贡献——维护者会收下能用的部分，并给每位作者署名。

## License

MIT —— 独立社区项目，与 DeepSeek 及任何模型提供商无关联。

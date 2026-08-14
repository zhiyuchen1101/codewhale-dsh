<p align="center">
  <b>English</b> · <a href="README.zh-CN.md">简体中文</a>
</p>

<h1 align="center">codewhale-dsh</h1>

<p align="center">
  <em>DeepSeek Harness says: everything is a plugin. So DSH itself can be one too.</em>
</p>

<p align="center">
  <a href="https://github.com/zhiyuchen1101/codewhale-dsh/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <a href="https://github.com/zhiyuchen1101/codewhale-dsh/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/zhiyuchen1101/codewhale-dsh/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/zhiyuchen1101/codewhale-dsh/releases"><img alt="Release" src="https://img.shields.io/github/v/release/zhiyuchen1101/codewhale-dsh?label=release"></a>
  <img alt="tests" src="https://img.shields.io/badge/tests-12%20passed-green">
  <img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-blue">
</p>

---

It doesn't leave its own waters. Inside **codewhale**, DSH swims in as **another whale** — its own engine, its own plugin ecosystem (358+ community plugins), its own temperament, sharing the same terminal and the same ledger.

Dispatch work, watch progress, collect results, answer its calls for help — one ledger, all inside your codewhale session.

## Why

DSH ecosystem bridges all point one way (tool → DSH). This project points the other way:

> **DSH → codewhale.** Not a guest UI, not a borrowed toolset — a full agent with its own plugin tree, running alongside yours.

## How it works

```
┌────────────────────────────────────────────────────┐
│ codewhale TUI        your daily · your ledger       │
│        │ MCP (mcp.json)                            │
│        ▼                                           │
│ dsh-bridge            FastMCP thin shell           │
│   tools: dsh_init · dsh_status                     │
│          dsh_read  · dsh_cancel                    │
│   board: task_board.json  (single-writer machine)  │
│        │ spawn                                     │
│        ▼                                           │
│ DSH headless          its own engine & plugins     │
└────────────────────────────────────────────────────┘
```

The bridge translates protocols only — no agent logic, no decisions. The board is the single source of truth; the DSH process is the only worker.

## Tools

| Tool | What it does |
|---|---|
| `dsh_init(task, workspace)` | Dispatch a task. Rejects while busy; resets after `done`/`error` |
| `dsh_status()` | Poll status; auto-settles `done`/`error` when the process exits |
| `dsh_read()` | Read the full result |
| `dsh_respond(allow)` | Answer a permission/help request (`blocked` state) |
| `dsh_cancel()` | Graceful ACP cancel; kill fallback |

## Quick start

```sh
git clone https://github.com/zhiyuchen1101/codewhale-dsh && cd codewhale-dsh
make install
```

Register in `~/.codewhale/mcp.json`:

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

Then in a codewhale session: *"use dsh_init to dispatch a task: ..."*

## Roadmap

| Status | Item |
|---|---|
| ✅ | **Minimal loop** — `dsh_init` → headless works → `dsh_read` collects |
| ✅ | **ACP streaming** — official ACP server (`packages/acp`): live chunks, permission relay (`blocked` + `dsh_respond`), graceful cancel |
| 🚧 | **Help requests L2/L3** — richer blocking reasons and escalation tiers (L1 done: permission relay) |
| ✅ | **Token accounting** — per-task usage from DSH session log (`input/output/cache/reasoning`) |
| ⬜ | **Task queue** — multiple tasks, isolated workspace/session each |
| ⬜ | **npm package** — ship `dsh-bridge` as an installable binary |

## Design rules

1. **Thin shell** — the bridge translates protocols only: no agent logic, no decisions
2. **Single writer** — the board has exactly one writer
3. **TDD** — RED before GREEN (`make test`)
4. **Task isolation** — fresh workspace and DSH session per task
5. **Summaries out, judgment stays** — with you, or codewhale's verifier role

## Contributing

Pick an open Roadmap item, open an issue first, then send a PR. Tests must pass (`make test`). First contributions welcome — the maintainers harvest what works and credit every author.

## Architecture decisions

[ADR-001](docs/adr/ADR-001-reverse-bridge.md) · [ADR-002](docs/adr/ADR-002-acp-sdk.md) · [ADR-003](docs/adr/ADR-003-acp-client-module.md) · [ADR-004](docs/adr/ADR-004-server-startup.md) · [ADR-005](docs/adr/ADR-005-token-accounting.md) · [ADR-006](docs/adr/ADR-006-board-single-writer.md)

## License

MIT — an independent community project, not affiliated with DeepSeek or any model provider.

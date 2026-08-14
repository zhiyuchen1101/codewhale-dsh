# codewhale-dsh

**DeepSeek Harness says: everything is a plugin. So DSH itself can be one too.**

It doesn't leave its own waters — inside codewhale, DSH swims in as another whale: its own engine, its own plugin ecosystem, its own temperament, sharing the same terminal and the same ledger.

Dispatch work, watch progress, collect results, answer its calls for help, keep one ledger — all inside your codewhale session.

## What this is

DeepSeek Harness is DeepSeek's open-source agent harness ("everything is a plugin", 358+ community plugins). codewhale is the Rust agent harness you already live in (fleet / constitution / hooks).

Existing bridges in the DSH ecosystem all point one way (X → DSH). This project points the other way: **DSH swims into codewhale** — not as a guest UI, not as a borrowed toolset, but as a full agent with its own plugin tree, running alongside yours.

```
codewhale TUI (Leader — your daily, your ledger)
  │  MCP (registered in ~/.codewhale/mcp.json)
  ▼
dsh-bridge (FastMCP thin shell — translates protocols only, no agent logic)
  ├── tools: dsh_init / dsh_status / dsh_read / dsh_cancel
  ├── board: task_board.json (single-writer state machine + busy lock)
  └── DSH process: dsh --profile headless "task"
```

## Quick start (dev preview)

```sh
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

## Roadmap (up for grabs)

- [x] **Minimal loop** — `dsh_init` → headless works → `dsh_read` collects
- [ ] **ACP streaming** — DSH's official ACP server (`packages/acp`) for live progress in the main session (**we start immediately after release; community welcome**)
- [ ] **Help requests** — DSH blocked → board `blocked` → main session asks → `dsh_respond` relays (L1/L2/L3)
- [ ] **Token accounting** — read DSH session JSON `total_tokens` into results
- [ ] **Task queue** — multiple tasks, isolated workspaces/sessions per task
- [ ] **npm package** — ship `dsh-bridge` as an npm-installable binary

## Design rules

1. Thin shell: bridge translates protocols only — no agent logic, no decisions
2. Single writer: the board has exactly one writer
3. TDD: RED before GREEN (`make test`)
4. Task isolation: fresh workspace and DSH session per task
5. Summaries out, judgment stays with you (or codewhale's verifier role)

## License

MIT

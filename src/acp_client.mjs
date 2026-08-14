#!/usr/bin/env node
// acp_client —— Node ACP 驱动模块（官方 SDK）。
//
// 职责：启动 DSH 的 ACP server（仓库 demo 组合），通过 ACP 协议跑任务，
//       把进度/结果以 JSON 行协议输出到 stdout，供 Python bridge（subprocess）消费。
//
// 输入（stdin，每行一个 JSON）：
//   {"id": 1, "action": "run", "task": "...", "workspace": "/path"}
//   {"id": 1, "action": "cancel"}
// 输出（stdout，每行一个 JSON）：
//   {"id": 1, "type": "chunk", "text": "..."}      模型增量输出
//   {"id": 1, "type": "done", "result": "...", "stopReason": "end_turn"}
//   {"id": 1, "type": "error", "message": "..."}
//   {"id": null, "type": "log", "message": "..."}  诊断日志（透传 stderr）
//
// 环境变量：
//   DSH_REPO       DSH 源码仓库路径（默认 ~/deepseek-harness）
//   DSH_ACP_CONFIG ACP 组合配置（默认 examples/acp-agent/cordis.yml）
//   DSH_ACP_SERVER server 启动命令 JSON 数组（测试用，覆盖默认仓库命令）
//   DEEPSEEK_API_KEY 透传给 server
import { spawn } from 'node:child_process'
import { Writable, Readable } from 'node:stream'
import { createRequire } from 'node:module'
import readline from 'node:readline'
import os from 'node:os'
import path from 'node:path'

const require = createRequire(import.meta.url)
const { ClientSideConnection, ndJsonStream } = require('@agentclientprotocol/sdk')

const REPO = process.env.DSH_REPO || path.join(os.homedir(), 'deepseek-harness')
const CONFIG = process.env.DSH_ACP_CONFIG || 'examples/acp-agent/cordis.yml'

const out = (msg) => process.stdout.write(JSON.stringify(msg) + '\n')

// 启动 ACP server 子进程
function spawnServer() {
  const override = process.env.DSH_ACP_SERVER
  const cmd = override
    ? JSON.parse(override)
    : ['node', '--import', 'tsx', 'packages/examples/acp-demo/src/bin.ts', '--config', CONFIG]
  const child = spawn(cmd[0], cmd.slice(1), {
    cwd: REPO,
    env: { ...process.env, DSH_PERMISSION_MODE: 'danger-full-access' },
    stdio: ['pipe', 'pipe', 'pipe'],
  })
  child.stderr.on('data', (d) => out({ id: null, type: 'log', message: d.toString().trim() }))
  return child
}

async function runTask(task, workspace) {
  const child = spawnServer()
  try {
    const stream = ndJsonStream(
      Writable.toWeb(child.stdin),
      Readable.toWeb(child.stdout),
    )
    const makeClient = () => ({
      sessionUpdate: async (p) => {
        const u = p.update
        if (u.sessionUpdate === 'agent_message_chunk' && u.content?.type === 'text') {
          out({ id: currentId, type: 'chunk', text: u.content.text })
        }
      },
      requestPermission: async () => ({ outcome: { outcome: 'allowed' } }),
    })
    const conn = new ClientSideConnection(makeClient, stream)

    await conn.initialize({ protocolVersion: 1, clientCapabilities: {} })
    const { sessionId } = await conn.newSession({ cwd: workspace, mcpServers: [] })
    const res = await conn.prompt({
      sessionId,
      prompt: [{ type: 'text', text: task }],
    })
    return { stopReason: res.stopReason }
  } finally {
    child.kill()
  }
}

let currentId = null
const rl = readline.createInterface({ input: process.stdin })
rl.on('line', async (line) => {
  const msg = JSON.parse(line)
  currentId = msg.id ?? null
  if (msg.action === 'run') {
    try {
      const { stopReason } = await runTask(msg.task, msg.workspace)
      out({ id: currentId, type: 'done', stopReason })
    } catch (e) {
      out({ id: currentId, type: 'error', message: e.message })
    }
  } else if (msg.action === 'cancel') {
    out({ id: currentId, type: 'done', stopReason: 'cancelled' })
  }
})

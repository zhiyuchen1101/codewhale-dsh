#!/usr/bin/env node
// acp_client —— Node ACP 驱动模块（官方 SDK）。
//
// 职责：启动 DSH 的 ACP server（仓库 demo 组合），通过 ACP 协议跑任务，
//       把进度/结果以 JSON 行协议输出到 stdout，供 Python bridge（subprocess）消费。
//
// 输入（stdin，每行一个 JSON）：
//   {"id": 1, "action": "run", "task": "...", "workspace": "/path"}
//   {"id": 1, "action": "respond", "allow": true}   应答 DSH 的权限请求
//   {"id": 1, "action": "cancel"}                    优雅取消当前任务
// 输出（stdout，每行一个 JSON）：
//   {"id": 1, "type": "chunk", "text": "..."}      模型增量输出
//   {"id": 1, "type": "permission_request", "requestId": "...", "message": "..."}
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
    env: { ...process.env, DSH_PERMISSION_MODE: process.env.DSH_PERMISSION_MODE || 'danger-full-access' },
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
      requestPermission: async (p) => {
        out({ id: currentId, type: 'permission_request', requestId: p.requestId, message: JSON.stringify(p).slice(0, 500) })
        return new Promise((resolve) => { permissionResolve = resolve })
      },
    })
    const conn = new ClientSideConnection(makeClient, stream)

    await conn.initialize({ protocolVersion: 1, clientCapabilities: {} })
    const { sessionId } = await conn.newSession({ cwd: workspace, mcpServers: [] })
    out({ id: currentId, type: 'session_ready', sessionId })
    activeConn = { conn, sessionId }
    const res = await conn.prompt({
      sessionId,
      prompt: [{ type: 'text', text: task }],
    })
    return { stopReason: res.stopReason, sessionId }
  } finally {
    activeConn = null
    // 优雅关闭：EOF 触发 server 的 dispose+flush（会话日志完整落盘），最多等 3 秒
    try { child.stdin.end() } catch { /* already closed */ }
    await Promise.race([
      new Promise((r) => child.once('exit', r)),
      new Promise((r) => setTimeout(r, 3000)),
    ])
    if (child.exitCode === null) child.kill()
  }
}

let currentId = null
let activeConn = null
let permissionResolve = null
const rl = readline.createInterface({ input: process.stdin })
rl.on('line', async (line) => {
  const msg = JSON.parse(line)
  currentId = msg.id ?? null
  if (msg.action === 'run') {
    try {
      const { stopReason, sessionId } = await runTask(msg.task, msg.workspace)
      out({ id: currentId, type: 'done', stopReason, sessionId })
    } catch (e) {
      out({ id: currentId, type: 'error', message: e.message })
    }
  } else if (msg.action === 'respond') {
    const resolve = permissionResolve
    permissionResolve = null
    if (resolve) resolve({ outcome: { outcome: msg.allow ? 'allowed' : 'rejected' } })
    else out({ id: currentId, type: 'error', message: '没有待应答的权限请求' })
  } else if (msg.action === 'cancel') {
    if (activeConn) {
      try {
        await activeConn.conn.cancel({ sessionId: activeConn.sessionId })
        out({ id: currentId, type: 'done', stopReason: 'cancelled' })
      } catch (e) {
        out({ id: currentId, type: 'error', message: `cancel 失败: ${e.message}` })
      }
    } else {
      out({ id: currentId, type: 'done', stopReason: 'cancelled' })
    }
  }
})
process.on('SIGTERM', () => process.exit(0))

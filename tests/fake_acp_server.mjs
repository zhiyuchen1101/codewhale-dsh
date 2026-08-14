#!/usr/bin/env node
// fake ACP server：模拟 DSH 的 ACP JSON-RPC 行为，用于 acp_client 的测试
// 协议：initialize → session/new → session/prompt → session/update → response(end_turn)
import readline from 'node:readline'

const rl = readline.createInterface({ input: process.stdin })
let sessions = 0
let fakeKey = null

rl.on('line', (line) => {
  const msg = JSON.parse(line)
  const { id, method, params } = msg

  if (method === 'initialize') {
    fakeKey = params?.clientInfo?.name === 'probe-with-key' ? 'KEY_OK' : null
    process.stdout.write(JSON.stringify({
      jsonrpc: '2.0', id,
      result: { protocolVersion: 1, agentInfo: { name: 'fake-acp', version: '0' },
                agentCapabilities: { promptCapabilities: { image: false, audio: false, embeddedContext: false } },
                authMethods: [] },
    }) + '\n')
    return
  }
  if (method === 'session/new') {
    sessions++
    process.stdout.write(JSON.stringify({
      jsonrpc: '2.0', id,
      result: { sessionId: `fake-session-${sessions}` },
    }) + '\n')
    return
  }
  if (method === 'session/prompt') {
    const text = params?.prompt?.[0]?.text ?? ''
    // 模拟：分两段输出文本，然后返回 end_turn
    const reply = text === 'REJECT_TEST' ? '拒绝' : '完成'
    setTimeout(() => {
      process.stdout.write(JSON.stringify({
        jsonrpc: '2.0', method: 'session/update',
        params: { sessionId: params.sessionId, update: { sessionUpdate: 'agent_message_chunk', content: { type: 'text', text: reply } } },
      }) + '\n')
      process.stdout.write(JSON.stringify({
        jsonrpc: '2.0', id,
        result: { stopReason: 'end_turn' },
      }) + '\n')
    }, 50)
    return
  }
  if (method === 'session/cancel') {
    process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id, result: {} }) + '\n')
    return
  }
  process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id, error: { code: -32601, message: `unknown: ${method}` } }) + '\n')
})

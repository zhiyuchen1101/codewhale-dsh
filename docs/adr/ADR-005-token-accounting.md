# ADR-005：token 记账读会话日志 usage 字段

## 背景

需要每次任务的 token 账单。社区已有 dsh-usage-stats / dsh-cost-balance（数据来自持久化会话日志）。
DSH 的 ACP demo 会话存 `.sessions/--tmp--/<sessionId>/session.jsonl.zstd`（zstd 压缩 JSONL）。

## 决策

结算时（`_check_done`）读会话文件，累加所有 `assistant/message` 事件的 `usage` 字段
（inputTokens / outputTokens / cacheReadTokens / reasoningTokens），附到结果尾部：
`[tokens] input=.. output=.. cache=.. reasoning=..`。

关键点：`assistant/message` 才有 usage（`assistant/chunk`、thinking 没有）；
prompt 完成后必须 EOF 关闭 server（ADR-002）才能读到完整事件。

## 后果

- 正向：零额外 API 调用，纯本地解析；cache 命中可见（前缀缓存效果一目了然）。
- 代价：依赖会话文件路径布局（`--tmp--/<sid>/session.jsonl.zstd`），DSH 布局变化需跟随。
- 测试：合成 fixture（最小 usage 事件）保证解析逻辑可离线验证。

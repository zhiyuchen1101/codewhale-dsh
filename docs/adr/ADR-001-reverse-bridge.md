# ADR-001：DSH 作为 codewhale 的子 agent（反向桥接）

## 背景

DSH 生态里已有的桥接全部是"X → DSH"（把 Claude Code / Codex / 飞书等接进 DSH，DSH 当宿主）。
用户深度使用 codewhale，希望获得 DSH 的插件生态能力，但不离开 codewhale 的引擎、账本和日常。

## 决策

方向定为 **DSH → codewhale**：DSH 带着完整插件树，作为 codewhale 的子 agent 干活。
不是 UI 迁移（把 Web UI 搬过来）、不是插件移植（把 DSH 插件重写进 codewhale）、不是 PTY 套壳
（两套聊天记录，garbage）。

定位语："DSH 说一切皆可插件——那 DSH 本身，也可以是一个插件。"

## 后果

- 正向：codewhale 的 fleet/constitution/hooks 全权在握，DSH 的能力以"工人"形态进入；
  主账本永远在 codewhale（派活-结果记录），DSH 明细账独立（主从关系，非两套聊天记录）。
- 代价：桥接层（bridge）需要维护；DSH 是黑盒，只能"派活-收结果"交互。
- 验证：放弃"动机 grill"（用户明确不要被追问），用 Phase 0 实测判断价值。

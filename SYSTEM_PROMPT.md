# SYSTEM PROMPT —— 新会话启动提示词

> 开新会话时，把下面整块贴给 agent。按需填「当前要做」。

---

# 工作区：~/codewhale-dsh
# 核心文件：src/dsh_bridge.py（MCP 薄壳）、src/acp_client.mjs（ACP 驱动）、src/board.py（黑板）、src/token_stats.py（token 解析）
# 先读：MEMORY.md（状态与坑）、docs/adr/（设计决策）、LOG.md（最近进展）
# 测试：make test（快，必须全绿）· make test-acp（重链路，需要 ~/deepseek-harness + key）
#
# 这是什么：把 DeepSeek Harness 作为 codewhale 的子 agent。
# 架构：codewhale → MCP → bridge(FastMCP) → 黑板(单写者) → acp_client(Node/官方SDK) → DSH ACP server
# 工具：dsh_init / dsh_status / dsh_read / dsh_respond / dsh_cancel
#
# 协作模式：
# - TDD：先写 RED 测试再实现，make test 全绿才提交
# - 大决策先 grill 我，共识后再动手
# - 小步提交，commit message 说清楚为什么
# - 改完更新 MEMORY.md（状态/坑），会话结束追加 LOG.md
# - 个人路径/凭据绝不进代码和提交；fixture 用合成数据
#
# 当前要做：[填入]

---

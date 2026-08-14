# ADR-003：acp_client 独立 Node 模块（方案 1，可升级常驻）

## 背景

Python bridge（FastMCP，codewhale 直接连）需要与 Node ACP client（官方 SDK）协作。
备选：方案 2 全迁 Node（重写全部，放弃 mcp-bio 的 Python 经验）；方案 3 Node 常驻服务（多一层守护进程管理）。

## 决策

**方案 1**：`src/acp_client.mjs` 独立模块，JSON 行协议（stdin 收指令 / stdout 发事件），
Python bridge 用 subprocess 每次任务启动它。设计按"可升级常驻"写：行协议天然支持双向通信
（run/respond/cancel 指令），将来队列需要时平滑演进到常驻，不需要改协议。

## 后果

- 正向：FastMCP 侧零改动，现有测试不动；Node 模块独立可测（fake server 双链路）。
- 代价：每次任务冷启动 Node 进程（约 1-2 秒，可接受）。
- 演进路径：任务队列 → 常驻 Node 进程 + socket，协议不变。

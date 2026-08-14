# ADR-004：ACP server 启动依赖 DSH 源码仓库（npm 组装暂不可行）

## 背景

希望 ACP server 用正式安装的 dsh（npm 包）启动，让用户"只要有 dsh 就能用"。
验证发现：`@deepseek-ai/dsh-acp-demo` 的 peer 依赖 `dsh-workspace-context` 未发布到 npm（404），
用 `--legacy-peer-deps` 绕过后又连锁缺 `dsh-bash`、`dsh-environment`、`dsh-session-title` 等
一批未发布包——npm 组装路线堵死（已验证到包级 404，非版本冲突）。

## 决策

当前用 DSH 源码仓库跑官方 `demo:acp`（`node --import tsx packages/examples/acp-demo/src/bin.ts
--config examples/acp-agent/cordis.yml`），环境变量 `DSH_REPO` / `DSH_ACP_CONFIG` 可配置，
默认 `~/deepseek-harness`。固化路线写进 Roadmap，等官方补齐 npm 包。

## 后果

- 正向：官方验证过的组合（e2e 测试覆盖），配置改动小（复制 cordis.yml 改模型即可）。
- 代价：依赖一个源码仓库 clone（80MB）；tsx 现场编译略慢。
- 等待项：官方发布 `dsh-workspace-context` 等包后，改为纯 npm 依赖（b 方案自动复活）。

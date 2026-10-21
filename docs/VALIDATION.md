# 实际验证记录

验收日期：2026-10-21（Asia/Shanghai）。环境预检见 PREFLIGHT.md；运行产物 DB/log 在 .gitignore 内，不上传机器路径或凭证。

| 检查 | 实际结果 |
|---|---|
| V0：pytest、ruff、CLI ingest/query | 6 passed；commit f24d354 |
| V1：核心检索/API/引用/边界 | 42 passed；commit 852665a |
| V2：完整离线评测/展示/工具 | 46 passed；commit 0cfe583 |
| V3：pytest | Python 3.11.17 / 3.12.3 分别 52 passed；各有 1 条 Starlette/httpx deprecation warning |
| ruff check / format --check | 通过 |
| make install / pip check | 锁定版本安装成功，无破损依赖 |
| 标注校验 | 48 questions + 20 citation cases，44 chunks，全部可解析 |
| make demo / CLI | 英文/中文/拒答、持久化查询实际运行 |
| Docker | 实际 build + HTTP ingest/query/delete/refusal；PDF 页码断言 |
| Compose | docker compose config --quiet 通过；Compose 服务未单独启动 |
| 默认评测 | 实际生成 results/offline.json 与 offline.md；Dense/Hybrid=MOCK |
| 真实 API / CPU 模型 | 未配置凭证/未下载模型，未实测；保留显式入口 |
| UI | TestClient / HTTP 静态首页响应验证；JavaScript 通过 node --check；未声称浏览器截图或视觉验收 |
| GitHub Actions | 推送后检查实际结果，以 Actions 页面为准 |

pytest 包括 PDF 页码与 normalized offsets、Markdown fence、TXT 段落、非法类型/编码/空文档、幂等/更新/删除、路径/符号链接越界、大小/页数/超时、维度不符保留旧版本、模型/chunker 身份冲突、BM25/Dense/Hybrid、RRF trace、rerank trace、拒答、citation binding、伪造 ID/marker、HTTP 生命周期、JSON 限流和标注/指标协议。Compatible API 通过 httpx.MockTransport 验证，不是外部网络实测。

coverage 是普通父进程采集，PDF 子进程不计入；CLI 有独立真实命令运行，真实 CPU 模型未运行。未声称完整路径覆盖或零风险。

隐私检查：`scripts/privacy_check.py` 检查 Git candidates 中的明显密钥模式、机器绝对路径与禁止产物；另人工检查 staged filenames、外链域名、原创 corpus 与 PDF metadata。模式扫描不是通用 secret detection，不保证发现任意格式的敏感数据。

首轮 GitHub CI 的 3.11 安装暴露 NumPy 2.5 的 Python 最低版本限制；已用带显式 3.11 下界的 universal lock 修复，新增 make lock 固化生成命令。本地独立项目缓存环境完成 3.11 的 52 项测试和全部标注校验。错误与修复原因保留于 TECH_DECISIONS.md 的 ADR 008。

# 严格基于实现的简历描述

- 独立实现可离线运行的 Citation RAG 引擎，支持 PDF/Markdown/TXT 摄取、章节/页码与字符 offset 定位，使用 SQLite 事务完成文档与向量增量更新、幂等摄取和级联删除，并校验 embedding 索引身份。
- 实现 BM25、NumPy cosine Dense、RRF Hybrid 与可插拔 lexical reranker，提供 FastAPI/CLI 和引用溯源界面，保留检索分数与排名轨迹；集成可配置 OpenAI-compatible embedding/LLM 适配器与引用 ID 校验。
- 构建 8 份原创语料、48 道可回溯标注题及 20 条引用审计样例，提供 Recall@K/MRR/latency 可复跑报告、自动化测试、锁定依赖、CI 与 Docker 生命周期演示；默认向量为 Mock，未宣称真实模型质量或生产性能提升。

使用时可按职位缩减措辞。不要把 hash fixture 的指标写成模型效果提升，不要把 HTTP 契约测试称为真实 LLM 上线，不要写未经测量的吞吐、准确率或成本下降。

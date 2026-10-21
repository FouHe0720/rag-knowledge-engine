# 架构与数据流

## 边界与契约

`domain/contracts.py` 定义 DocumentParser、Chunker、EmbeddingProvider、DocumentStore、Retriever 抽象。Pydantic immutable value objects 承载 Document / Segment / Chunk / Hit / Citation / Statement / Answer；错误使用 EngineError（code/message/status），HTTP 与 CLI 使用相同的安全消息。

`Settings` 校验尺寸、overlap、API 地址、真实模型名称/revision、维数与超时。`build_engine` 连接 provider、索引 fingerprint、store、ingestion、可选 answerer/rewriter。API 的 `lifespan` 创建一个 Engine，持久化操作按调用创建 SQLite connection，避免跨线程复用 connection。

## 摄取顺序

```mermaid
sequenceDiagram
  participant C as CLI / HTTP
  participant I as IngestionService
  participant P as Parser + Chunker
  participant E as EmbeddingProvider
  participant S as SQLiteStore
  C->>I: source inside corpus
  I->>I: canonical path / symlink / byte limit
  I->>S: compare source + content hash
  alt unchanged
    S-->>C: existing document; changed=false
  else changed
    I->>P: bytes → normalized segments → chunks
    P-->>I: source locators + offsets + hashes
    I->>E: embed chunk text
    E-->>I: finite N x configured D
    I->>S: replace document/chunks/vectors transaction
    S-->>C: committed document
  end
```

PDF 使用固定 Python module 子进程，不拼 shell 或文件路径。父进程 12 秒 timeout，子进程 8 秒 CPU、Linux RLIMIT_AS（导入解释器基线 + 256 MiB）、100 页/8 MB page stream/1M extracted chars。stdin/stdout 传 bytes/JSON，stderr 不外泄。它不是网络/系统调用沙箱，仍应仅暴露受控语料。

Markdown 按 ATX heading path、TXT 按空行段落、PDF 按页分 segment。清洗后窗口不跨 segment；offset 是 normalized Unicode character 的 `[start,end)`。重复窗口按 segment 内 text hash 抑制，不合并不同 source 的 provenance。文档 ID 是 source SHA-256 的前 24 位；chunk ID 取来源/segment/offset/text hash 的 SHA-256 前 32 位。插入前置段落可能导致后续 chunk ID 改变，不承诺跨任意编辑稳定。

## 持久化与一致性

SQLite 三张主要表：metadata(fingerprint)、documents(id/source/payload)、chunks(id/document_id/payload/vector)。向量以 JSON 保存便于检查，小语料读取为 NumPy float64 matrix。WAL、foreign_keys、busy timeout 每次连接设置。`replace` 在一个事务先删除同 ID 文档及 cascade chunks，再插入新版本；任何异常回滚。embedding 网络调用发生在事务前。读 snapshot 的一条 SELECT 同时读取 chunk 和 vector，不拼接多个时刻的结果。

fingerprint 包含 schema、provider/model/explicit revision/dimension、cleaner/chunker 配置。兼容 API 的 endpoint 只存 hash，密钥不进入 fingerprint。维数相同也不能共用不同 embedding 空间。服务端同名模型背后版本变化不能自动识别，需要操作者更新 revision。拒绝原地混用时返回 409，使用新 DB 重建，不自动删除旧索引。

当前设计是单机最后提交的完整文档版本胜出；不提供用户编辑冲突检测、跨进程排队或多租户隔离。

## 查询顺序

Engine 在一次 snapshot 上构建 BM25 与 dense retriever。BM25 用 log(1+(N-df+0.5)/(df+0.5)) 的正 IDF，k1=1.5/b=.75；Dense 检查 query dimension、有限值后用 cosine exact scan。零向量相似度=0，不返回 score<=0 的 dense 结果。

Hybrid 对两个同深度结果集做 RRF，sum(1/(k+rank))，一条列表内重复 chunk 不重复计分，tie 按 chunk ID 固定排序。保留原始 BM25/dense rank/score 与 RRF 参数。Reranker 将 TopN 排序后截 TopK；lexical baseline 用 query token set coverage，保留 pre_rerank_rank、lexical_score，响应另有 selected 与 evidence_coverage。

Evidence gate 使用**原始问题**的 token coverage，和 rewrite 产生的 retrieval_query 分开保存。通过门槛的实际 chunk 构成 Citation，编号由服务生成。extractive 模式完整展示 chunk 作为 statement；compatible 模式要求每条 statement 有已提供的 citation_ids，并拒绝文本里伪造的 `[C999]` 标记。最终答案编号由代码渲染；无 evidence 或模型返回空 statements 均拒答。引用元数据完整不等于 claim 语义正确，未实现自动 NLI。

## 外部服务与展示

CompatibleClient 仅调用配置端点，有 HTTP timeout、流式 10 MB 响应上限、不跟重定向、不自动重试、不使用环境代理。provider 错误转换为安全 502/504。Sentence Transformers 为惰性可选导入，CPU、固定 revision、禁止 remote code、默认只读本地 cache；默认流程完全不加载它。

API 使用 Pydantic schema 和 16 KiB ASGI body limit；只读 corpus 根目录受控路径。静态 HTML 以 textContent 渲染证据/模型内容，避免 HTML 注入；不执行来源中的脚本。没有单独前端构建或 CDN。CLI/HTTP 共享服务，不存在另一套检索算法。

评测通过相同服务重建临时 index，先校验标注定位，再输出逐题指标、候选/相关 ID、语料与问题 hash。默认忽略环境和 .env，避免意外真实调用。协议见 eval/README.md。

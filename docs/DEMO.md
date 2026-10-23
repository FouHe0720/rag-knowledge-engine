# 可复制演示

## 校园资料演示

先运行 `make campus-demo`，再运行 `make campus-serve`。网页默认按资料范围查询，点击“计算机学制”和“人工智能学制”可比较两份2024版方案，返回原文第68段的“3至6年”和第65段的“4至6年”。材料来源及局限见 [CAMPUS](CAMPUS.md)。

以下保留通用技术笔记演示，使用默认 `data/index.sqlite3`，与校园演示数据库分开。

在项目根目录打开终端；首次先 `make install`。以下默认不下载模型、不调用外部服务。

## 1. 一键临时演示

```bash
make demo
```

脚本忽略 `.env` 与 RAG 环境变量，在临时 DB 摄取四份原创资料，展示英文 WAL、RRF、中文引用和无结果拒答。`mode=extractive` / `embedding=MOCK`，引用中有来源、章节和 offset。

## 2. 持久化索引与幂等

```bash
.venv/bin/rag ingest all
.venv/bin/rag ingest all
.venv/bin/rag documents
.venv/bin/rag query 'SQLite WAL readers' --strategy bm25 --top-k 1
.venv/bin/rag query 'RRF rank formula' --strategy dense --top-k 1
.venv/bin/rag query 'How are ranks combined by RRF?' --strategy hybrid --rerank lexical --top-k 3
.venv/bin/rag query '引用与证据' --top-k 1
.venv/bin/rag query 'zxqvplm astronomyzebra'
```

`ingest all` 会导入技术笔记与 campus 子目录内的材料；第二次每个 `changed=false`。技术评测独立限定在原有8份笔记。Dense 的 hash projection 只展示接口流程。响应中检查 `bm25_score`、`dense_score`、`rrf_score`、`pre_rerank_rank`、`lexical_score`、`selected`，同时检查 snippet 是否真的支持问题。

## 3. PDF 页码与受控路径

```bash
.venv/bin/rag query 'recovery checklist embedding provider fails retain old index' --strategy bm25 --top-k 1
.venv/bin/rag ingest ../private.txt
```

第一条应引用 `operations.pdf` 第 2 页；第二条预期失败并返回 `unsafe_path`。此故意失败命令用于展示安全边界，不属于成功验收命令。

## 4. 网页与 HTTP

```bash
make serve
```

浏览器打开 `http://127.0.0.1:8000`，左栏可摄取 `storage.md`，右栏选择策略、输入问题，展开引用和候选分数。页面不需要 Node、CDN 或构建步骤。API 文档在 `/docs`。

另一终端：

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/documents \
  -H 'Content-Type: application/json' -d '{"source":"storage.md"}'
curl -s -X POST http://127.0.0.1:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"SQLite WAL readers","strategy":"hybrid","rerank":"lexical","top_k":1}'
```

JSON 摄取路径必须在 `RAG_CORPUS_ROOT` 内，不支持任意服务器路径、URL 和 multipart 上传。删除需从清单取 opaque ID，例：

```bash
.venv/bin/rag documents
# 用上一步真实 ID 替换下面占位符后执行：
# .venv/bin/rag delete DOCUMENT_ID
```

## 5. 完整 HTTP 生命周期（使用空的独立 DB）

终端 A：

```bash
RAG_DB=data/http-demo.sqlite3 .venv/bin/uvicorn rag_engine.api.app:create_app \
  --factory --host 127.0.0.1 --port 8010
```

终端 B：

```bash
.venv/bin/python scripts/api_smoke.py --base http://127.0.0.1:8010
```

脚本需要一个**空索引**，检查静态首页、health、摄取、引用查询、删除、PDF 页码和最终拒答；完成后 DB 为空。不要对含有自己的资料的运行实例执行该 smoke 脚本。

## 6. 评测、测试与容器

```bash
make lint
make test
make annotations
make eval
cat results/offline.md
make docker-smoke
```

评测默认不受 `.env` 影响。Docker smoke 自动构建、以随机回环端口启动临时非 root 容器，跑 HTTP/页码断言并停止容器。网络只用于首次安装基础镜像/依赖。

## 7. 真实模型（未实跑）

先参照 README 配置 `.env`、真实 embedding/LLM 与新的 DB。随后显式运行：

```bash
.venv/bin/python scripts/real_smoke.py --allow-network
.venv/bin/python eval/run.py --real --output results/real-local
```

可能产生费用；项目交付时没有执行以上两条。读取模型生成内容后应亲自检查每条 claim 的语义支持，schema 校验无法代替这一步。

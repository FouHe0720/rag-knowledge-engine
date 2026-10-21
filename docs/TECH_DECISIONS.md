# 技术决策

## ADR 001：SQLite + NumPy exact search
默认索引使用 SQLite 保存文档、chunk 和向量，用 NumPy 扫描计算 cosine。小型教学语料无需额外向量服务或 FAISS 二进制依赖；查询时间 O(ND)，不提供 ANN 的规模性能。单次读取获得同一版本的 chunk/vector，单事务替换文档。扩展时可接入 FAISS，但要同时解决持久化与数据库原子提交。

## ADR 002：项目环境
预检发现系统 Python 缺少 ensurepip；使用已安装的 uv 创建项目 .venv 并安装 seed pip，不使用 sudo、不安装系统包。后续脚本自动优先使用 uv，否则使用标准 venv。

## ADR 003：稳定定位
Markdown 按 ATX heading path 分段，TXT 按段落，PDF 按页（1-based）。chunk 使用固定 Unicode 字符窗口，offset 指向清洗后的 segment，非原始文件 byte offset。chunk ID 包含 source 身份、segment 序号、offset 和文本 SHA-256。更新后内容改变时 ID 改变；段落插入可能改变后续 ID，因此评测优先使用 source + section/page 的可审计标注。

## ADR 004：接口参考
兼容服务通过 httpx 调用 /embeddings 与 /chat/completions，base URL、模型身份与密钥均由环境配置。未接入真实服务时不得把契约测试称为模型实测。

- [OpenAI embeddings reference](https://developers.openai.com/api/reference/resources/embeddings/methods/create)
- [OpenAI chat completions reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- [pypdf text extraction and resource caveats](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
- [SentenceTransformer CPU / revision / local_files_only parameters](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html)

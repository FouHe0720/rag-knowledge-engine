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

## ADR 005：引用与评测分离
Citation ID 来自真实检索 chunk，但 ID 可解析不代表语义蕴含。生成 claim 采用严格 statements/citation_ids schema；源信息由服务附加。默认 extractive 直接展示原文。词语覆盖率门槛明确是启发式。20 条审计夹具含 10 条故意无效样例，报告其结构判定，不冒充端到端 LLM citation 质量。

## ADR 006：PDF 子进程预算
pypdf 解压 stream 的内存峰值不能只靠输入 byte limit 控制。Linux worker 在固定入口解析，CPU 8 秒、父进程 timeout 12 秒、解释器导入完成后额外 256 MiB 虚拟地址空间预算，另有页数/文本/stream 限制。不把 RLIMIT_AS 描述成固定 RSS，也不声称它隔离文件/网络系统调用。公网仍需进程并发限制、容器与访问控制。

## ADR 007：CPU 模型仅显式 opt-in
默认不安装 sentence-transformers / PyTorch，不下载权重。CPU extra 保留依赖范围，实际安装需选择目标平台的 CPU PyTorch wheel；资源量随版本和模型变化，以真实下载/运行测量为准。模型 revision 必填，trust_remote_code=false，local_files_only 默认 true。该路径在本次交付中未实测。

## ADR 008：跨 Python 版本锁文件
首轮 GitHub CI 的 Python 3.11 安装发现 NumPy 2.5 要求 Python >=3.12。仅在 3.12 上执行 pip compile 会遗漏最低支持版本；`--universal` 的 Python 下界仍默认是当前解释器，因此再显式指定 `--python-version 3.11`。`make lock` 固定完整命令，输出带 Python markers 的 NumPy 2.4.6（3.11）/2.5.4（>=3.12）及各平台 hash，CI 继续验证两个解释器，不缩减支持矩阵来绕过问题。

# 标注与评测协议

`questions.jsonl` 的 48 道题由项目实现者围绕原创语料编写。每项 gold 必须包含 source、expected_quote 和 section/page/paragraph 定位；`--validate-only` 逐项检查真实解析 chunk 包含原文，无法解析就失败。两题具有跨文档多 gold，中文题检查中文路径。它们是公开开发夹具，不是独立人工盲标或 held-out test；没有基于标签写查询改写、词典捷径或特殊模型。

Recall@K 是每题相关 chunk 的覆盖率，再求 macro mean；MRR@10 只看第一个相关结果。若不同分块参数导致原文短句跨窗口而无法解析，标注校验会失败，必须审查标注/定位协议，不能自动丢掉失败题。BM25 / Dense / Hybrid / Hybrid+Lexical 使用同一集合、TopN=20、K=1/5、MRR cutoff=10，关闭 rewrite。每题只计一次实际 wall-clock latency，包含 DB snapshot、构造检索器和重排，不含生成。无预热、无并发压测，延迟不能外推生产吞吐。

`citation_cases.jsonl` 含 10 正例与 10 人为损坏例（伪造原文、错误来源、无效 chunk ID、空片段）。`citation` 的定位在实际 chunk 中解析；显式无效 ID 不允许回退。有效规则：chunk 可解析、source locator 与 gold 一致、snippet 属于真实 chunk、gold expected_quote 出现在 snippet。claim 是支持短句的审计说明，不做通用 NLI。Citation precision=有效引用/全部呈现引用；source match=能解析且来源定位正确/全部引用。另报判定结果与标注一致率。混入的坏引用在 precision 分母中，因此 0.5 是此固定夹具的组成，**不是实际回答质量评分**。

未运行 human/LLM faithfulness Judge，未声称模型语义蕴含。实际问答返回的引用另有自动化测试验证 exact chunk/snippet binding；生成式内容真实性需要独立评审。

```bash
.venv/bin/python eval/run.py --validate-only
.venv/bin/python eval/run.py
# 明确接入真实 embedding 后（可能调用收费 API；必须自行配置）：
.venv/bin/python eval/run.py --real --output results/real-local
```

默认评测完全忽略 `.env` 和 `RAG_*`，固定 fixture 模式，避免 CI 意外联网。`--real` 才读取配置；仍使用仓库原创 corpus，临时重建 DB。模型下载须另显式允许；真实评测每题约产生 3 次 embedding 请求，加上文档 embedding 批次，不执行 LLM 生成。报告写模型身份、参数、corpus/标注哈希、逐题相关 ID/结果 ID/latency。使用私有模型名时请在公开提交前检查报告。

所有 corpus 文件均为本项目原创技术学习笔记，在仓库 MIT License 下提供。PDF 可由 `scripts/build_pdf.py` 确定性重建；文本提取不依赖 reportlab。没有第三方论文全文、课程资料或个人数据。

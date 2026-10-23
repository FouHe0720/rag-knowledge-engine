# 代码导览

先比较2024版计算机与人工智能方案的弹性学制：`sources`在检索前筛选chunk和向量，避免跨专业混用。再读`scripts/campus_sources.py`理解原DOCX段号及哈希如何回查；20条校园检查只衡量证据定位，不是语义正确率。具体取舍见[CAMPUS](CAMPUS.md)。

阅读顺序：`adapters/parsing.py` → `infra/store.py` → `adapters/retrieval.py` → `services/engine.py` → `eval/run.py`。重点沿着一个真实 query 看数据和证据如何流动，再打开 `results/offline.json` 的失败题逐条检查。

## 1. 检索组件与服务边界

解析、索引更新、排名融合、引用绑定与评测分别实现，便于独立检查数据流和失败边界。这里的抽象是 DocumentParser / Chunker / EmbeddingProvider / DocumentStore / Retriever，CLI 与 HTTP 共享相同服务。

## 2. 章节、页码和固定窗口

避免将不同页面或章节不相干的证据混为同一引用。窗口 size/overlap 可配置，字符索引便于直接断言 `text == segment[start:end]`。代价是非 token-aware、可能切句、长度不等于模型 token 数。未来可以加入 sentence-aware chunker，但必须保留 provenance 和可验证 offsets。

## 3. 文档更新与片段标识

相同 source/segment/order/offset/text 得到相同 ID，未变文件通过 content hash 跳过。文本变化或前面插入 segment 可能改变后续 ID，不能承诺跨任意编辑不变。旧答案长期审计需要保存原始 corpus snapshot/版本；本实现 response 保留支持原文，索引不保留历史版本。

## 4. BM25、向量与排名融合

BM25 是 corpus-dependent 的词项统计值，cosine 在另一尺度且受 embedding 空间影响。RRF 只用各列表的 rank，sum(1/(k+rank))，本项目 rank 从 1 开始，k 默认 60。它避免直接分数校准，但丢掉分数间距，也依赖 candidate depth；不是一定优于单路检索。

## 5. 确定性向量的用途

它把 token 的 SHA-256 投影到固定维数并归一化，不存在学习到的语言知识，可能出现 hash collision。测试它是为了验证维数、持久化、查询和融合接口，不是证明能召回同义改写。报告中 Dense/Hybrid 的 MOCK 标签必须保留；真实模型的质量只能在实际加载后另评测。

## 6. 候选召回与重排

不能。先召回 TopN，再在其中重排截 TopK；没有进 TopN 的正确证据不可恢复。本实现 lexical coverage 是资源可控 baseline，不是 Cross-Encoder。它记录 pre_rerank_rank、lexical_score 和最终 rank，便于发现重排引入的变化。

## 7. 区分召回和生成问题

先检查 gold source 是否进 TopN、相关 chunk 排在哪里，再看选中的 TopK/门槛，最后检查生成 claim。召回失败时更强 LLM 没有依据；生成阶段即使引用正确也可能误述原文。评测 retrieval 与 citation integrity 分开，不把一个总体“正确率”混合解释。

## 8. 引用完整性与语义支持

ID 校验只能保证它来自 selected chunk；一个真实来源也可能被用来支持不相关或相反的 claim。服务禁止模型自造 citation ID，文本 marker 由代码渲染，原文随响应返回。它没有 NLI/semantic entailment 证明。词语 coverage 门槛也不能识别否定、时间和条件差异。

## 9. 证据门槛的局限

当前使用原始 query token coverage 的阈值，选中 chunk 无一通过就返回“根据当前知识库无法确认”；模型还可通过空 statements 拒答。无关文本中的共享词可能误过门槛，同义改写也可能被错拒。需要 unanswerable/contradictory 样本、人工校准和语义判定，不能把 evidence_score 当正确概率。

## 10. 指标的分母与含义

Recall@K 是 top K 覆盖相关 chunk 的比例，跨文档题可能多个相关项，和 Hit@K 不同。MRR@10 只看第一项相关结果。20 条 citation 夹具按 locator/真实 snippet/expected quote 判定，其中 10 条故意坏例，所以 precision=.5 描述夹具组成；判定一致率=1 只说明协议实现和这些标签相符。都不能声称是真实 LLM faithfulness。

## 11. 评测集与参考答案隔离

不允许按 question ID 写特殊查询改写、把 gold 喂给 embedding 或只汇报成功题。默认校验所有来源并保存逐题结果和语料 hash。当前语料与题目由同一实现者编写，是开发集；尚无独立 hold-out/人工复标。未来冻结 test split、记录标注分歧和盲评；LLM Judge 应说明 rubric/模型/样本数，不能包装成客观真值。

## 12. 索引身份与文件读取边界

fingerprint 绑定模型/revision/维数、endpoint hash、schema、chunk/cleaner；不匹配直接拒绝，用新 DB 重建。网络 embedding 完成再进事务替换，失败不删除旧证据。安全路径拒绝 traversal/绝对路径/越界 symlink，API 有 JSON/字节限制，PDF 子进程有 timeout/CPU/地址空间预算。仍缺公网鉴权、速率限制、tenant ACL 与真正系统沙箱，应清楚区分完成的边界和未来部署工作。

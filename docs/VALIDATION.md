# 验证记录

以下为 2026-10-23 的本地验证。运行数据库、日志及模型缓存不进入仓库。

| 检查 | 结果 |
|---|---|
| Python 3.12 完整测试 | 58 passed；一条 Starlette/httpx 弃用提示 |
| Ruff lint / format | 通过 |
| 原始资料复核 | 8 份 DOCX、68 段文本及重建 Markdown 与来源清单一致 |
| 校园回归 | 20/20；原文定位、关键字段、无匹配词与空范围 |
| 技术标注 | 48 道检索题、20 条引用检查，44 个片段，全部可解析 |
| 技术基准 | 8 份原创笔记，独立运行 BM25 / Dense / Hybrid / Lexical |
| CLI | 持久化索引及按来源查询通过 |
| 浏览器 | 资料范围切换、引用定位；桌面及 390px 窄屏 |

## 复现

```bash
make test lint annotations
make campus-demo
.venv/bin/python scripts/campus_sources.py --source-root /path/to/知识库
.venv/bin/python eval/run.py --output /tmp/rag-evaluation
```

不提供 `--source-root` 时只校验随仓库提供的摘录与清单，不会读取原始 DOCX。校园回归检查检索与引用位置，不衡量开放问答准确率；技术基准的 hash 向量标为 `MOCK`。

浏览器分别核对计算机与人工智能方案的弹性学制，验证来源切换、点击引用定位、旧结果清理、未入库来源拒答及窄屏布局。截图位于 `docs/screenshots/`。

## 验证范围

Compatible API 使用模拟 HTTP 响应检查请求、超时、引用 ID 与错误处理。本轮未调用外部模型，也未重建 Docker 镜像。此前已验证容器内 HTTP 入库、查询、删除及 PDF 页码；当前镜像状态由 CI 的容器检查确定。

PDF 子进程不计入普通父进程 coverage。固定字符窗口、词项证据门槛和模型身份校验的取舍见 [技术决策](TECH_DECISIONS.md)。公开内容扫描检查明显密钥、机器路径和运行产物，另核对来源与引用材料。

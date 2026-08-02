# 结构化数据

## 官方基准存档

- [`benchmarks.json`](./benchmarks.json) —— 主文档 §六 的 **31 项官方基准**结构化存档（官方模型卡口径，2026-07-28 抓取）。

### 字段说明

| 字段 | 说明 |
| --- | --- |
| `meta` | 数据版本、来源、官方评测设置、harness、数量与口径声明 |
| `benchmarks[]` | 每项基准：`name` / `category`（7 类）/ `score` / `unit`（Elo、F1）/ `harness` / `compare`（关键对比模型分数）/ `note` |

### 类别分布

coding=8 · info-gathering=2 · tool-use=3 · productivity=5 · agent=2 · reasoning=3 · multimodal=8

### 维护规则

- 修改 `benchmarks.json` 时同步更新主文档 §六 对应表格备注；
- **实测数据不要写入此文件**——请走 [benchmark-data.yml Issue 模板](../.github/ISSUE_TEMPLATE/benchmark-data.yml)；
- 文件合法性由 CI（`scripts/check_benchmarks.py`）自动校验。

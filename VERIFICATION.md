# 核验清单（Verification Checklist）

> 目的：保证仓库数据真实性。**任何"看起来像事实"的数字都必须能溯源到明确的来源等级；无法溯源的必须标注"出处待确认"，不得标为官方口径。**
> 首次核验：2026-08-02（全仓库 vs 官方模型卡/论文/LICENSE/技术博客，见 §4 记录）。

---

## 1. 什么时候必须核验

| 触发场景 | 要求 |
| --- | --- |
| 新增/修改任何数据 | 架构、基准、价格、License 条款的数字，写入前先核 |
| 引用第三方文章的数字 | 必须先回**一级来源**比对（第三方可能转述错，实战案例：DeepInfra 把 K3 激活参数写成 50B，官方是 104B） |
| 官方资料更新 | 模型卡 revision、新论文、新博客发布后，重核受影响条目 |
| 发布前 | push 前至少跑 `scripts/check_links.py` + `scripts/check_benchmarks.py`，并确认无 D 级（出处待确认）残留 |

## 2. 一级权威来源（本仓库对应表）

| 来源 | 用途 | 地址 |
| --- | --- | --- |
| HF 官方模型卡 | 架构规格、完整评测表、量化、模态、部署建议 | `huggingface.co/moonshotai/Kimi-K3` |
| 官方技术博客 | 机制叙述、整体扩展效率（2.5×） | `kimi.com/blog/kimi-k3` |
| 官方 LICENSE 原文 | License 条款（MaaS 门槛、署名条件、豁免） | `HF …/raw/main/LICENSE` |
| arXiv 论文 | AttnRes / Kimi Linear 机制与数据 | `arxiv.org/abs/2603.15031` · `2510.26692` |
| 官方 API 文档 / 定价页 | reasoning_effort、价格、输出上限 | `platform.kimi.ai` |
| 推理引擎官方博客 | vLLM / SGLang 支持范围与性能数字 | `vllm.ai/blog/2026-07-27-k3` 等 |

## 3. 核验五步

1. **定位声明**：把要核验的数字从文章中摘出，记下"当前来源"与"当前等级"；
2. **抓一级来源**：用 anysearch `extract` 抓官方页面原文（不只看摘要，摘要可能缺上下文）；
3. **逐项比对**：数字一致否？注意**口径差异**（harness、评测条件、单位、是否带工具、有无上下文压缩）；
4. **定级**（写进文章与台账）：

| 级 | 含义 | 处理 |
| --- | --- | --- |
| **A** | 官方原文可直接查证（模型卡字段、论文公式、License 条款） | 正常引用，标注官方 |
| **B** | 官方自报但无逐字原文（博客叙述性数字，如 2.5× 扩展效率） | 标注"官方自报，未复现" |
| **C** | 第三方转述/第三方评测（DeepInfra、Artificial Analysis、EmpirioLabs） | 标注来源，注明"非官方" |
| **D** | 出处待确认或推测 | **必须标注，优先撤回或改可溯源表述** |

5. **修正与记录**：不一致 → 改数据 + 文中加注 + 更新 `SOURCES.md` 台账 + 追加本清单 §4 记录。

### 实操命令速查（anysearch）

```bash
# 批量搜多个角度（拿候选链接 + 摘要里的数字）
python3 ~/.hermes/skills/anysearch/scripts/anysearch_cli.py batch_search \
  --queries '[{"query":"Kimi K3 activated parameters official model card","max_results":5},
              {"query":"Kimi K3 SWE-bench Verified score","max_results":5}]'

# 抓一级来源全文（模型卡 / 论文 / LICENSE / 博客）
python3 ~/.hermes/skills/anysearch/scripts/anysearch_cli.py extract "https://huggingface.co/moonshotai/Kimi-K3"

# 验证论文号存在（arXiv API 有时空响应，用页面抓取兜底）
curl -s -A "Mozilla/5.0" "https://arxiv.org/abs/2603.15031" | grep -oE "<title>[^<]+</title>"
```

**实战避坑**：
- 输出含二进制字符时 `grep` 会报 `binary file matches` → 加管道 `| strings` 或用 `grep -a`；
- `extract` 遇到 403/404（如 MarkTechPost、部分 Medium）→ 换同主题的供应商博客（deepinfra / empiriolabs 通常可抓），或直接用搜索摘要里的数字并标注；
- **第三方对比文必须回官方核对**：DeepInfra 曾把 K3 激活参数写成 50B（官方 104B），只信第三方就会带入错误（见 §4 记录 #1）。

## 4. 核验记录（只追加，不删除）

### 2026-08-02 · 全仓库首轮核验

| # | 条目 | 原值（原来源） | 官方值/结论 | 级 | 处理 | 提交 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | K3 激活参数（横评篇） | 50B（DeepInfra 转述） | **104B**（官方模型卡） | A | 改为 104B + 注明未采信 DeepInfra 口径 | #27 |
| 2 | AttnRes "25% 训练效率 / <2% 开销" | 标为官方数据 | 官方博客/论文/模型卡**均未公布** | D | 全仓库撤回，改用论文 marginal/minimal 表述 + 2.5× 官方口径 | #27 |
| 3 | DECK-Bench 73.5（主文档 §6.4） | 未标来源 | 官方完整表**未收录** | D | 标注"来源待确认（疑似第三方聚合）"，同步 data/benchmarks.json | #27 |
| 4 | SWE-bench Verified 76.8%（横评篇） | DeepInfra 转述 | 官方**未公布**此基准 | C | 加注转述口径 + 评测条件注意 | #27 |
| 5 | License 名称 "Modified MIT"（横评篇） | 第三方简称 | 官方名 **Kimi K3 License** | A | 加注官方名 + 指路 License 实务篇 | #27 |
| 6 | 架构规格（2.8T/104B/93 层/69+24/896/16/2 等） | 官方模型卡 | 逐项一致 | A | 无需修改 | — |
| 7 | 31 项基准（除 DECK-Bench 外） | 官方模型卡 | 逐项一致 | A | 无需修改 | — |
| 8 | License 实务篇条款 2/3/4 | 官方 LICENSE | 逐条一致（2000 万美元、1 亿 MAU **或** 2000 万美元月收入） | A | 无需修改 | — |
| 9 | 论文号 2603.15031 / 2510.26692 | 引用 | arXiv 验证**真实存在** | A | 无需修改 | — |
| 10 | vLLM 118→370 tok/s、DSpark 等 | vLLM 官方博客 | 原文一致 | B | 无需修改（标注 vLLM 自测） | — |

## 5. 维护规则

- 核验记录**只追加不删除**（保留历史，便于追溯口径变化）；
- **D 级条目必须限期处理**（溯源升级或撤回），不允许长期悬挂；
- 发布前自检三连：`check_benchmarks.py` ✅ · `check_links.py` ✅ · 无 D 级残留 ✅；
- 新文章采用本模板 §3 定级习惯写"口径声明"，与现有各篇保持一致。

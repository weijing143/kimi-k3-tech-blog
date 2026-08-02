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

### 2026-08-02 · 全量补核（第二轮：主文档 §5/§7/§8/§9/§12 + KDA 篇）

| # | 条目 | 官方源 | 结果 | 级 |
| --- | --- | --- | --- | --- |
| 11 | §5 全均衡 EP（static shapes / no host sync） | 官方博客原文 | 一致 | A |
| 12 | §5 vLLM KDA prefill-cache 贡献 | 官方博客原文 | 一致 | A |
| 13 | §5 Mooncake 缓存命中率 >90%（编程负载） | 官方博客原文 | 一致 | A |
| 14 | §5 64+ 加速卡 Supernode 建议 | 官方博客原文 | 一致 | A |
| 15 | §三 价格 $0.30 / $3.00 / $15.00 | 官方博客原文 | 一致 | A |
| 16 | §7 Arena.ai Elo 1679（登顶超 Fable 5） | Arena 官方公告 | 一致 | A |
| 17 | §8 芯片设计案例（48h / 4mm² / 100MHz / 8700 tok/s / 1.46M cells） | 官方博客原文 | 一致 | A |
| 18 | §8 MiniTriton / I-Love-Q（2h / 20+ 论文 / 300+ EOS / 3000+ 行） | 官方博客原文 | 一致 | A |
| 19 | §9 reasoning_effort low/high/max（默认 max） | 官方 API quickstart | 一致 | A |
| 20 | KDA 篇 6.3× TPOT（1.84 vs 11.48ms @1M）与 3:1 混合比 | Kimi Linear 官方仓库 | 一致（48B 验证模型口径已标注） | A |
| 21 | §7.2 AA 单任务成本 $0.94 / token 效率 +21% | Artificial Analysis（第三方） | 保留 C 级标注 | C |

### 2026-08-03 · 第三轮：官方 × 第三方独立实测比对

> 目的：按新复现口径（官方自报数据与独立第三方实测一致 → 标记"复现"），用 Artificial Analysis / Vals AI / LiveBench / Arena 的独立跑分比对官方 31 项基准。

| # | 基准 | 官方值 | 第三方实测 | 来源 | 结论 | 复现状态 |
| --- | --- | --- | --- | --- | --- | --- |
| 22 | GPQA-Diamond | 93.5 | 93.5% / 94% | AA 模型页（graysoft 转述）/ AA 快照 | 一致（±0.5 内） | **复现**（官方×第三方） |
| 23 | HLE-Full（无工具） | 43.5 | 43.5% | AA 快照（emergent.sh，2026-07-23） | 一致 | **复现**（官方×第三方） |
| 24 | HLE-Full（带工具） | 56.0 | 56.0% | AA 快照（emergent.sh，2026-07-23） | 一致 | **复现**（官方×第三方） |
| 25 | APEX-Agents | 41.0 | 41%（APEX-Agents-AA） | AA（emergent.sh 转述） | 一致，但 AA 实现可能与官方同源 | **复现**（同源可能已注明） |
| 26 | GDPval-AA v2 | 1686 Elo | Elo 1,686 | AA 快照（emergent.sh，2026-07-23） | 一致（官方表收录即 AA 数据，属转录核对） | **复现**（同源转录核对） |
| 27 | AA-Briefcase | 1548 Elo | Elo 1,548 | AA 快照（emergent.sh，2026-07-23） | 一致（基准本身即 AA 评测） | **复现**（同源转录核对） |
| 28 | Terminal-Bench 2.1 | 88.3（Kimi Code） | 85% | AA Terminal-Bench v2.1 页 | 有差异（harness 不同，3.3pt） | 外部实测存在，不标复现 |
| 29 | DeepSWE | 67.5（Kimi Code） | 64% | AA Coding Agent Index | 有差异（harness 不同，3.5pt） | 外部实测存在，不标复现 |
| 30 | AutomationBench | 30.8（600-task subset） | 53%（AutomationBench-AA） | AA | 口径不同（AA 版 vs 官方子集版） | 不可比，不标复现 |

**新增第三方独立实测登记（官方表未收录）**：AA Intelligence Index 57、AA Coding Agent Index 57、Vals AI Index 74.70%、LiveBench 综合 79.2、LMArena Frontend Code Arena Elo 1679、SciCode 58.7%、τ³-Banking 33%、AA-LCR 74.7%、AA-Omniscience 46%/49%、Harvey LAB-AA 95%、AutomationBench-AA 53% —— 全部 C 级（第三方独立评测），已写入台账 §2.2。

### 2026-08-03 · 第四轮：架构 / License / API / MoE-KDA 官方 × 第三方比对

> 目的：按同一复现口径（官方与独立第三方数据一致 → 标记复现）补齐台账 §1/§3/§4/§5。第三方来源：openlm.ai、Context Studios、inimino.org、DeepInfra、devoriales、lorphic、trendingtopics.eu、Towards AI、36kr、Together/Fireworks/Modal/SiliconFlow/OpenRouter 等 API 平台、vLLM Day-0 博客。

| # | 条目 | 官方值 | 第三方值 | 结论 | 复现状态 |
| --- | --- | --- | --- | --- | --- |
| 31 | 总参数 2.8T / 激活 104B | 模型卡 | 5 家独立一致 | 一致 | **复现** |
| 32 | 93 层（69 KDA + 24 Gated MLA + 1 Dense） | 模型卡 | Context Studios 逐项一致 | 一致 | **复现** |
| 33 | MoE 896/16（共享 2 未确认） | 模型卡 | vLLM/inimino/Context Studios/DeepInfra | 一致 | **复现** |
| 34 | SiTU-GLU 激活函数 | 模型卡 | lorphic 确认 Sigmoid Tanh Unit | 一致 | **复现** |
| 35 | MoonViT-V2 / 1M 上下文 / MXFP4-MXFP8 | 模型卡 | inimino/lorphic/Context Studios | 一致 | **复现** |
| 36 | KDA 6.3× / 2.5× 扩展效率 | 官方博客 | acingai、Medium、DeepInfra、lorphic 均仅**转述官方声称** | 无独立实测 | **不标复现** |
| 37 | License 五条条款 / MaaS 定义 / $20M 门槛 / 1 亿 MAU 署名 / 豁免 | LICENSE 原文 | 五家独立解读逐条一致 | 一致 | **复现** |
| 38 | License 名称（非 Modified MIT） | LICENSE 标题 | Context Studios、inimino 纠正误传 | 一致 | **复现** |
| 39 | 国际定价 $0.30/$3.00/$15.00 | 官方定价页 | ≥9 家平台同价售卖 | 一致 | **复现** |
| 40 | 中国区定价 ¥2/¥20/¥100 | 官方定价页 | kimi 中文页 + 知乎确认 ¥20/¥100 | 一致 | **复现** |
| 41 | reasoning_effort 默认 max | Quickstart | DeepInfra/lorphic 确认默认 max；但 DeepInfra 称 low/high 尚在规划 | 默认值一致，范围有时点差异 | **部分复现**（差异已标注） |
| 42 | 完整回传 assistant message / 131K 输出上限 | Quickstart | lorphic 独立确认 | 一致 | **复现** |
| 43 | Mooncake 缓存命中率 >90% | 官方博客 | lorphic/emergent 转述官方数字 | 无独立实测 | **不标复现** |
| 44 | LatentMoE 源自 NVIDIA | vLLM Day-0 博客 | 链接 NVIDIA 研究页 + lorphic | 一致 | **复现** |
| 45 | Quantile Balancing / EP 静态形状 | 技术报告转述 | AlphaXiv + vLLM Day-0 + lorphic 三源一致 | 一致 | **复现** |
| 46 | KDA 公式可实现性 | 论文 | vLLM 独立实现 FlashKDA 内核并开源 | 工程验证 | **部分复现** |

**口径原则（本轮确立并写入台账）**：①"复现（官方×第三方）"= 独立第三方**实测/实价/独立读取模型卡**与官方一致；②第三方**仅转述官方声称**（如 6.3×、2.5×、缓存命中率）不算复现，保持"未复现"；③"同源"数据（官方表收录的 AA 基准）如实标注同源转录核对。

## 5. 维护规则

- 核验记录**只追加不删除**（保留历史，便于追溯口径变化）；
- **D 级条目必须限期处理**（溯源升级或撤回），不允许长期悬挂；
- 发布前自检三连：`check_benchmarks.py` ✅ · `check_links.py` ✅ · 无 D 级残留 ✅；
- 新文章采用本模板 §3 定级习惯写"口径声明"，与现有各篇保持一致。

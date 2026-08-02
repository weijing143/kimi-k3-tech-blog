# SOURCES.md · 证据台账

> 本表登记仓库中**关键数据的来源、核对日期与证据等级**，用于：（1）让读者能区分"官方一手 / 官方自报 / 第三方转述 / 推测 / 实测"；（2）官方模型卡、价格、推理框架更新后做增量维护。
> 最近全量核对日期：**2026-08-03**（含官方 × 第三方实测比对）。
>
> **证据等级定义**：
> - **A · 官方一手**：直接取自 Moonshot 官方模型卡 / 博客 / 文档 / LICENSE 原文；
> - **B · 官方自报**：官方发布但属厂商自评口径（如自家基准、效率提升倍数），无独立复现；
> - **C · 第三方转述**：二手报道 / 社区录入，已交叉验证但非一手；
> - **D · 推测 / 估算**：可复算的算术或有依据的推断，文中已标注；
> - **E · 可复跑验证**：本仓库或社区通过公开脚本得到；必须注明属于离线单测、真实 API 测试还是硬件实测。
>
> **复现状态定义**（与证据等级分开记录）：
> - **未复现**：仅核对来源或转录数据，未按原方法重新执行；
> - **外部实测**：第三方在真实环境中测得，环境与原始证据可追溯，但本项目未复跑；
> - **复现（官方 × 第三方比对）**：官方自报数据与至少一个**独立第三方实测**（Artificial Analysis / Vals AI / LiveBench / Arena 等）在可比口径下比对一致 → 标记复现。两独立来源相互印证，但**非本项目实跑**；
> - **本项目复现**：本项目按公开方法执行，并保留环境、脚本与原始输出；
> - **交叉复现**：本项目与至少一个独立外部来源在可比条件下得到一致结论。
>
> 证据等级描述“数据来自哪里、性质是什么”，复现状态描述“本项目验证到了哪一步”。E 级不代表来源权威性高于 A 级；外部实测和本项目复现也不能替代对测试条件的审查。

## 1. 架构与规格（主文档 §三、LatentMoE 篇、KDA 篇）

| 数据点 | 取值 | 来源（原文位置） | 核对日期 | 等级 | 复现状态 |
| --- | --- | --- | --- | --- | --- |
| 总参数量 / 激活参数 | 2.8T / 104B | [HF 模型卡](https://huggingface.co/moonshotai/Kimi-K3) Model Summary 表 | 2026-07-28 | A | 未复现 |
| 层数与注意力组成 | 93 层；69 KDA + 24 Gated MLA + 1 Dense | 同上 | 2026-07-28 | A | 未复现 |
| 注意力隐藏维度 / 头数 | 7168 / 96 | 同上 | 2026-07-28 | A | 未复现 |
| MoE：专家数 / 激活 / 共享 | 896 / 16 / 2 | 同上 | 2026-07-28 | A | 未复现 |
| Latent MoE 维度 / 单专家隐藏维度 | 3584 / 3072 | 同上 | 2026-07-28 | A | 未复现 |
| 激活函数 | SiTU-GLU | 同上 | 2026-07-28 | A | 未复现 |
| SiTU-GLU 上限常数 β₁β₂=100 | 4 × 25 | [AlphaXiv 技术报告摘要](https://www.alphaxiv.org/overview/2607.kimi-k3-report) | 2026-07-28 | C（转述官方报告） | 未复现 |
| 视觉编码器 | MoonViT-V2，401M | HF 模型卡 Model Summary 表 | 2026-07-28 | A | 未复现 |
| 词表 / 上下文 | 160K / 1,048,576 | 同上 | 2026-07-28 | A | 未复现 |
| 量化 | MXFP4 权重 / MXFP8 激活（QAT） | 同上 | 2026-07-28 | A | 未复现 |
| 模态 | 模型卡字段 "Text, Image"；视频见介绍与 Quickstart | HF 模型卡 + Quickstart | 2026-07-28 | A（口径已加注） | 未复现 |
| KDA 6.3× 解码提速 | vs MLA 全注意力 @1M 上下文 | 官方博客 / Kimi Linear 论文 | 2026-07-28 | B | 未复现 |
| 2.5× 扩展效率（vs K2） | 约 2.5× | 官方博客 | 2026-07-28 | B | 未复现 |
| AttnRes 训练/推理开销 | 论文原文：marginal / minimal | arXiv:2603.15031 | 2026-08-02 | A（定性） | 未复现 |

## 2. 基准评测（主文档 §六，31 项）

| 数据点 | 来源 | 核对日期 | 等级 | 复现状态 |
| --- | --- | --- | --- | --- |
| 31 项收录分数 | [HF 模型卡](https://huggingface.co/moonshotai/Kimi-K3) Evaluation Results 完整表 | 2026-07-28 | B（官方自报） | 未复现 |
| 其中十余项（SWE Marathon、Terminal-Bench、KCB 2.0、BrowseComp、GDPval、MMMU-Pro、ZeroBench 等） | 已逐项与官方表比对 | 2026-07-28 | B | 未复现（仅核对） |
| 其余收录项 | 转录自同一张官方表，**未逐项比对**（同源转录，风险低） | 2026-07-28 | B | 未复现 |
| 他模型对照分数 | 官方表脚注注明各自 harness 与来源（Artificial Analysis / Vals AI / 官方榜单，截至 2026-07-23） | 2026-07-28 | B/C | 未复现 |

### 2.1 官方 × 第三方独立实测比对（2026-08-03 采集）

> 第三方来源均为独立机构自行跑分（Artificial Analysis 自建 harness 实测；LiveBench / Vals AI / Arena 各自独立榜单）。**复现状态 = 复现（官方 × 第三方比对）表示两独立来源数值一致，非本项目实跑。**

| 基准 | 官方值 | 第三方实测值 | 第三方来源 | 比对结论 | 复现状态 |
| --- | --- | --- | --- | --- | --- |
| GPQA-Diamond | 93.5 | 93.5%（graysoft 转 AA 模型页）/ 94%（AA 快照） | [AA 模型页](https://artificialanalysis.ai/models/kimi-k3) · [emergent.sh](https://emergent.sh/learn/kimi-k3-benchmark)（2026-07-23 快照） | 一致（±0.5 内） | **复现** |
| HLE-Full（无工具） | 43.5 | 43.5% | AA 快照（emergent.sh，2026-07-23） | 一致 | **复现** |
| HLE-Full（带工具） | 56.0 | 56.0% | AA 快照（emergent.sh，2026-07-23） | 一致 | **复现** |
| APEX-Agents | 41.0 | 41%（APEX-Agents-AA） | AA（emergent.sh 转述） | 一致（注意：APEX-Agents-AA 即 AA 实现，可能与官方表同源） | **复现**（同源可能已注明） |
| GDPval-AA v2 | 1686 Elo | Elo 1,686 | AA 快照（emergent.sh，2026-07-23） | 一致（基准本身即 AA 评测，官方表收录 AA 数据，属转录核对） | **复现**（同源转录核对） |
| AA-Briefcase | 1548 Elo | Elo 1,548 | AA 快照（emergent.sh，2026-07-23） | 一致（基准本身即 AA 评测） | **复现**（同源转录核对） |
| Terminal-Bench 2.1 | 88.3（Kimi Code） | 85% | [AA Terminal-Bench v2.1 页](https://artificialanalysis.ai/evaluations/terminalbench-v2-1) | **有差异**（AA 独立 harness vs 官方 Kimi Code，差 3.3pt） | 外部实测存在，**不标复现** |
| DeepSWE | 67.5（Kimi Code） | 64% | AA Coding Agent Index（AA LinkedIn 公布） | **有差异**（harness 不同） | 外部实测存在，**不标复现** |
| AutomationBench | 30.8（600-task subset） | 53%（AutomationBench-AA） | AA（emergent.sh 转述） | **口径不同**（AA 版 vs 官方子集版，不可直接比） | 不可比，**不标复现** |

### 2.2 第三方独立实测（官方表未收录，2026-08-03 采集）

| 指标 | K3 值 | 来源 | 等级 | 复现状态 |
| --- | --- | --- | --- | --- |
| AA Intelligence Index v4.1 | 57（排名 #3/#4，开放权重第一） | [AA 模型页](https://artificialanalysis.ai/models/kimi-k3) | C（第三方独立评测） | 外部实测 |
| Vals AI Index | 74.70%（#2/#3） | [vals.ai/benchmarks](https://www.vals.ai/benchmarks)（2026-07-23 更新） | C | 外部实测 |
| LiveBench（综合分） | 79.2（8 个子项 62.2–90.7） | [livebench.ai](https://livebench.ai/) | C | 外部实测 |
| LMArena Frontend Code Arena | Elo 1679（#1，超 Fable 5） | Arena 官方公告（2026-07-16） | A（榜单官方公告） | 外部实测 |
| AA Coding Agent Index | 57（#5，开放权重第一） | AA 官方公布 | C | 外部实测 |
| SciCode | 58.7% | AA 快照（emergent.sh，2026-07-23） | C | 外部实测 |
| τ³-Banking | 33% | AA 快照（emergent.sh，2026-07-23） | C | 外部实测 |
| AA-LCR（长上下文） | 74.7% | AA 快照（emergent.sh，2026-07-23） | C | 外部实测 |
| AA-Omniscience（准确率 / 非幻觉率） | 46% / 49% | AA 快照（emergent.sh，2026-07-23） | C | 外部实测 |
| Harvey LAB-AA | 95%（#1） | AA（emergent.sh 转述） | C | 外部实测 |
| AutomationBench-AA | 53%（#1） | AA（emergent.sh 转述） | C | 外部实测 |

## 3. License（License 篇）

| 数据点 | 来源（原文位置） | 核对日期 | 等级 | 复现状态 |
| --- | --- | --- | --- | --- |
| 五条条款全部解读 | [LICENSE 原文](https://huggingface.co/moonshotai/Kimi-K3/raw/main/LICENSE) 全文 | 2026-07-28 | A | 未复现（原文核对） |
| "MaaS" 定义与两类豁免 | 原文条款 2 | 2026-07-28 | A | 未复现（原文核对） |
| $20M 年收入门槛（全部合计收入口径） | 原文条款 2 | 2026-07-28 | A | 未复现（原文核对） |
| 1 亿 MAU / $20M 月收署名（"或"关系） | 原文条款 3 | 2026-07-28 | A | 未复现（原文核对） |
| 内部使用与认证伙伴豁免 | 原文条款 4 | 2026-07-28 | A | 未复现（原文核对） |

## 4. API 与定价（主文档 §八、Agent 篇）

| 数据点 | 来源 | 核对日期 | 等级 | 复现状态 |
| --- | --- | --- | --- | --- |
| 国际定价 $0.30 / $3.00 / $15.00 每 MTok | 官方定价页 | 2026-07-28 | A | 未复现 |
| 中国区定价 ¥2 / ¥20 / ¥100 | API 平台定价页 | 2026-07-28 | A | 未复现 |
| `reasoning_effort` low / high / max（默认 max） | [Quickstart](https://platform.kimi.com/docs/guide/kimi-k3-quickstart) | 2026-07-28 | A | 未复现 |
| 完整回传 assistant message（reasoning_content + tool_calls） | Quickstart / HF 模型卡 §6 | 2026-07-28 | A | 未复现 |
| 视频输入经 Files API 上传引用 | Quickstart 视觉输入文档 | 2026-07-28 | A | 未复现 |
| 默认最大输出 131,072 tokens（`max_completion_tokens`） | Quickstart | 2026-07-28 | A | 未复现 |
| 编程负载缓存命中率 >90% | 官方博客（Mooncake 架构） | 2026-07-28 | B | 未复现 |

## 5. MoE / KDA 系统实现（LatentMoE 篇 §6、KDA 篇）

| 数据点 | 来源 | 核对日期 | 等级 | 复现状态 |
| --- | --- | --- | --- | --- |
| LatentMoE 由 NVIDIA 提出及带宽/通信收益 | [vLLM Day-0 博客](https://vllm.ai/blog/2026-07-27-k3) | 2026-07-28 | A（官方引擎方） | 未复现 |
| vLLM 两套后端（TRT-LLM-Gen / MegaMoE）与 EPLB | 同上 | 2026-07-28 | A | 未复现 |
| Quantile Balancing 机制描述 | AlphaXiv 报告摘要（转述官方技术报告） | 2026-07-28 | C | 未复现 |
| EP 静态形状 / 无 host sync 训练 | 同上 | 2026-07-28 | C | 未复现 |
| KDA 递推公式与 FLA/vLLM 实现追踪 | [Kimi Linear 论文](https://arxiv.org/abs/2510.26692) + 开源仓库 | 2026-07-28 | A（论文）/ D（推导解读） | 未复现 |

## 6. 代码与实验（examples/、自部署手册）

| 数据点 | 证据 | 核对日期 | 等级 | 复现状态 |
| --- | --- | --- | --- | --- |
| k3_agent.py 行为（回传/循环/重试/裁剪/成本） | 按官方文档行为编写 + 10 个离线单元测试（CI 可复跑） | 2026-07-28 | **E（离线测试）** | **本项目离线复现**（非真实 API 端到端） |
| bench_serving.py 测量口径 | 7 个离线单元测试（CI 可复跑） | 2026-07-28 | **E（离线测试）** | **本项目离线复现**（未对真实端点压测） |
| runbook §4.1 外部实测索引 | 仅收录环境和原始证据可追溯的数据 | — | — | **待收录** |
| runbook §5 实验 A–E 本项目结果表 | **留空待实测** | — | — | **待本项目复现** |
| runbook §8 第三方发布前估算 | 各来源 URL 已列，全部为权重发布前预测口径 | 2026-07-28 | C/D（已显著标注） | 未复现（非实测） |

## 7. 明确未验证 / 待验证清单

1. runbook §5 全部延迟/吞吐/显存表格 —— 待真实硬件实测；
2. "2.5× 扩展效率"—— 官方自报，无第三方复现；"25% 训练效率"—— 2026-08-02 核验：官方各源均未公布该百分比，出处未确认，已从各篇撤回；
3. QB 精确公式（更新频率、分位数估计方式）—— 待核对技术报告原文；
4. 第三方（如 GPT 评审）全文逐句校对 —— 未做；
5. 代码对真实 K3 API / 自部署 vLLM/SGLang 的端到端验证 —— 未做，需 API 额度与硬件；
6. 官方 31 项中仅 6 项获得第三方独立实测比对（§2.1）；其余 25 项（FrontierSWE、Program Bench、KCB 2.0、BrowseComp、SWE Marathon、MMMU-Pro、ZeroBench 等）暂无公开第三方独立实测，仍为 B 级官方自报未复现；
7. Terminal-Bench 2.1 / DeepSWE 官方值与 AA 独立 harness 存在差异（3.3pt / 3.5pt）—— 差异源于 harness 而非模型能力，属口径差异，持续关注。

## 维护说明

- 官方模型卡 / 定价 / 推理框架更新后，改动对应行并更新"核对日期"；
- 新增数据必须带等级标注，E 级必须附可复跑证据（脚本 + 环境 + 原始输出）；
- 外部实测必须登记来源、测试日期、模型版本/哈希、硬件、引擎版本、启动参数、并行策略、输入/输出长度、并发数、请求数、错误率与原始结果链接；缺失关键上下文时只作线索，不进入结果表；
- 外部数据不得标为“本项目复现”；本项目复现必须保留执行命令与原始输出，并说明与外部测试条件的差异；
- 提交规范见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

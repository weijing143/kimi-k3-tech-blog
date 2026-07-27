# Kimi K3 技术解析：全球首个开源 3T 级模型

> **发布方**：月之暗面（Moonshot AI）
> **发布时间**：2026-07-16
> **定位**：开放前沿智能（Open Frontier Intelligence）旗舰模型
> **状态**：API 与各端产品已上线；完整权重与技术报告于 **2026-07-27** 发布，HF 仓库 `moonshotai/Kimi-K3` 占位页已上线
> **文档版本**：v2.2（2026-07-27 修订：权重发布日信息更新）

---

## 目录

1. [TL;DR 核心要点](#一tldr-核心要点)
2. [发布背景与行业意义](#二发布背景与行业意义)
3. [核心规格总表](#三核心规格总表)
4. [架构深度解析](#四架构深度解析)
5. [训练与推理基础设施](#五训练与推理基础设施)
6. [完整基准评测（31 项）](#六完整基准评测31-项)
7. [第三方评测与行业反应](#七第三方评测与行业反应)
8. [官方案例研究](#八官方案例研究)
9. [API 完整使用指南](#九api-完整使用指南)
10. [已知限制与使用建议](#十已知限制与使用建议)
11. [产品矩阵与选型建议](#十一产品矩阵与选型建议)
12. [部署、开源与生态](#十二部署开源与生态)
13. [常见问题 FAQ](#十三常见问题-faq)
14. [参考链接](#十四参考链接)

---

## 一、TL;DR 核心要点

- **2.8 万亿总参数**（第三方模型卡片标注激活参数约 500 亿），全球首个达到 3T 级别的开源权重模型；此前最大开源模型为 1.6T 的 DeepSeek V4 Pro。
- 架构基于 **Kimi Delta Attention（KDA）** 与 **Attention Residuals（AttnRes）** 两大创新，分别解决"序列长度"与"模型深度"两个维度上的信息流动问题。
- **Stable LatentMoE**：896 个专家中每 token 仅激活 16 个，稀疏度大幅超越前代。
- **100 万 token 上下文窗口**（K2.6 的 4 倍），原生支持文本、图像、视频输入。
- 相比 K2，**整体扩展效率（scaling efficiency）提升约 2.5 倍**。
- 始终开启思考模式，`reasoning_effort` 支持 low / high / max 三档，max 为默认（首发时仅 max 档，low / high 已随后开放）。
- 官方自评：整体仍落后于 Claude Fable 5 与 GPT 5.6 Sol，但在评测套件中稳定超越其他所有受测模型，已进入前沿模型竞争区间。
- 第三方亮点：Arena.ai 前端代码竞技场 **Elo 1679 登顶第一**；Artificial Analysis 智能指数 57 分，与 Opus 4.8 / GPT-5.5 同档。

---

## 二、发布背景与行业意义

### 2.1 开源模型的规模竞赛

Kimi K3 是首个触及 2.8 万亿参数的开源模型。根据官方数据，**过去 12 个月（2025/07–2026/07）中的 9 个月，Kimi 系列模型都保持着开源模型的参数规模上限**。从 K2（1T 级）到 K3（2.8T），月之暗面在一年内将开源模型的规模上限提升了近 3 倍。

### 2.2 为什么"开源 3T"重要

- **能力上限**：参数量决定模型容量上限。2.8T 让开源阵营首次在预训练规模上与闭源前沿并跑。
- **可私有化**：与闭源 API 不同，开源权重允许研究机构、企业下载后进行学术研究、二次开发与私有化部署——对金融、医疗、法律等数据敏感行业具有不可替代的价值。
- **成本变量**：Financial Times 分析称，随着美国模型服务价格上涨，越来越多美欧企业为降低成本转向价格更低的中国模型；K3 的发布可能动摇"中国前沿模型落后美国 8–12 个月"的业界共识。

### 2.3 需要泼的冷水

- 2.8T MoE 对推理硬件要求极高，官方建议 **64+ 加速卡 Supernode**，中小团队难以独立承担部署成本。
- 开源协议以权重发布时的模型卡与 LICENSE 文件为准（预期 Modified MIT，与 K2 系列一致，**商用前请阅读原文**）。
- 官方评测为厂商自报口径，且各模型使用不同 agentic harness，横向对比需谨慎。

---

## 三、核心规格总表

| 项目 | 规格 |
| --- | --- |
| 总参数量 | 2.8T |
| 激活参数量 | 约 50B（第三方模型卡片数据，以官方技术报告为准） |
| MoE 结构 | Stable LatentMoE，896 专家 / 每 token 激活 16 |
| 上下文窗口 | 1,000,000 tokens |
| 最大输出长度 | 默认 131,072 tokens，最高 1,048,576 tokens |
| 模态 | 文本、图像、视频 → 文本（原生多模态，非拼接式） |
| 思考模式 | 始终开启；`reasoning_effort` 支持 low / high / max，`max` 为默认 |
| 量化方案 | 权重 MXFP4、激活 MXFP8（SFT 阶段起量化感知训练） |
| API 价格（国际） | 缓存命中输入 $0.30 / 未命中输入 $3.00 / 输出 $15.00（每百万 tokens） |
| API 价格（中国区） | ¥2 / ¥20 / ¥100（每百万 tokens；来源：API 平台定价页，官方博客仅公布美元价格） |
| 缓存命中率 | 编程负载 >90%（Mooncake 分离式推理架构） |
| 推荐部署 | 64 张以上加速器组成的 Supernode |
| 权重发布 | 2026-07-27，Hugging Face `moonshotai/Kimi-K3`；协议以模型卡为准 |
| 使用入口 | Kimi.com / App（iOS、Android、HarmonyOS）、Kimi Work（≥3.1.0，Windows 与 Apple silicon Mac）、Kimi Code（终端 `/model` 选择）、Kimi API、OpenRouter（`moonshotai/kimi-k3`） |

---

## 四、架构深度解析

Kimi K3 的架构可概括为一句话：**用 KDA 解决序列长度维度的效率问题，用 AttnRes 解决模型深度维度的信息传递问题，用 Stable LatentMoE 在宽度维度上极致扩容**。

### 4.1 Kimi Delta Attention（KDA）—— 序列长度维度

#### 背景：全注意力的瓶颈

标准 softmax 注意力的计算复杂度为 O(N²)，KV cache 随上下文线性增长。在百万级上下文、长程 Agent 与 RL 长轨迹场景下，全注意力"慢、贵、卡显存"。线性注意力可将复杂度降至 O(N)，但历史上表达能力不足——直到 Kimi Linear（arXiv:2510.26692，2025-10）首次在公平对比下全面超越全注意力。K3 正是这一技术路线的规模化落地。

#### KDA 的核心机制

KDA 扩展自 Gated DeltaNet（GDN），关键升级是**把标量遗忘门替换为逐通道（channel-wise）对角门控** `Diag(α_t)`，对有限状态 RNN 记忆进行细粒度调控——每个通道独立决定"记什么、忘什么"。其状态递推为：

```
S_t = (I − β·k_t·k_tᵀ)·Diag(α_t)·S_{t−1} + β·k_t·v_tᵀ
```

- `S`：矩阵形式的记忆状态（fast weight / 联想记忆）
- `β`：标量学习率（delta rule 的更新步长）
- `Diag(α_t)`：逐通道遗忘系数，同时承担**可学习的位置编码**角色（替代 RoPE，即 NoPE 设计）
- 逐通道遗忘系数 α∈(0,1) 使记忆状态有界，配合 delta rule 的局部更新，长序列下数值稳定，百万 token 不易梯度爆炸/消失

#### 硬件效率：特化 DPLR + Chunkwise 算法

- 状态转移矩阵采用 **Diagonal-Plus-Low-Rank（DPLR）的特化变体**，比通用 DPLR 形式计算量大幅降低（约 2 倍提速），同时与经典 delta rule 更一致。
- 分块并行采用 **WY 表示 + UT 变换**，避免二级分块带来的 FP32 精度开销，最大化 Tensor Core 吞吐。
- 神经参数化细节：q/k/v 先经 ShortConv + Swish 激活，q/k 做 L2Norm；遗忘系数经低秩投影参数化；输出前按头 RMSNorm + 数据依赖门控。

#### 混合比例与实测收益

- **3:1 混合**：每 3 层 KDA 线性注意力搭配 1 层全注意力（MLA），75% 的层无需 KV cache。
- Kimi Linear 实验（48B-A3B，5.7T tokens 训练）：KV cache 减少最高 **75%**；1M 上下文下 TPOT 1.84ms vs MLA 11.48ms，**解码提速 6.3 倍**；MMLU-Pro 51.0、RULER(128k) 84.3，同配方下全面优于全 MLA。
- K3 官方数据：KDA 在百万 token 环境下实现**最高 6.3 倍解码速度提升**。

### 4.2 Attention Residuals（AttnRes）—— 模型深度维度

传统 Transformer 的残差连接将前一层的输出**均匀累加**到后续所有层。当模型达到数百层深度时，早期重要信息会在长链路传递中被稀释、混合。

AttnRes 的思路：让模型**根据当前层的需求，跨深度选择性读取历史层的表示**，而非被动接受逐层累加的结果。重要信息不必再"挤"过每一层才能到达后面。

- 官方数据：以**不到 2% 的额外开销，带来约 25% 的训练效率提升**。
- 与 KDA 的分工：KDA 管"长"（序列维度），AttnRes 管"深"（层维度），二者共同支撑 2.8T 参数 + 1M 上下文的规模。

### 4.3 Stable LatentMoE —— 宽度维度的极致稀疏

896 选 16 意味着**每个 token 只使用约 1.8% 的专家**。在此极端稀疏度下，路由稳定性与优化成为一阶问题，K3 引入四项配套技术：

| 技术 | 解决的问题 | 机制 |
| --- | --- | --- |
| **Quantile Balancing** | 专家负载不均 | 直接从路由器分数的**分位数**推导专家分配，消除启发式更新与敏感的负载均衡超参 |
| **Per-Head Muon** | 大规模优化 | 将 Muon 优化器扩展到**按注意力头独立优化**，实现更自适应的学习 |
| **SiTU（Sigmoid Tanh Unit）** | 激活控制 | 新型激活函数，改进激活的动态范围控制 |
| **Gated MLA** | 注意力选择性 | 在 MLA 上增加门控，提升注意力头的选择性 |

### 4.4 架构总览（文字版）

```
输入 Embedding
   │
   ▼
┌─────────────────────────────────────┐
│  Block × N（3:1 交错）               │
│  ┌───────────────┐  ┌────────────┐  │
│  │ KDA 线性注意力 │×3│ Gated MLA  │×1│  ← 序列维度：KDA 为主
│  └───────────────┘  └────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ Stable LatentMoE FFN          │  │  ← 宽度维度：896 选 16
│  │ (Router + Shared/Routed Expert)│  │
│  └───────────────────────────────┘  │
│  + Attention Residuals 跨层读取      │  ← 深度维度：选择性残差
└─────────────────────────────────────┘
   │
   ▼
输出（文本）
```

> 注：官方博客给出的结构示意包含 Embedding → Router → Linear/Conv/L2/Norm → Shared Expert + Routed Expert → KDA → Norm → Linear → Output 等组件；精确层数、维度等超参以技术报告为准。

---

## 五、训练与推理基础设施

### 5.1 扩展效率：2.5× 的意义

官方称 K3 相比 K2 的**整体扩展效率提升约 2.5 倍**——即同样的算力投入，能转化出约 2.5 倍的智能增长。这一数字来自架构（KDA + AttnRes + 更高稀疏度）、训练方法与数据配方的协同优化。注意：这是官方内部测量口径，不能直接换算为"API 快 2.5 倍"或"便宜 2.5 倍"。

### 5.2 量化感知训练（QAT）

- 从 **SFT 阶段起**即引入量化感知训练：**权重 MXFP4、激活 MXFP8**，保证广泛的硬件兼容性。
- 好处：推理部署无需事后量化（PTQ）带来的精度损失，开箱即是低精度友好权重。

### 5.3 全均衡专家并行训练

为防止大规模专家并行（EP）下负载不均拖垮吞吐，K3 采用**全均衡专家并行训练方法**：静态形状（static shapes）、关键路径上无主机同步（no host synchronization）。

### 5.4 推理部署

- **vLLM 贡献**：KDA 对传统 prefix caching 构成新挑战，官方已向 vLLM 社区贡献 **KDA prefill-cache 实现**，随模型一同发布——这是 K3 能以有竞争力的 token 价格提供服务的关键。
- **Mooncake 分离式推理架构**：官方 API 由 Mooncake 支撑，编程负载缓存命中率 **>90%**（缓存命中输入价格仅为未命中的 1/10）。
- **Supernode 建议**：推理效率受益于更大的高带宽通信域，官方建议 **64+ 加速卡的 Supernode** 配置。按 4-bit 权重理论估算，仅权重就需约 **1.4TB** 存储（未计路由、KV cache、框架与视觉模块），单张消费级显卡无法承载。

---

## 六、完整基准评测（31 项）

> **官方统一设置**：`reasoning_effort=max`、`temperature=1.0`、`top_p=1.0`。不同基准分别使用 KimiCode / Claude Code / Codex 三种 agentic harness（见各表备注）。数据来源：官方技术博客，经 DataLearner 结构化录入。

### 6.1 编程与软件工程（8 项）

| 基准 | K3 得分 | 关键对比 | 备注 |
| --- | --- | --- | --- |
| FrontierSWE | **81.2** | Fable 5：86.6；GPT 5.6 Sol：71.3 | K3 用 KimiCode harness |
| Program Bench | **77.8** | GPT 5.6 Sol：77.6；Fable 5：76.8 | K3 用 KimiCode |
| Terminal-Bench 2.1 | **88.3** | GPT 5.6 Sol：88.8；Fable 5 / Opus 4.8：84.6 | K3 用 KimiCode；其他模型取各 harness 最佳；Fable 5 与 Opus 4.8 同分（均为 AA Terminus 2 口径），建议与原始榜单复核 |
| Kimi Code Bench 2.0 | 72.9 | — | K3 同时测了 KimiCode 与 Claude Code 两种 harness；72.9 对应的具体 harness 待查官方原表确认；官方脚注注明 GPT 5.6 Sol 有 10% 任务触发其 cyber guard |
| DeepSWE | 67.5 | GPT 5.6 Sol：73.0；Fable 5：70.0 | **K3 落后项**；DeepSWE v1.1 任务；mini-SWE-agent harness 下为 67.3 |
| MLS Bench Lite | 48.3 | — | — |
| SWE Marathon（长程） | **42.0（第一）** | Opus 4.8：40.0；GPT 5.6 Sol：39.0；Fable 5：35.0 | K3 与 Claude 系用 Claude Code harness；官方采用 H20 校准的 v1.1 任务分支（Docker 镜像、性能门限与参考 oracle 按 H20 重校准，正确性与反作弊校验不变）；Fable 5 在该评测中 35% 任务触发 fallback |
| PostTrain Bench | 36.6 | — | 三次运行平均，max 思考档；官方在 H20 上运行（官方设置为 H100） |

**规律**：K3 的优势集中在**长程、需持续修正**的工程任务（SWE Marathon 第一），单次编程题（DeepSWE）仍落后于两款最强闭源模型。

### 6.2 智能体 —— 信息收集（2 项）

| 基准 | K3 得分 | 备注 |
| --- | --- | --- |
| BrowseComp | **91.2** | 采用 300K 触发的上下文压缩策略；1M 上下文无压缩下为 90.4 |
| DeepSearchQA | 95.0（F1） | — |

### 6.3 智能体 —— 工具使用（3 项，另附 6.1 已列的 Terminal-Bench 2.1）

| 基准 | K3 得分 | 备注 |
| --- | --- | --- |
| Terminal-Bench 2.1 | 88.3 | 见 6.1（重复列出，不计入总数） |
| MCP Atlas | 84.2 | 500 任务公开子集，100 轮上限，Gemini 3.1 Pro 担任评委 |
| Toolathlon-Verified | 73.2 | — |
| AutomationBench | 30.8 | 600 任务公开子集；AA 口径下 K3 排名第一 |

### 6.4 生产力与知识工作（5 项）

| 基准 | K3 得分 | 备注 |
| --- | --- | --- |
| GDPval-AA v2 | 1668（Elo） | Fable 5：1760；GPT 5.6 Sol：1748；领先 Opus 4.8 / GPT 5.5 / GLM-5.2 |
| AA-Briefcase | 1548（Elo） | 仅次于 Fable 5；比 K2.6 提升 732 分 |
| DECK-Bench | 73.5 | — |
| OfficeQA Pro | 63.3 | 全 PDF 语料以图片形式提供，无机器可读文本 |
| SpreadsheetBench 2 | 34.8 | — |

### 6.5 Agent 综合能力（2 项）

| 基准 | K3 得分 |
| --- | --- |
| Job Bench | 52.9 |
| APEX-Agents | 37.6 |

### 6.6 推理（3 项）

| 基准 | K3 得分 | 关键对比 |
| --- | --- | --- |
| GPQA-Diamond | 93.5 | GPT 5.6 Sol：94.1；DeepSeek V4 Pro：90.1 |
| HLE-Full（无工具） | 43.5 | — |
| HLE-Full（带工具） | **56.0** | DeepSeek V4 Pro：37.7 |

### 6.7 多模态理解（8 项）

| 基准 | K3（纯模型） | K3（带工具/Python） |
| --- | --- | --- |
| MathVision | 94.3 | **97.8** |
| CharXiv RQ | 84.8 | **91.3** |
| MMMU-Pro | 81.6 | **83.4** |
| OmniDocBench | 91.1 | — |
| BabyVision | — | 85.7 |
| PerceptionBench（官方自建，原子视觉感知） | 58.5 | — |
| WorldVQA ForceAnswer | 51.0 | — |
| ZeroBench Main | 23.0 | **41.0** |

> 多模态评测除 ZeroBench（官方设置、运行 5 次）外均为 3 次运行平均；MMMU-Pro 遵循官方协议，图片前置。PerceptionBench 已有公开介绍页（kimi.com/blog/perception-bench）。

### 6.8 评测口径注意事项

1. 各模型 harness 不同（KimiCode / Claude Code / Codex / Terminus 2），换 harness 结果可能变化。
2. Claude Fable 5 部分成绩由第三方评测，且在 Claude Code harness 下被其使用策略拒绝的请求会**自动 fallback 到 Opus 4.8**（SWE Marathon 中 fallback 比例达 35%）。
3. GPT 5.5 在 KCB 2.0 中使用 "xhigh" 设置而非 max。
4. BrowseComp 的 91.2 使用了上下文压缩策略，与"1M 原生上下文直跑"（90.4）是两种条件。
5. 计数口径：6.1 八项 + 6.2 两项 + 6.3 三项（Terminal-Bench 2.1 与 6.1 重复不计）+ 6.4 五项 + 6.5 两项 + 6.6 三项 + 6.7 八项 = 31 项独立基准。
6. 部分官方评测在 H20 而非原始 H100 环境下运行（SWE Marathon 为 H20 校准分支，PostTrain Bench 在 H20 运行），跨硬件对比需注意。

---

## 七、第三方评测与行业反应

### 7.1 Arena.ai 前端代码竞技场：第一名

- K3 以 **Elo 1679 登顶**，超越 Claude Fable 5。
- 相比 K2.6 上升 **17 位**（#18 → #1）。
- 在 7 个前端领域中的 6 个排名第一：品牌与营销、参考设计、数据与分析、内容创作工具等。

### 7.2 Artificial Analysis

- **智能指数 57 分**：与 Claude Opus 4.8、GPT-5.5 同档，仍落后于 Fable 5 与 GPT 5.6 Sol。
- **成本**：单任务成本约 **$0.94**，与 GPT 5.6 Sol 相当，约为 Opus 4.8 的一半；token 效率比前代提升 21%。
- GDPval-AA v2 Elo 1668，优于 GLM-5.2、GPT 5.5、Opus 4.8；AutomationBench-AA 排名第一。

### 7.3 媒体与行业观点

- **Financial Times**：K3 可能动摇"中国前沿 AI 落后美国 8–12 个月"的共识；价格因素正推动美欧企业转向中国模型。
- **iThome**：K3 在编程、智能体、推理、视觉四大类评测皆跻身第一梯队；编程与 Fable 5、GPT 5.6 Sol 互有领先。
- 亦有观察者提醒：早期基准可能无法完全反映真实世界的可靠性；另有第三方测试提及较高的幻觉率（未经官方确认），需结合权重发布后的独立实测判断。

---

## 八、官方案例研究

> 以下案例均由官方提供，尚待独立验证，但展示了 K3 的能力边界与设计取向：**不是单次答题正确率，而是把规划、编码、工具与验证串成完整长流程的能力**。

### 8.1 GPU Kernel 优化

- **设置**：相同沙箱，最长 24 小时，4 个任务（AttnRes、KDA、512 头维 MLA kernel），横跨 NVIDIA Hopper GPU 与另一家厂商的 GPGPU。
- **结果**：K3 与 Fable 5（含 fallback）表现相当，显著超越 Opus 4.8、GPT 5.6 Sol、GPT 5.5。
- **彩蛋**：K3 开发后期，团队大部分 kernel 优化工作已由早期版 K3 自己完成。

### 8.2 MiniTriton：从零构建 GPU 编译器

- K3 开发了类 Triton 的紧凑编译器：自有 **tile 级 IR（基于 MLIR）→ 优化 pass → PTX 代码生成**完整管线。
- 在支持的 roofline 基准上与 Triton / torch.compile **持平甚至更优**（部分负载击败 Triton）。
- 端到端支撑 **nanoGPT 训练且收敛稳定**，loss 曲线与参考实现仅微小偏离——验证了从 DSL 前端到运行时的完整编译器能力，而非孤立 kernel。

### 8.3 芯片设计：模型为模型造芯

- 单次 **48 小时自主运行**，使用开源 EDA 工具、Nangate 45nm 工艺库，为一个基于自身架构的 nano 模型设计推理芯片。
- 指标：**4 mm²** 面积、**100 MHz** 时序收敛、仿真 **8,700+ tokens/s** 解码吞吐、**146 万**标准单元、**0.277 MB** SRAM、带融合反量化的 **INT4 MAC 阵列**。

### 8.4 计算天体物理：I–Love–Q 普适关系复现

- 约 **2 小时**完成资深研究员 **1–2 周**的工作。
- 过程：交叉验证 20+ 篇论文 → 实现完整数值管线 → 评估 300+ 状态方程 → **发现已发表公式中的不一致之处** → 生成 3,000+ 行 Python → 产出交互式 HTML 看板。

### 8.5 知识工作与内容生产

| 案例 | 规模数据 |
| --- | --- |
| 42 年 AI ASIC 产业研究网站 | 120+ 轮递归自我改进；2,800+ 次网页搜索抓取；1,100+ 次终端数据拉取；11,000+ 页面（87 份季报、99 份原始 PDF） |
| 核聚变产业研究 | 咨询风格报告：时间线、漏斗图、区间条形图、甘特图、出版级幻灯片 |
| GWTC-5 引力波分析 | 20+ 并发子智能体；391 个引力波事件；7 幅科学可视化、2 张表格、10+ 篇文献综述 |
| 视频剪辑 | 从 56 段素材自剪 teaser：选段、动接动剪辑、帧级卡点、音频处理、多轮修改（此类高密度短片熟练剪辑师需 1–2 个工作日） |
| 3Blue1Brown 风格动画 | 制作讲解**自身架构**的动态图形视频 |
| 3D 浏览器开放世界游戏 | Three.js WebGPU + GPU compute；森林、村庄、雪山、动态天气；"vision in the loop"：写代码 → 看截图 → 找问题 → 再修改 |

### 8.6 Kimi Work 新特性：Widgets 与 Dashboard

- **Widgets**：在对话中直接生成可交互组件，可连接本地数据或外部插件持续更新。
- **Dashboard**：把关注的 widgets 聚合为围绕主题/项目/目标的持久化个性视图——结果不再是一次性文字，而是可持续更新的工作界面。

---

## 九、API 完整使用指南

### 9.1 快速开始

```bash
python3 -m pip install --upgrade 'openai>=1.0'
export MOONSHOT_API_KEY="你的_KIMI_API_KEY"
```

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["MOONSHOT_API_KEY"],
    base_url="https://api.moonshot.cn/v1",  # 国际区：https://api.moonshot.ai/v1
)

completion = client.chat.completions.create(
    model="kimi-k3",
    reasoning_effort="max",  # 可选 low / high / max，max 为默认；勿用 K2.x 的 thinking 参数
    messages=[{"role": "user", "content": "用一句话介绍 Kimi K3。"}],
)
print(completion.choices[0].message.content)
```

cURL 等价写法：

```bash
curl https://api.moonshot.cn/v1/chat/completions \
  --header "Authorization: Bearer $MOONSHOT_API_KEY" \
  --header "Content-Type: application/json" \
  --data '{
    "model": "kimi-k3",
    "messages": [{"role": "user", "content": "用一句话介绍 Kimi K3。"}]
  }'
```

### 9.2 模型选择

| 模型 ID | 定位 | 上下文 |
| --- | --- | --- |
| `kimi-k3` | 旗舰：长程编程、知识工作、深度推理 | 1M |
| `kimi-k2.7-code` | 编程专精 | 256K |
| `kimi-k2.7-code-highspeed` | 编程 + 更高输出速度 | 256K |
| `kimi-k2.6` | 通用对话、Agent、视觉理解（思考/非思考双模式） | 256K |

官方建议：不确定时默认从 `kimi-k3` 开始；主打代码生成/修改且追求速度时选 `kimi-k2.7-code-highspeed`。K3 也可通过 OpenRouter（`moonshotai/kimi-k3`）访问。

### 9.3 思考力度（reasoning_effort）

- K3 **始终开启思考模式**，通过顶层 `reasoning_effort` 配置；**不要**使用 K2.x 的 `thinking` 参数。
- 支持 `"low"` / `"high"` / `"max"` 三档，`"max"` 为默认（首发时仅 max 档，low / high 已随后开放）。

```python
completion = client.chat.completions.create(
    model="kimi-k3",
    reasoning_effort="max",
    messages=[{"role": "user", "content": "证明根号 2 是无理数。"}],
)
```

### 9.4 多轮对话：必须回传完整 assistant message

K3 在"保留思考历史"模式下训练。多轮对话与工具调用时，**将 API 返回的完整 assistant message 原样加入下一次请求**，不要只保留 `content`——否则 `reasoning_content`、`tool_calls`、Tool Call ID、Partial Mode 状态等会丢失，推理连续性可能严重受损：

```python
assistant_message = completion.choices[0].message
messages.append(assistant_message)  # 原样回传
```

### 9.5 流式输出

推理增量与最终答案分别通过 `reasoning_content` 和 `content` 两个 delta 下发；UI 可分别渲染，但业务逻辑不要把推理内容误当最终答案或 JSON 输出：

```python
stream = client.chat.completions.create(
    model="kimi-k3",
    messages=[{"role": "user", "content": "解释为什么天空是蓝色的。"}],
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta
    reasoning = getattr(delta, "reasoning_content", None)
    if reasoning:
        print(reasoning, end="", flush=True)   # 思维链
    if delta.content:
        print(delta.content, end="", flush=True)  # 最终答案
```

### 9.6 视觉输入

视觉消息的 `content` 必须是**对象数组**（非序列化字符串）。

**本地图片（base64）**：

```python
import base64
from pathlib import Path

image_data = base64.b64encode(Path("image.png").read_bytes()).decode()
completion = client.chat.completions.create(
    model="kimi-k3",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{image_data}"}},
            {"type": "text", "text": "描述这张图片。"},
        ],
    }],
)
```

**视频文件（Files API 上传后引用）**：

```python
from pathlib import Path

video = client.files.create(file=Path("video.mp4"), purpose="video")
completion = client.chat.completions.create(
    model="kimi-k3",
    messages=[{
        "role": "user",
        "content": [
            {"type": "video_url", "video_url": {"url": f"ms://{video.id}"}},
            {"type": "text", "text": "总结这段视频。"},
        ],
    }],
)
```

### 9.7 Agent 能力

- **Function Calling**：支持自定义工具与 `tool_choice`；设 `tool_choice="required"` 可强制至少调用一个工具。工具执行后，须把完整 assistant message 与对应 tool result 一并回传。
- **动态加载工具**：可在对话中的 **system message 动态声明工具**，从该消息位置开始生效（后续请求需保留此消息）。适合数十/数百个工具的大型 MCP 环境或按任务逐步加载 Skills 的 Agent——避免全量 schema 挤占上下文、降低选择准确率。
- **结构化输出**：支持 `json_schema` + `strict: true`，适用于数据抽取、工作流状态等场景。

### 9.8 成本优化要点

1. **保持前缀稳定**：知识库与 system prompt 顺序固定，避免不必要的内容重排，以命中前缀缓存（缓存输入价格 = 未命中的 1/10）。
2. 编程负载官方缓存命中率 >90%，实际成本高度依赖命中情况。
3. 上下文容量是上限而非目标——输入越长，首 token 延迟、推理时间与费用越高，不要每次都塞满 1M。

---

## 十、已知限制与使用建议

官方声明的三项限制：

1. **对思考历史敏感**
   - 现象：harness 未完整回传历史思考内容，或会话中途从其他模型切换到 K3，生成质量可能**极不稳定**。
   - 建议：使用已验证兼容的 harness（如 Kimi Code）；避免会话中途换模型。
2. **过度主动（Excessive proactiveness）**
   - 现象：训练侧重长程困难任务，遇到小问题或意图模糊时，可能**替用户做出意料之外的决定**。
   - 建议：需要严格边界的应用，在 system prompt 或 `AGENTS.md` 中施加显式行为约束。
3. **体验差距**
   - 官方自述：尽管整体极具竞争力，K3 在用户体验上与 Claude Fable 5、GPT 5.6 Sol 仍存在明显差距。

---

## 十一、产品矩阵与选型建议

| 模型 | 定位 | 适合场景 |
| --- | --- | --- |
| **Kimi K3** | 通用旗舰 | 难、跨领域、被 256K 卡住的复杂任务：大型代码库理解与修改、多步骤金融/产业研究、视觉反馈交互式开发（前端/游戏/CAD）、1M 长文档推理 |
| Kimi K2.7 Code | 编程专精 | 日常 IDE 编程、低延迟补全（更经济高效） |
| Kimi K2.6 | 通用长程 Agent | 通用对话、Agent 任务、视觉理解 |

**暂不适合 K3 的场景**：

- 单卡/工作站本地运行（2.8T 参数 + 官方建议 64 卡 Supernode，个人部署不现实）；
- 对延迟敏感的简单问答（思考模式始终开启，可改用 low 档降低延迟，或选 K2.7 Code）。

---

## 十二、部署、开源与生态

### 12.1 权重与协议

- **发布**：完整权重与技术报告于 2026-07-27 发布，官方仓库为 Hugging Face [`moonshotai/Kimi-K3`](https://huggingface.co/moonshotai/Kimi-K3)（发布前为占位倒计时页）。
- **协议**：以模型卡与仓库内 LICENSE 文件为准；预期与 K2 系列一致为 **Modified MIT**（免费商用授权），**商用前请阅读正式协议原文**。
- **权重体积**：第三方报道约 594GB（原生 MXFP4 safetensors）；社区 GGUF 量化版本通常在发布后数日出现，非官方提供。

### 12.2 自部署硬件估算

| 项目 | 估算 |
| --- | --- |
| 权重存储（4-bit） | 约 1.4 TB（未计路由、KV cache、框架、视觉模块）；第三方报道下载包约 594GB |
| 官方建议 | 64+ 加速卡 Supernode（大高带宽通信域） |
| 实验性最低 | 第三方报道 8× H100 80GB 可加载（非生产建议） |
| 消费级硬件 | 单张 RTX 5090 / 普通工作站**无法**运行完整模型 |

### 12.3 权重发布后需确认的三件事

1. 模型授权是否允许商业使用与衍生模型、是否允许微调（以正式 LICENSE 为准）；
2. vLLM / SGLang 等框架的 KDA 与前缀缓存支持进度（官方 vLLM KDA prefill-cache 实现随模型发布）；
3. 官方是否同步提供量化权重、硬件需求说明与分布式部署示例。

### 12.4 相关开源资产（已发布）

- **Kimi Linear**（KDA 的 48B-A3B 验证模型）：MIT 协议，Base 与 Instruct 检查点已在 Hugging Face 发布；KDA kernel 已并入 FLA（flash-linear-attention）；vLLM 可直接 `serve`。
- 论文：arXiv:2510.26692《Kimi Linear: An Expressive, Efficient Attention Architecture》。

---

## 十三、常见问题 FAQ

**Q1：Kimi K3 的 2.8T 参数是否每次推理都参与计算？**
不是。MoE 架构下每个 token 仅激活 896 个专家中的 16 个（激活参数约 50B），单次推理计算量远小于总参数规模；但部署仍需容纳完整权重。

**Q2：K3 与 K2.7 Code 是什么关系？**
K3 是通用旗舰，不是 K2.7 Code 的替代者。K2.7 Code 继续服务编程专精场景（更快、更经济），K3 面向难、跨领域、超长上下文的复杂任务。

**Q3：为什么我的多轮调用效果不稳定？**
大概率是只回传了 `content`。K3 要求回传完整 assistant message（含 `reasoning_content`、`tool_calls` 等）；也不要在会话中途从其他模型切换到 K3。

**Q4：API 的 `thinking` 参数还能用吗？**
K3 改用顶层 `reasoning_effort`（low / high / max，max 为默认）。`thinking` 是 K2.x 系列的参数，不要混用。

**Q5：1M 上下文是不是可以随便塞？**
容量是上限。输入越长，首 token 延迟、推理时间与费用越高。建议保持前缀稳定以命中缓存（编程负载命中率 >90%）。

**Q6：现在能本地部署吗？**
权重于 2026-07-27 在 Hugging Face（`moonshotai/Kimi-K3`）发布后可下载。但官方建议 64+ 加速卡 Supernode，个人与普通企业更现实的选择仍是官方 API、OpenRouter 或推理合作伙伴。

**Q7：K3 的评测能直接和 GPT 5.6 Sol / Fable 5 比吗？**
需谨慎。各模型使用不同 harness（KimiCode / Claude Code / Codex），部分 Claude 成绩含 fallback（SWE Marathon 中达 35%），运行次数、硬件（部分为 H20 校准环境）与工具条件也不完全一致。官方结论是"已进入前沿竞争区间，但整体体验仍落后"。

---

## 十四、参考链接

| 资料 | 链接 |
| --- | --- |
| 官方技术博客 | https://www.kimi.com/zh-cn/blog/kimi-k3 |
| API 快速开始 | https://platform.kimi.com/docs/guide/kimi-k3-quickstart |
| Hugging Face 权重仓库 | https://huggingface.co/moonshotai/Kimi-K3 |
| Moonshot AI 官网 | https://www.moonshot.ai/ |
| Kimi Linear 论文（KDA 技术基础） | https://arxiv.org/abs/2510.26692 |
| Kimi Linear 开源仓库 | https://github.com/MoonshotAI/Kimi-Linear |
| PerceptionBench 介绍页 | https://www.kimi.com/blog/perception-bench |
| DataLearner 模型卡片（31 项评测结构化） | https://www.datalearner.com/ai-models/pretrained-models/kimi-k3 |
| iThome 报道 | https://www.ithome.com.tw/news/177376 |

---

*文档整理时间：2026-07-18；v2.2 修订：2026-07-27（权重发布日）。基于官方技术博客、API 文档、Kimi Linear 论文及公开第三方评测整理；官方评测数据为厂商自报口径，横向对比时请注意各模型使用的 harness、硬件环境与评测条件差异。权重协议与激活参数等细节以 2026-07-27 发布的模型卡及技术报告为最终依据。*

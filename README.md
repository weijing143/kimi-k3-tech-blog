# Kimi K3 技术博客整理

本仓库是对 Moonshot AI（月之暗面）于 2026-07-16 发布的 **Kimi K3** 模型的技术资料整理，仅供个人学习参考。权重与技术报告已于 2026-07-27 发布（Hugging Face `moonshotai/Kimi-K3`，Kimi K3 License）。

## 阅读路径

按你的目标选路线，建议遵循"先看证据等级，再读对应文章，最后运行示例"的顺序：

| 你的目标 | 推荐阅读顺序 |
| --- | --- |
| 初次了解 K3 | [README](./README.md) → [SOURCES.md](./SOURCES.md)（证据等级）→ [主文档](./kimi-k3-tech-blog.md) 的 TL;DR、规格表、架构、限制与选型 |
| 理解模型原理 | 主文档架构与训练章节 → [KDA 专题](./posts/kda-from-formula-to-vllm.md) → [LatentMoE 专题](./posts/latentmoe-engineering.md) → 对照 [SOURCES.md](./SOURCES.md) 证据等级 |
| 接入 API / 构建 Agent | 主文档 API 章节 → [Agent 工程实践](./posts/k3-agent-engineering.md) → [examples/k3_agent_framework](./examples/k3_agent_framework/)（README、demo、源码、测试） |
| 自部署 / 性能验证 | 主文档部署章节 → [自部署实验手册](./posts/k3-selfhost-runbook.md) → [examples/k3_selfhost_bench](./examples/k3_selfhost_bench/)（注意：留空结果表是方法模板，不是实测结论） |
| 评估商用与再分发 | [License 实务](./posts/k3-license-practice.md) → 官方 [Kimi K3 License 原文](https://huggingface.co/moonshotai/Kimi-K3/raw/main/LICENSE) → [SOURCES.md](./SOURCES.md) License 条目 |
| 参与维护 | README → [SOURCES.md](./SOURCES.md) → [CONTRIBUTING.md](./CONTRIBUTING.md) → Issue 模板 |

## 内容

主文档：[kimi-k3-tech-blog.md](./kimi-k3-tech-blog.md)

- 发布背景与行业意义
- 核心规格总表
- 架构深度解析（KDA / Attention Residuals / Stable LatentMoE）
- 训练与推理基础设施
- 基准评测（31 项，已按官方模型卡评测表校正；官方完整表另含十余项未收录指标）
- 第三方评测与行业反应
- 官方案例研究
- API 完整使用指南
- 已知限制与使用建议
- 产品矩阵与选型建议
- 部署、开源与生态
- 常见问题 FAQ

## 专题文章（posts/）

- [《Kimi K3 Agent 工程实践：完整回传 reasoning / tool history 的可靠调用框架》](./posts/k3-agent-engineering.md) —— 配套可运行代码见 [examples/k3_agent_framework/](./examples/k3_agent_framework/)
- [《开源三巨头横评：Kimi K3 vs DeepSeek V4 Pro vs GLM-5.2》](./posts/k3-vs-v4pro-vs-glm52.md) —— 规格/基准/价格/吞吐横向对比 + 决策框架，标注"第三方评测 vs 官方自报"
- [《Attention Residuals 工程解析：残差连接还不够——让每层自己决定"读谁"》](./posts/attnres-engineering.md) —— 伪查询注意力 over depth、Full/Block 版内存权衡、官方伪代码逐行解读
- [《KDA 不是"线性注意力"这么简单：从递推公式到 vLLM Prefix Cache》](./posts/kda-from-formula-to-vllm.md) —— 从 delta rule 推导到 FLA / vLLM 源码追踪
- [《Stable LatentMoE 工程解析：Quantile Balancing、EP 通信与 896 专家路由》](./posts/latentmoe-engineering.md) —— LatentMoE 原理、QB 无辅助损失均衡、vLLM EP 后端与路由健康诊断
- [《Kimi K3 微调实践：3T 模型的 LoRA 路线、成本账与奖励设计》](./posts/k3-finetune-practice.md) —— LoRA rank 与容量、RL 成本实测（~$65/20 步）、Countdown vs Frozen Lake 奖励设计对比
- [《Kimi K3 License 实务：商用、微调和再分发的条款对照与部署清单》](./posts/k3-license-practice.md) —— 逐条拆解 + 场景决策矩阵 + 合规清单，纠正"K3 是 MIT"的误传
- [《Kimi K3 自部署实验手册：从 8× H100 到 64 卡 Supernode》](./posts/k3-selfhost-runbook.md) —— 显存算术、启动命令、压测方法学与留空结果表，配套脚本见 [examples/k3_selfhost_bench/](./examples/k3_selfhost_bench/)

另附：[《发布帖文案（长版 + 短版）》](./posts/release-announcement.md) —— 仓库对外发布用的介绍文案（非专题）

## 结构化数据（data/）

- [`data/benchmarks.json`](./data/benchmarks.json) —— 主文档 §六 的 31 项官方基准结构化存档（官方模型卡口径，2026-07-28 抓取），由 CI（`scripts/check_benchmarks.py`）自动校验数量、唯一性与字段合法性。如需新增/修正条目，直接改 JSON 并补充对应主文档表格备注；**实测数据请走 [benchmark-data.yml Issue 模板](.github/ISSUE_TEMPLATE/benchmark-data.yml)，勿写入此官方口径文件**。

## 资料来源

内容整理自以下公开资料，版权归原作者 / 机构所有：

- Kimi 官方技术博客：<https://www.kimi.com/zh-cn/blog/kimi-k3>
- Hugging Face 官方模型卡（含完整评测表与技术报告入口）：<https://huggingface.co/moonshotai/Kimi-K3>
- Kimi API 文档：<https://platform.kimi.com/docs/guide/kimi-k3-quickstart>
- Kimi Linear 论文：<https://arxiv.org/abs/2510.26692>
- Kimi Linear 开源仓库：<https://github.com/MoonshotAI/Kimi-Linear>
- DataLearner 模型卡片（第三方结构化录入）：<https://www.datalearner.com/ai-models/pretrained-models/kimi-k3>
- iThome 报道：<https://www.ithome.com.tw/news/177376>

## 核验声明

本仓库事实可靠性口径（2026-07-28）：**架构规格、License 条款、API 关键参数及部分代表性基准分数**已按官方一手来源（HF 模型卡 / LICENSE 原文 / Quickstart / 定价页）逐项核对；叙述性段落、公式推导与第三方材料均已标注其性质（官方自报 / 第三方转述 / 推测估算）。逐条来源与证据等级见 [SOURCES.md](./SOURCES.md)（证据台账）。

需要注意的边界：

- 基准分数为**官方自报口径**，其中十余项已逐项比对官方完整表，其余为同源转录；
- 示例代码通过 17 个**离线单元测试**（CI 自动复跑，见 Actions 页），但**未构成**对真实 K3 API 与自部署 vLLM/SGLang 环境的端到端验证；
- 自部署手册的结果表全部留空待实测，请勿引用为空数据。

### 数据补充原则

本仓库采用“**来源等级 + 复现状态**”双维度记录数据：来源等级说明数据来自官方、第三方、推测还是实测；复现状态说明数据尚未复现、属于外部实测，还是已由本项目复现。两者不能互相替代。

- 权威外部实测可以收录，但必须保留来源、测试环境、方法与原始证据，并明确标为“外部实测，项目未复现”；
- 本项目结果表只填写按仓库方法实际执行得到的数据，不用外部数字代填；
- 官方自报且复现成本极高的训练效率或案例不强求本项目复跑，继续保留其原始口径与限制说明。

字段定义与收录要求见 [SOURCES.md](./SOURCES.md)，性能数据的分层记录模板见 [自部署实验手册](./posts/k3-selfhost-runbook.md)。

## 许可证

本仓库的**整理与汇编内容**采用 [CC BY-NC 4.0](./LICENSE)（知识共享 署名-非商业性使用 4.0 国际）许可：

- ✅ 可自由分享、复制、改编
- ✅ 需保留署名与出处
- ❌ **禁止商业用途**

注意：文中引用的原始资料（官方博客、模型卡、论文、报道、评测数据等）的版权归原权利方所有，本仓库仅作个人学习用途的整理与引用，不代表对原始内容主张任何权利。

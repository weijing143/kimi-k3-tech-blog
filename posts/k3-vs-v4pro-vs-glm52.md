# 开源三巨头横评：Kimi K3 vs DeepSeek V4 Pro vs GLM-5.2

> 写作日期：2026-08-02｜姊妹篇：本仓库 K3 各专题、[SOURCES.md](../SOURCES.md)
> **口径声明**：三模型对比数据主要来自 [DeepInfra 对比博客](https://deepinfra.com/blog/kimi-k3-vs-deepseek-v4-pro-vs-glm-5-2)（2026-07-28 发布，2026-08-02 抓取）与 [EmpirioLabs 价格对比](https://empiriolabs.ai/blog/kimi-k3-vs-glm-5-2-vs-deepseek-v4-pro)（2026-08-02 抓取）；K3 侧数字与主文档 §六（官方模型卡口径）交叉核对，不一致处以主文档/官方为准并标注。**AA Index、SWE-bench、GPQA、LiveCodeBench、吞吐量等均为第三方评测（Artificial Analysis / BenchLM / 供应商自测）**，非厂商官方自报；厂商自报与第三方评测已分列。

---

## 1. 一句话版本

2026 年 4–7 月，三家中国实验室接连发布开源旗舰，**开源层级不再是闭源的廉价替代**：Kimi K3（Moonshot，2.8T 参数、首个 3T 级开源模型，AA Index 57 全球第四，唯一原生视觉）；DeepSeek V4 Pro（1.6T，成本最低，LiveCodeBench 93.5% 全球第一，竞赛编程专精）；GLM-5.2（~753B，吞吐近三倍于对手 ~168 tok/s，SWE-bench Pro 开源领先）。三者都是 1M 上下文、MIT/Modified-MIT 许可，但**架构路线、优势域、成本结构完全不同**——选型不是"谁分高用谁"，而是瓶颈在哪。

## 2. 规格总表

| 维度 | Kimi K3 | DeepSeek V4 Pro | GLM-5.2 |
| --- | --- | --- | --- |
| 发布时间 | 2026-07 | 2026-04 | 2026-06 |
| 总参数 / 激活 | **2.8T** / 50B | 1.6T / 49B | ~753B / 40B |
| 上下文 | 1M | 1M | 1M |
| 许可 | Modified MIT | MIT | MIT |
| 权重状态 | 7/27 已发布 | 已发布 | 已发布 |
| 多模态 | **原生（文本+图像）** | 仅文本 | 发布时仅文本 |
| API 价格（$ / 1M token） | $3.00 / $15.00 | **$1.65 / $3.30** | $1.40 / $4.40 |
| 吞吐（AA 实测，约） | ~62 tok/s | ~62 tok/s | **~168 tok/s** |
| 自部署门槛 | 建议 64 卡 Supernode | 多节点集群（BF16） | 约 8×H100 |

> 价格来源：EmpirioLabs（2026-08-02）；吞吐来源：Artificial Analysis（经 DeepInfra 转述）。

## 3. 基准横评：看什么、别信什么

| 基准 | Kimi K3 | DeepSeek V4 Pro | GLM-5.2 | 说明 |
| --- | --- | --- | --- | --- |
| AA Intelligence Index | **57（#4 全球，超 Opus 4.8 的 56）** | 44（Max 推理） | 51 | 综合指数，K3 领先 |
| SWE-bench Verified | 76.8% | **80.6%（组内最高）** | ~79–81%（前代 77.8%） | K3 反而不如两家 |
| GPQA Diamond | **93.5%** | 90.1% | 发布时未公布 | 科学推理 |
| LiveCodeBench | — | **93.5%（全球 #1）** | — | 竞赛编程；Codeforces 3206 |
| SWE-bench Pro | — | — | **62.1%（开源领先，超 GPT-5.5 的 58.6%）** | 长程编码 |
| BenchLM BenchAlign | 80.96 | — | — | 第三方聚合；agentic 子项 89.5 vs V4 Pro 59.1 |
| Arena.ai Frontend Code | **#1**（超 Fable 5 / GPT-5.6 Sol） | — | — | 人类偏好前端编码 |

**三条"别被标题骗"的注意点**（DeepInfra 原文观点，深以为然）：

1. **综合指数领先 ≠ 单项领先**：K3 的 AA Index 57 全场最高，但 SWE-bench Verified（76.8%）是三家里**最低**的——最可能的解释是评测条件/版本差异。按 SWE-bench 路由的团队应直接看单项。
2. **V4 Pro 的 44 分不矛盾**：它是"为竞赛编程专门优化"的模型，LiveCodeBench 93.5% 全球第一，但综合指数低。另外一个**生产警示**：AA-Omniscience 基准上 V4 Pro 幻觉率 94%（几乎不管知不知道都会给答案）——校准和"知道何时不回答"是产品契约的场景要小心。
3. **GLM-5.2 发布时没有官方基准**：所有发布初期的分数全是第三方测的。另一个工程警示：RL 训练中 GLM-5.2 出现过 **reward hacking**（尝试读取受保护文件、访问隐藏测试用例），Z.ai 用两阶段反作弊（规则过滤 + LLM judge）和 critic-based PPO 修复——在有权访问文件系统/真实工具的环境里值得显式评估。

## 4. 架构三岔路：三种"效率"哲学

| 模型 | 核心机制 | 效率哲学 |
| --- | --- | --- |
| **K3** | KDA（Delta Rule 线性注意力）+ AttnRes（深度选择性残差）+ Stable LatentMoE（896 选 16） | 三个维度（长/深/宽）同时压缩，买**容量**（2.8T） |
| **V4 Pro** | CSA + HCA 压缩稀疏注意力 | KV-cache 降到前代 ~10%，买**成本**（1M 上下文下最便宜） |
| **GLM-5.2** | IndexShare 路由 + MTP 多 token 预测 + KVShare 投机解码 | 投机解码买**吞吐**（draft-token 接受长度 +20%，~168 tok/s） |

## 5. 成本与部署账

- **每 token 成本**：K3 输出价 $15/M 是 V4 Pro（$3.30）的 **4.5 倍**；且社区普遍反馈 K3 完成同样任务消耗更多输出 token——**实际成本差距可能大于价目表差距**。
- **吞吐**：GLM-5.2 约 168 tok/s 是另两家的近 3 倍，延迟敏感管线优先；
- **自部署**：三家都重。K3 官方建议 ≥64 加速器；V4 Pro 1.6T 需多节点；GLM-5.2 753B 相对最轻（~8×H100）——对大多数团队，托管 API 仍是现实选择，许可自由 ≠ 部署自由。

## 6. 怎么选（决策框架）

| 你的瓶颈 | 选谁 | 理由 |
| --- | --- | --- |
| 综合能力 + 原生视觉 + 前端代码/深度 agentic | **K3** | AA Index 57、唯一多模态；接受高输出成本和 token 消耗 |
| 每 token 成本 + 竞赛编程 + 要权重现成 | **V4 Pro** | 最便宜、LiveCodeBench #1、SWE-bench Verified 组内最高 |
| 吞吐/延迟 + 长程编码 | **GLM-5.2** | ~3× 吞吐、SWE-bench Pro 开源领先、价格居中 |

## 7. 关键数字与证据等级

| 项 | 值 | 来源 / 等级 |
| --- | --- | --- |
| AA Index 57（K3, #4） | 第三方（Artificial Analysis，经 DeepInfra 转述） | 第三方评测 |
| SWE-bench Verified 76.8/80.6/~80 | 同上 | 第三方评测（版本差异待核） |
| LiveCodeBench 93.5%（V4 Pro #1） | 同上 + DeepSeek 官方 | 第三方 + 官方自报一致 |
| 幻觉率 94%（AA-Omniscience） | Artificial Analysis | 第三方评测 |
| GLM-5.2 reward hacking | DeepInfra 转述 Z.ai 技术说明 | 第三方转述（Z.ai 承认并修复） |
| 价格表 | EmpirioLabs | 供应商实时价目（随时间变动） |
| 吞吐 ~62/~62/~168 tok/s | Artificial Analysis | 第三方实测 |
| K3 2.8T / 896 专家等架构数字 | 官方模型卡（与主文档一致） | 官方 |

## 8. 参考来源

- [DeepInfra：Kimi K3 vs DeepSeek V4 Pro vs GLM-5.2 对比（2026-07-28）](https://deepinfra.com/blog/kimi-k3-vs-deepseek-v4-pro-vs-glm-5-2)
- [EmpirioLabs：三模型价格与能力对比（2026-07-16）](https://empiriolabs.ai/blog/kimi-k3-vs-glm-5-2-vs-deepseek-v4-pro)
- [DeepSeek V4 Pro 官方仓库（HF）](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro)
- [GLM-5.2 官方博客（z.ai）](https://z.ai/blog/glm-5.2) 与 [HF 仓库](https://huggingface.co/zai-org/GLM-5.2)
- 主文档 §六（K3 31 项基准，官方模型卡口径）

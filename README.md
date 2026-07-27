# Kimi K3 技术博客整理

本仓库是对 Moonshot AI（月之暗面）于 2026-07-16 发布的 **Kimi K3** 模型的技术资料整理，仅供个人学习参考。权重与技术报告已于 2026-07-27 发布（Hugging Face `moonshotai/Kimi-K3`，Kimi K3 License）。

## 内容

主文档：[kimi-k3-tech-blog.md](./kimi-k3-tech-blog.md)

- 发布背景与行业意义
- 核心规格总表
- 架构深度解析（KDA / Attention Residuals / Stable LatentMoE）
- 训练与推理基础设施
- 完整基准评测（31 项，已按官方模型卡完整评测表校正）
- 第三方评测与行业反应
- 官方案例研究
- API 完整使用指南
- 已知限制与使用建议
- 产品矩阵与选型建议
- 部署、开源与生态
- 常见问题 FAQ

## 专题文章（posts/）

- [《Kimi K3 Agent 工程实践：完整回传 reasoning / tool history 的可靠调用框架》](./posts/k3-agent-engineering.md) —— 配套可运行代码见 [examples/k3_agent_framework/](./examples/k3_agent_framework/)
- [《KDA 不是"线性注意力"这么简单：从递推公式到 vLLM Prefix Cache》](./posts/kda-from-formula-to-vllm.md) —— 从 delta rule 推导到 FLA / vLLM 源码追踪

## 资料来源

内容整理自以下公开资料，版权归原作者 / 机构所有：

- Kimi 官方技术博客：<https://www.kimi.com/zh-cn/blog/kimi-k3>
- Hugging Face 官方模型卡（含完整评测表与技术报告入口）：<https://huggingface.co/moonshotai/Kimi-K3>
- Kimi API 文档：<https://platform.kimi.com/docs/guide/kimi-k3-quickstart>
- Kimi Linear 论文：<https://arxiv.org/abs/2510.26692>
- Kimi Linear 开源仓库：<https://github.com/MoonshotAI/Kimi-Linear>
- DataLearner 模型卡片（第三方结构化录入）：<https://www.datalearner.com/ai-models/pretrained-models/kimi-k3>
- iThome 报道：<https://www.ithome.com.tw/news/177376>

## 许可证

本仓库的**整理与汇编内容**采用 [CC BY-NC 4.0](./LICENSE)（知识共享 署名-非商业性使用 4.0 国际）许可：

- ✅ 可自由分享、复制、改编
- ✅ 需保留署名与出处
- ❌ **禁止商业用途**

注意：文中引用的原始资料（官方博客、模型卡、论文、报道、评测数据等）的版权归原权利方所有，本仓库仅作个人学习用途的整理与引用，不代表对原始内容主张任何权利。

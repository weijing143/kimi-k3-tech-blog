# Kimi K3 技术博客 · 发布帖文案

> 本文件为仓库对外发布时使用的介绍文案，分长版（知乎 / 公众号 / 掘金）与短版（X / 即刻）。
> 最后更新：2026-07-28（已对齐仓库最新内容：5 篇专题 + 14 个单元测试）

---

## 长版发布帖

**开源了一个 Kimi K3 技术参考库：2.8T 参数、1M 上下文的开源旗舰，我把官方资料+工程实践+可运行代码全整理进去了**

2026 年 7 月 27 日，月之暗面正式开源 Kimi K3 权重——2.8T 总参、104B 激活参数、原生 1M token 上下文，SWE Marathon 长程编程榜第一，解码速度较 K2.5 提升 6.3 倍。这可能是目前最值得研究的开源大模型之一。

但官方模型卡信息分散，工程细节（KDA 线性注意力怎么实现、896 专家路由怎么稳住、工具调用循环怎么写、自部署要多少显存、License 到底允许什么）几乎没有系统的中文资料。所以我建了这个仓库：**Kimi K3 技术博客 · 中文权威索引与工程实践库**

📦 仓库里有什么：

- **主文档**：从架构（69 层 KDA + 24 层 Gated MLA）、Stable LatentMoE、MXFP4 量化，到 31 项独立基准、API 定价与商用 License 拆解，一站式覆盖"是什么、强在哪、怎么用"
- **五篇工程专题**：
  - 《K3 Agent 工程实践》——完整回传 reasoning/tool history 的可靠调用框架（附可直接 import 的 Python 代码 + 单元测试）
  - 《KDA 不是"线性注意力"这么简单》——从递推公式到 vLLM Prefix Cache 的实现追踪
  - 《Stable LatentMoE 工程解析》——Quantile Balancing 无辅助损失均衡、EP 通信与 896 专家路由
  - 《Kimi K3 License 实务》——逐条拆解 + 场景决策矩阵，纠正"K3 是 MIT"的误传（它不是，但比你想的宽松）
  - 《K3 自部署实验手册》——vLLM/SGLang 版本锁定、TP/EP 并行策略、显存与压测模板（runbook，结果留空待实测）
- **可运行代码**：`examples/` 下的 Agent 框架与压测脚本，配 14 个单元测试，clone 即用

⚠️ 诚实声明：官方评测数据均标注为官方自报口径；自部署手册是实验框架而非评测报告；所有引用都带来源与日期。欢迎社区提交实测数据补充。

License：CC BY-NC 4.0，欢迎引用与贡献（CONTRIBUTING 里有数据提交规范）。

🔗 https://github.com/weijing143/kimi-k3-tech-blog

---

## 短版（X / 即刻）

Moonshot 开源了 2.8T 参数的 Kimi K3（1M 上下文，SWE Marathon 第一）。我把官方资料、KDA/LatentMoE 架构解析、Agent 调用框架、License 实务拆解、自部署 runbook 整理成了一个中文技术参考库，附可运行代码+单元测试：

https://github.com/weijing143/kimi-k3-tech-blog

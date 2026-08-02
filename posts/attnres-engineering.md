# Attention Residuals 工程解析：残差连接还不够——让每层自己决定"读谁"

> 写作日期：2026-08-02｜姊妹篇：[《Stable LatentMoE 工程解析》](./latentmoe-engineering.md)、[《KDA 不是"线性注意力"这么简单》](./kda-from-formula-to-vllm.md)
> **口径声明**：本文的机制描述、公式与伪代码来自[官方 Attention-Residuals 仓库 README](https://github.com/MoonshotAI/Attention-Residuals)（2026-08-02 抓取，3.4k stars）与[论文页](https://arxiv.org/abs/2603.15031)（论文号经 arXiv 验证存在）。**2026-08-02 核验修正**：早期版本引用"不到 2% 额外开销、约 25% 训练效率提升"并标为官方自报；经与官方技术博客、论文原文、官方模型卡比对，**均未公布这两个具体百分比**，出处未确认，本文已撤回该组数字，改用论文原文的"边际训练开销/极小推理开销"表述。推理引擎兼容性部分为本文推测，已明确标注。

---

## 1. 一句话版本

标准 Transformer 的残差连接把所有历史层输出**以固定单位权重均匀累加**；模型越深，早期信息被稀释得越厉害，PreNorm 下隐状态幅值还会无界增长。**AttnRes（Attention Residuals）** 把它替换成"对深度做注意力"：每层用自己学到的一个**伪查询**，对前面所有层的输出做 softmax 加权——让模型按当前层的需求，**选择性**读取深度方向上的早期表示。Full 版内存开销 O(Ld)，**Block 版**（约 8 个块）把内存降到 O(Nd) 且恢复大部分收益，可作 drop-in 替换。

## 2. 问题：数百层深度下，均匀残差为什么失效

标准残差连接：

$$h_l = h_{l-1} + F(h_{l-1})$$

等价于把每一层的输出以**固定单位权重**累加进后续所有层。官方 README 指出两个随深度恶化的问题：

1. **贡献稀释**：早期层的表示被几十上百个后续层等权混入，单层贡献被摊薄——模型无法"强调"某段特别重要的历史。
2. **幅值无界增长**：均匀累加导致隐状态范数随深度累积增长，这是 PreNorm 架构的已知顽疾。

直觉：在标准架构里，一条重要信息必须**逐层挤过去**才能到达深层，中途还要和无关信息等权混合；而模型没有任何手段按需"跳过"或"放大"某一段历史。

## 3. 核心机制：伪查询注意力 over depth

AttnRes 用一层 softmax 注意力替代固定累加：

$$h_l = \sum_{i=0}^{l-1} \alpha_{i \to l} \cdot v_i$$

其中权重 $\alpha_{i \to l}$ 由**每层一个学到的伪查询** $w_l \in \mathbb{R}^d$ 计算得出。关键设计点：

| 特征 | 说明 |
| --- | --- |
| 查询来源 | 不是当前 token（内容驱动），而是**层参数**（深度驱动）——这一层"固定想要什么" |
| 值来源 | 所有历史层的输出 $v_i$（含 token embedding） |
| 权重归一 | softmax over depth（对 $l$ 个历史层） |
| 容量含义 | 每层获得对所有早期表示的**选择性、内容感知**访问 |

注意与标准注意力的分工差异：标准注意力回答"**当前 token 该关注序列里哪些位置**"（序列维度）；AttnRes 回答"**当前层该强调深度方向上哪些历史表示**"（深度维度）。

## 4. Full AttnRes vs Block AttnRes

Full 版直观但需要 O(Ld) 内存（L 层 × 每层 d 维的块表示全部保留）。**Block AttnRes** 的折中：

- 把 L 层分成 **N 个块**；
- 块**内部**继续用标准残差累加；
- 注意力只发生在**块级表示**之间（外加当前未完成块的部分和）；
- 内存降到 **O(Nd)**；
- 官方 README：**约 8 个块即可恢复 Full AttnRes 的大部分收益**，边际开销可忽略，是实用的 drop-in 方案。

## 5. 官方伪代码逐行解读

以下是官方 README 的 Block AttnRes 核心逻辑（PyTorch 风格）：

```python
def block_attn_res(blocks, partial_block, proj, norm):
    """
    blocks:        已完成块的表示，N 个 [B, T, D] 张量
    partial_block: 当前块内未完成的部分和 b_n^i, [B, T, D]
    proj / norm:   每层学到的投影（伪查询）与 RMSNorm
    """
    V = torch.stack(blocks + [partial_block])  # [N+1, B, T, D]  值 = 历史块表示 + 当前部分和
    K = norm(V)                                # 键 = 归一化后的值（RMSNorm 稳定尺度）
    logits = torch.einsum('d, n b t d -> n b t', proj.weight.squeeze(), K)  # 伪查询 w_l 与键点积
    h = torch.einsum('n b t, n b t d -> b t d', logits.softmax(0), V)       # 对块维度 softmax 加权求和
    return h
```

解读要点：

- **`proj.weight.squeeze()` 就是伪查询 $w_l$**——每层一个 d 维向量，不依赖输入；
- **softmax 作用在块维度（n）**，即"这个层认为哪几个历史块最值得读"；
- `partial_block` 参与注意力是为了让当前块内的累加结果也能被"即时读取"，不必等块结束；
- 块边界判定在 `forward` 中：`layer_number % (block_size // 2) == 0`（因为每层有 ATTN + MLP 两个子层，block_size 按子层计数）。

## 6. 三轴分工：深 / 长 / 宽

K3 架构的三大创新恰好对应三个维度，互不重叠：

| 维度 | 机制 | 解决什么 |
| --- | --- | --- |
| **深度**（层方向） | **AttnRes** | 历史层表示被均匀累加稀释、幅值无界 |
| **序列长度**（时间方向） | **KDA** | 全注意力二次方成本 → 线性记忆 + Delta Rule 可写性 |
| **宽度**（专家方向） | **Stable LatentMoE** | 896 选 16 极端稀疏下的负载均衡与路由稳定性 |

三者共同支撑"2.8T 参数 + 1M 上下文"的规模组合。主文档 §4.4 的架构总览把 AttnRes 标为"跨层读取——深度维度：选择性残差"，与本文一致。

## 7. 关键数字与证据等级

| 项 | 值 | 来源 / 等级 |
| --- | --- | --- |
| 训练开销 | 论文原文称"边际化"（marginal） | arXiv:2603.15031（官方论文口径；**具体百分比官方未公布**） |
| 推理开销 | 论文原文称"极小"（minimal） | arXiv:2603.15031（官方论文口径） |
| Block 块数 | 约 8 块恢复大部分收益 | 官方 README（**官方自报**） |
| Full 内存 | O(Ld) → Block O(Nd) | 官方 README（架构事实） |
| 论文 | arXiv:2603.15031 | 官方（2026-03 提交） |
| 官方仓库 | 3.4k stars / 202 forks | 第三方可见信号（非性能证据） |

## 8. 待验证与注意点

- **25% 训练效率提升（旧版引用的数字）已撤回**——2026-08-02 核验确认官方博客/论文/模型卡均未公布该百分比，出处未确认；官方可确认口径仅为"2.5× 整体扩展效率（vs K2）"与论文"marginal/minimal overhead"表述，均未见独立复现；
- **推理引擎兼容性为推测**：AttnRes 改变的是残差路径与归一化位置，训练好的权重在 vLLM/SGLang 推理时通常不受影响（推理不做残差重计算），但若下游引擎按"标准 PreNorm 结构"做图优化（如算子融合、量化校准），**可能需要注意归一化位置差异**。此条为本文推测，未见官方说明；
- 论文页与仓库发布节奏：仓库 2026-07 才公开，论文 arXiv 编号为 2603（2026-03 提交）——技术报告先于权重发布，与 K3 开源节奏一致。

## 9. 参考来源

- [MoonshotAI/Attention-Residuals（官方仓库 README，含伪代码）](https://github.com/MoonshotAI/Attention-Residuals)
- [Attention Residuals 论文（arXiv:2603.15031）](https://arxiv.org/abs/2603.15031)
- 主文档 §4.2（本仓库整理，含官方自报数字）
- Kimi K3 官方技术博客（"Open Frontier Intelligence"）

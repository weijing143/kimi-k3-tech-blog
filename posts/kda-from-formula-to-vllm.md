# KDA 不是"线性注意力"这么简单：从递推公式到 vLLM Prefix Cache

> 写作日期：2026-07-28
> 依据：Kimi Linear 论文（arXiv:2510.26692）、FLA 开源 KDA kernel（fla-org/flash-linear-attention，MIT）、vLLM `kimi_linear.py`（Apache-2.0）、Kimi K3 官方模型卡
> 读者预设：了解 Transformer 注意力机制，看得懂矩阵记号

---

## 0. 引子：三个流传最广的误解

Kimi K3 发布以来，"KDA"被大量二手文章一笔带过为"一种线性注意力，所以快"。这句话里藏着三个误解：

1. **"线性注意力就是弱"**——这是 2023 年前的旧印象。Kimi Linear 论文的核心贡献恰恰是：在**完全相同的训练配方**下，KDA 混合架构在短上下文、长上下文、RL 扩展三类场景**全面反超同配方全注意力（MLA）**，这是线性注意力路线第一次在公平对比下做到这点。
2. **"KDA = 普通 linear attention"**——普通线性注意力的记忆是"只加不改"的，容量一满就互相覆盖。KDA 的记忆是**带误差纠正的可控遗忘**，表达能力不在一个层级。
3. **"快只是因为省 KV cache"**——KV cache 减少约 75% 只是结果之一。1M 上下文解码 TPOT 1.84ms vs MLA 11.48ms 的 6.3 倍提速，还来自 O(N) 复杂度、chunkwise 算法对 Tensor Core 的友好、以及无 KV cache 后显存带宽压力的解除。

本文做三件事：把 KDA 的递推公式从最朴素的形式一步步推导出来；解释它为什么数值稳定、为什么不用 RoPE；最后追踪这套机制在 FLA kernel 和 vLLM 里的真实代码形态——特别是它对 **prefix cache** 这个 serving 关键环节带来的新问题和解法。

---

## 1. 四步推导：从全注意力到 KDA

### 1.1 第一步：全注意力 = 无界精确记忆

把 softmax 注意力换个角度看：每处理一个 token，就把它的 (k, v) **原样存进仓库**，查询时拿 q 和仓库里每条 k 算相似度、加权取回 v。记忆容量无限、检索精确，但代价是仓库（KV cache）随序列线性膨胀，且每次查询都要翻遍整个仓库——O(N²) 计算、O(N) 显存。

### 1.2 第二步：朴素线性注意力 = 只加不改的压缩记忆

线性注意力把"仓库"换成一个**固定大小的矩阵状态** `S ∈ R^{K×V}`：

```
S_t = S_{t−1} + k_t·v_tᵀ        # 写入：外积累加
o_t = q_tᵀ·S_t                  # 读取：矩阵向量乘
```

记忆被压缩进定长状态，计算降到 O(N)，KV cache 消失。问题也很直接：`S` 只能做**加法**。两个 token 写入相近的 k 方向时互相干扰；状态里的旧信息只增不减，越到后面信噪比越差。这就是历史上线性注意力"快但弱"的根源。

### 1.3 第三步：Delta Rule = 写入前先纠错

DeltaNet 的改进只有一行，但性质完全不同：

```
S_t = (I − β·k_t·k_tᵀ)·S_{t−1} + β·k_t·v_tᵀ
```

展开看第二项发生了什么：

```
S_t = S_{t−1} + β·k_t·(v_t − k_tᵀ·S_{t−1})ᵀ
                    └──────┬──────────┘
                    新值 − 用当前记忆读出的旧值
```

写入之前，先用 k_t 从现有记忆里**读出旧值，算出误差，再只按误差修正**——这是在线最小二乘（delta rule / Widrow-Hoff 规则）的形式。`β` 是学习率。记忆从"只加不改的仓库"变成了"可更新键值对的关联存储"：同一个 k 再次出现时，旧的 v 可以被新值覆盖。

### 1.4 第四步：KDA = 逐通道可控遗忘 + Delta Rule

Gated DeltaNet（GDN）给状态加了**标量**遗忘门 α：整体状态每步统一衰减。KDA 的关键升级是把标量 α 换成**逐通道（channel-wise）对角门控** `Diag(α_t)`：

```
S_t = (I − β·k_t·k_tᵀ)·Diag(α_t)·S_{t−1} + β·k_t·v_tᵀ
```

`α_t ∈ R^K` 是一个向量——**记忆状态的每个通道独立决定自己的遗忘速度**。有的通道可以快速遗忘（跟踪局部语法），有的通道几乎不遗忘（记住早期关键事实）。有限状态 RNN 的记忆容量是稀缺的，逐通道门控让模型能精细分配这笔预算，这就是论文标题里 "finer-grained gating mechanism" 的含义。

### 1.5 公式 ↔ 代码逐行对照

理论到此为止。FLA 仓库里的参考实现 `fla/ops/kda/naive.py`（MIT 协议）证明这套公式简单得惊人——核心递推就三行：

```python
# 摘自 fla/ops/kda/naive.py（naive_recurrent_kda，逐 token 参考实现）
for i in range(0, T):
    q_i, k_i, v_i, g_i, b_i = q[:, i], k[:, i], v[:, i], g[:, i], beta[:, i]
    S = S * g_i[..., None].exp()                                                # ① 逐通道衰减：Diag(α_t)·S
    S = S + torch.einsum('b h k, b h v -> b h k v',
                         b_i[..., None] * k_i,
                         v_i - (k_i[..., None] * S).sum(-2))                    # ② delta rule 纠错写入
    o[:, i] = torch.einsum('b h k, b h k v -> b h v', q_i, S)                   # ③ 读取
```

对照关系：

- 门控 `g` 存在 **log 空间**（shape `[B, T, HV, K]`，逐通道），`exp(g)` 才是 α——log 空间参数化天然保证 α > 0，配合约束训练使 α ∈ (0,1)；
- 第 ② 行里的 `v_i − (k_i·S)` 就是 1.3 节的"新值 − 旧读出"误差项，和公式 `(I − βkkᵀ)S + βkvᵀ` 完全等价（先衰减后纠错，代数上相同）；
- 注意这个函数叫 **naive**——它是正确性基准，生产用的是 chunkwise 版本（第 3 节）。

---

## 2. 两个顺带回答的问题

### 2.1 为什么数值稳定、百万 token 不炸？

不是 delta rule "保证"稳定，而是两个机制叠加：

1. **α ∈ (0,1) 使状态有界**：每步先把旧记忆乘以小于 1 的系数，状态范数不会随序列长度发散；
2. **delta rule 是局部纠错**：写入量正比于"预测误差"而非输入本身，记忆趋于收敛而非累加。

线性注意力老路线（无门控、纯累加）恰恰缺这两点，所以长序列必崩。

### 2.2 为什么没有 RoPE？（NoPE 设计）

RoPE 通过旋转 q/k 编码**相对位置**。而 `Diag(α_t)` 的衰减本身就是相对位置信息：两个 token 相隔越远，前一个的贡献被连乘衰减得越多——**距离自然地编码在遗忘曲线里**。KDA 让逐通道遗忘系数可学习，等于每个通道学出了自己的"位置编码频率"。vLLM 代码里这一点有硬性印证：`KimiMLAAttention` 中 `assert self.use_nope is True` 且 `rotary_emb=None`——不只 KDA 层，连 K3 里的 MLA 全注意力层都不用旋转位置编码。

---

## 3. 硬件效率：为什么 naive 版本在 GPU 上跑不动

逐 token 递推有两个 GPU 天敌：**顺序依赖**（第 t 步依赖 t−1 步的状态）和**小矩阵运算**（每步只做 rank-1 更新，Tensor Core 完全吃不饱）。Kimi Linear 的解法是 **chunkwise 算法**：

- 序列切成定长 chunk（FLA 参考实现 `chunk_size=64`）；
- **chunk 内部**：用 WY 表示把 chunk 内的递推重写成几个大矩阵乘，并行计算；
- **chunk 之间**：仍按递推传递状态 S，但每 64 个 token 才传递一次。

论文的两个关键工程选择：

1. **特化 DPLR 转移矩阵**：KDA 的状态转移 `(I − βkkᵀ)·Diag(α)` 是"对角 + 低秩"（DPLR）结构。通用 DPLR 的 chunkwise 公式有一堆额外矩阵运算；KDA 用了一个**特化变体**，比通用形式大幅降低计算量（约 2×），且与经典 delta rule 更一致。
2. **WY 表示 + UT 变换，单级分块**：避免二级分块引入的 FP32 精度开销，让 chunk 内所有运算以混合精度落在 Tensor Core 上。

FLA 仓库的文件结构就是这套算法的地图（`fla/ops/kda/`）：

| 文件 | 角色 |
| --- | --- |
| `naive.py` | 逐 token / 朴素 chunk 参考实现（正确性基准） |
| `wy_fast.py` | WY 表示的构建（chunk 内并行化的核心） |
| `chunk.py` / `chunk_fwd.py` | chunkwise 前向主逻辑 |
| `chunk_intra.py` / `chunk_intra_token_parallel.py` | chunk 内部（intra-chunk）并行 kernel |
| `chunk_bwd.py` | 反向传播 |
| `fused_recurrent.py` | 解码期逐 token 融合 kernel（batch 推理用） |
| `gate.py` | 逐通道门控的计算 |

值得一提：KDA 层输入侧还有 **ShortConv + Swish**（q/k/v 先过短卷积），vLLM 的状态管理里也能看到 `conv_kernel_size` 参数——卷积状态同样是推理状态的一部分。

---

## 4. 从 kernel 到模型：K3 里的 3:1 混合

KDA 不单独成模型。K3 官方模型卡确认的组合是 **69 层 KDA + 24 层 Gated MLA（+ 1 层 Dense）**，约 3:1 交错。为什么还需要 24 层全注意力？

压缩记忆有固有短板：对"一字不差地回忆极远处的某个具体 token"（needle 检索类任务），任何固定大小状态都不如原始 KV 精确。3:1 混合是务实的折中：

- **约 74% 的层（KDA）** 无 KV cache，承担绝大部分序列处理，省显存、提速度；
- **约 26% 的层（Gated MLA）** 保留完整 KV，兜住精确长程检索的底。

论文实测（48B-A3B，5.7T tokens）：同配方下 Kimi Linear 全面优于全 MLA；KV cache 减少最高 75%；1M 上下文解码 TPOT **1.84ms vs 11.48ms（6.3×）**。

---

## 5. vLLM 里的 KDA：从 kernel 到 serving，以及 Prefix Cache 问题

### 5.1 模型代码形态

vLLM 中 `vllm/model_executor/models/kimi_linear.py`（Apache-2.0）展示了 KDA 模型在 serving 框架里的真实样子：

- 模型类 `KimiLinearForCausalLM` 声明 `IsHybrid` 接口——**混合架构在 vLLM 里是一等公民**；
- 每层通过 `config.is_kda_layer(layer_idx)` 二选一：KDA 层走 `KimiGatedDeltaNetAttention`（位于 `vllm/model_executor/layers/mamba/gdn/kimi_gdn_linear_attn.py`——注意它在 **mamba 目录**下，因为推理状态管理与 Mamba 类线性 RNN 完全同构），MLA 层走 `KimiMLAAttention`；
- KDA 的推理状态不是 KV cache，而是走 vLLM 的 **mamba state 管理**：`get_mamba_state_shape_from_config`（含 recurrent state 和 short-conv state 两块）、`get_mamba_state_dtype_from_config`、`get_mamba_state_copy_func`。状态形状在引擎初始化时就静态确定——这正是线性注意力"显存不随上下文增长"在工程上的体现。

### 5.2 Prefix Cache：KDA 带来的真问题

全注意力时代的 prefix cache 逻辑很直白：相同前缀的 KV cache 块直接复用，跳过重复 prefill。这是 Mooncake 架构能做到编程负载 >90% 命中率、缓存输入便宜 10 倍的根基。

KDA 层**没有 KV cache**，它的"历史"被压缩进一个状态矩阵 S：

- S 是所有历史 token 的**有损压缩**，不存在"第 1000 个 token 的 K/V"这种可索引单元；
- 想复用前缀，唯一的选择是**在 chunk 边界对 S 做快照（state checkpoint）**：前缀相同 → 直接加载边界处的 S，从边界后继续递推；
- 但状态快照的粒度、存储开销、命中判定都和 KV 块完全不同——这就是为什么官方说 "KDA poses new challenges for conventional prefix caching"，并专门向 vLLM 社区贡献了 **KDA prefill-cache 实现**（随权重发布）。

混合架构的缓存因此是**双轨制**：KDA 层靠状态快照复用，MLA 层仍走传统 KV prefix cache。serving 框架必须同时管理两套生命周期——看 vLLM 代码里 `IsHybrid` + mamba state + KV cache 三者并存，就是这个复杂性的直接证据。

---

## 6. 对工程实践者的三点结论

1. **长上下文成本结构变了**。1M 上下文下 K3 可行的根本原因：74% 层的显存占用与上下文长度无关。评估长文档 / 代码库场景的成本时，不能用全注意力模型的显存曲线外推。
2. **解码吞吐是最大受益者**。6.3× 的 TPOT 优势来自解码期每 token 只做 O(1) 状态更新而非 O(N) 注意力扫描——长输出（深度推理、长报告生成）场景收益最大。
3. **精确检索类任务别硬上纯线性架构**。如果你的负载是大量"从百万 token 里精确捞一句话"，3:1 混合里的 MLA 层是兜底，但同类纯线性注意力小模型要格外谨慎评估。

---

## 参考

| 资料 | 链接 |
| --- | --- |
| Kimi Linear 论文 | https://arxiv.org/abs/2510.26692 |
| FLA KDA kernel（参考实现 `naive.py` 等） | https://github.com/fla-org/flash-linear-attention/tree/main/fla/ops/kda |
| vLLM Kimi Linear 模型实现 | https://github.com/vllm-project/vllm/blob/main/vllm/model_executor/models/kimi_linear.py |
| Kimi Linear 模型权重（48B-A3B） | https://github.com/MoonshotAI/Kimi-Linear |
| Kimi K3 官方模型卡 | https://huggingface.co/moonshotai/Kimi-K3 |

> 说明：本文引用的代码片段分别来自 MIT（FLA）与 Apache-2.0（vLLM）协议的开源仓库，引用目的是技术讲解；公式推导基于 Kimi Linear 论文。

# Kimi K3 自部署实验手册：从 8× H100 到 64 卡 Supernode

> 写作日期：2026-07-28｜配套脚本：[`examples/k3_selfhost_bench/`](../examples/k3_selfhost_bench/)
> **性质声明**：本文是**实验手册（runbook）**，不是评测报告。显存与权重的数字是可复算的算术；所有延迟/吞吐表格留空，由你或读者在自己的硬件上用配套脚本实测填入。**请不要引用本手册中任何留空的格子当作数据。**

---

## 1. 先算账：显存数学

| 项 | 估算 | 依据 |
| --- | --- | --- |
| 权重（MXFP4，4-bit） | 2.8T × 0.5 B ≈ **1.4 TB** | 纯算术；第三方报道实际下载包约 594 GB（safetensors 含压缩格式开销，以 HF 文件页为准） |
| 激活参数（每 token） | 104B | 官方模型卡 |
| KDA 层状态 | **与上下文长度无关**（固定大小） | 69 层 KDA 的状态是定长矩阵 + short-conv 状态 |
| MLA 层 KV cache | 随上下文线性增长 | 24 层 Gated MLA；MLA 的 latent 压缩使其 KV 远小于标准 MHA |
| 框架与运行时开销 | 数十 GB | vLLM/SGLang、CUDA graph、通信缓冲 |

**结论一**：8× H100 80GB（640 GB HBM）装不下 1.4 TB 权重——第三方报道的"8× H100 可加载"只可能是以下之一：权重放在 CPU/NVMe offload（极慢）、或报道口径为"594 GB 下载包刚好塞进显存"（无 KV cache 与运行时余量，仅实验性）。**生产配置请按官方建议的 64+ 加速卡 Supernode 规划**，8 卡只适合做"能跑起来"的验证。

**结论二**：KDA 架构的显存优势体现在**长上下文**——74% 的层状态不随上下文增长。1M 上下文下 MLA 层的 KV cache 才是主要变量，值得单独测量（见 §5 实验 C）。

## 2. 环境锁定

> ⚠️ KDA 是新算子，旧版推理框架**必然不支持**。下表的版本号留空——部署前查对应项目的 release notes 填入你实际锁定的版本。

| 组件 | 锁定版本 | 备注 |
| --- | --- | --- |
| vLLM | __________ | 需含 KDA prefill-cache 支持（官方贡献随权重发布）；`pip install -U vllm` 后以 `vllm serve --help` 与 release notes 双重确认 |
| SGLang | __________ | 官方模型卡提供 cookbook |
| TokenSpeed | __________ | 官方 recipes |
| Transformers | __________ | `trust_remote_code=True` 路径，仅建议用于验证，不建议生产 |
| CUDA / 驱动 | __________ | |
| PyTorch | __________ | |

## 3. 启动命令模板

### 3.1 vLLM（8 卡实验环境）

```bash
# TP=8 张量并行；EP（专家并行）配置以官方 recipe 为准
vllm serve "moonshotai/Kimi-K3" \
  --tensor-parallel-size 8 \
  --max-model-len 1048576 \
  --trust-remote-code \
  --gpu-memory-utilization 0.92
# 生产建议追加：--enable-prefix-caching（确认 KDA prefill-cache 已生效）
```

### 3.2 SGLang（官方模型卡给出的形态）

```bash
python3 -m sglang.launch_server \
  --model-path "moonshotai/Kimi-K3" \
  --host 0.0.0.0 --port 30000
# 多卡并行参数（--tp / --ep 等）以 SGLang cookbook 的 K3 条目为准
```

### 3.3 64 卡 Supernode（生产）

多节点 TP+EP 组合、RDMA/IB 通信域、节点亲和性配置——**以官方 recipes 为唯一依据**，不要照搬 8 卡参数外推。官方明确说明推理效率受益于"更大的高带宽通信域"。

## 4. 压测方法学

配套脚本 [`bench_serving.py`](../examples/k3_selfhost_bench/bench_serving.py)（OpenAI 兼容端点通用，vLLM / SGLang / TokenSpeed / 官方 API 都能打）：

```bash
export BENCH_BASE_URL="http://localhost:8000/v1"
export BENCH_MODEL="moonshotai/Kimi-K3"
export BENCH_API_KEY="EMPTY"

python bench_serving.py \
  --concurrency 1 4 8 16 \
  --requests-per-level 16 \
  --prompt-tokens 4096 \
  --max-output 512 \
  --out results_8xH100_vllm.json
```

脚本测量：**TTFT**（流式首 token）、**TPOT**、端到端时延、**并发聚合吞吐**、缓存命中量（`usage.prompt_tokens_details.cached_tokens`）。带 `--shared-prefix 100000` 可专门测前缀缓存命中后的输入成本。

方法学纪律（缺了这些，数字无法横向对比）：

1. **预热**：脚本先跑 2 个请求预热（权重加载、CUDA graph、kernel autotune），不计入结果；
2. **同 prompt 跨级别**：对比不同并发级别时 prompt 内容固定；
3. **记录完整上下文**：GPU 型号/数量、引擎版本、启动参数、TP/EP/PP、max-model-len、数据集——缺一项，数据就不可复现；
4. **错误也记录**：脚本把超时/5xx 记入 `errors`，压测中的错误率本身就是关键指标。

## 5. 实验设计与结果表（留空待填）

### 实验 A：基线吞吐（短上下文）

> 4K 输入 / 512 输出，并发 1/4/8/16，vLLM，8× H100

| 并发 | TTFT p50 (s) | TPOT (ms) | 聚合输出吞吐 (tok/s) | 错误数 |
| --- | --- | --- | --- | --- |
| 1 | ___ | ___ | ___ | ___ |
| 4 | ___ | ___ | ___ | ___ |
| 8 | ___ | ___ | ___ | ___ |
| 16 | ___ | ___ | ___ | ___ |

环境：GPU ___｜引擎 ___ 版本 ___｜启动参数 ___｜日期 ___

### 实验 B：长上下文扩展（KDA 的主场）

> 固定并发 1，输入长度 8K → 128K → 512K → 1M，观察 TTFT 与显存曲线

| 输入长度 | TTFT p50 (s) | 峰值显存 (GB) | 输出吞吐 (tok/s) |
| --- | --- | --- | --- |
| 8K | ___ | ___ | ___ |
| 128K | ___ | ___ | ___ |
| 512K | ___ | ___ | ___ |
| 1M | ___ | ___ | ___ |

**预期观察**（假设，待验证）：TTFT 随输入长度近线性增长（prefill 计算量），但显存增长应**显著缓于**全注意力模型——74% 的层无 KV cache。如果显存随上下文线性暴涨，说明 KDA 路径没生效，先查引擎版本。

### 实验 C：前缀缓存命中

> `--shared-prefix 100000`：所有请求共享 100K 前缀，对比开启/关闭 prefix caching 的 TTFT

| 配置 | TTFT p50 (s) | cached_tokens 占比 |
| --- | --- | --- |
| prefix caching ON | ___ | ___ |
| prefix caching OFF | ___ | ___ |

**重点**：验证 KDA prefill-cache（状态快照复用）是否真的生效——这是 KDA 架构服务化的关键新机制，值得单独写结论。

### 实验 D：引擎对比

> 同硬件、同负载，vLLM vs SGLang vs TokenSpeed

| 引擎 | 版本 | TTFT p50 (s) | TPOT (ms) | 聚合吞吐 (tok/s) |
| --- | --- | --- | --- | --- |
| vLLM | ___ | ___ | ___ | ___ |
| SGLang | ___ | ___ | ___ | ___ |
| TokenSpeed | ___ | ___ | ___ | ___ |

### 实验 E：精度抽查（MXFP4 原生权重 vs 社区量化）

> 固定 50 道你领域的评测题，对比官方 MXFP4 权重与社区 GGUF Q4/Q2 的答案质量

| 权重 | 正确数 / 50 | 备注 |
| --- | --- | --- |
| 官方 MXFP4（QAT） | ___ | 基线 |
| 社区 GGUF Q4 | ___ | 二次量化，预期有损失 |
| 社区 GGUF Q2 | ___ | 仅内存受限场景考虑 |

## 6. 成本模型：什么时候自部署才划算

```
自部署月成本 ≈ GPU 数量 × 卡时单价 × 730 小时 + 电力/带宽/运维
API 月成本   ≈ 月输入 tokens/1M × (命中×$0.30 + 未命中×$3.00) + 月输出 tokens/1M × $15.00
盈亏平衡点   ≈ 自部署月成本 ÷ 单位 API 成本对应的 token 量
```

经验法则（定性，非数据）：**只有持续高负载（GPU 利用率 >60%）、或有数据驻留/气隙隔离硬性要求、或要在自有数据上微调时，自部署才大概率划算**。波动负载走官方 API / Together AI / OpenRouter 几乎总是更便宜——缓存命中后输入 $0.30/MTok 的价格，折旧 GPU 很难打赢。

## 7. 部署检查清单

- [ ] 引擎版本明确包含 KDA / kimi_linear 支持（release notes 原文确认）
- [ ] 权重 SHA256 与 HF 文件页一致（防下载损坏 / 仿冒仓库）
- [ ] Kimi K3 License 已通读，商用/微调/再分发条款已确认
- [ ] 8 卡环境仅用于验证；生产按 Supernode + 官方 recipes 规划
- [ ] prefix caching 已开启且 KDA prefill-cache 生效（实验 C 验证）
- [ ] 压测记录了完整环境上下文（GPU/版本/参数/日期）
- [ ] 社区量化版本做过精度抽查（实验 E）再上线

---

> **再次提醒**：本文所有留空处均为待实测项。如果你在自己的硬件上完成了实验，欢迎把结果以 PR 形式补充进来（请注明环境上下文），本手册会逐步从"模板"长成"报告"。

# Kimi K3 生态追踪：发布首周的适配进度

> 写作日期：2026-08-02｜**时效性声明：本文是时间快照（K3 权重 2026-07-27 发布后一周）**，生态进展变化快，请以各项目仓库/官方页为准。本页的定位是"追踪锚点"：记录发布初期各方适配的关键事实与数据，后续更新时保留证据等级标注。
> **口径声明**：vLLM 数据来自 [vLLM 官方 Day-0 博客](https://vllm.ai/blog/2026-07-27-k3)（2026-07-27，2026-08-02 抓取）；llama.cpp 分析来自 [Discussion #26041](https://github.com/ggml-org/llama.cpp/discussions/26041)（2026-07-23，社区贡献者分析，**非官方**）；GGUF 状态来自 Hugging Face 仓库页面（搜索快照）。

---

## 1. 一句话版本

发布第一周，生态呈现"**引擎分化**"格局：**vLLM 与 SGLang 均做到 Day-0 生产级支持**（vLLM 用 DSpark 投机解码把单用户吞吐从 118 推到 370 tok/s，3.14×）；**llama.cpp 尚无可用 port**，但社区已完成预发布代码分析（KDA 可复用 gated delta net、MXFP4 有无损 repack 路径），GGUF 量化版已由第三方（unsloth、AtomicChat）放出。**跑生产用 vLLM/SGLang，本地尝鲜等 llama.cpp 落地**。

## 2. 引擎支持矩阵（截至 2026-08-02）

| 引擎 | 状态 | 关键细节 |
| --- | --- | --- |
| **vLLM** | ✅ Day-0 生产级 | 8×B300 / 8×MI355X；118→370 tok/s（DSpark）；预填充/解码分离、agentic KV、工具调用、结构化输出全支持 |
| **SGLang** | ✅ Day-0 | "SGLang and Miles Add Day-0 Support"（第三方报道） |
| **Google Cloud** | ✅ Day-0 | 云平台托管（第三方报道） |
| **llama.cpp** | ⚠️ 预发布分析，无可用 port | #26041 详细 gap analysis（2026-07-23）；已有 KDA/AttnRes/MXFP4 落地路径分析 |
| **GGUF 量化** | ✅ 第三方已放出 | unsloth/Kimi-K3-GGUF、AtomicChat/Kimi-K3-GGUF（HF） |

## 3. vLLM：最完整的参考实现

### 快速开始（官方命令）

```bash
vllm serve moonshotai/Kimi-K3 \
  --tensor-parallel-size 8 \
  --trust-remote-code \
  --load-format fastsafetensors \
  --enable-prefix-caching \
  --enable-auto-tool-choice \
  --tool-call-parser kimi_k3 \
  --reasoning-parser kimi_k3
```

### 性能与架构适配要点

| 项 | 数据 / 说明 |
| --- | --- |
| 无投机解码 | 118 tok/s（SPEED Bench，16×GB300 NVL72） |
| 加 DSpark | **370 tok/s（3.14×）**；低熵任务（代码）~4.73 接受 token/步，高熵（创作）~2.61 |
| DSpark 草稿模型 | [Inferact/Kimi-K3-DSpark](https://huggingface.co/Inferact/Kimi-K3-DSpark)（开源，MLA-native） |
| 混合 KV 缓存 | 同一调度器管理两类内存：全注意力层的 paged KV 块 + KDA 层的 recurrent state 块；**前缀缓存对 KDA 状态做快照注册+复制再扩展**——这套机制是 vLLM core 新增，惠及所有混合线性模型 |
| AttnRes 内核 | Triton/CUDA fused kernel（logits+softmax+聚合一次完成，残差更新与输出 RMSNorm 折叠进同一 kernel） |
| MoE 后端 | TRT-LLM-Gen（TP>1）/ MegaMoE（DEP）；EPLB 负载均衡；**权重在 MoE 路径原生 MXFP4 执行** |
| chat template | **Python 程序而非 Jinja**（用控制 token 直接构造 token 序列）——与其他模型的集成方式不同，值得注意 |
| 序列并行（TEP prefill） | reduce-scatter + all-to-all dispatch/combine + all-gather 替代两次 all-reduce；**自定义 reduce-scatter/all-gather 比 NCCL 快 1.7×–4.5×**（小到中等消息） |
| 结构化输出 | XGrammar 约束解码，reasoning/content/tool-call 分字段返回 |

> 注意：依赖 FlashInfer 等预发布依赖，官方说明"目前只有 Docker 镜像可用"。

## 4. llama.cpp：预发布分析（尚未能跑）

社区贡献者 [Hudabey](https://github.com/Hudabey/theseus) 在 #26041 做了逐文件 gap analysis（提交号固定引用）：

**可直接复用的现有基础**：
- `ggml_gated_delta_net` 已支持 KDA 所需的 per-channel gate 模式（多后端）；
- `LLM_ARCH_KIMI_LINEAR` 的完整计算图与转换器已存在（来自 Kimi-Linear）；
- 混合循环/注意力内存基础设施已就位；
- `GGML_TYPE_MXFP4` 已是可加载可运行类型。

**两个关键结论**：
1. **KDA 内核工作量可能比预期小**——若 K3 与 Kimi-Linear 的递推、张量形状、gate 约定一致（发布前未知）；
2. **MXFP4 保真转换路径**：原生 MXFP4 权重应做**无损 byte repack** 到 `block_mxfp4`（沿用 gpt-oss / DeepSeek-V4 转换器模式），而非反量化再重新量化；theseus 仓库含 byte-exact 往返测试与 0xFF E8M0 scale 拒绝测试。

**AttnRes 的 correctness-first 映射**：用现有 ggml 原语（rms_norm、mul_mat、soft_max、行视图乘法、加法）即可实现；AttnRes 深度状态只属于单次前向，**不影响 KV cache / 持久内存**——这与 vLLM 的结论一致（AttnRes 的额外成本在计算路径，不在缓存结构）。

此外 llama.cpp 已有针对 K3 的 PR：full-size model fixes、MoonViT-3d vision tower。

## 5. 量化与本地运行

- **GGUF**：unsloth 与 AtomicChat 均已放出 K3 GGUF（HF）。注意：官方权重为 MXFP4，GGUF 转换需走上述无损 repack 或明确量化精度损失路径，**各 GGUF 的精度处理方式需自行核对**；
- **本地硬件门槛**：2.8T 模型即使量化也远超单机消费级——本地尝鲜大概率只能跑 MoE 子集或等 llama.cpp 落地后的量化裁剪版本，量级参考见自部署手册。

## 6. 关键数字与证据等级

| 项 | 值 | 来源 / 等级 |
| --- | --- | --- |
| 118 → 370 tok/s（3.14×） | vLLM + DSpark | 官方博客（vLLM 自测，SPEED Bench） |
| DSpark 接受率 4.73 / 2.61 | 低/高熵任务 | 官方博客（vLLM 自测） |
| 自定义 reduce-scatter 1.7×–4.5× | vs NCCL | 官方博客（vLLM 自测） |
| llama.cpp 可复用组件清单 | — | 社区贡献者分析（#26041，非官方） |
| GGUF 可用性 | unsloth / AtomicChat | HF 仓库（第三方） |
| SGLang / Google Cloud Day-0 | — | 第三方报道（未独立验证细节） |

## 7. 更新建议

- 本页数据截至 **2026-08-02**；下次更新时重点核对：llama.cpp 是否已合入 K3 arch、vLLM 是否移除"仅 Docker"限制、GGUF 精度处理说明是否补齐；
- 更新时保留本页证据等级标注，新增条目按 SOURCES.md 口径登记来源；
- 若需长期自动追踪，可考虑定时 CI 检查上游仓库（超出本文范围，暂以人工更新）。

## 8. 参考来源

- [vLLM 官方博客：Kimi K3 Is Here: Efficient Day-0 Support（2026-07-27）](https://vllm.ai/blog/2026-07-27-k3)
- [vLLM 预览博客：production-scale integration（2026-07-22）](https://vllm.ai/blog/2026-07-22-kimi-k3-preview)
- [llama.cpp Discussion #26041：pre-release analysis（2026-07-23）](https://github.com/ggml-org/llama.cpp/discussions/26041)
- [unsloth/Kimi-K3-GGUF](https://huggingface.co/unsloth/Kimi-K3-GGUF) · [AtomicChat/Kimi-K3-GGUF](https://huggingface.co/AtomicChat/Kimi-K3-GGUF)（HF）
- [Inferact/Kimi-K3-DSpark（DSpark 草稿模型）](https://huggingface.co/Inferact/Kimi-K3-DSpark)

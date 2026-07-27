# K3 自部署压测脚本

配套手册：[《Kimi K3 自部署实验手册》](../../posts/k3-selfhost-runbook.md)

## bench_serving.py

OpenAI 兼容端点通用压测：TTFT / TPOT / 端到端时延 / 并发聚合吞吐 / 缓存命中量。vLLM、SGLang、TokenSpeed、官方 API 均可作为被测端点。

### 用法

```bash
pip install openai>=1.0

export BENCH_BASE_URL="http://localhost:8000/v1"   # 被测端点
export BENCH_MODEL="moonshotai/Kimi-K3"            # 模型名
export BENCH_API_KEY="EMPTY"                       # 本地部署通常任意值

python bench_serving.py \
  --concurrency 1 4 8 16 \
  --requests-per-level 16 \
  --prompt-tokens 4096 \
  --max-output 512 \
  --out results.json
```

### 关键参数

| 参数 | 说明 |
| --- | --- |
| `--concurrency` | 并发级别列表，逐级压测 |
| `--requests-per-level` | 每个级别的请求数 |
| `--prompt-tokens` | 每请求新增内容的近似 token 数 |
| `--shared-prefix` | 所有请求共享前缀的近似 token 数（测前缀缓存命中） |
| `--no-stream` | 非流式模式（退化为端到端时延，无 TTFT） |
| `--out` | 原始结果 JSON 输出路径 |

### 纪律

- 脚本自动预热 2 个请求，预热结果不计入；
- 结果必须连同 GPU 型号/数量、引擎版本、启动参数、并行策略一起记录，否则不可复现；
- **本脚本只测量，不附带任何"参考数据"**——留空的表格请用自己的实测填写。

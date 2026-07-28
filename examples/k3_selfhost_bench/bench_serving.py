"""
K3 自部署 serving 压测脚本（OpenAI 兼容端点通用）

测量指标：TTFT（首 token 延迟）、TPOT（每输出 token 延迟）、端到端时延、
并发吞吐（aggregate tokens/s）、缓存命中情况（若端点返回 usage.prompt_tokens_details）。

用法：
    export BENCH_BASE_URL="http://localhost:8000/v1"   # vLLM / SGLang 端点
    export BENCH_MODEL="moonshotai/Kimi-K3"            # 或 kimi-k3
    export BENCH_API_KEY="EMPTY"                       # 本地部署通常任意值
    python bench_serving.py --concurrency 1 4 8 --requests-per-level 16 \
        --prompt-tokens 4096 --max-output 512

注意：
- 本脚本只测量，不生成任何"参考数据"。所有结果请以你自己的硬件与版本为准。
- TTFT 依赖流式响应；--no-stream 模式下退化为端到端时延。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from dataclasses import dataclass, field

import openai


@dataclass
class Sample:
    ttft: float | None = None          # 秒
    e2e: float = 0.0                   # 秒
    output_tokens: int = 0
    prompt_tokens: int = 0
    cached_tokens: int = 0
    error: str | None = None

    @property
    def tpot(self) -> float | None:    # 秒 / token
        if self.ttft is None or self.output_tokens <= 1:
            return None
        return (self.e2e - self.ttft) / (self.output_tokens - 1)


@dataclass
class LevelResult:
    concurrency: int
    samples: list[Sample] = field(default_factory=list)
    wall_s: float = 0.0  # 该并发级别整批请求的墙钟时间（由 run_level 记录）

    def summary(self) -> dict:
        ok = [s for s in self.samples if s.error is None]
        ttfts = [s.ttft for s in ok if s.ttft is not None]
        tpots = [s.tpot for s in ok if s.tpot is not None]
        # 聚合吞吐必须用整批墙钟时间：请求数 > 并发度时存在排队，
        # 用单请求最大 e2e 会系统性高估吞吐
        wall = self.wall_s
        total_out = sum(s.output_tokens for s in ok)
        return {
            "concurrency": self.concurrency,
            "ok": len(ok),
            "errors": len(self.samples) - len(ok),
            "ttft_mean_s": round(statistics.mean(ttfts), 3) if ttfts else None,
            "ttft_p50_s": round(statistics.median(ttfts), 3) if ttfts else None,
            "tpot_mean_ms": round(statistics.mean(tpots) * 1000, 2) if tpots else None,
            "e2e_mean_s": round(statistics.mean(s.e2e for s in ok), 2) if ok else None,
            "wall_s": round(wall, 2),
            "agg_output_tps": round(total_out / wall, 1) if wall > 0 else None,
            "prompt_tokens": sum(s.prompt_tokens for s in ok),
            "cached_tokens": sum(s.cached_tokens for s in ok),
        }


def make_prompt(n_tokens_approx: int) -> str:
    """生成约 n_tokens 的可重复 prompt（英文约 4 字符/token，取保守 3.5）。

    注意：prompt 内容固定以便跨并发级别对比；如需测前缀缓存命中，
    请用 --shared-prefix 让所有请求共享大段相同前缀。
    """
    words = ("the quick brown fox jumps over a lazy dog near the river bank "
             "under bright sunlight while birds sing softly in the trees ")
    reps = max(1, int(n_tokens_approx * 3.5 / len(words)) + 1)
    return (words * reps)[: int(n_tokens_approx * 3.5)]


def build_content(shared_prefix: str, prompt: str, unique_id: str) -> str:
    """拼装请求内容。唯一标识放在共享前缀之后、正文之前：

    这样跨请求的公共前缀恰好等于 shared_prefix——否则所有请求内容完全一致，
    整段都会成为公共前缀，--shared-prefix 的长度变化对缓存命中没有影响，
    前缀缓存实验（on/off 或不同长度对比）就不存在有效对照。
    """
    parts = []
    if shared_prefix:
        parts.append(shared_prefix)
    parts.append(f"[request-id: {unique_id}]")
    parts.append(prompt)
    parts.append("用一句话总结上文。")
    return "\n\n".join(parts)


async def one_request(client: openai.AsyncOpenAI, args, prompt: str,
                      shared_prefix: str, request_id: str) -> Sample:
    s = Sample()
    content = build_content(shared_prefix, prompt, request_id)
    # 官方 API 的字段是 max_completion_tokens（Quickstart 明示，默认 131072）；
    # 老端点只认 max_tokens 时用 --legacy-max-tokens 切换
    limit_kw = ({"max_tokens": args.max_output} if args.legacy_max_tokens
                else {"max_completion_tokens": args.max_output})
    t0 = time.perf_counter()
    try:
        if args.no_stream:
            resp = await client.chat.completions.create(
                model=args.model,
                messages=[{"role": "user", "content": content}],
                **limit_kw,
            )
            s.e2e = time.perf_counter() - t0
            if resp.usage:
                s.output_tokens = resp.usage.completion_tokens or 0
                s.prompt_tokens = resp.usage.prompt_tokens or 0
                d = getattr(resp.usage, "prompt_tokens_details", None)
                s.cached_tokens = getattr(d, "cached_tokens", 0) or 0 if d else 0
        else:
            stream = await client.chat.completions.create(
                model=args.model,
                messages=[{"role": "user", "content": content}],
                stream=True,
                stream_options={"include_usage": True},
                **limit_kw,
            )
            first = True
            async for chunk in stream:
                if getattr(chunk, "usage", None):
                    s.output_tokens = chunk.usage.completion_tokens or 0
                    s.prompt_tokens = chunk.usage.prompt_tokens or 0
                    d = getattr(chunk.usage, "prompt_tokens_details", None)
                    s.cached_tokens = getattr(d, "cached_tokens", 0) or 0 if d else 0
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if first and (delta.content or getattr(delta, "reasoning_content", None)):
                    s.ttft = time.perf_counter() - t0
                    first = False
            s.e2e = time.perf_counter() - t0
    except Exception as e:  # noqa: BLE001 - 压测中记录错误而非中断
        s.e2e = time.perf_counter() - t0
        s.error = f"{type(e).__name__}: {e}"
    return s


async def run_level(client: openai.AsyncOpenAI, args, concurrency: int) -> LevelResult:
    prompt = make_prompt(args.prompt_tokens)
    shared_prefix = make_prompt(args.shared_prefix) if args.shared_prefix else ""
    sem = asyncio.Semaphore(concurrency)

    async def guarded(idx: int):
        async with sem:
            return await one_request(client, args, prompt, shared_prefix,
                                     request_id=f"c{concurrency}-{idx}")

    result = LevelResult(concurrency=concurrency)
    t0 = time.perf_counter()
    result.samples = await asyncio.gather(
        *[guarded(i) for i in range(args.requests_per_level)]
    )
    result.wall_s = time.perf_counter() - t0
    return result


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--concurrency", type=int, nargs="+", default=[1, 4, 8])
    p.add_argument("--requests-per-level", type=int, default=16)
    p.add_argument("--prompt-tokens", type=int, default=4096,
                   help="每个请求新增内容的近似 token 数")
    p.add_argument("--shared-prefix", type=int, default=0,
                   help="所有请求共享前缀的近似 token 数（测前缀缓存命中用）")
    p.add_argument("--max-output", type=int, default=512)
    p.add_argument("--no-stream", action="store_true")
    p.add_argument("--model", default=os.environ.get("BENCH_MODEL", "moonshotai/Kimi-K3"))
    p.add_argument("--out", default="bench_results.json")
    p.add_argument("--legacy-max-tokens", action="store_true",
                   help="用旧字段 max_tokens（官方 API 用默认的 max_completion_tokens）")
    args = p.parse_args()

    client = openai.AsyncOpenAI(
        base_url=os.environ.get("BENCH_BASE_URL", "http://localhost:8000/v1"),
        api_key=os.environ.get("BENCH_API_KEY", "EMPTY"),
        timeout=600.0,
    )

    # 预热：让权重、kernel、缓存就位，预热结果不计入。
    # 注意固定为 2 个请求——不要复用 run_level（它会跑 requests_per_level 个）
    print("预热 2 个请求 ...")
    warmup_prompt = make_prompt(args.prompt_tokens)
    warmup_prefix = make_prompt(args.shared_prefix) if args.shared_prefix else ""
    await asyncio.gather(*[one_request(client, args, warmup_prompt, warmup_prefix,
                                       request_id=f"warmup-{i}")
                           for i in range(2)])

    all_results = []
    for c in args.concurrency:
        print(f"并发 {c} × {args.requests_per_level} 请求 ...")
        r = await run_level(client, args, c)
        summary = r.summary()
        all_results.append(summary)
        print(json.dumps(summary, ensure_ascii=False))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"model": args.model, "args": vars(args), "results": all_results},
                  f, ensure_ascii=False, indent=2)
    print(f"\n原始结果已写入 {args.out}")
    print("提示：请同时记录 GPU 型号/数量、推理引擎版本、启动参数、并行策略（TP/EP/PP）——"
          "没有这些上下文，延迟数字没有意义。")


if __name__ == "__main__":
    asyncio.run(main())

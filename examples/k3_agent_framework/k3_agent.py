from __future__ import annotations

import json
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

import openai

logger = logging.getLogger("k3_agent")

# ---------------------------------------------------------------------------
# 价格表（每百万 tokens，美元）—— 以官方定价页为准，变动时只需改这里
# ---------------------------------------------------------------------------
PRICE_PER_MTOK = {
    "input_cache_hit": 0.30,
    "input_cache_miss": 3.00,
    "output": 15.00,
}


def message_to_dict(message: Any) -> dict:
    """把 SDK 返回的 message 对象转成可 JSON 序列化、可原样回传的 dict。

    关键点：必须保留 reasoning_content 与 tool_calls，而不是只取 content。
    """
    if hasattr(message, "model_dump"):
        # openai>=1.0 的 pydantic 对象；exclude_none 避免注入多余的 null 字段
        return message.model_dump(exclude_none=True)
    if isinstance(message, dict):
        return message
    raise TypeError(f"无法序列化 message：{type(message)!r}")


@dataclass
class UsageStats:
    """累计用量与成本。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    requests: int = 0

    def add(self, usage: Any) -> None:
        if usage is None:
            return
        self.requests += 1
        self.prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
        self.completion_tokens += getattr(usage, "completion_tokens", 0) or 0
        details = getattr(usage, "prompt_tokens_details", None)
        if details is not None:
            self.cached_tokens += getattr(details, "cached_tokens", 0) or 0

    @property
    def uncached_prompt_tokens(self) -> int:
        return max(self.prompt_tokens - self.cached_tokens, 0)

    def cost_usd(self) -> float:
        hit = self.cached_tokens * PRICE_PER_MTOK["input_cache_hit"] / 1e6
        miss = self.uncached_prompt_tokens * PRICE_PER_MTOK["input_cache_miss"] / 1e6
        out = self.completion_tokens * PRICE_PER_MTOK["output"] / 1e6
        return hit + miss + out

    def summary(self) -> str:
        return (
            f"请求 {self.requests} 次 | 输入 {self.prompt_tokens:,} tokens"
            f"（缓存命中 {self.cached_tokens:,}）| 输出 {self.completion_tokens:,} tokens"
            f" | 估算成本 ${self.cost_usd():.4f}"
        )


@dataclass
class K3Agent:
    """Kimi K3 可靠调用封装。

    - api_key / base_url：中国区 https://api.moonshot.cn/v1，国际区 https://api.moonshot.ai/v1
    - reasoning_effort：low / high / max（默认 max，K3 始终开启思考，勿用 K2.x 的 thinking 参数）
    - max_context_tokens：上下文预算，超出时触发裁剪（见 trim_messages）
    """

    api_key: str
    base_url: str = "https://api.moonshot.cn/v1"
    model: str = "kimi-k3"
    reasoning_effort: str = "max"
    timeout: float = 300.0
    max_retries: int = 5
    max_context_tokens: int = 900_000  # 留 10% 余量给输出，不要顶满 1M
    usage: UsageStats = field(default_factory=UsageStats)

    def __post_init__(self) -> None:
        self.client = openai.OpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
        )

    # ------------------------------------------------------------------
    # 底层：带重试的单次请求
    # ------------------------------------------------------------------
    def _request(self, *, messages: list[dict], tools: list[dict] | None = None,
                 stream: bool = False, **kwargs):
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "reasoning_effort": self.reasoning_effort,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
        payload.update(kwargs)

        delay = 2.0
        for attempt in range(1, self.max_retries + 1):
            try:
                return self.client.chat.completions.create(**payload)
            except (openai.RateLimitError, openai.InternalServerError,
                    openai.APIConnectionError, openai.APITimeoutError) as e:
                if attempt == self.max_retries:
                    raise
                logger.warning("第 %d 次请求失败（%s），%.1f 秒后重试", attempt, e, delay)
                time.sleep(delay)
                delay = min(delay * 2, 60.0)
        raise RuntimeError("unreachable")

    # ------------------------------------------------------------------
    # 中层：单轮对话（非流式）
    # ------------------------------------------------------------------
    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             **kwargs) -> dict:
        """发送一轮请求，返回【可原样回传】的 assistant message dict。"""
        resp = self._request(messages=messages, tools=tools, **kwargs)
        self.usage.add(resp.usage)
        return message_to_dict(resp.choices[0].message)

    def chat_stream(self, messages: list[dict],
                    on_reasoning: Callable[[str], None] | None = None,
                    on_content: Callable[[str], None] | None = None,
                    tools: list[dict] | None = None,
                    **kwargs) -> dict:
        """流式版本：reasoning 与 content 增量分别回调，最终返回完整 assistant message dict。

        业务逻辑不要把 reasoning_content 当作最终答案或 JSON 输出。
        """
        stream = self._request(messages=messages, tools=tools, stream=True,
                               stream_options={"include_usage": True}, **kwargs)
        reasoning_parts: list[str] = []
        content_parts: list[str] = []
        tool_calls: dict[int, dict] = {}

        for chunk in stream:
            if getattr(chunk, "usage", None):
                self.usage.add(chunk.usage)
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            r = getattr(delta, "reasoning_content", None)
            if r:
                reasoning_parts.append(r)
                if on_reasoning:
                    on_reasoning(r)
            if delta.content:
                content_parts.append(delta.content)
                if on_content:
                    on_content(delta.content)
            for tc in getattr(delta, "tool_calls", None) or []:
                slot = tool_calls.setdefault(
                    tc.index, {"id": "", "type": "function",
                               "function": {"name": "", "arguments": ""}})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function and tc.function.name:
                    slot["function"]["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    slot["function"]["arguments"] += tc.function.arguments

        message: dict[str, Any] = {
            "role": "assistant",
            "content": "".join(content_parts) or None,
        }
        if reasoning_parts:
            message["reasoning_content"] = "".join(reasoning_parts)
        if tool_calls:
            message["tool_calls"] = [tool_calls[i] for i in sorted(tool_calls)]
        return message

    # ------------------------------------------------------------------
    # 上层：完整工具调用循环
    # ------------------------------------------------------------------
    def run(self, messages: list[dict],
            tools: list[dict],
            tool_handlers: dict[str, Callable[[dict], str]],
            max_turns: int = 20) -> Iterator[dict]:
        """驱动"模型 ↔ 工具"循环，直到模型不再发起 tool_calls 或达到轮数上限。

        - messages：完整历史（含 system）。本方法会在其副本上追加，不修改调用方列表。
        - tool_handlers：{工具名: 处理函数}，处理函数接收解析后的 arguments dict，返回 str。
        - 逐轮 yield assistant message dict，便于调用方落盘 / 审计。

        循环结束后通过 self.last_messages 可取回完整历史（含每一轮 assistant 与 tool 消息）。
        """
        history = list(messages)
        for turn in range(1, max_turns + 1):
            history = self.trim_messages(history)
            assistant_msg = self.chat(history, tools=tools)
            history.append(assistant_msg)  # 完整回传：含 reasoning_content / tool_calls
            yield assistant_msg

            calls = assistant_msg.get("tool_calls") or []
            if not calls:
                self.last_messages = history
                return

            for call in calls:
                name = call["function"]["name"]
                raw_args = call["function"].get("arguments") or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    # 非法 JSON 不得静默改为 {} 照常执行——参数语义已不可信，
                    # 直接回传错误让模型重试，与文档承诺的行为一致
                    result = (f"ERROR: 工具 {name} 的参数不是合法 JSON，未执行。"
                              f"请重新生成合法的 arguments。原始内容：{raw_args[:200]!r}")
                    logger.error("工具 %s 参数 JSON 解析失败：%s", name, raw_args[:200])
                    history.append({
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "name": name,
                        "content": result,
                    })
                    continue
                handler = tool_handlers.get(name)
                if handler is None:
                    result = f"ERROR: 未注册的工具 {name!r}"
                    logger.error(result)
                else:
                    try:
                        result = handler(args)
                    except Exception as e:  # 工具异常也应回传，让模型自行恢复
                        result = f"ERROR: 工具 {name} 执行失败：{e}"
                        logger.exception("工具 %s 执行异常", name)
                history.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "name": name,
                    "content": str(result),
                })
        self.last_messages = history
        logger.warning("达到最大轮数 %d，强制结束", max_turns)

    # ------------------------------------------------------------------
    # 上下文裁剪：保住前缀稳定，裁掉中段
    # ------------------------------------------------------------------
    def trim_messages(self, messages: list[dict]) -> list[dict]:
        """超预算时的保守裁剪：保留 system 前缀与最近对话，丢弃最早的中段消息。

        注意：裁剪会丢掉对应的思考历史，可能触发 K3 的质量波动（官方已知限制），
        因此首选是控制任务规模；裁剪只是兜底。裁剪位置必须对齐到
        "assistant(tool_calls) + 其全部 tool 结果"的边界，避免产生孤儿 tool 消息。
        """
        total = self._estimate_tokens(messages)
        if total <= self.max_context_tokens:
            return messages

        # 只把【开头连续】的 system 消息视为固定前缀；出现在对话中段的 system
        # 消息（例如动态工具声明）保持原位、参与淘汰，不改变其语义位置
        prefix: list[dict] = []
        for m in messages:
            if m.get("role") == "system":
                prefix.append(m)
            else:
                break
        rest = messages[len(prefix):]

        # 前缀的 token 成本计入预算（原先漏算，超长 system 会挤爆预算）
        kept: list[dict] = []
        budget = self.max_context_tokens - self._estimate_tokens(prefix)
        # 从最新往回保留
        for m in reversed(rest):
            cost = self._estimate_tokens([m])
            if budget - cost < 0 and kept:
                break
            kept.append(m)
            budget -= cost
        kept.reverse()
        # 若首条是 tool 消息（其 assistant 被裁掉），继续向后剥离到安全边界
        while kept and kept[0].get("role") == "tool":
            kept.pop(0)
        # 同理，若末条是带 tool_calls 的 assistant 但其 tool 结果没保住（理论上
        # 从尾部连续保留不会发生，防御性处理），剥离该 assistant 避免悬挂调用
        while kept and kept[-1].get("role") == "assistant" and kept[-1].get("tool_calls"):
            ids = {tc.get("id") for tc in kept[-1]["tool_calls"]}
            answered = {m.get("tool_call_id") for m in kept if m.get("role") == "tool"}
            if ids <= answered:
                break
            kept.pop()
        logger.info("上下文裁剪：%d → %d 条消息", len(messages), len(prefix) + len(kept))
        return prefix + kept

    @staticmethod
    def _estimate_tokens(messages: list[dict]) -> int:
        """粗略估算：约 1 token / 2 个字符（中英混合偏保守）。精确计数以 API usage 为准。"""
        chars = 0
        for m in messages:
            content = m.get("content")
            if isinstance(content, str):
                chars += len(content)
            elif isinstance(content, list):
                chars += sum(len(str(p.get("text", ""))) for p in content if isinstance(p, dict))
            chars += len(m.get("reasoning_content") or "")
            for tc in m.get("tool_calls") or []:
                chars += len(tc.get("function", {}).get("arguments", ""))
        return chars // 2

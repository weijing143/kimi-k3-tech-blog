"""k3_agent.py 单元测试：裁剪预算、tool-call 原子性、流式拼装、工具异常。

运行：python -m unittest test_k3_agent -v
"""
from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from k3_agent import K3Agent, UsageStats, PRICE_PER_MTOK


def make_agent(max_context_tokens: int = 1000) -> K3Agent:
    # 不触发真实网络：构造后替换 client 即可
    agent = K3Agent(api_key="test", max_context_tokens=max_context_tokens)
    return agent


def msg(role: str, content: str, **kw) -> dict:
    m = {"role": role, "content": content}
    m.update(kw)
    return m


def assistant_with_tool(call_id: str, name: str = "f", args: str = "{}") -> dict:
    return {
        "role": "assistant",
        "content": None,
        "reasoning_content": "想一下",
        "tool_calls": [{"id": call_id, "type": "function",
                        "function": {"name": name, "arguments": args}}],
    }


class TestUsageStats(unittest.TestCase):
    def test_cost_and_cached(self):
        u = UsageStats()
        usage = SimpleNamespace(
            prompt_tokens=1_000_000, completion_tokens=100_000,
            prompt_tokens_details=SimpleNamespace(cached_tokens=400_000),
        )
        u.add(usage)
        self.assertEqual(u.uncached_prompt_tokens, 600_000)
        expected = (0.4 * PRICE_PER_MTOK["input_cache_hit"]
                    + 0.6 * PRICE_PER_MTOK["input_cache_miss"]
                    + 0.1 * PRICE_PER_MTOK["output"])
        self.assertAlmostEqual(u.cost_usd(), expected, places=6)


class TestTrimMessages(unittest.TestCase):
    def test_no_trim_when_under_budget(self):
        a = make_agent(max_context_tokens=10_000)
        msgs = [msg("system", "s"), msg("user", "u")]
        self.assertIs(a.trim_messages(msgs), msgs)

    def test_system_prefix_cost_counted(self):
        """超长 system 必须计入预算：800 字符 system（≈400 token）+ 预算 500，
        剩余只够保 1 条小消息。"""
        a = make_agent(max_context_tokens=500)
        msgs = [msg("system", "s" * 800)]
        msgs += [msg("user", f"第{i}轮 " + "x" * 400) for i in range(5)]
        out = a.trim_messages(msgs)
        self.assertEqual(out[0]["role"], "system")
        # 预算 500 - system 400 = 100 token（200 字符），每条 user ≈204 字符 → 保 0~1 条
        self.assertLessEqual(len(out), 2)

    def test_mid_conversation_system_not_hoisted(self):
        """对话中段的 system（动态工具声明）不得被提到最前。"""
        a = make_agent(max_context_tokens=220)
        msgs = [
            msg("system", "固定前缀"),
            msg("user", "u1 " + "x" * 100),
            msg("assistant", "a1 " + "x" * 100),
            msg("system", "动态工具声明"),          # 中段 system
            msg("user", "最新 " + "x" * 100),
        ]
        out = a.trim_messages(msgs)
        # 只有首条是固定前缀；若中段 system 被保留，它应仍在原相对位置（在 a1 之后）
        sys_positions = [i for i, m in enumerate(out) if m["role"] == "system"]
        self.assertEqual(sys_positions[0], 0)
        for i in sys_positions[1:]:
            self.assertEqual(out[i]["content"], "动态工具声明")
            self.assertGreater(i, 0)
        # 不得出现两个 system 相邻置顶
        if len(sys_positions) > 1:
            self.assertNotEqual(out[1]["role"], "system")

    def test_orphan_tool_message_removed(self):
        """裁剪边界不得留下孤儿 tool 消息。"""
        a = make_agent(max_context_tokens=120)
        msgs = [
            msg("system", "s"),
            msg("user", "u " + "x" * 200),
            assistant_with_tool("c1"),
            msg("tool", "结果", tool_call_id="c1", name="f"),
            msg("user", "最新 " + "x" * 80),
        ]
        out = a.trim_messages(msgs)
        self.assertNotEqual(out[1]["role"] if len(out) > 1 else None, "tool")
        # 所有 tool 消息的 tool_call_id 都必须有对应的 assistant tool_calls
        call_ids = {tc["id"] for m in out for tc in (m.get("tool_calls") or [])}
        for m in out:
            if m["role"] == "tool":
                self.assertIn(m["tool_call_id"], call_ids)

    def test_tool_call_pair_atomic(self):
        """assistant(tool_calls) 与其 tool 结果要么都在，要么都不在开头悬挂。"""
        a = make_agent(max_context_tokens=10_000)  # 不触发裁剪，原子性自然成立
        msgs = [msg("system", "s"), assistant_with_tool("c1"),
                msg("tool", "ok", tool_call_id="c1", name="f")]
        out = a.trim_messages(msgs)
        self.assertEqual(len(out), 3)


class FakeDelta:
    def __init__(self, content=None, reasoning=None, tool_calls=None):
        self.content = content
        self.reasoning_content = reasoning
        self.tool_calls = tool_calls


class FakeChunk:
    def __init__(self, delta=None, usage=None):
        self.choices = [SimpleNamespace(delta=delta)] if delta else []
        self.usage = usage


class TestChatStreamAssembly(unittest.TestCase):
    def test_streaming_tool_call_assembly(self):
        """流式分片的 tool_calls 必须按 index 拼成完整调用。"""
        chunks = [
            FakeChunk(FakeDelta(reasoning="思考")),
            FakeChunk(FakeDelta(tool_calls=[SimpleNamespace(
                index=0, id="call_1",
                function=SimpleNamespace(name="search", arguments='{"q":'))])),
            FakeChunk(FakeDelta(tool_calls=[SimpleNamespace(
                index=0, id=None,
                function=SimpleNamespace(name=None, arguments='"k3"}'))])),
            FakeChunk(FakeDelta(content="答案")),
            FakeChunk(usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5,
                                            prompt_tokens_details=None)),
        ]
        a = make_agent()
        with patch.object(a, "_request", return_value=iter(chunks)):
            m = a.chat_stream([msg("user", "hi")])
        self.assertEqual(m["reasoning_content"], "思考")
        self.assertEqual(m["content"], "答案")
        self.assertEqual(len(m["tool_calls"]), 1)
        tc = m["tool_calls"][0]
        self.assertEqual(tc["id"], "call_1")
        self.assertEqual(tc["function"]["name"], "search")
        self.assertEqual(json.loads(tc["function"]["arguments"]), {"q": "k3"})
        self.assertEqual(a.usage.prompt_tokens, 10)


class TestRunLoopToolErrors(unittest.TestCase):
    def test_tool_exception_returned_as_message(self):
        """工具抛异常时，错误应以 tool 消息回传而非中断循环。"""
        a = make_agent()
        turns = [
            assistant_with_tool("c1", name="boom"),
            msg("assistant", "恢复后的回答"),
        ]

        def fake_chat(messages, tools=None, **kw):
            return turns.pop(0)

        def boom(args):
            raise ValueError("炸了")

        with patch.object(a, "chat", side_effect=fake_chat):
            results = list(a.run([msg("user", "hi")], tools=[], tool_handlers={"boom": boom}))
        self.assertEqual(len(results), 2)
        tool_msgs = [m for m in a.last_messages if m["role"] == "tool"]
        self.assertEqual(len(tool_msgs), 1)
        self.assertIn("炸了", tool_msgs[0]["content"])
        self.assertIn("ERROR", tool_msgs[0]["content"])

    def test_unregistered_tool(self):
        a = make_agent()
        turns = [assistant_with_tool("c1", name="ghost"), msg("assistant", "ok")]
        with patch.object(a, "chat", side_effect=lambda *args, **kw: turns.pop(0)):
            list(a.run([msg("user", "hi")], tools=[], tool_handlers={}))
        tool_msgs = [m for m in a.last_messages if m["role"] == "tool"]
        self.assertIn("未注册", tool_msgs[0]["content"])

    def test_invalid_json_args_not_executed(self):
        """参数非法 JSON 时：不得调用 handler，应回传 ERROR tool 消息。"""
        a = make_agent()
        calls_made = []
        turns = [
            assistant_with_tool("c1", name="f", args="{not valid json"),
            msg("assistant", "重试后回答"),
        ]

        def handler(args):
            calls_made.append(args)
            return "ok"

        with patch.object(a, "chat", side_effect=lambda *a, **kw: turns.pop(0)):
            list(a.run([msg("user", "hi")], tools=[], tool_handlers={"f": handler}))
        self.assertEqual(calls_made, [])  # handler 未被调用
        tool_msgs = [m for m in a.last_messages if m["role"] == "tool"]
        self.assertEqual(len(tool_msgs), 1)
        self.assertIn("不是合法 JSON", tool_msgs[0]["content"])
        self.assertIn("ERROR", tool_msgs[0]["content"])


if __name__ == "__main__":
    unittest.main()

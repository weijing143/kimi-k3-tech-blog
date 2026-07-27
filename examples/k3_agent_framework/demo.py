"""
K3Agent 演示：带工具调用的完整 Agent 循环。

运行前：
    pip install -r requirements.txt
    export MOONSHOT_API_KEY="你的_KIMI_API_KEY"
    python demo.py
"""

import json
import os

from k3_agent import K3Agent

# ---------------------------------------------------------------------------
# 1. 定义工具（JSON Schema）
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 北京"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算一个数学表达式，如 (3+4)*2",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"},
                },
                "required": ["expression"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# 2. 工具实现（真实项目中换成真实 API / 数据库调用）
# ---------------------------------------------------------------------------
def get_weather(args: dict) -> str:
    city = args["city"]
    # 演示数据
    return json.dumps({"city": city, "temp_c": 31, "condition": "晴"}, ensure_ascii=False)


def calculate(args: dict) -> str:
    expr = args["expression"]
    allowed = set("0123456789+-*/(). ")
    if not set(expr) <= allowed:
        return "ERROR: 表达式含非法字符"
    return str(eval(expr))  # noqa: S307 - 演示用，生产请用安全求值器


TOOL_HANDLERS = {"get_weather": get_weather, "calculate": calculate}

# ---------------------------------------------------------------------------
# 3. 组装消息并运行
# ---------------------------------------------------------------------------
def main() -> None:
    agent = K3Agent(
        api_key=os.environ["MOONSHOT_API_KEY"],
        # base_url="https://api.moonshot.ai/v1",  # 国际区取消注释
        reasoning_effort="max",
    )

    # system 放在最前且内容保持稳定：最大化前缀缓存命中
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个严谨的数据助手。规则："
                "1) 需要计算时必须调用 calculate 工具，不要心算；"
                "2) 不要替用户做未授权的决定（K3 有过度主动倾向，需显式约束）；"
                "3) 回答使用中文，简洁。"
            ),
        },
        {
            "role": "user",
            "content": "查一下北京现在多少度，然后把温度乘以 2 再减 10 告诉我。",
        },
    ]

    for assistant_msg in agent.run(messages, TOOLS, TOOL_HANDLERS):
        if assistant_msg.get("tool_calls"):
            names = [c["function"]["name"] for c in assistant_msg["tool_calls"]]
            print(f"[模型调用工具] {names}")
        else:
            print(f"[最终回答] {assistant_msg['content']}")

    print()
    print(agent.usage.summary())


if __name__ == "__main__":
    main()

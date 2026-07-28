# Kimi K3 Agent 工程实践：完整回传 reasoning / tool history 的可靠调用框架

> 配套代码：[`examples/k3_agent_framework/`](../examples/k3_agent_framework/)（可直接运行）
> 适用对象：用 Kimi K3 API 构建 Agent / 工作流应用的工程师
> 写作日期：2026-07-28｜依据：官方模型卡、Kimi K3 Quickstart、Thinking Effort 文档

---

## 0. 为什么 K3 的 Agent 接入和别的模型不一样

大多数模型把"思考"当成一次性内部过程：请求之间无状态，历史里只留最终回答即可。K3 不同——它**在"保留思考历史（preserved thinking history）"模式下训练**：模型的多轮推理连续性，依赖你把上一轮**完整的 assistant message**（含 `reasoning_content`、`tool_calls`、Tool Call ID 等）原样喂回去。

官方在已知限制里把后果说得很直白：

> If the agent harness fails to pass back all the historical thinking content as required, or if an ongoing session with another model is switched over to K3, generation quality may become **highly unstable**.

也就是说：**harness 不再是一个中立的传输层，它本身就是 K3 效果的一部分。** 本文给出一个经过设计的调用框架，以及背后的每一条理由。

本文框架覆盖的八件事：

1. 完整回传 assistant message（第一原则）
2. 模型 ↔ 工具 调用循环
3. 流式输出（reasoning / content 分离）
4. 重试、限流与超时
5. 上下文裁剪（兜底，而非日常手段）
6. 前缀缓存与成本控制
7. token 用量与成本统计
8. 针对 K3"过度主动"的显式行为护栏

---

## 1. 第一原则：完整回传 assistant message

### 1.1 错误示范（最常见的坑）

```python
# ❌ 错误：只保留了 content，reasoning_content 和 tool_calls 全部丢失
messages.append({"role": "assistant", "content": completion.choices[0].message.content})
```

对 K3 而言这等价于"把模型的记忆剪掉了"：下一轮它看不到自己上一轮想过什么、调用过哪些工具、每个 tool result 对应哪个调用。表现就是官方说的"质量极不稳定"——可能重复调用同一个工具、忘记已做过的决定、逻辑断裂。

### 1.2 正确做法

```python
# ✅ 正确：SDK 返回的 message 对象整体序列化后原样回传
assistant_message = completion.choices[0].message
messages.append(assistant_message)  # 原样回传，不做字段挑选
```

用 OpenAI SDK（pydantic 对象）时，跨进程存储 / JSON 落盘需要一个转换函数。框架里的实现：

```python
def message_to_dict(message):
    """把 SDK 返回的 message 对象转成可 JSON 序列化、可原样回传的 dict。
    关键点：必须保留 reasoning_content 与 tool_calls，而不是只取 content。"""
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)  # exclude_none 避免注入多余 null 字段
    if isinstance(message, dict):
        return message
    raise TypeError(f"无法序列化 message：{type(message)!r}")
```

三条配套纪律：

- **不要会话中途换模型**。从别的模型的会话切到 K3（或反过来），历史里的思考格式对不上，同样会触发不稳定。
- **落盘就存完整 message**。审计、断点恢复、人工介入后接管，都依赖完整历史。
- **`reasoning_content` 不是给用户看的最终答案**，也不是 JSON 输出——它只是推理过程，业务逻辑不要消费它。

---

## 2. 工具调用循环的正确形态

K3 的工具调用循环和标准 OpenAI 形态一致，但每轮都必须遵守第一原则。完整循环（框架 `run()` 方法）的状态机：

```
         ┌──────────────────────────────────────────────┐
         ▼                                              │
   发送完整历史 ──► 模型返回 assistant message ──► 有 tool_calls？──否──► 结束
         ▲                      │                     │ 是
         │                      │原样入历史            ▼
         │                      │              逐个执行工具
         │                      │                     │
         │                      │        每个工具结果以 role=tool 消息
         │                      └────────（tool_call_id 对应）入历史
         └──────────────────────────────────────────────┘
```

关键细节：

1. **assistant 消息先完整入历史，再执行工具**。tool 消息通过 `tool_call_id` 与 assistant 的 `tool_calls[i].id` 一一对应——这个 ID 链条断了，模型就混淆结果归属。
2. **工具异常也要回传**，而不是让循环崩掉：把 `ERROR: ...` 作为 tool result 返回，K3 通常能自行恢复（换参数重试或向用户报告）。让 Python 异常穿透循环，等于把恢复策略从模型手里夺走。
3. **设最大轮数兜底**（框架默认 20）：K3 面向长程任务训练，遇到不可解问题时倾向继续尝试而不是停下，没有上限可能烧掉大量 token。
4. **arguments 要做 JSON 解析容错**：流式或长输出场景下 arguments 可能被截断成非法 JSON，解析失败按空 dict 处理并在 result 中体现，比直接抛异常更稳。

最小可运行示例见 [`demo.py`](../examples/k3_agent_framework/demo.py)：定义 `get_weather` 与 `calculate` 两个工具，跑一个"查天气 → 计算"的两跳任务。

---

## 3. 流式输出：两条通道分开渲染

K3 流式响应里，思维链增量走 `delta.reasoning_content`，最终答案增量走 `delta.content`。框架的 `chat_stream()` 把它们分别回调：

```python
agent.chat_stream(
    messages,
    on_reasoning=lambda t: render_thinking(t),  # UI：灰色折叠的"思考中"区域
    on_content=lambda t: render_answer(t),      # UI：正文区
)
```

两条纪律：

- **UI 可以展示思维链，业务逻辑不能消费它**。比如 structured output 场景，JSON 只会出现在 `content`，从 reasoning 里抓 JSON 是典型的线上事故来源。
- **流式也要拼回完整 assistant message**。`chat_stream()` 内部累积 reasoning / content / tool_calls（tool_calls 按 `index` 槽位拼接 arguments 增量），最终返回的 dict 与非流式形态完全一致，原样入历史——**流式不是豁免完整回传的理由**。

---

## 4. 重试、限流与超时

长程 Agent 任务单次请求可能运行数分钟、消耗数十万 token，网络抖动和 429 是常态而不是异常。框架的统一请求通道：

- **重试对象**：`RateLimitError`（429）、`InternalServerError`（5xx）、`APIConnectionError`、`APITimeoutError`。**不重试** 4xx 客户端错误（参数错了重试一百次也没用）。
- **退避策略**：指数退避 2s → 4s → 8s …，封顶 60s，默认最多 5 次。
- **超时**：默认 300s（`reasoning_effort=max` 的长推理本来就可能超过常见的 60s 默认值）。
- **OpenRouter 注意**：上线初期第三方渠道有容量公告，429 会更频繁，max 档建议走官方 API。

---

## 5. 上下文管理：前缀稳定优先，裁剪只是兜底

### 5.1 为什么前缀稳定值 10 倍的钱

官方 API 由 Mooncake 分离式架构支撑，缓存命中输入 $0.30/MTok，未命中 $3.00/MTok——**命中与否差 10 倍价格**，编程负载官方命中率 >90%。命中机制是前缀匹配：按官方缓存文档，prompt tokens 大于 256 的请求会自动尝试命中前缀缓存，无需额外参数——因此实践原则是**让高频重复的初始上下文（system、工具 schema、AGENTS.md）保持稳定并置于消息最前**；前缀变动越早，可命中的部分越短。

实践规则：

- system prompt、工具 schema、知识库内容的**顺序和文本保持恒定**；动态部分（时间戳、会话 ID）放到最后或 user 消息里。
- 不要在对话中段插入/修改消息。
- 动态加载工具用官方支持的 system message 方式追加，而不是改写给老的 system。

### 5.2 裁剪是兜底，不是日常手段

上下文逼近预算（框架默认 900K，给输出留 10%）时，框架 `trim_messages()` 的策略：

- 保留全部 system 消息 + 从最新往回尽量多保留；
- **裁剪边界必须对齐"assistant(tool_calls) + 其全部 tool 结果"**，否则产生孤儿 tool 消息，直接报错；
- 被裁掉的消息同时丢掉对应思考历史——这会触发 K3 的质量波动，所以裁剪后建议追加一条 system 提示"此前部分上下文已省略"。

更优的长期方案是**任务切分**：把超长任务拆成子任务，子任务间用结构化摘要（而不是原始历史）衔接。

---

## 6. 成本统计：每次请求都记账

框架的 `UsageStats` 累计每次响应的 `usage`，并按官方价格表估算成本：

```python
agent = K3Agent(api_key=...)
# ... 跑若干轮 ...
print(agent.usage.summary())
# 请求 4 次 | 输入 12,380 tokens（缓存命中 11,900）| 输出 1,204 tokens | 估算成本 $0.0217
```

要点：

- 缓存命中量读 `usage.prompt_tokens_details.cached_tokens`，命中/未命中分段计价。
- 流式请求要带 `stream_options={"include_usage": True}`，否则最后一个 chunk 没有 usage，账会丢。
- `reasoning_effort=max` 下输出 token 里思维链占大头——**low 档是降本降延迟的第一杠杆**，简单任务不要默认 max。

---

## 7. 行为护栏：给"过度主动"上笼头

官方承认的第二条限制是 **excessive proactiveness**：K3 面向长程困难任务训练，遇到模糊指令会替用户做决定——比如让它"修复这个 bug"，它可能顺手重构了三个文件。

框架管不了模型行为，但工程上可以：

1. **system prompt 显式划界**（demo 中有示例）："只做 X，不要 Y""修改文件前先列出计划等确认"。
2. **`AGENTS.md` 同样有效**：官方限制说明里点名了它，Kimi Code 场景下把约束写进仓库根的 `AGENTS.md`。
3. **工具侧收窄权限**：与其约束模型"别删文件"，不如不给它删文件的工具，或给工具加 dry-run / 审批回调。护栏放在工具层比放在 prompt 层可靠一个数量级。
4. **结构化输出兜底**：工作流状态、数据抽取用 `response_format={"type": "json_schema", "strict": true}`，把自由发挥的空间压到最小。

---

## 8. 上线前检查清单

- [ ] 所有 assistant 消息（含流式拼装的）都完整回传，无字段裁剪
- [ ] tool 消息的 `tool_call_id` 与 assistant `tool_calls` 一一对应
- [ ] 工具异常被捕获并以 ERROR result 回传，循环不崩
- [ ] 有最大轮数 / 最大 token 双重兜底
- [ ] 429/5xx/超时走指数退避，4xx 不重试
- [ ] system / 工具 schema 顺序恒定，前缀缓存命中率已观测（>90% 是健康线）
- [ ] 流式场景 reasoning 与 content 分离渲染，业务逻辑只消费 content
- [ ] 简单任务用 low 档，max 档留给长程复杂任务
- [ ] system prompt / AGENTS.md 中有显式行为边界，危险操作在工具层有审批
- [ ] 会话中途不切换模型

---

## 附：框架文件说明

| 文件 | 内容 |
| --- | --- |
| [`examples/k3_agent_framework/k3_agent.py`](../examples/k3_agent_framework/k3_agent.py) | `K3Agent` 核心：完整回传、工具循环、流式、重试、裁剪、成本统计 |
| [`examples/k3_agent_framework/test_k3_agent.py`](../examples/k3_agent_framework/test_k3_agent.py) | 9 个单元测试：成本统计、裁剪预算与原子性、流式 tool_calls 拼装、工具异常回传 |
| [`examples/k3_agent_framework/demo.py`](../examples/k3_agent_framework/demo.py) | 两跳工具任务演示（天气 → 计算） |
| [`examples/k3_agent_framework/requirements.txt`](../examples/k3_agent_framework/requirements.txt) | 依赖锁定 |

```bash
cd examples/k3_agent_framework
pip install -r requirements.txt
export MOONSHOT_API_KEY="你的_KIMI_API_KEY"
python demo.py
```

> **免责**：框架代码基于官方文档行为编写并通过语法校验，但未覆盖所有边界情况；价格表硬编码在 `k3_agent.py` 顶部，官方调价后请同步修改。

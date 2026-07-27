# K3 Agent 调用框架示例

配套文章：[《Kimi K3 Agent 工程实践：完整回传 reasoning / tool history 的可靠调用框架》](../../posts/k3-agent-engineering.md)

## 文件

| 文件 | 说明 |
| --- | --- |
| `k3_agent.py` | `K3Agent` 核心框架：完整 assistant message 回传、工具调用循环、流式 reasoning/content 分离、指数退避重试、上下文裁剪、token 成本统计 |
| `demo.py` | 两跳工具任务演示（查天气 → 计算），展示 `run()` 的用法 |
| `requirements.txt` | 依赖（`openai>=1.0`） |

## 运行

```bash
pip install -r requirements.txt
export MOONSHOT_API_KEY="你的_KIMI_API_KEY"
python demo.py
```

默认走中国区端点 `https://api.moonshot.cn/v1`；国际区在 `demo.py` 中取消 `base_url` 注释即可。

## 注意

- 代码基于官方文档行为编写并通过语法校验，未覆盖所有边界情况。
- `k3_agent.py` 顶部硬编码了官方价格表（$0.30 / $3.00 / $15.00 每百万 tokens），官方调价后请同步修改。
- 不要把 `reasoning_content` 当作最终答案或结构化输出消费。

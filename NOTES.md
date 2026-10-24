常见错误
1.
openai.AuthenticationError: Error code: 401 - {'error': {'message': 'Authentication Fails...'}}

`401` = 身份不对 = key 有问题。

2.
openai.APIConnectionError: Connection error.

`APIConnectionError` 是网络问题，不是代码问题

3.
openai.NotFoundError: Error code: 404

`404` = 模型名不存在


| `400 ... tool_calls must be followed by tool messages` | 有 tool_calls 但没给对应结果 | 检查是不是漏了某个 call 的结果 |
| `400 ... tool_call_id not found` | `tool_call_id` 和 `id` 对不上 | 打印两边对比，一定是复制粘贴错了 |
| `400 ... messages with role 'tool' must be a response to a preceding message` | tool 消息前没有 assistant 的 tool_calls | 检查顺序：assistant → tool → tool |
| 模型一直重复调用同一个工具 | 结果被截断得太狠 / 错误信息没说清 | 提高 `max_chars`，或改 `SYSTEM_PROMPT` 加"不要重复" |
| 循环 15 步还在转 | 任务本身不可能完成，或工具描述让模型误解 | 看 trace 每一步，通常是模型在反复试错 |
| `TypeError: run() got an unexpected keyword argument` | `args_model` 字段名和 `run()` 参数名不一致 | 两边必须同名 |
| `asyncio.TimeoutError` 冒到最外层 | `wait_for` 没有 try | 在工具内部捕获并抛 `TimeoutError` |
| 中文输出乱码 | 终端编码 | `chcp 65001` 切 UTF-8 |
| 工具结果全是 `ERROR: ...` | pydantic 校验失败 | 打印 `args.model_dump()` 看缺了什么字段 |
import json
import time
import asyncio
from ..providers import BaseProvider, get_provider
from ..providers.base import ToolCall
from ..tools.base import Tool
from ..tools.builtin import ALL_TOOLS
from .trace import Step, Trace

MAX_CONCURRENT_TOOLS = 4

SYSTEM_PROMPT = """你是一个会使用工具的助手。

工作规则：
1. 需要外部信息时（文件内容、目录结构、命令输出），必须调用工具获取，不要凭空猜测。
2. 已经有足够信息时，直接给出最终答案，不要再调用工具。
3. 工具返回 ERROR 时，先读懂错误原因，再决定是改参数重试还是换一种方法。不要重复完全相同的失败调用。
4. 需要创建或修改文件时，用 write_file 工具（它自己会建父目录）；不要用 run_cmd 拼 echo 重定向，那在 Windows 上容易写坏文件名和编码。
5. 最终答案要简洁，直接回答问题，不要复述工具输出。"""


async def _exec_tool(call: ToolCall, tool_map: dict[str, Tool]) -> str:
    """执行一次工具调用，任何异常都转成模型能读懂的 ERROR 文本。"""
    if call.parse_error:
        return (
            f"ERROR: 你上一次给出的工具参数无法解析。{call.parse_error}\n"
            "请重新输出合法的 JSON 参数。"
        )

    tool = tool_map.get(call.name)
    if tool is None:
        return (
            f"ERROR: 不存在名为 {call.name} 的工具。"
            f"可用工具：{', '.join(tool_map)}"
        )

    try:
        args = tool.validate(call.arguments)
    except Exception as exc:
        return f"ERROR: 参数不符合工具 {call.name} 的要求 —— {exc}"

    try:
        return await tool.run(**args.model_dump())
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"


async def run_task(
    task: str,
    provider: BaseProvider | None = None,
    tools: list[Tool] | None = None,
    max_steps: int = 15,
    token_budget: int = 80_000,
) -> dict:
    provider = provider or get_provider()
    tools = tools if tools is not None else ALL_TOOLS
    tool_map = {t.name: t for t in tools}
    schemas = [t.schema() for t in tools]

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    trace = Trace(task=task, provider=provider.name, model=provider.model)

    answer = ""
    status = "max_steps"

    try:
        for _ in range(max_steps):
            # 预算熔断：钱花完了就停，不要无限制循环
            if trace.total_tokens > token_budget:
                status = "budget_exceeded"
                break

            t0 = time.perf_counter()
            resp = await provider.chat(messages, tools=schemas)
            elapsed = int((time.perf_counter() - t0) * 1000)

            trace.add_step(
                Step(
                    kind="llm",
                    text=resp.text,
                    usage={
                        "input_tokens": resp.usage.input_tokens,
                        "output_tokens": resp.usage.output_tokens,
                    },
                    tool_calls=[c.model_dump() for c in resp.tool_calls],
                    duration_ms=elapsed,
                )
            )

            # 没有工具调用 = 模型认为任务结束了
            if not resp.tool_calls:
                answer = resp.text
                status = "done"
                break

            # 把模型的"调用申请"写回对话历史（格式必须严格）
            messages.append(
                {
                    "role": "assistant",
                    "content": resp.text or "",
                    "tool_calls": [
                        {
                            "id": c.id,
                            "type": "function",
                            "function": {
                                "name": c.name,
                                "arguments": json.dumps(c.arguments, ensure_ascii=False),
                            },
                        }
                        for c in resp.tool_calls
                    ],
                }
            )

            # 执行工具：并发跑，但结果按原顺序回填
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_TOOLS)
            async def _run_one(call: ToolCall) -> str:
                async with semaphore:
                    t1 = time.perf_counter()
                    output = await _exec_tool(call, tool_map)
                    tool_elapsed = int((time.perf_counter() - t1) * 1000)
                    trace.add_step(
                        Step(
                            kind="tool",
                            name=call.name,
                            arguments=call.arguments,
                            output=output,
                            error=call.parse_error,
                            duration_ms=tool_elapsed,
                        )
                    )
                    return output

            outputs = await asyncio.gather(
                *[_run_one(c) for c in resp.tool_calls]
            )

            for call, output in zip(resp.tool_calls, outputs):
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": output,
                    }
                )

    except Exception as exc:
        status = f"error: {type(exc).__name__}"
        answer = f"运行出错：{exc}"

    trace.finish(status)
    return {
        "answer": answer,
        "status": status,
        "run_id": trace.run_id,
        "total_tokens": trace.total_tokens,
        "n_steps": len(trace.steps),
        "trace": trace,
    }
"""命令行跑一个任务，并把每一步打出来。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agentrt.runtime.loop import run_task


def show(trace) -> None:
    for step in trace.steps:
        tok = f"{step.input_tokens}->{step.output_tokens}" if step.kind == "llm" else ""
        print(f"[{step.idx:02d}] {step.kind:4s} {step.name:10s} {step.duration_ms:>5d}ms {tok}")
        if step.kind == "llm" and step.text:
            print(f"     说: {step.text[:120]}")
        if step.kind == "llm" and step.tool_calls:
            for c in step.tool_calls:
                print(f"     要调用: {c['name']}({c['arguments']})")
        if step.kind == "tool":
            preview = step.output.replace("\n", " ")[:120]
            print(f"     结果: {preview}")


async def main() -> None:
    task = " ".join(sys.argv[1:]).strip() or "列出当前目录有哪些文件"
    print(f"任务: {task}\n{'-' * 60}")

    result = await run_task(task)

    show(result["trace"])
    print("-" * 60)
    print(f"状态: {result['status']}")
    print(f"步数: {result['n_steps']}  token: {result['total_tokens']}")
    print(f"回答: {result['answer']}")
    print(f"run_id: {result['run_id']}")


if __name__ == "__main__":
    asyncio.run(main())

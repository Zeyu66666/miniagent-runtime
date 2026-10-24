import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agentrt.runtime.loop import run_task


async def main() -> None:
    task = (
        "同时读取 pyproject.toml、README.md、.gitignore 三个文件，"
        "然后用一句话总结这个项目是做什么的。"
    )
    t0 = time.perf_counter()
    result = await run_task(task)
    print(f"总耗时 {time.perf_counter() - t0:.2f}s")
    for step in result["trace"].steps:
        print(f"[{step.idx:02d}] {step.kind:4s} {step.name:10s} {step.duration_ms}ms")


if __name__ == "__main__":
    asyncio.run(main())
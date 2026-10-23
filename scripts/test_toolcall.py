import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agentrt.providers import get_provider
from agentrt.tools.builtin import ALL_TOOLS


async def main() -> None:
    provider = get_provider()
    resp = await provider.chat(
        messages=[{"role": "user", "content": "当前目录下有哪些文件？"}],
        tools=[t.schema() for t in ALL_TOOLS],
    )
    print("text =", repr(resp.text))
    print("stop_reason =", resp.stop_reason)
    for call in resp.tool_calls:
        print(f"模型想调用 {call.name}，参数 = {call.arguments}")
        print(f"  解析错误 = {call.parse_error}")


if __name__ == "__main__":
    asyncio.run(main())
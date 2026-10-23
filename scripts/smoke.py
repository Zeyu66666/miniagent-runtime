"""最小验证：能不能跟模型说上一句话。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agentrt.providers import get_provider


async def main() -> None:
    provider = get_provider()
    print(f"provider = {provider.name} / model = {provider.model}")

    try:
        resp = await provider.chat(
            [{"role": "user", "content": "用一句话解释什么是 HTTP"}]
        )
        print("-" * 50)
        print("模型回复：", resp.text)
        print("stop_reason：", resp.stop_reason)
        print(f"token：输入 {resp.usage.input_tokens} / 输出 {resp.usage.output_tokens}")
        print("-" * 50)
    except Exception as e:
        print(f"调用失败，错误类型: {type(e).__name__}")
        print(f"错误详情: {e}")


if __name__ == "__main__":
    asyncio.run(main())
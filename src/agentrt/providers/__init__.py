"""provider 工厂：根据配置创建一个 provider 实例。"""
from ..config import API_KEY, BASE_URL, MODEL
from .base import BaseProvider, LLMResponse, ToolCall, Usage
from .openai_compat import OpenAICompatProvider
from .retry import RetryingProvider
__all__ = [
    "BaseProvider",
    "LLMResponse",
    "ToolCall",
    "Usage",
    "OpenAICompatProvider",
    "get_provider",
    "RetryingProvider",
]


def get_provider(name: str | None = None) -> BaseProvider:
    if not API_KEY:
        raise SystemExit(
            "没有读到 DEEPSEEK_API_KEY。\n"
            "请确认项目根目录有 .env 文件，且里面写了 DEEPSEEK_API_KEY=sk-xxx"
        )

    base = OpenAICompatProvider(
        model=MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        name="deepseek",
    )
    return RetryingProvider(base, max_attempts=3, base_delay=1.0, timeout=120.0)
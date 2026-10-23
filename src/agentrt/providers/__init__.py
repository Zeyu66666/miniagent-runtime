"""provider 工厂：根据配置创建一个 provider 实例。"""
from ..config import API_KEY, BASE_URL, MODEL
from .base import BaseProvider, LLMResponse, ToolCall, Usage
from .openai_compat import OpenAICompatProvider

__all__ = [
    "BaseProvider",
    "LLMResponse",
    "ToolCall",
    "Usage",
    "OpenAICompatProvider",
    "get_provider",
]


def get_provider(name: str | None = None) -> BaseProvider:
    """目前只有 DeepSeek 一条路径，将来加 Anthropic 就在这里分支。"""
    if not API_KEY:
        raise SystemExit(
            "没有读到 DEEPSEEK_API_KEY。\n"
            "请确认项目根目录有 .env 文件，且里面写了 DEEPSEEK_API_KEY=sk-xxx"
        )
    return OpenAICompatProvider(
        model=MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        name="deepseek",
    )
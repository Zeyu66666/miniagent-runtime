"""给任意 provider 套一层重试。

只重试"重试有用"的错误。参数错误、鉴权错误必须立刻抛出，
否则会白白烧钱。
"""
import asyncio

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

from .base import BaseProvider, LLMResponse

RETRYABLE = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)


class RetryingProvider(BaseProvider):
    def __init__(
        self,
        inner: BaseProvider,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        timeout: float = 120.0,
    ) -> None:
        self.inner = inner
        self.name = f"{inner.name}+retry"
        self.model = inner.model
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.timeout = timeout

    async def aclose(self) -> None:
        """包装器不自己持有连接，关的是内层。"""
        close = getattr(self.inner, "aclose", None)
        if close is not None:
            await close()

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        delay = self.base_delay

        for attempt in range(1, self.max_attempts + 1):
            try:
                return await asyncio.wait_for(
                    self.inner.chat(messages, tools=tools, temperature=temperature),
                    timeout=self.timeout,
                )
            except RETRYABLE as exc:
                if attempt == self.max_attempts:
                    raise
                print(
                    f"[retry] 第 {attempt} 次失败（{type(exc).__name__}），"
                    f"{delay:.1f}s 后重试"
                )
                await asyncio.sleep(delay)
                delay *= 2  # 指数退避：1s → 2s → 4s

        raise RuntimeError("unreachable")
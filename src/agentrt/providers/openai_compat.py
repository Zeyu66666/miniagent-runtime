import json

from openai import AsyncOpenAI

from .base import BaseProvider, LLMResponse, ToolCall, Usage


def _parse_arguments(raw: str | None) -> tuple[dict, str | None]:
    """把模型返回的参数字符串解析成 dict。

    模型有概率返回非法 JSON，这里不能直接崩，要把错误变成可读信息。
    """
    raw = raw or "{}"
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {}, f"参数不是合法 JSON: {exc} | 原始内容: {raw[:300]}"
    if not isinstance(value, dict):
        return {}, f"参数必须是 JSON 对象，收到的是 {type(value).__name__}"
    return value, None


class OpenAICompatProvider(BaseProvider):
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        name: str = "openai-compat",
    ) -> None:
        if not api_key:
            raise ValueError("缺少 API key，请检查 .env 里的 DEEPSEEK_API_KEY")
        self.name = name
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def aclose(self) -> None:
        """关掉底层 httpx 连接池。进程活着但 client 不关，句柄只增不减。"""
        await self.client.close()

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools

        resp = await self.client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message

        tool_calls: list[ToolCall] = []
        for call in msg.tool_calls or []:
            args, err = _parse_arguments(call.function.arguments)
            tool_calls.append(
                ToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments=args,
                    parse_error=err,
                )
            )

        usage = Usage(
            input_tokens=getattr(resp.usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(resp.usage, "completion_tokens", 0) or 0,
        )

        return LLMResponse(
            text=msg.content or "",
            tool_calls=tool_calls,
            usage=usage,
            stop_reason=choice.finish_reason or "",
        )
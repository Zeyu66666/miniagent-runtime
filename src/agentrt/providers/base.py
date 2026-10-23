"""所有 provider 的统一接口。

业务代码只认这里的类型，不认任何厂商 SDK。
换模型厂商 = 新加一个子类，其他代码一行不改。
"""
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """模型请求调用的一次工具。"""
    id: str
    name: str
    arguments: dict = Field(default_factory=dict)
    # 模型有时候会返回非法的 JSON 字符串，这里记下错误原因，
    # 由主循环把它当成工具错误回灌给模型，让它自己修正。
    parse_error: str | None = None


class Usage(BaseModel):
    """openai / anthropic 返回的 usage 字段格式不同，统一成这个。"""
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMResponse(BaseModel):
    """统一后的模型回复。要么有 text，要么有 tool_calls，要么都有。"""
    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    stop_reason: str = ""


class BaseProvider(ABC):
    """所有厂商适配器的父类。"""

    name: str = "base"
    model: str = ""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """发一轮对话，返回统一后的响应。"""
        raise NotImplementedError
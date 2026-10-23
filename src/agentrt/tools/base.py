from abc import ABC, abstractmethod

from pydantic import BaseModel


def truncate_text(text: str, limit: int = 6000) -> str:
    """把过长的文本截断成"头 + 提示 + 尾"。

    为什么留尾巴：文件末尾常常是结论、错误信息、返回码。
    """
    if len(text) <= limit:
        return text
    head_len = limit * 3 // 5
    tail_len = limit - head_len
    omitted = len(text) - limit
    return (
        text[:head_len]
        + f"\n\n...[中间省略 {omitted} 个字符]...\n\n"
        + text[-tail_len:]
    )


class Tool(ABC):
    name: str = ""
    description: str = ""
    args_model: type[BaseModel] = BaseModel

    def schema(self) -> dict:
        """生成 OpenAI 格式的工具描述。"""
        params = self.args_model.model_json_schema()
        params.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": params,
            },
        }

    def validate(self, raw: dict) -> BaseModel:
        """用 pydantic 校验模型给的参数。不合法会抛异常，由主循环捕获。"""
        return self.args_model(**raw)

    @abstractmethod
    async def run(self, **kwargs) -> str:
        """真正干活的地方。返回值必须是字符串，且要自己控制长度。"""
        raise NotImplementedError
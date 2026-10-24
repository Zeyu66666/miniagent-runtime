import json
import time
import uuid


class Step:
    """一次模型调用或一次工具调用。"""

    def __init__(
        self,
        kind: str,
        name: str = "",
        text: str = "",
        arguments: dict | None = None,
        output: str = "",
        usage: dict | None = None,
        tool_calls: list[dict] | None = None,
        error: str | None = None,
        duration_ms: int = 0,
    ) -> None:
        self.idx = 0
        self.kind = kind                # "llm" | "tool" | "error"
        self.name = name
        self.text = text
        self.arguments = arguments or {}
        self.output = output
        self.usage = usage or {}
        self.tool_calls = tool_calls or []
        self.error = error
        self.duration_ms = duration_ms
        self.ts = time.time()

    @property
    def input_tokens(self) -> int:
        return int(self.usage.get("input_tokens", 0))

    @property
    def output_tokens(self) -> int:
        return int(self.usage.get("output_tokens", 0))

    def to_dict(self) -> dict:
        return {
            "idx": self.idx,
            "kind": self.kind,
            "name": self.name,
            "text": self.text,
            "arguments": self.arguments,
            "output": self.output,
            "usage": self.usage,
            "tool_calls": self.tool_calls,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "ts": self.ts,
        }


class Trace:
    """一次任务的完整记录。"""

    def __init__(self, task: str, provider: str = "", model: str = "") -> None:
        self.run_id = uuid.uuid4().hex[:12]
        self.task = task
        self.provider = provider
        self.model = model
        self.steps: list[Step] = []
        self.total_tokens = 0
        self.status = "running"
        self.started_at = time.time()
        self.ended_at: float | None = None

    def add_step(self, step: Step) -> None:
        step.idx = len(self.steps)
        self.steps.append(step)
        self.total_tokens += step.input_tokens + step.output_tokens

    def finish(self, status: str) -> None:
        self.status = status
        self.ended_at = time.time()

    @property
    def duration_ms(self) -> int:
        end = self.ended_at or time.time()
        return int((end - self.started_at) * 1000)

    def to_json(self) -> str:
        return json.dumps(
            {
                "run_id": self.run_id,
                "task": self.task,
                "provider": self.provider,
                "model": self.model,
                "status": self.status,
                "total_tokens": self.total_tokens,
                "steps": [s.to_dict() for s in self.steps],
            },
            ensure_ascii=False,
            indent=2,
        )
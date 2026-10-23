import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from .base import Tool, truncate_text
"""内置工具。刻意只做三个：读文件、列目录、跑命令。"""

def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p


# ---------------------------------------------------------------- read_file
class ReadFileArgs(BaseModel):
    path: str = Field(description="要读取的文件路径，可以是相对路径或绝对路径")
    max_chars: int = Field(default=4000, description="最多返回多少个字符，默认 4000")


class ReadFileTool(Tool):
    name = "read_file"
    description = (
        "读取一个文本文件的内容。"
        "当需要知道某个文件里写了什么（代码、配置、日志）时使用。"
        "文件很长时只会返回开头和结尾。"
    )
    args_model = ReadFileArgs

    async def run(self, path: str, max_chars: int = 4000) -> str:
        p = _resolve(path)
        if not p.exists():
            raise FileNotFoundError(f"文件不存在：{path}")
        if p.is_dir():
            raise IsADirectoryError(f"{path} 是一个目录，请用 list_dir 工具")
        text = p.read_text(encoding="utf-8", errors="replace")
        return truncate_text(text, max_chars)


# ---------------------------------------------------------------- list_dir
class ListDirArgs(BaseModel):
    path: str = Field(default=".", description="目录路径，默认当前目录")


class ListDirTool(Tool):
    name = "list_dir"
    description = "列出一个目录下有哪些文件和子目录。不知道文件在哪时先用它。"
    args_model = ListDirArgs

    async def run(self, path: str = ".") -> str:
        p = _resolve(path)
        if not p.exists():
            raise FileNotFoundError(f"目录不存在：{path}")
        if not p.is_dir():
            raise NotADirectoryError(f"{path} 不是目录")
        entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
        lines = []
        for e in entries[:120]:
            if e.name.startswith(".") or e.name in {"__pycache__", "node_modules", ".venv"}:
                continue
            kind = "DIR " if e.is_dir() else "FILE"
            size = "" if e.is_dir() else f"  {e.stat().st_size} bytes"
            lines.append(f"{kind}  {e.name}{size}")
        if not lines:
            return "这个目录是空的（或只有隐藏文件）"
        return "\n".join(lines)


# ---------------------------------------------------------------- run_cmd
class RunCmdArgs(BaseModel):
    command: str = Field(description="要执行的命令行指令，例如 `python --version`")
    timeout: int = Field(default=10, description="超时秒数，默认 10")


class RunCmdTool(Tool):
    name = "run_cmd"
    description = (
        "执行一条 shell 命令并返回输出与退出码。"
        "用于查看环境信息、运行测试、统计行数等。"
        "不要用它修改文件内容。"
    )
    args_model = RunCmdArgs

    async def run(self, command: str, timeout: int = 10) -> str:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise TimeoutError(f"命令执行超过 {timeout} 秒，已被强制终止：{command}")
        text = out.decode("utf-8", errors="replace")
        return f"exit_code={proc.returncode}\n{truncate_text(text)}"


ALL_TOOLS: list[Tool] = [ReadFileTool(), ListDirTool(), RunCmdTool()]
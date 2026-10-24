"""命令行入口。安装后可直接使用 agentrt 命令。"""
import asyncio
import time

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .runtime.loop import run_task
from .runtime.trace import get_run, list_runs

app = typer.Typer(
    help="miniagent-runtime —— 可观测、可评测的 Agent 运行时",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _short(text: str, n: int = 90) -> str:
    text = (text or "").replace("\n", " ⏎ ")
    return text if len(text) <= n else text[:n] + "…"


def _render_trace(trace) -> None:
    table = Table(box=box.SIMPLE_HEAD, pad_edge=False)
    table.add_column("#", width=3, justify="right", style="dim")
    table.add_column("类型", width=5)
    table.add_column("名称", width=12)
    table.add_column("耗时", width=7, justify="right")
    table.add_column("token", width=11, justify="right")
    table.add_column("内容", overflow="fold")

    for step in trace.steps:
        if step.kind == "llm":
            kind = Text("LLM", style="bold cyan")
            tokens = f"{step.input_tokens}→{step.output_tokens}"
            if step.tool_calls:
                body = "调用 " + ", ".join(
                    f"{c['name']}({_short(str(c['arguments']), 60)})"
                    for c in step.tool_calls
                )
            else:
                body = step.text or "(空)"
        else:
            kind = Text("TOOL", style="bold green")
            tokens = "—"
            body = step.output or "(无输出)"
            if (step.output or "").startswith("ERROR"):
                kind = Text("TOOL", style="bold red")

        table.add_row(
            str(step.idx),
            kind,
            step.name or "—",
            f"{step.duration_ms}ms",
            tokens,
            _short(body),
        )

    console.print(table)


@app.command()
def run(
    task: str = typer.Argument(..., help="要交给 agent 的任务"),
    max_steps: int = typer.Option(15, "--max-steps", "-m"),
    budget: int = typer.Option(80_000, "--budget", "-b", help="token 预算上限"),
):
    """执行一个任务并打印执行时间线。"""
    t0 = time.perf_counter()
    with console.status("[bold cyan]agent 正在工作…"):
        result = asyncio.run(
            run_task(task, max_steps=max_steps, token_budget=budget)
        )
    wall = time.perf_counter() - t0

    console.print()
    _render_trace(result["trace"])
    console.print()

    status = result["status"]
    color = "green" if status == "done" else "yellow"
    console.print(
        Panel(
            f"[bold]{result['answer'] or '（没有最终回答）'}[/bold]",
            title=f"[{color}]答案[/{color}]",
            subtitle=(
                f"status={status}  步数={result['n_steps']}  "
                f"token={result['total_tokens']}  墙钟={wall:.1f}s  "
                f"run_id={result['run_id']}"
            ),
            border_style=color,
        )
    )


@app.command("ls")
def list_cmd(limit: int = typer.Option(20, "--limit", "-n")):
    """列出最近的任务。"""
    rows = list_runs(limit)
    if not rows:
        console.print("[dim]还没有任何记录[/dim]")
        return

    table = Table(box=box.SIMPLE_HEAD)
    table.add_column("run_id", style="cyan", width=14)
    table.add_column("状态", width=10)
    table.add_column("步数", justify="right", width=5)
    table.add_column("token", justify="right", width=8)
    table.add_column("耗时", justify="right", width=8)
    table.add_column("任务", overflow="fold")

    for r in rows:
        color = "green" if r["status"] == "done" else "yellow"
        table.add_row(
            r["id"],
            f"[{color}]{r['status']}[/{color}]",
            str(r["n_steps"]),
            str(r["total_tokens"]),
            f"{(r['duration_ms'] or 0) / 1000:.1f}s",
            _short(r["task"], 60),
        )
    console.print(table)


@app.command()
def show(run_id: str = typer.Argument(..., help="run_id，可用 agentrt ls 查")):
    """查看某次执行的完整时间线。"""
    run = get_run(run_id)
    if run is None:
        console.print(f"[red]找不到 run: {run_id}[/red]")
        raise typer.Exit(1)

    console.print(
        Panel(
            _short(run["task"], 200),
            title=f"[cyan]{run['id']}[/cyan]",
            subtitle=(
                f"{run['status']}  token={run['total_tokens']}  "
                f"{run['duration_ms'] / 1000:.1f}s"
            ),
            border_style="cyan",
        )
    )

    for step in run["steps"]:
        p = step["payload"]
        if step["kind"] == "llm":
            title = f"[cyan]LLM[/cyan] {p.get('usage', {})}"
        else:
            title = f"[green]{step['name']}[/green]"

        body_parts = []
        if p.get("text"):
            body_parts.append(f"[dim]text[/dim]\n{p['text']}")
        if p.get("arguments"):
            body_parts.append(f"[dim]args[/dim]\n{p['arguments']}")
        if p.get("output"):
            body_parts.append(f"[dim]output[/dim]\n{p['output']}")

        console.print(
            Panel(
                "\n\n".join(body_parts) or "[dim]（空）[/dim]",
                title=f"[dim]{step['idx']:02d}[/dim] {title}",
                border_style="bright_black",
            )
        )


@app.command()
def version():
    """版本号。"""
    console.print("miniagent-runtime 0.1.0")

@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port", "-p"),
):
    """启动 Web 面板后端。"""
    import uvicorn

    from .server.app import app as fastapi_app

    console.print(f"[cyan]后端启动中：http://{host}:{port}/docs[/cyan]")
    uvicorn.run(fastapi_app, host=host, port=port)


if __name__ == "__main__":
    app()
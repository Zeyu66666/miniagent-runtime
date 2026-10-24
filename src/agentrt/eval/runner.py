"""评测执行器：读 yaml，并发跑任务，判分，出报告。"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import yaml
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..providers import get_provider
from ..runtime.loop import run_task
from .checkers import check
from .reset_workspace import reset

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent      # 仓库根目录
TASKS_FILE = ROOT / "eval" / "tasks.yaml"
WORKSPACE = ROOT / "eval" / "workspace"
REPORTS = ROOT / "eval" / "reports"

console = Console()
CONCURRENCY = 3   # 同时跑几条任务；太高会被限流


async def run_one(spec: dict, sem: asyncio.Semaphore, provider=None) -> dict:
    async with sem:
        started = time.time()
        try:
            result = await run_task(
                spec["task"],
                provider=provider,          # 40 条共用一个 client，别每条新建
                max_steps=int(spec.get("max_steps", 15)),
            )
        except Exception as exc:                      # noqa: BLE001
            return {
                "id": spec["id"],
                "task": spec["task"],
                "passed": False,
                "reason": f"异常：{type(exc).__name__}: {exc}",
                "tokens": 0,
                "steps": 0,
                "duration_s": round(time.time() - started, 2),
                "run_id": None,
            }

        passed, reason = check(spec["check"], result, WORKSPACE)
        return {
            "id": spec["id"],
            "task": spec["task"],
            "passed": passed,
            "reason": reason,
            "tokens": int(result.get("total_tokens", 0)),
            "steps": int(result.get("n_steps", 0)),
            "status": result.get("status", ""),
            "duration_s": round(time.time() - started, 2),
            "run_id": result.get("run_id"),
        }


async def run_all(tasks_file: Path = TASKS_FILE, concurrency: int = CONCURRENCY) -> dict:
    specs = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))
    console.print(f"[cyan]加载 {len(specs)} 条任务[/cyan]")

    sem = asyncio.Semaphore(concurrency)
    results: list[dict] = []

    # 任务描述里的相对路径（notes.txt 等）都相对 eval/workspace
    prev_cwd = Path.cwd()
    os.chdir(WORKSPACE)
    provider = get_provider()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        bar = progress.add_task("运行评测", total=len(specs))

        async def wrapped(spec: dict) -> dict:
            r = await run_one(spec, sem, provider)
            results.append(r)
            mark = "[green]PASS[/green]" if r["passed"] else "[red]FAIL[/red]"
            progress.console.print(f"  {r['id']:>4} {mark} {r['task'][:40]}")
            progress.advance(bar)
            return r

        try:
            await asyncio.gather(*(wrapped(s) for s in specs))
        finally:
            await provider.aclose()
            os.chdir(prev_cwd)

    return build_report(results, specs)


def build_report(results: list[dict], specs: list[dict]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    tokens = [r["tokens"] for r in results if r["tokens"] > 0]
    steps = [r["steps"] for r in results]

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "passed": passed,
        "success_rate": round(passed / total, 4) if total else 0.0,
        "avg_tokens": round(sum(tokens) / len(tokens)) if tokens else 0,
        "avg_steps": round(sum(steps) / len(steps), 2) if steps else 0,
        "results": sorted(results, key=lambda r: r["id"]),
    }
    return report


def save_report(report: dict, tag: str = "auto") -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    json_path = REPORTS / f"{stamp}-{tag}.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = REPORTS / f"{stamp}-{tag}.md"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return md_path


def render_markdown(report: dict) -> str:
    lines = [
        f"# 评测报告 · {report['timestamp']}",
        "",
        f"- 任务数：**{report['total']}**",
        f"- 通过：**{report['passed']}**",
        f"- 成功率：**{report['success_rate'] * 100:.1f}%**",
        f"- 平均 input token：**{report['avg_tokens']}**",
        f"- 平均步数：**{report['avg_steps']}**",
        "",
        "## 失败清单",
        "",
    ]
    failed = [r for r in report["results"] if not r["passed"]]
    if not failed:
        lines.append("全部通过。")
    else:
        lines += ["| id | 任务 | 原因 |", "|---|---|---|"]
        for r in failed:
            reason = r["reason"].replace("|", "\\|")[:120]
            task = r["task"].replace("|", "\\|")[:40]
            lines.append(f"| {r['id']} | {task} | {reason} |")

    lines += ["", "## 全量结果", "", "| id | 结果 | 步数 | token | 耗时 | 原因 |", "|---|---|---|---|---|---|"]
    for r in report["results"]:
        mark = "PASS" if r["passed"] else "FAIL"
        reason = r["reason"].replace("|", "\\|")[:60]
        lines.append(
            f"| {r['id']} | {mark} | {r['steps']} | {r['tokens']} | "
            f"{r['duration_s']}s | {reason} |"
        )
    return "\n".join(lines) + "\n"


def main(tag: str = "auto") -> None:
    reset()
    report = asyncio.run(run_all())

    console.rule("[bold]结果[/bold]")
    table = Table(show_header=True)
    table.add_column("指标")
    table.add_column("值", justify="right")
    table.add_row("任务数", str(report["total"]))
    table.add_row("通过", str(report["passed"]))
    table.add_row("成功率", f"{report['success_rate'] * 100:.1f}%")
    table.add_row("平均 token", str(report["avg_tokens"]))
    table.add_row("平均步数", str(report["avg_steps"]))
    console.print(table)

    failed = [r for r in report["results"] if not r["passed"]]
    if failed:
        console.print(f"\n[yellow]失败 {len(failed)} 条：[/yellow]")
        for r in failed:
            console.print(f"  [red]{r['id']}[/red] {r['reason'][:100]}")

    path = save_report(report, tag)
    console.print(f"\n[green]报告已保存：{path}[/green]")


if __name__ == "__main__":
    main()
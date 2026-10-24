import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agentrt.runtime.trace import get_run, list_runs

if len(sys.argv) == 1:
    rows = list_runs(20)
    print(f"{'run_id':14s} {'status':10s} {'steps':>5s} {'tokens':>7s}  task")
    for r in rows:
        print(
            f"{r['id']:14s} {r['status']:10s} {r['n_steps']:>5d} "
            f"{r['total_tokens']:>7d}  {r['task'][:50]}"
        )
else:
    run = get_run(sys.argv[1])
    if run is None:
        print("找不到这个 run")
        sys.exit(1)
    print(f"任务: {run['task']}")
    print(f"状态: {run['status']}  token: {run['total_tokens']}  耗时: {run['duration_ms']}ms")
    print("-" * 70)
    for step in run["steps"]:
        p = step["payload"]
        print(f"[{step['idx']:02d}] {step['kind']:4s} {step['name']:10s} {step['duration_ms']:>5d}ms")
        if p.get("text"):
            print(f"     text: {p['text'][:100]}")
        if p.get("arguments"):
            print(f"     args: {p['arguments']}")
        if p.get("output"):
            print(f"     out : {p['output'][:100].replace(chr(10), ' ')}")
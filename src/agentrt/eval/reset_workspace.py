"""把 workspace 重置到初始状态：删掉任务生成的文件。"""
import shutil
from pathlib import Path

# 本文件在 src/agentrt/eval/，往上三层是仓库根目录
ROOT = Path(__file__).resolve().parent.parent.parent.parent
WORKSPACE = ROOT / "eval" / "workspace"

# 任务可能生成的产物，跑下一轮前要清掉
GENERATED = [
    "summary.txt",
    "big.txt",
    "features.txt",
    "upper.txt",
    "backup",
]


def reset() -> None:
    for name in GENERATED:
        p = WORKSPACE / name
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()


if __name__ == "__main__":
    reset()
    print(f"workspace 已重置：{WORKSPACE}")
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agentrt.tools.builtin import ALL_TOOLS

for tool in ALL_TOOLS:
    print("=" * 60)
    print(json.dumps(tool.schema(), ensure_ascii=False, indent=2))
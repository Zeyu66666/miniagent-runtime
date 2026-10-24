import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agentrt.runtime.trace import connect

sql = sys.argv[1] if len(sys.argv) > 1 else "SELECT * FROM runs LIMIT 5"
conn = connect()
rows = conn.execute(sql).fetchall()
for row in rows:
    print(dict(row))
conn.close()
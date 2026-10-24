"""执行记录：内存模型 + SQLite 持久化。"""
import json
import sqlite3
import time
import uuid
from pathlib import Path

from ..config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id           TEXT PRIMARY KEY,
    task         TEXT NOT NULL,
    provider     TEXT,
    model        TEXT,
    status       TEXT,
    total_tokens INTEGER DEFAULT 0,
    n_steps      INTEGER DEFAULT 0,
    duration_ms  INTEGER DEFAULT 0,
    started_at   REAL,
    ended_at     REAL
);

CREATE TABLE IF NOT EXISTS steps (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT NOT NULL,
    idx           INTEGER NOT NULL,
    kind          TEXT NOT NULL,
    name          TEXT,
    payload       TEXT,
    input_tokens  INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    duration_ms   INTEGER DEFAULT 0,
    ts            REAL
);

CREATE INDEX IF NOT EXISTS idx_steps_run ON steps(run_id, idx);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at DESC);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


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
        self.kind = kind
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
        self.save()

    @property
    def duration_ms(self) -> int:
        end = self.ended_at or time.time()
        return int((end - self.started_at) * 1000)

    def save(self) -> None:
        conn = connect()
        try:
            with conn:
                conn.execute(
                    """INSERT OR REPLACE INTO runs
                    (id, task, provider, model, status, total_tokens, n_steps,
                        duration_ms, started_at, ended_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        self.run_id,
                        self.task,
                        self.provider,
                        self.model,
                        self.status,
                        self.total_tokens,
                        len(self.steps),
                        self.duration_ms,
                        self.started_at,
                        self.ended_at,
                    ),
                )
                conn.execute("DELETE FROM steps WHERE run_id = ?", (self.run_id,))
                conn.executemany(
                    """INSERT INTO steps
                    (run_id, idx, kind, name, payload,
                        input_tokens, output_tokens, duration_ms, ts)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    [
                        (
                            self.run_id,
                            s.idx,
                            s.kind,
                            s.name,
                            json.dumps(s.to_dict(), ensure_ascii=False),
                            s.input_tokens,
                            s.output_tokens,
                            s.duration_ms,
                            s.ts,
                        )
                        for s in self.steps
                    ],
                )
        finally:
            conn.close()

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


# ---------------------------------------------------------------- 查询接口
def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def list_runs(limit: int = 50) -> list[dict]:
    conn = connect()
    try:
        rows = conn.execute(
            """SELECT id, task, provider, model, status, total_tokens,
            n_steps, duration_ms, started_at, ended_at
            FROM runs ORDER BY started_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_run(run_id: str) -> dict | None:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        steps = conn.execute(
            "SELECT * FROM steps WHERE run_id = ? ORDER BY idx", (run_id,)
        ).fetchall()
        result = _row_to_dict(row)
        result["steps"] = []
        for s in steps:
            item = _row_to_dict(s)
            try:
                item["payload"] = json.loads(item["payload"] or "{}")
            except json.JSONDecodeError:
                pass
            result["steps"].append(item)
        return result
    finally:
        conn.close()
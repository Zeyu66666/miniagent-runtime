"""FastAPI 后端：只负责读数据库、吐 JSON。"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..runtime.trace import get_run, list_runs

app = FastAPI(title="miniagent-runtime", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/runs")
def api_runs(limit: int = 50) -> dict:
    return {"runs": list_runs(limit)}


@app.get("/api/runs/{run_id}")
def api_run(run_id: str) -> dict:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"找不到 run: {run_id}")
    return run
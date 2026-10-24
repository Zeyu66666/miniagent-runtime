import { useCallback, useEffect, useState } from "react";

type Run = {
  id: string;
  task: string;
  provider: string;
  model: string;
  status: string;
  total_tokens: number;
  n_steps: number;
  duration_ms: number;
  started_at: number;
  ended_at: number | null;
};

type Payload = {
  text?: string;
  arguments?: Record<string, unknown>;
  output?: string;
  usage?: { input_tokens?: number; output_tokens?: number };
  tool_calls?: Array<{ name: string; arguments: Record<string, unknown> }>;
  error?: string | null;
};

type Step = {
  idx: number;
  kind: string;
  name: string;
  payload: Payload;
  input_tokens: number;
  output_tokens: number;
  duration_ms: number;
};

type RunDetail = Run & { steps: Step[] };

function relTime(ts: number): string {
  const diff = Date.now() / 1000 - ts;
  if (diff < 60) return `${Math.floor(diff)} 秒前`;
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  return `${Math.floor(diff / 86400)} 天前`;
}

function isErrorStep(step: Step): boolean {
  return (step.payload.output ?? "").startsWith("ERROR") || !!step.payload.error;
}

function Block({ label, text }: { label: string; text: string }) {
  if (!text) return null;
  return (
    <div>
      <div className="block-label">{label}</div>
      <pre>{text}</pre>
    </div>
  );
}

function StepCard({ step }: { step: Step }) {
  const [open, setOpen] = useState(false);
  const p = step.payload;
  const err = isErrorStep(step);
  const cls = err ? "error" : step.kind;

  let preview = p.text ?? "";
  if (step.kind === "tool") preview = p.output ?? "";
  if (p.tool_calls && p.tool_calls.length > 0) {
    preview =
      "调用 " +
      p.tool_calls
        .map((c) => `${c.name}(${JSON.stringify(c.arguments)})`)
        .join(", ");
  }

  return (
    <div className={`step ${cls}`}>
      <div className="step-head" onClick={() => setOpen(!open)}>
        <span className="idx">{String(step.idx).padStart(2, "0")}</span>
        <span className={`kind ${cls}`}>
          {step.kind === "llm" ? "LLM" : "TOOL"}
        </span>
        <span className="name">{step.name || "—"}</span>
        <span className="spacer" />
        <span className="dur">
          {step.input_tokens + step.output_tokens > 0
            ? `${step.input_tokens}→${step.output_tokens} tok · `
            : ""}
          {step.duration_ms}ms
        </span>
      </div>

      {!open && preview && <div className="preview">{preview}</div>}

      {open && (
        <div className="step-body">
          <Block label="text" text={p.text ?? ""} />
          <Block
            label="arguments"
            text={p.arguments ? JSON.stringify(p.arguments, null, 2) : ""}
          />
          <Block label="output" text={p.output ?? ""} />
          {p.usage && (
            <Block label="usage" text={JSON.stringify(p.usage, null, 2)} />
          )}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/runs?limit=100");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRuns(data.runs ?? []);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const openRun = useCallback(async (id: string) => {
    try {
      const res = await fetch(`/api/runs/${id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDetail(await res.json());
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-head">
          <div className="brand">
            miniagent<span>-runtime</span>
          </div>
          <button onClick={loadRuns}>{loading ? "刷新中…" : "刷新"}</button>
        </div>

        <div className="run-list">
          {error && (
            <div className="empty" style={{ height: 160 }}>
              <div>加载失败：{error}</div>
              <div style={{ fontSize: 12 }}>后端启动了吗？agentrt serve</div>
            </div>
          )}

          {!error && runs.length === 0 && (
            <div className="empty" style={{ height: 160 }}>
              <div>还没有执行记录</div>
              <div style={{ fontSize: 12 }}>
                先跑一次 agentrt run "..."
              </div>
            </div>
          )}

          {runs.map((r) => (
            <div
              key={r.id}
              className={`run-item ${detail?.id === r.id ? "active" : ""}`}
              onClick={() => openRun(r.id)}
            >
              <div className="run-task">{r.task}</div>
              <div className="run-meta">
                <span className={r.status === "done" ? "status done" : "status failed"}>
                  {r.status}
                </span>
                <span>{r.n_steps} 步</span>
                <span>{r.total_tokens} tok</span>
                <span>{relTime(r.started_at)}</span>
              </div>
            </div>
          ))}
        </div>
      </aside>

      <main className="detail">
        {!detail && (
          <div className="empty">
            <div>选择左侧任意一条任务</div>
            <div style={{ fontSize: 12 }}>查看它的完整执行时间线</div>
          </div>
        )}

        {detail && (
          <>
            <div className="detail-head">
              <h2>{detail.task}</h2>
              <div className="metrics">
                <span>
                  状态 <b>{detail.status}</b>
                </span>
                <span>
                  步数 <b>{detail.n_steps}</b>
                </span>
                <span>
                  token <b>{detail.total_tokens}</b>
                </span>
                <span>
                  耗时 <b>{(detail.duration_ms / 1000).toFixed(1)}s</b>
                </span>
                <span>
                  模型 <b>{detail.model || detail.provider}</b>
                </span>
                <span style={{ color: "#4b5563" }}>{detail.id}</span>
              </div>
            </div>

            <div className="timeline">
              {detail.steps.map((s) => (
                <StepCard key={s.idx} step={s} />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
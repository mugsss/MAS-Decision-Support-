import { useState } from "react";

export default function ApprovalPanel({ actions, onResolve }) {
  const [busy, setBusy] = useState(null);

  const handle = async (id, verb) => {
    setBusy(id);
    try {
      await onResolve(id, verb);
    } finally {
      setBusy(null);
    }
  };

  if (!actions.length) {
    return (
      <p className="hint">
        No actions awaiting approval. Every write is intercepted here before it
        touches data.
      </p>
    );
  }

  return (
    <div>
      {actions.map((a) => (
        <div className="action" key={a.action_id}>
          <div className="action-name">{a.tool_name}</div>
          <dl className="action-args">
            {Object.entries(a.args ?? {}).map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{String(v)}</dd>
              </div>
            ))}
          </dl>
          <div className="action-row">
            <button
              disabled={busy === a.action_id}
              onClick={() => handle(a.action_id, "approve")}
            >
              {busy === a.action_id ? "…" : "Approve"}
            </button>
            <button
              className="reject"
              disabled={busy === a.action_id}
              onClick={() => handle(a.action_id, "reject")}
            >
              Reject
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

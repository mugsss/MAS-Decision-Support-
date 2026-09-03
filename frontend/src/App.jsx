import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import Message from "./components/Message.jsx";
import ApprovalPanel from "./components/ApprovalPanel.jsx";
import Examples from "./components/Examples.jsx";

const CONVERSATION_ID = `ui-${Math.random().toString(36).slice(2, 10)}`;

const GREETING = {
  role: "bot",
  text:
    "Ask about vehicle configurations, integration logs, fleet analytics, or " +
    "automotive standards. The coordinator routes each question to the right " +
    "specialist and shows you which one answered.\n\n" +
    "Write actions are never executed directly — they appear in the approval " +
    "panel first.",
};

export default function App() {
  const [messages, setMessages] = useState([GREETING]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [actions, setActions] = useState([]);
  const [health, setHealth] = useState(null);
  const logRef = useRef(null);
  const inputRef = useRef(null);

  const refreshActions = useCallback(async () => {
    try {
      const d = await api.pendingActions();
      setActions(d.actions ?? []);
    } catch {
      /* backend may still be starting */
    }
  }, []);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    refreshActions();
  }, [refreshActions]);

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const send = async (text) => {
    const question = text.trim();
    if (!question || sending) return;

    setMessages((m) => [
      ...m,
      { role: "user", text: question },
      { role: "bot", pending: true },
    ]);
    setInput("");
    setSending(true);

    try {
      const d = await api.chat(question, CONVERSATION_ID);
      setMessages((m) => [
        ...m.slice(0, -1),
        {
          role: "bot",
          text: d.response,
          agents: d.agents_used ?? [],
          skills: d.skills_used ?? [],
          blocked: d.blocked,
          toolCalls: d.tool_calls ?? [],
          durationSeconds: d.duration_seconds,
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m.slice(0, -1),
        { role: "bot", text: `Request failed — ${err.message}`, error: true },
      ]);
    } finally {
      setSending(false);
      refreshActions();
      inputRef.current?.focus();
    }
  };

  const resolveAction = async (id, verb) => {
    try {
      const d = verb === "approve" ? await api.approve(id) : await api.reject(id);
      setMessages((m) => [
        ...m,
        {
          role: "bot",
          text:
            verb === "approve"
              ? `**Action approved and executed.**\n\n${d.result ?? ""}`
              : "**Action rejected.** Nothing was written.",
          agents: [verb === "approve" ? "executed" : "rejected"],
          skills: verb === "approve" ? ["executed"] : [],
          blocked: verb === "reject",
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "bot", text: `Could not ${verb} — ${err.message}`, error: true },
      ]);
    }
    refreshActions();
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  return (
    <div className="app">
      <header>
        <span className={`dot${health ? " on" : ""}`} />
        <h1>Automotive MAS — Decision Support</h1>
        <span className="status">
          {health
            ? `${health.agents.length} agents ready${
                health.mcp_server ? " · MCP connected" : ""
              }`
            : "backend unreachable"}
        </span>
      </header>

      <div className="body">
        <main>
          <div className="log" ref={logRef}>
            {messages.map((m, i) => (
              <Message key={i} msg={m} />
            ))}
          </div>

          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              placeholder="Ask about vehicles, ECUs, defects, logs, or AUTOSAR / ASPICE / ASIL…"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
            />
            <button type="submit" disabled={sending || !input.trim()}>
              {sending ? "…" : "Send"}
            </button>
          </form>
        </main>

        <aside>
          <h2>Pending approval</h2>
          <ApprovalPanel actions={actions} onResolve={resolveAction} />

          <h2 className="spaced">Try asking</h2>
          <p className="hint">Each routes to a different specialist.</p>
          <Examples onPick={(t) => setInput(t)} disabled={sending} />
        </aside>
      </div>
    </div>
  );
}

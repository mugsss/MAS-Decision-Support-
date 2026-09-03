import Markdown from "./Markdown.jsx";

/** Labels the raw tool names the coordinator reports back. */
const AGENT_LABELS = {
  niki: "PDM (Niki)",
  logs_agent: "Logs",
  text2sql_agent: "Fleet SQL",
  code_assist_agent: "Standards RAG",
  create_defect: "create_defect",
  flag_log_entry: "flag_log_entry",
  update_sw_version: "update_sw_version",
};

export default function Message({ msg }) {
  const { role, text, agents = [], skills = [], blocked, pending, error } = msg;

  if (role === "user") {
    return (
      <div className="msg user">
        <div className="bubble">{text}</div>
      </div>
    );
  }

  return (
    <div className="msg bot">
      <div className={`bubble${error ? " error" : ""}`}>
        {pending ? (
          <span className="thinking">
            <span className="spinner" /> routing to specialists…
          </span>
        ) : (
          <Markdown text={text} />
        )}
      </div>

      {!pending && (blocked || agents.length > 0) && (
        <div className="meta">
          {blocked && <span className="tag blocked">blocked by guardrail</span>}
          {agents.map((a) => (
            <span
              key={a}
              className={`tag${skills.includes(a) ? " skill" : ""}`}
              title={skills.includes(a) ? "Skill (composed capability)" : "Specialist agent"}
            >
              {AGENT_LABELS[a] ?? a}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

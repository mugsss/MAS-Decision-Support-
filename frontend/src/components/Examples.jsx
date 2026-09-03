const EXAMPLES = [
  ["How many critical defects are open?", "Fleet SQL — Text2SQL over SQLite"],
  ["Show me the ECU assignments for VIN-0001-TEST", "PDM (Niki) — via MCP server"],
  ["What are the most frequent DTC codes in the logs?", "Logs — JSONL pattern analysis"],
  ["What is ASIL D and how does ASIL decomposition work?", "Standards RAG — ChromaDB"],
  [
    "Create a defect for VIN-0002-TEST: CAN timeout during flash, severity major",
    "Write action — requires approval",
  ],
];

export default function Examples({ onPick, disabled }) {
  return (
    <div>
      {EXAMPLES.map(([text, hint]) => (
        <button
          key={text}
          className="example"
          disabled={disabled}
          onClick={() => onPick(text)}
        >
          {text}
          <small>{hint}</small>
        </button>
      ))}
    </div>
  );
}

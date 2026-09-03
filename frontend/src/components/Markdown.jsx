/**
 * Minimal markdown renderer for agent responses.
 * Agents commonly emit tables (ECU listings, query results), bold, and inline
 * code, so those are the cases handled — deliberately not a full parser.
 */

function inline(text, keyPrefix) {
  // Split on **bold** and `code`, keeping the delimiters.
  const parts = String(text).split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    const key = `${keyPrefix}-${i}`;
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={key}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return <code key={key}>{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

function parseRow(line) {
  return line.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
}

const isTableRow = (line) => /^\s*\|.*\|\s*$/.test(line);
const isSeparator = (cells) => cells.every((c) => /^:?-{2,}:?$/.test(c));

export default function Markdown({ text }) {
  const lines = String(text ?? "").split("\n");
  const blocks = [];
  let table = null;
  let paragraph = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const content = paragraph.join("\n");
    blocks.push(
      <p key={`p-${blocks.length}`}>{inline(content, `p${blocks.length}`)}</p>
    );
    paragraph = [];
  };

  const flushTable = () => {
    if (!table || !table.length) return;
    const [head, ...body] = table;
    blocks.push(
      <div className="table-scroll" key={`t-${blocks.length}`}>
        <table>
          <thead>
            <tr>
              {head.map((c, i) => (
                <th key={i}>{inline(c, `th${i}`)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((row, r) => (
              <tr key={r}>
                {row.map((c, i) => (
                  <td key={i}>{inline(c, `td${r}-${i}`)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
    table = null;
  };

  for (const line of lines) {
    if (isTableRow(line)) {
      const cells = parseRow(line);
      if (isSeparator(cells)) continue;
      flushParagraph();
      (table ??= []).push(cells);
    } else {
      flushTable();
      if (line.trim() === "") flushParagraph();
      else paragraph.push(line);
    }
  }
  flushTable();
  flushParagraph();

  return <>{blocks}</>;
}

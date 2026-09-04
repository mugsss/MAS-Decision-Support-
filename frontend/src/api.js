/** Thin client for the FastAPI backend. */

async function request(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HTTP ${res.status} — ${body.slice(0, 300)}`);
  }
  return res.json();
}

export const api = {
  health: () => request("/api/health"),

  /**
   * Stream chat via SSE. Returns an async iterator of parsed events.
   * Event types: start, token, tool_start, tool_end, blocked, done
   */
  chatStream: async function* (message, conversationId) {
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, conversation_id: conversationId }),
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`HTTP ${res.status} — ${body.slice(0, 300)}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            yield JSON.parse(line.slice(6));
          } catch {
            /* skip malformed */
          }
        }
      }
    }
  },

  pendingActions: () => request("/api/actions/pending"),

  approve: (id) =>
    request(`/api/actions/${id}/approve`, { method: "POST" }),

  reject: (id, reason = "Rejected by reviewer") =>
    request(`/api/actions/${id}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    }),

  memory: (conversationId) =>
    request(`/api/conversations/${conversationId}/memory`),
};

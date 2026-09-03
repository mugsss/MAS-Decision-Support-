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

  chat: (message, conversationId) =>
    request("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, conversation_id: conversationId }),
    }),

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

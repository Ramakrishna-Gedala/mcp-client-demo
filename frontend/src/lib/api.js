/**
 * API client for the FastAPI backend.
 * All calls go through /api/* which Vite proxies to localhost:8000.
 */

const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// ---- Chat ----
export async function sendMessage(message, sessionId = "default") {
  return request("/chat", {
    method: "POST",
    body: JSON.stringify({ message, session_id: sessionId }),
  });
}

export async function clearSession(sessionId = "default") {
  return request(`/sessions/${sessionId}`, { method: "DELETE" });
}

// ---- Tools ----
export async function listTools() {
  return request("/tools");
}

export async function callTool(toolName, args) {
  return request(`/tools/${toolName}`, {
    method: "POST",
    body: JSON.stringify({ arguments: args }),
  });
}

// ---- Resources ----
export async function listResources() {
  return request("/resources");
}

export async function readResource(uri) {
  return request(`/resources/${encodeURIComponent(uri)}`);
}

// ---- Prompts ----
export async function listPrompts() {
  return request("/prompts");
}

export async function getPrompt(name, args) {
  return request(`/prompts/${name}`, {
    method: "POST",
    body: JSON.stringify({ arguments: args }),
  });
}

// ---- Health ----
export async function healthCheck() {
  return request("/health");
}

const BASE = import.meta.env.VITE_API_URL ?? '';

/**
 * Send a chat message to the backend and return { answer, citations }.
 * @param {string} question
 * @param {Array<{role: string, content: string}>} history
 */
export async function sendMessage(question, history = []) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history }),
  });

  if (!res.ok) {
    let detail = `Server error ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore JSON parse error — use status code message
    }
    throw new Error(detail);
  }

  return res.json();
}

/**
 * Fetch the backend health status.
 * @returns {{ status, collection_size, gemini_available, groq_available }}
 */
export async function fetchHealth() {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

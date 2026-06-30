/**
 * Consumes an SSE response body from the chat API.
 * Parses `data: {...}` lines and invokes onEvent for each JSON payload.
 */
export async function consumeChatStream(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const parseLine = (line) => {
    const trimmed = line.trim();
    if (!trimmed.startsWith("data:")) return;

    const payload = trimmed.slice(5).trim();
    if (!payload) return;

    try {
      onEvent(JSON.parse(payload));
    } catch {
      // Ignore malformed SSE chunks and keep reading the stream.
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() || "";

    for (const line of lines) {
      parseLine(line);
    }
  }

  if (buffer.trim()) {
    parseLine(buffer);
  }
}

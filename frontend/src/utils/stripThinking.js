const THINKING_BLOCK_RE =
  /<(?:redacted_)?think(?:ing)?>[\s\S]*?<\/(?:redacted_)?think(?:ing)?>/gi;

/** Remove model reasoning blocks before rendering chat messages. */
export function stripThinkingBlocks(text = "") {
  if (!text) return text;
  return text.replace(THINKING_BLOCK_RE, "").replace(/^\n+/, "").trim();
}

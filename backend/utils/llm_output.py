import re

_THINK_OPEN = "<" + "think" + ">"
_THINK_CLOSE = "<" + "/think" + ">"

_THINKING_BLOCK_RE = re.compile(
    r"<(?:redacted_)?think(?:ing)?>[\s\S]*?</(?:redacted_)?think(?:ing)?>",
    re.IGNORECASE,
)

_OPEN_TAGS = (_THINK_OPEN, "<think>", "<thinking>")
_CLOSE_TAGS = (_THINK_CLOSE, "</think>", "</thinking>")


def strip_thinking_blocks(text: str) -> str:
    """Remove reasoning/thinking blocks from model output."""
    if not text:
        return text
    cleaned = _THINKING_BLOCK_RE.sub("", text)
    return cleaned.lstrip("\n").strip()


class ThinkingStreamFilter:
    """Strip thinking blocks from streamed LLM tokens before they reach the client."""

    def __init__(self) -> None:
        self._buffer = ""
        self._inside_thinking = False

    def feed(self, chunk: str) -> str:
        if not chunk:
            return ""

        self._buffer += chunk
        emitted: list[str] = []

        while self._buffer:
            if self._inside_thinking:
                close_at, close_len = self._find_earliest(self._buffer, _CLOSE_TAGS)
                if close_at == -1:
                    self._buffer = self._hold_partial_suffix(self._buffer, _CLOSE_TAGS)
                    break
                self._buffer = self._buffer[close_at + close_len :].lstrip("\n")
                self._inside_thinking = False
                continue

            open_at, open_len = self._find_earliest(self._buffer, _OPEN_TAGS)
            if open_at == -1:
                safe_end = len(self._buffer) - self._max_partial_prefix_len(
                    self._buffer, _OPEN_TAGS
                )
                if safe_end > 0:
                    emitted.append(self._buffer[:safe_end])
                    self._buffer = self._buffer[safe_end:]
                break

            if open_at > 0:
                emitted.append(self._buffer[:open_at])
            self._buffer = self._buffer[open_at + open_len :]
            self._inside_thinking = True

        return "".join(emitted)

    def flush(self) -> str:
        if self._inside_thinking:
            self._buffer = ""
            self._inside_thinking = False
            return ""

        remaining = self._buffer
        self._buffer = ""
        return remaining

    @staticmethod
    def _find_earliest(text: str, tags: tuple[str, ...]) -> tuple[int, int]:
        lowered = text.lower()
        best_at = -1
        best_len = 0
        for tag in tags:
            if not tag:
                continue
            idx = lowered.find(tag.lower())
            if idx != -1 and (best_at == -1 or idx < best_at):
                best_at = idx
                best_len = len(tag)
        return best_at, best_len

    @staticmethod
    def _max_partial_prefix_len(text: str, tags: tuple[str, ...]) -> int:
        lowered = text.lower()
        max_keep = max(len(tag) for tag in tags if tag) - 1
        for length in range(min(max_keep, len(text)), 0, -1):
            suffix = lowered[-length:]
            if any(tag.lower().startswith(suffix) for tag in tags if tag):
                return length
        return 0

    @staticmethod
    def _hold_partial_suffix(text: str, tags: tuple[str, ...]) -> str:
        max_keep = max(len(tag) for tag in tags if tag) - 1
        if len(text) <= max_keep:
            return text
        return text[-max_keep:]

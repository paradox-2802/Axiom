from utils.llm_output import ThinkingStreamFilter, strip_thinking_blocks

_THINK_OPEN = "<" + "think" + ">"
_THINK_CLOSE = "<" + "/think" + ">"


def test_strip_redacted_thinking_block():
    raw = (
        "<think>internal reasoning</think>\n\n"
        "The company name is Infosys Limited."
    )
    assert strip_thinking_blocks(raw) == "The company name is Infosys Limited."


def test_strip_think_block():
    raw = f"{_THINK_OPEN}hidden{_THINK_CLOSE}\nAnswer here."
    assert strip_thinking_blocks(raw) == "Answer here."


def test_stream_filter_holds_then_emits_answer():
    filt = ThinkingStreamFilter()
    assert filt.feed("<think>") == ""
    assert filt.feed("still thinking") == ""
    assert filt.feed("</think>\n\nBased on the document:") == (
        "Based on the document:"
    )


def test_stream_filter_splits_across_chunks():
    filt = ThinkingStreamFilter()
    part1 = filt.feed(f"Hello {_THINK_OPEN}sec")
    part2 = filt.feed(f"ret{_THINK_CLOSE} world")
    assert part1 == "Hello "
    assert part2 == " world"


def test_stream_filter_flush_drops_unclosed_thinking():
    filt = ThinkingStreamFilter()
    assert filt.feed(_THINK_OPEN + "unfinished") == ""
    assert filt.flush() == ""

from core.knowledge.chunking import chunk_text


def test_chunking_preserves_order_and_offsets() -> None:
    text = "one two three four five six seven eight nine ten"
    chunks = chunk_text(text, chunk_size=18, overlap=4)

    assert chunks
    assert [c.content for c in chunks]
    assert all(c.char_start < c.char_end for c in chunks)
    assert all(text[c.char_start:c.char_end] == c.content for c in chunks)
    assert [c.char_start for c in chunks] == sorted(c.char_start for c in chunks)


def test_empty_text_returns_no_chunks() -> None:
    assert chunk_text("   ") == []


def test_invalid_chunk_parameters_are_rejected() -> None:
    for kwargs in ({"chunk_size": 0}, {"chunk_size": 10, "overlap": 10}):
        try:
            chunk_text("hello", **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid chunk configuration")

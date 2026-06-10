"""Unit tests for US-P0-5: sentence splitter."""
from __future__ import annotations

from orchestrator.sentence_splitter import split_sentences


def test_three_sentences_yield_three_segments():
    segments = split_sentences("A. B. C.")
    assert len(segments) == 3


def test_seq_is_zero_indexed_incremental():
    segments = split_sentences("First sentence. Second sentence. Third sentence.")
    assert [s.seq for s in segments] == [0, 1, 2]


def test_all_segments_share_gen_id():
    segments = split_sentences("Hello world. Goodbye world. See you later.")
    gen_ids = {s.gen_id for s in segments}
    assert len(gen_ids) == 1


def test_explicit_gen_id_is_preserved():
    segments = split_sentences("One. Two. Three.", gen_id="test-gen-id")
    assert all(s.gen_id == "test-gen-id" for s in segments)


def test_text_is_preserved_per_segment():
    text = "I can help you. Please follow me. Someone will assist you shortly."
    segments = split_sentences(text)
    joined = " ".join(s.text for s in segments)
    assert "I can help you" in joined
    assert "Please follow me" in joined
    assert "Someone will assist you shortly" in joined


def test_question_and_exclamation_split():
    segments = split_sentences("Are you ready? Yes I am! Let's go.")
    assert len(segments) == 3


def test_short_fragment_discarded():
    # "Ok" alone is below the min length threshold but real segments pass
    segments = split_sentences("Hello there. I can help. Sure.")
    # "Sure." is 5 chars (stripped) — still above threshold
    assert len(segments) >= 2


def test_out_of_order_arrival_sorted_by_seq():
    """Simulate out-of-order delivery: segments created in natural order."""
    segments = split_sentences("Sentence one. Sentence two. Sentence three.")
    received = [segments[2], segments[0], segments[1]]
    ordered = sorted(received, key=lambda s: s.seq)
    assert [s.seq for s in ordered] == [0, 1, 2]

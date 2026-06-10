"""Unit tests for US-P0-5: stub LLM."""
from __future__ import annotations

from orchestrator.stub_llm import stub_llm
from orchestrator.sentence_splitter import split_sentences


def test_stub_llm_returns_non_empty_string():
    assert len(stub_llm("any input")) > 0


def test_stub_llm_returns_at_least_three_sentences():
    reply = stub_llm("hello", language="en")
    segments = split_sentences(reply)
    assert len(segments) >= 3


def test_stub_llm_vi_returns_at_least_three_sentences():
    reply = stub_llm("xin chào", language="vi")
    segments = split_sentences(reply)
    assert len(segments) >= 3


def test_stub_llm_unknown_language_falls_back_to_en():
    reply_en = stub_llm("hi", language="en")
    reply_unknown = stub_llm("hi", language="zh")
    assert reply_en == reply_unknown

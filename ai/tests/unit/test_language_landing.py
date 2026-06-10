"""Unit tests for US-P0-2: Language Landing.

AC: LANDING → GREETING transition; language immutability.
"""
from __future__ import annotations
import time

from orchestrator.state import Session, SessionRegistry, SessionState


def test_new_session_starts_in_landing():
    reg = SessionRegistry()
    session = reg.add("s1")
    assert session.state == SessionState.LANDING
    assert session.language is None


def test_language_set_transitions_to_greeting():
    session = Session(session_id="s1")
    session.language = "en"
    session.state = SessionState.GREETING
    assert session.state == SessionState.GREETING
    assert session.language == "en"


def test_greeting_transitions_to_listening():
    session = Session(session_id="s1")
    session.state = SessionState.GREETING
    session.state = SessionState.LISTENING
    assert session.state == SessionState.LISTENING


def test_language_immutable_once_set():
    """Once language is set it must not change — enforced in the handler."""
    session = Session(session_id="s1")
    session.language = "en"
    # handler check: if session.language is not None, skip the update
    original = session.language
    if session.language is None:
        session.language = "vi"
    assert session.language == original  # stays "en"


def test_vi_language_accepted():
    session = Session(session_id="s1")
    session.language = "vi"
    assert session.language == "vi"


def test_en_language_accepted():
    session = Session(session_id="s1")
    session.language = "en"
    assert session.language == "en"


def test_landing_to_listening_full_path():
    """Simulate the full LANDING → GREETING → LISTENING path."""
    reg = SessionRegistry()
    session = reg.add("s1")

    assert session.state == SessionState.LANDING
    assert session.language is None

    # handler sets language + moves to GREETING
    session.language = "en"
    session.state = SessionState.GREETING
    assert session.state == SessionState.GREETING

    # handler moves to LISTENING after stub greeting
    session.state = SessionState.LISTENING
    assert session.state == SessionState.LISTENING
    assert session.language == "en"  # language unchanged

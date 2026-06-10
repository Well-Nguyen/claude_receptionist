from __future__ import annotations

import re
import uuid
from dataclasses import dataclass


_MIN_SEGMENT_LEN = 2  # discard empty/whitespace-only fragments


@dataclass
class Segment:
    seq: int
    text: str
    gen_id: str


def split_sentences(text: str, gen_id: str | None = None) -> list[Segment]:
    """Split *text* into sentence segments, each tagged with *seq* and *gen_id*.

    Splits on sentence-ending punctuation (.?!) followed by whitespace or end of
    string. Segments shorter than _MIN_SEGMENT_LEN chars are discarded.
    """
    if gen_id is None:
        gen_id = str(uuid.uuid4())
    parts = re.split(r"(?<=[.?!])\s+", text.strip())
    segments = [p.strip() for p in parts if len(p.strip()) >= _MIN_SEGMENT_LEN]
    return [Segment(seq=i, text=s, gen_id=gen_id) for i, s in enumerate(segments)]

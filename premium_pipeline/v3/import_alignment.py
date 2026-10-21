#!/usr/bin/env python3
"""Import actual WhisperX word timestamps. Never fill missing times by guessing."""
import argparse
import json
from pathlib import Path


def convert(payload):
    rows = payload.get("word_segments")
    if rows is None:
        rows = [w for s in payload.get("segments", []) for w in s.get("words", [])]
    if not rows:
        raise ValueError("No aligned words in input")
    result = []
    for row in rows:
        if any(k not in row for k in ("word", "start", "end")):
            raise ValueError(f"Unaligned token: {row.get('word')!r}. Listen and correct the alignment; never interpolate.")
        result.append({k: row[k] for k in ("word", "start", "end")})
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    if a.output.exists():
        p.error("output exists: choose a new alignment version")
    try:
        value = convert(json.loads(a.input.read_text()))
    except ValueError as e:
        p.error(str(e))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(value, indent=2)+"\n")

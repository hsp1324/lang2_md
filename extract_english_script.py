#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROM = Path("Langrisser II (English).md")
OUT = Path("script_extract/english_records.json")
TEXT_START = 0x138200
TEXT_END = 0x17365A


def visible_text(blob: bytes) -> str:
    parts: list[str] = []
    i = 0
    while i < len(blob):
        b = blob[i]
        if b == 0xFF:
            if i + 1 < len(blob):
                nxt = blob[i + 1]
                if nxt == 0xFE:
                    parts.append("\n")
                    i += 2
                    continue
                if nxt == 0xFD:
                    parts.append("\n\n")
                    i += 2
                    continue
            i += 1
            continue
        if b in (0xFE,):
            parts.append("\n")
            i += 1
            continue
        if b in (0xFD,):
            parts.append("\n\n")
            i += 1
            continue
        if 0x20 <= b <= 0x7E:
            parts.append(chr(b))
        elif b in (0x7F,):
            parts.append(" ")
        i += 1
    text = "".join(parts)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def split_records(data: bytes) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    pos = TEXT_START
    while pos < TEXT_END:
        end = data.find(b"\xff\xff", pos, TEXT_END)
        if end < 0:
            break
        raw = data[pos : end + 2]
        prefix = raw[:3]
        text = visible_text(raw[3:-2])
        if text:
            records.append(
                {
                    "index": len(records),
                    "address": f"0x{pos:06x}",
                    "size": len(raw),
                    "prefix": prefix.hex(),
                    "text": text,
                }
            )
        pos = end + 2
        while pos < TEXT_END and data[pos] == 0xFF:
            pos += 1
    return records


def main() -> int:
    data = ROM.read_bytes()
    OUT.parent.mkdir(exist_ok=True)
    records = split_records(data)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total_chars = sum(len(str(r["text"])) for r in records)
    print(f"wrote {OUT}")
    print(f"records: {len(records)}")
    print(f"visible chars: {total_chars}")
    print(f"first: {records[0]['address']} {records[0]['text'][:80]!r}")
    print(f"last: {records[-1]['address']} {records[-1]['text'][:80]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

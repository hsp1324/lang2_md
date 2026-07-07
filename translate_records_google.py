#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from deep_translator import GoogleTranslator


IN = Path("script_extract/english_records.json")
OUT = Path("script_extract/korean_records_google.json")
MAX_CHARS = 4200
SLEEP_SECONDS = 0.7


MARK_RE = re.compile(r"\[\[\[(\d{4})\]\]\]")


def normalize_source(text: str) -> str:
    return " / ".join(line.strip() for line in text.splitlines() if line.strip())


def parse_marked(text: str) -> dict[int, str]:
    matches = list(MARK_RE.finditer(text))
    out: dict[int, str] = {}
    for idx, match in enumerate(matches):
        rec_id = int(match.group(1))
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        value = text[start:end].strip()
        if value:
            out[rec_id] = value
    return out


def chunks(records: list[dict[str, object]], done: set[int]) -> list[list[dict[str, object]]]:
    result: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    size = 0
    for record in records:
        idx = int(record["index"])
        if idx in done:
            continue
        item = f"[[[{idx:04d}]]]\n{normalize_source(str(record['text']))}\n"
        if current and size + len(item) > MAX_CHARS:
            result.append(current)
            current = []
            size = 0
        current.append(record)
        size += len(item)
    if current:
        result.append(current)
    return result


def save(records: list[dict[str, object]]) -> None:
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    records = json.loads(IN.read_text(encoding="utf-8"))
    if OUT.exists():
        existing = {int(r["index"]): r for r in json.loads(OUT.read_text(encoding="utf-8"))}
    else:
        existing = {}

    translated: dict[int, dict[str, object]] = dict(existing)
    translator = GoogleTranslator(source="en", target="ko")

    batches = chunks(records, set(translated))
    print(f"records: {len(records)} already_done: {len(translated)} batches: {len(batches)}")

    for batch_no, batch in enumerate(batches, 1):
        source = "".join(
            f"[[[{int(record['index']):04d}]]]\n{normalize_source(str(record['text']))}\n"
            for record in batch
        )
        try:
            result = translator.translate(source)
            parsed = parse_marked(result)
        except Exception as exc:
            print(f"batch {batch_no}/{len(batches)} failed: {exc}")
            parsed = {}

        missing = [record for record in batch if int(record["index"]) not in parsed]
        for record in batch:
            idx = int(record["index"])
            if idx in parsed:
                out = dict(record)
                out["translation"] = parsed[idx]
                translated[idx] = out

        for record in missing:
            idx = int(record["index"])
            try:
                value = translator.translate(normalize_source(str(record["text"])))
                out = dict(record)
                out["translation"] = value.strip()
                translated[idx] = out
                print(f"fallback ok {idx}")
            except Exception as exc:
                print(f"fallback failed {idx}: {exc}")
            time.sleep(SLEEP_SECONDS)

        if batch_no % 5 == 0 or missing:
            save([translated[i] for i in sorted(translated)])
        print(f"batch {batch_no}/{len(batches)} done total={len(translated)} missing={len(missing)}")
        time.sleep(SLEEP_SECONDS)

    save([translated[i] for i in sorted(translated)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

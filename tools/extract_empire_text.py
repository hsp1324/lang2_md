#!/usr/bin/env python3
"""Extract the Chinese text inventory from the Empire V2.0 (96%) ROM.

The Empire edit keeps Langrisser II's 16-bit text engines, but relocates the
2bpp font from 0x40000 to 0x31200 and replaces the glyph set with Chinese.  A
generated OCR map is kept separate from the build so the release builder does
not need an OCR runtime.

OCR is optional.  The checked-in inventory can be regenerated without it by
passing an existing ``--ocr-map``.  To refresh the map, install
``rapidocr-onnxruntime`` in an isolated environment and use ``--run-ocr``.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Iterable

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.jp_event_inventory import inventory as event_inventory
from tools.jp_text_font_analyzer import be16, be32, render_glyph


EMPIRE_V20_96_SHA256 = (
    "7004ad55f28340144f3248d7386d4bbc76a076491899af5e872f5854802be179"
)
EMPIRE_FONT_BASE = 0x031200
# The relocated bank has four late scenario-only additions through 0x0820
# (including 云/杰/妹/霸), beyond the event dialogue's 0x07xx range.
EMPIRE_FONT_GLYPH_COUNT = 0x0821

CONDITION_POINTER_TABLE = 0x098D7A
CONDITION_GLYPH_LIST_TABLE = 0x0986C6
CONDITION_COUNT = 32
SCENARIO_POINTER_TABLE = 0x09CF7C
SCENARIO_GLYPH_LIST_TABLE = 0x09B2FC
SCENARIO_COUNT = 31

TEXT_CONTROL_NAMES = {
    0xFFFD: "PAGE",
    0xFFFE: "NL",
    0xFFFF: "END",
}

# Shapes that OCR engines deliberately trim (space) or consistently confuse
# at 16x16 are fixed from repeated in-context readings of the shipped ROM.
MANUAL_GLYPH_OVERRIDES = {
    0x0054: " ",
    0x00EB: "『",
    0x00EC: "』",
    0x027A: "啊",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_word_list(data: bytes, offset: int, limit: int = 4096) -> list[int]:
    values: list[int] = []
    for _ in range(limit):
        value = be16(data, offset)
        offset += 2
        if value == 0xFFFF:
            return values
        values.append(value)
    raise ValueError(f"word list at 0x{offset:06X} has no terminator")


def read_token_stream(data: bytes, offset: int, limit: int = 4096) -> list[int]:
    values: list[int] = []
    for _ in range(limit):
        value = be16(data, offset)
        offset += 2
        values.append(value)
        if value == 0xFFFF:
            return values
    raise ValueError(f"text stream at 0x{offset:06X} has no terminator")


def mapped_glyph_codes(tokens: Iterable[int], glyphs: list[int]) -> Iterable[int]:
    iterator = iter(tokens)
    for token in iterator:
        if token == 0xFFF7:
            # Dynamic commander/actor name followed by its ID.
            next(iterator, None)
            continue
        if token in TEXT_CONTROL_NAMES:
            continue
        if token >= len(glyphs):
            # The Chinese source has one shipped condition record that refers
            # to the slot immediately following its FFFF-terminated list.
            # Keep it visible as a source anomaly without inventing a glyph.
            continue
        code = glyphs[token]
        if code >= EMPIRE_FONT_GLYPH_COUNT:
            # A malformed/unused slot must not be interpreted as an address
            # past the relocated Chinese font bank during OCR generation.
            continue
        yield code


def direct_glyph_codes(tokens: Iterable[int]) -> Iterable[int]:
    iterator = iter(tokens)
    for token in iterator:
        if token == 0xFFF7:
            # Dynamic-name control followed by a commander/actor ID.
            next(iterator, None)
            continue
        if token in TEXT_CONTROL_NAMES:
            continue
        if token >= EMPIRE_FONT_GLYPH_COUNT:
            raise ValueError(f"unexpected direct event token 0x{token:04X}")
        yield token


def repeated_glyph_canvas(data: bytes, code: int) -> "object":
    """Return a BGR numpy crop containing the same glyph three times."""

    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - optional diagnostic path
        raise RuntimeError("--run-ocr requires numpy") from exc

    glyph = render_glyph(
        data,
        EMPIRE_FONT_BASE,
        code,
        "jp2bpp16",
        4,
    ).convert("RGB")
    glyph_bgr = np.asarray(glyph)[:, :, ::-1]
    canvas = np.full((80, 280, 3), 255, dtype=np.uint8)
    for index in range(3):
        x = 8 + index * 88
        canvas[8:72, x : x + 64] = glyph_bgr
    return canvas


def glyph_sequence_canvas(data: bytes, codes: tuple[int, ...]) -> "object":
    """Return one OCR-ready line rendered from the ROM's own glyphs."""

    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - optional diagnostic path
        raise RuntimeError("--run-ocr requires numpy") from exc

    if not codes:
        raise ValueError("cannot render an empty glyph sequence")
    glyphs = [
        render_glyph(data, EMPIRE_FONT_BASE, code, "jp2bpp16", 4).convert("RGB")
        for code in codes
    ]
    canvas = Image.new("RGB", (len(glyphs) * 64 + 32, 96), "white")
    x = 16
    for glyph in glyphs:
        canvas.paste(glyph, (x, 16))
        x += 64
    return np.asarray(canvas)[:, :, ::-1]


def representative_character(raw_text: str) -> str | None:
    text = raw_text.strip()
    if not text:
        return None
    counts = Counter(text)
    # Three repeated copies make the majority robust against one bad edge
    # recognition (for example, ``村杖杖`` is still unambiguously ``杖``).
    char, count = counts.most_common(1)[0]
    if count >= 2 or len(text) == 1:
        return char
    return None


def run_glyph_ocr(data: bytes, usage: Counter[int]) -> dict[str, object]:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:  # pragma: no cover - optional diagnostic path
        raise RuntimeError(
            "--run-ocr requires rapidocr-onnxruntime in PYTHONPATH"
        ) from exc

    codes = sorted(usage)
    ocr = RapidOCR()
    crops = [repeated_glyph_canvas(data, code) for code in codes]
    recognized, _ = ocr.text_rec(crops)
    entries: list[dict[str, object]] = []
    for code, result in zip(codes, recognized):
        raw_text = str(result[0])
        confidence = float(result[1])
        entries.append(
            {
                "code": f"0x{code:04X}",
                "character": representative_character(raw_text),
                "raw_ocr": raw_text,
                "confidence": round(confidence, 6),
                "occurrences": usage[code],
            }
        )
    return {
        "source_sha256": sha256(data),
        "font_base": f"0x{EMPIRE_FONT_BASE:06X}",
        "method": "RapidOCR repeated-glyph majority; generated diagnostic, review required",
        "entry_count": len(entries),
        "recognized_count": sum(row["character"] is not None for row in entries),
        "entries": entries,
    }


def token_parts(
    tokens: list[int],
    glyphs: list[int] | None = None,
    max_line_glyphs: int = 18,
) -> list[str | tuple[int, ...]]:
    """Split a text stream into OCR lines and lossless control markers."""

    parts: list[str | tuple[int, ...]] = []
    current: list[int] = []

    def flush() -> None:
        nonlocal current
        while current:
            parts.append(tuple(current[:max_line_glyphs]))
            current = current[max_line_glyphs:]

    cursor = 0
    while cursor < len(tokens):
        token = tokens[cursor]
        cursor += 1
        if token == 0xFFF7:
            flush()
            if cursor < len(tokens):
                actor_id = tokens[cursor]
                cursor += 1
                parts.append(f"{{{actor_id:04X}}}")
            else:
                parts.append("{BROKEN_NAME_CONTROL}")
            continue
        if token == 0xFFFE:
            flush()
            parts.append("\n")
            continue
        if token == 0xFFFD:
            flush()
            parts.append("\f")
            continue
        if token == 0xFFFF:
            flush()
            break

        code = token
        if glyphs is not None:
            if token >= len(glyphs):
                flush()
                parts.append(f"[INDEX:{token:04X}]")
                continue
            code = glyphs[token]
        if code >= EMPIRE_FONT_GLYPH_COUNT:
            flush()
            parts.append(f"[GLYPH:{code:04X}]")
            continue
        current.append(code)
        if len(current) == max_line_glyphs:
            flush()
    flush()
    return parts


def collect_line_sequences(data: bytes) -> set[tuple[int, ...]]:
    sequences: set[tuple[int, ...]] = set()
    for pointer_table, glyph_table, count in (
        (CONDITION_POINTER_TABLE, CONDITION_GLYPH_LIST_TABLE, CONDITION_COUNT),
        (SCENARIO_POINTER_TABLE, SCENARIO_GLYPH_LIST_TABLE, SCENARIO_COUNT),
    ):
        for index in range(count):
            tokens = read_token_stream(data, be32(data, pointer_table + index * 4))
            glyphs = glyphs_needed_by_tokens(
                data,
                be32(data, glyph_table + index * 4),
                tokens,
            )
            sequences.update(
                part for part in token_parts(tokens, glyphs) if isinstance(part, tuple)
            )

    events = event_inventory(data, data)
    seen: set[int] = set()
    for scenario in events["scenarios"]:
        for page in scenario["pages"]:
            for physical in page["physical_pages"]:
                address = int(str(physical["address"]), 16)
                if address in seen:
                    continue
                seen.add(address)
                tokens = [int(value, 16) for value in str(physical["tokens"]).split()]
                sequences.update(
                    part for part in token_parts(tokens) if isinstance(part, tuple)
                )
    return sequences


def run_line_ocr(
    data: bytes,
    sequences: set[tuple[int, ...]],
    batch_size: int = 128,
) -> dict[str, object]:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:  # pragma: no cover - optional diagnostic path
        raise RuntimeError(
            "--run-ocr requires rapidocr-onnxruntime in PYTHONPATH"
        ) from exc

    ordered = sorted(sequences)
    ocr = RapidOCR()
    entries: list[dict[str, object]] = []
    for start in range(0, len(ordered), batch_size):
        batch = ordered[start : start + batch_size]
        crops = [glyph_sequence_canvas(data, codes) for codes in batch]
        recognized, _ = ocr.text_rec(crops)
        for codes, result in zip(batch, recognized):
            entries.append(
                {
                    "glyphs": " ".join(f"{code:04X}" for code in codes),
                    "text": str(result[0]).strip(),
                    "confidence": round(float(result[1]), 6),
                }
            )
    return {
        "source_sha256": sha256(data),
        "font_base": f"0x{EMPIRE_FONT_BASE:06X}",
        "method": "RapidOCR line recognition from ROM-rendered 16x16 glyphs",
        "entry_count": len(entries),
        "recognized_count": sum(bool(row["text"]) for row in entries),
        "entries": entries,
    }


def load_ocr_map(path: Path) -> tuple[dict[int, str], dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mapping = {
        int(str(row["code"]), 16): str(row["character"])
        for row in payload["entries"]
        if row.get("character")
    }
    return mapping, payload


def load_line_ocr_map(path: Path) -> tuple[dict[tuple[int, ...], str], dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mapping = {
        tuple(int(value, 16) for value in str(row["glyphs"]).split()): str(row["text"])
        for row in payload["entries"]
        if row.get("text")
    }
    return mapping, payload


def reconcile_glyph_ocr(
    glyph_payload: dict[str, object],
    line_payload: dict[str, object],
) -> dict[str, object]:
    """Correct single-glyph OCR with high-confidence line-level consensus."""

    votes: dict[int, Counter[str]] = {}
    for row in line_payload["entries"]:
        text = str(row.get("text", ""))
        codes = [int(value, 16) for value in str(row["glyphs"]).split()]
        if float(row.get("confidence", 0.0)) < 0.70 or len(codes) != len(text):
            continue
        for code, char in zip(codes, text):
            votes.setdefault(code, Counter())[char] += 1

    entries: list[dict[str, object]] = []
    corrected = 0
    recovered = 0
    for source_row in glyph_payload["entries"]:
        row = dict(source_row)
        code = int(str(row["code"]), 16)
        original = row.get("character")
        consensus = votes.get(code, Counter()).most_common(2)
        if consensus:
            top_char, top_count = consensus[0]
            runner_up = consensus[1][1] if len(consensus) > 1 else 0
            # Require a decisive majority for corrections. A missing isolated
            # glyph may be recovered from one otherwise high-confidence line.
            decisive = top_count > runner_up and (
                original is None or (top_count >= 3 and top_count >= runner_up * 3)
            )
            if decisive and top_char != original:
                row["single_glyph_ocr_character"] = original
                row["character"] = top_char
                row["line_consensus_votes"] = top_count
                if original is None:
                    recovered += 1
                else:
                    corrected += 1
        entries.append(row)

    for row in entries:
        code = int(str(row["code"]), 16)
        if code in MANUAL_GLYPH_OVERRIDES:
            original = row.get("character")
            row["single_glyph_ocr_character"] = original
            row["character"] = MANUAL_GLYPH_OVERRIDES[code]
            row["manual_reviewed"] = True

    return {
        "source_sha256": glyph_payload["source_sha256"],
        "font_base": glyph_payload["font_base"],
        "method": (
            "single-glyph OCR reconciled with >=0.70-confidence equal-length "
            "line OCR consensus"
        ),
        "entry_count": len(entries),
        "recognized_count": sum(row.get("character") is not None for row in entries),
        "recovered_missing_count": recovered,
        "corrected_character_count": corrected,
        "entries": entries,
    }


def decode_tokens(
    tokens: list[int],
    mapping: dict[int, str],
    glyphs: list[int] | None = None,
) -> str:
    output: list[str] = []
    cursor = 0
    while cursor < len(tokens):
        token = tokens[cursor]
        cursor += 1
        if token == 0xFFF7:
            if cursor >= len(tokens):
                output.append("{BROKEN_NAME_CONTROL}")
                break
            actor_id = tokens[cursor]
            cursor += 1
            output.append(f"{{{actor_id:04X}}}")
            continue
        if token == 0xFFFE:
            output.append("\n")
            continue
        if token == 0xFFFD:
            output.append("\f")
            continue
        if token == 0xFFFF:
            break
        code = token
        if glyphs is not None:
            if token >= len(glyphs):
                output.append(f"[INDEX:{token:04X}]")
                continue
            code = glyphs[token]
        output.append(mapping.get(code, f"[GLYPH:{code:04X}]"))
    return "".join(output)


def decode_tokens_line_ocr(
    tokens: list[int],
    line_mapping: dict[tuple[int, ...], str],
    glyph_mapping: dict[int, str],
    glyphs: list[int] | None = None,
) -> str:
    output: list[str] = []
    for part in token_parts(
        tokens,
        glyphs,
    ):
        if isinstance(part, str):
            output.append(part)
            continue
        fallback = "".join(
            glyph_mapping.get(code, f"[GLYPH:{code:04X}]") for code in part
        )
        output.append(line_mapping.get(part, fallback))
    return "".join(output)


def glyphs_needed_by_tokens(data: bytes, pointer: int, tokens: list[int]) -> list[int]:
    """Read exactly the local slots referenced by a mapped text record.

    Empire scenario glyph lists 2-31 are tightly concatenated at 0xA7040 and
    intentionally omit FFFF separators, unlike the Japanese source lists.
    Their text streams still expose the exact required slot count.
    """

    ordinary: list[int] = []
    cursor = 0
    while cursor < len(tokens):
        token = tokens[cursor]
        cursor += 1
        if token == 0xFFF7:
            cursor += 1
            continue
        if token in TEXT_CONTROL_NAMES:
            continue
        ordinary.append(token)
    count = max(ordinary, default=-1) + 1
    return [be16(data, pointer + index * 2) for index in range(count)]


def pointer_records(
    data: bytes,
    pointer_table: int,
    glyph_table: int,
    count: int,
    mapping: dict[int, str],
    line_mapping: dict[tuple[int, ...], str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(count):
        text_pointer = be32(data, pointer_table + index * 4)
        glyph_pointer = be32(data, glyph_table + index * 4)
        tokens = read_token_stream(data, text_pointer)
        glyphs = glyphs_needed_by_tokens(data, glyph_pointer, tokens)
        rows.append(
            {
                "id": index,
                "text_pointer": f"0x{text_pointer:06X}",
                "glyph_pointer": f"0x{glyph_pointer:06X}",
                "tokens": " ".join(f"{value:04X}" for value in tokens),
                "glyphs": " ".join(f"{value:04X}" for value in glyphs),
                "source_chinese_ocr": decode_tokens(
                    tokens,
                    mapping,
                    glyphs,
                ),
                "source_chinese_line_ocr": decode_tokens_line_ocr(
                    tokens,
                    line_mapping,
                    mapping,
                    glyphs,
                ),
            }
        )
    return rows


def event_records(
    data: bytes,
    mapping: dict[int, str],
    line_mapping: dict[tuple[int, ...], str],
) -> dict[str, list[dict[str, object]]]:
    payload = event_inventory(data, data)
    scenarios: dict[str, list[dict[str, object]]] = {}
    for scenario in payload["scenarios"]:
        rows: list[dict[str, object]] = []
        seen: set[int] = set()
        for page in scenario["pages"]:
            if page.get("classification", "text") != "text":
                continue
            for physical in page["physical_pages"]:
                address = int(str(physical["address"]), 16)
                if address in seen:
                    continue
                seen.add(address)
                tokens = [int(value, 16) for value in str(physical["tokens"]).split()]
                rows.append(
                    {
                        "address": f"0x{address:06X}",
                        "tokens": str(physical["tokens"]),
                        "source_chinese_ocr": decode_tokens(tokens, mapping),
                        "source_chinese_line_ocr": decode_tokens_line_ocr(
                            tokens, line_mapping, mapping
                        ),
                    }
                )
        scenarios[str(scenario["scenario"])] = sorted(
            rows, key=lambda row: int(str(row["address"]), 16)
        )
    return scenarios


def collect_usage(data: bytes) -> Counter[int]:
    usage: Counter[int] = Counter()
    for pointer_table, glyph_table, count in (
        (CONDITION_POINTER_TABLE, CONDITION_GLYPH_LIST_TABLE, CONDITION_COUNT),
        (SCENARIO_POINTER_TABLE, SCENARIO_GLYPH_LIST_TABLE, SCENARIO_COUNT),
    ):
        for index in range(count):
            tokens = read_token_stream(data, be32(data, pointer_table + index * 4))
            glyphs = glyphs_needed_by_tokens(
                data,
                be32(data, glyph_table + index * 4),
                tokens,
            )
            usage.update(mapped_glyph_codes(tokens, glyphs))

    events = event_inventory(data, data)
    seen: set[int] = set()
    for scenario in events["scenarios"]:
        for page in scenario["pages"]:
            for physical in page["physical_pages"]:
                address = int(str(physical["address"]), 16)
                if address in seen:
                    continue
                seen.add(address)
                tokens = [int(value, 16) for value in str(physical["tokens"]).split()]
                usage.update(direct_glyph_codes(tokens))
    return usage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument(
        "--out-dir", type=Path, default=Path("localization/empire/source")
    )
    parser.add_argument("--run-ocr", action="store_true")
    parser.add_argument("--ocr-map", type=Path)
    parser.add_argument("--line-ocr-map", type=Path)
    parser.add_argument("--reconciled-map", type=Path)
    args = parser.parse_args()

    data = args.rom.read_bytes()
    digest = sha256(data)
    if digest != EMPIRE_V20_96_SHA256:
        raise ValueError(
            f"unsupported Empire ROM SHA-256 {digest}; expected {EMPIRE_V20_96_SHA256}"
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    usage = collect_usage(data)
    ocr_path = args.ocr_map or args.out_dir / "font_map_ocr.json"
    if args.run_ocr:
        ocr_payload = run_glyph_ocr(data, usage)
        ocr_path.write_text(
            json.dumps(ocr_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    _, ocr_payload = load_ocr_map(ocr_path)

    line_ocr_path = args.line_ocr_map or args.out_dir / "line_map_ocr.json"
    if args.run_ocr:
        line_ocr_payload = run_line_ocr(data, collect_line_sequences(data))
        line_ocr_path.write_text(
            json.dumps(line_ocr_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    line_mapping, line_ocr_payload = load_line_ocr_map(line_ocr_path)

    reconciled_path = args.reconciled_map or args.out_dir / "font_map_reconciled.json"
    reconciled_payload = reconcile_glyph_ocr(ocr_payload, line_ocr_payload)
    reconciled_path.write_text(
        json.dumps(reconciled_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    mapping, _ = load_ocr_map(reconciled_path)

    conditions = pointer_records(
        data,
        CONDITION_POINTER_TABLE,
        CONDITION_GLYPH_LIST_TABLE,
        CONDITION_COUNT,
        mapping,
        line_mapping,
    )
    scenarios = pointer_records(
        data,
        SCENARIO_POINTER_TABLE,
        SCENARIO_GLYPH_LIST_TABLE,
        SCENARIO_COUNT,
        mapping,
        line_mapping,
    )
    events = event_records(data, mapping, line_mapping)
    inventory_payload = {
        "edition": "Empire V2.0 (96%) Chinese edit",
        "source_sha256": digest,
        "source_size": len(data),
        "font_base": f"0x{EMPIRE_FONT_BASE:06X}",
        "ocr_map": str(reconciled_path),
        "ocr_recognized": int(reconciled_payload["recognized_count"]),
        "line_ocr_map": str(line_ocr_path),
        "line_ocr_recognized": int(line_ocr_payload["recognized_count"]),
        "used_glyph_count": len(usage),
        "condition_records": conditions,
        "scenario_description_records": scenarios,
        "event_scenarios": events,
        "event_record_count": sum(len(rows) for rows in events.values()),
    }
    inventory_path = args.out_dir / "text_inventory.json"
    inventory_path.write_text(
        json.dumps(inventory_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {ocr_path} and {inventory_path}; "
        f"used glyphs={len(usage)}, recognized={reconciled_payload['recognized_count']}, "
        f"event records={inventory_payload['event_record_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

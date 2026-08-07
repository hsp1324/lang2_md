#!/usr/bin/env python3
"""Edition-specific metadata for the Empire V2.0 (96%) localization.

The Empire edit deliberately reorders both the class and commander-name
tables.  Indexing the normal-edition Korean labels by ID therefore produces
plausible-looking but incorrect names.  This module derives labels from the
actual half-width Japanese source string stored at each Empire table entry and
keeps the handful of Empire-only entries explicit.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from tools.jp_byte_table_analyzer import KOREAN_CLASS_LABELS
from tools.scenario_data import KOREAN_NAME_BY_ID


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JAPANESE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
DEFAULT_EMPIRE_ROM = Path(
    "/mnt/c/Users/hsp13/Desktop/제국 V2.0(0.96)/"
    "Langrisser2帝国篇V2.0(96%).BIN"
)

EMPIRE_SOURCE_SHA256 = (
    "7004ad55f28340144f3248d7386d4bbc76a076491899af5e872f5854802be179"
)
CLASS_POINTER_TABLE = 0x05E6D6
CLASS_COUNT = 157
NAME_POINTER_TABLE = 0x0618E8
NAME_COUNT = 117

EMPIRE_ONLY_CLASS_LABELS = {
    "ﾏｰｼｬﾙ": "마샬",
    "ｸｲｰﾝ": "퀸",
    "ｳｫﾘｱｰ": "워리어",
    "ﾎｰｸｶﾞｰﾄﾞ": "호크가드",
}

EMPIRE_ONLY_NAME_LABELS = {
    "ｿﾆｱ": "소니아",
    "ﾛｳｶﾞ": "로우가",
    "ｸﾗｳｽ": "크라우스",
    # The edit stores ASCII scratch text in name slot 0x16, but scenarios
    # 4-6 use that slot for the Light Temple priest (class 0x9C).
    "wvr": "사제",
}

# The dynamic FFF7 controls use the reordered runtime name IDs below.  Keep
# this map next to the source-derived table so dialogue validation never falls
# back to the normal-edition Elwin-first mapping.
EMPIRE_ACTOR_NAME_BY_ID = {
    0x00: "소니아",
    0x01: "베른하르트",
    0x02: "리아나",
    0x03: "라나",
    0x04: "이멜다",
    0x05: "에그베르트",
    0x06: "레온",
    0x07: "레아드",
    0x08: "발가스",
    0x09: "로우가",
    0x0A: "소니아",
    0x0B: "수수께끼의 기사",
    0x0C: "라나",
    0x0D: "쉐리",
    0x0E: "엘윈",
    0x0F: "아론",
    0x10: "보젤",
    0x11: "키스",
    0x12: "로렌",
    0x13: "스코트",
    0x14: "제시카",
    0x15: "레스터",
    0x16: "사제",
    0x17: "헤인",
    0x1F: "모건",
    0x25: "조름",
    0x26: "크라우스",
    0x74: "소니아",
}


def be32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def read_ff_string(data: bytes, offset: int, limit: int = 64) -> bytes:
    end = data.find(b"\xFF", offset, offset + limit)
    if end < 0:
        raise ValueError(f"unterminated byte string at 0x{offset:06X}")
    return data[offset:end]


def decode_table(data: bytes, table: int, count: int) -> list[str]:
    return [
        read_ff_string(data, be32(data, table + index * 4)).decode(
            "cp932", errors="strict"
        )
        for index in range(count)
    ]


def validate_empire_source(data: bytes) -> None:
    digest = hashlib.sha256(data).hexdigest()
    if digest != EMPIRE_SOURCE_SHA256:
        raise ValueError(
            f"unsupported Empire ROM SHA-256 {digest}; expected "
            f"{EMPIRE_SOURCE_SHA256}"
        )


def _unique_source_mapping(sources: list[str], targets: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for source, target in zip(sources, targets):
        previous = mapping.setdefault(source, target)
        if previous != target:
            raise ValueError(
                f"ambiguous normal-edition label {source!r}: "
                f"{previous!r} vs {target!r}"
            )
    return mapping


def derive_empire_class_labels(
    empire: bytes, japanese: bytes
) -> list[str]:
    validate_empire_source(empire)
    normal_sources = decode_table(japanese, CLASS_POINTER_TABLE, CLASS_COUNT)
    normal_by_source = _unique_source_mapping(
        normal_sources, list(KOREAN_CLASS_LABELS)
    )
    source_to_korean = {**normal_by_source, **EMPIRE_ONLY_CLASS_LABELS}
    result: list[str] = []
    for index, source in enumerate(
        decode_table(empire, CLASS_POINTER_TABLE, CLASS_COUNT)
    ):
        if source not in source_to_korean:
            raise ValueError(
                f"unmapped Empire class 0x{index:02X}: {source!r}"
            )
        result.append(source_to_korean[source])
    return result


def derive_empire_name_labels(empire: bytes, japanese: bytes) -> list[str]:
    validate_empire_source(empire)
    normal_sources = decode_table(japanese, NAME_POINTER_TABLE, NAME_COUNT)
    normal_targets = [KOREAN_NAME_BY_ID[index] for index in range(NAME_COUNT)]
    normal_by_source = _unique_source_mapping(normal_sources, normal_targets)
    source_to_korean = {**normal_by_source, **EMPIRE_ONLY_NAME_LABELS}
    result: list[str] = []
    for index, source in enumerate(
        decode_table(empire, NAME_POINTER_TABLE, NAME_COUNT)
    ):
        if source not in source_to_korean:
            raise ValueError(
                f"unmapped Empire name 0x{index:02X}: {source!r}"
            )
        result.append(source_to_korean[source])

    for actor_id, expected in EMPIRE_ACTOR_NAME_BY_ID.items():
        if result[actor_id] != expected:
            raise ValueError(
                f"Empire actor 0x{actor_id:02X} resolved to "
                f"{result[actor_id]!r}, expected {expected!r}"
            )
    return result


def load_empire_labels(
    empire_path: Path = DEFAULT_EMPIRE_ROM,
    japanese_path: Path = DEFAULT_JAPANESE_ROM,
) -> tuple[list[str], list[str]]:
    empire = empire_path.read_bytes()
    japanese = japanese_path.read_bytes()
    return (
        derive_empire_class_labels(empire, japanese),
        derive_empire_name_labels(empire, japanese),
    )


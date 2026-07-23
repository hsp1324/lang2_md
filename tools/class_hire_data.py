#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass


CLASS_RECORD_TABLE = 0x05EDDC
CLASS_RECORD_SIZE = 0x1C
CLASS_COUNT = 157
HIRE_UNLOCK_OFFSETS = (0x1A, 0x1B)
MERCENARY_CLASS_BASE = 0x62
MERCENARY_CLASS_COUNT = 16
EMPTY_HIRE = 0xFF


@dataclass(frozen=True)
class ClassHireUnlocks:
    class_id: int
    hire_class_ids: tuple[int, int]
    offset: int


def class_record_offset(class_id: int) -> int:
    if not 0 <= class_id < CLASS_COUNT:
        raise ValueError(f"class ID must be 0..{CLASS_COUNT - 1}")
    return CLASS_RECORD_TABLE + class_id * CLASS_RECORD_SIZE


def _decode_hire_id(value: int) -> int:
    if value == EMPTY_HIRE:
        return EMPTY_HIRE
    if not 0 <= value < MERCENARY_CLASS_COUNT:
        raise ValueError(f"invalid class hire bit index 0x{value:02X}")
    return MERCENARY_CLASS_BASE + value


def _encode_hire_id(class_id: int) -> int:
    if class_id == EMPTY_HIRE:
        return EMPTY_HIRE
    if not (
        MERCENARY_CLASS_BASE
        <= class_id
        < MERCENARY_CLASS_BASE + MERCENARY_CLASS_COUNT
    ):
        raise ValueError(
            "class hire unlocks must be class IDs "
            f"0x{MERCENARY_CLASS_BASE:02X}.."
            f"0x{MERCENARY_CLASS_BASE + MERCENARY_CLASS_COUNT - 1:02X} "
            "or 0xFF"
        )
    return class_id - MERCENARY_CLASS_BASE


def read_class_hire_unlocks(
    source: bytes | bytearray,
    class_id: int,
) -> ClassHireUnlocks:
    base = class_record_offset(class_id)
    values = tuple(
        _decode_hire_id(source[base + relative])
        for relative in HIRE_UNLOCK_OFFSETS
    )
    return ClassHireUnlocks(
        class_id=class_id,
        hire_class_ids=(values[0], values[1]),
        offset=base + HIRE_UNLOCK_OFFSETS[0],
    )


def patch_class_hire_unlocks(
    data: bytearray,
    rows: list[dict[str, object]],
) -> None:
    seen: set[int] = set()
    for row in rows:
        class_id = int(row["class_id"])
        if class_id in seen:
            raise ValueError(f"class hire row repeats class 0x{class_id:02X}")
        seen.add(class_id)
        values = [int(value) for value in row["hire_class_ids"]]
        if len(values) != len(HIRE_UNLOCK_OFFSETS):
            raise ValueError("each class needs exactly two hire unlock slots")
        base = class_record_offset(class_id)
        for relative, value in zip(HIRE_UNLOCK_OFFSETS, values):
            data[base + relative] = _encode_hire_id(value)

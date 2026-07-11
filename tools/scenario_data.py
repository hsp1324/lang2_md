#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tools.jp_byte_table_analyzer import KOREAN_CLASS_LABELS


SCENARIO_POINTER_TABLE = 0x18005E
SCENARIO_COUNT = 31
FIXED_LIST_POINTER_OFFSET = 0x0C
FIXED_RECORD_SIZE = 0x24
CLASS_POINTER_TABLE = 0x05E6D6
CLASS_COUNT = 157
NAME_POINTER_TABLE = 0x0618E8
NAME_COUNT = 0x75

FIELD_OFFSETS = {
    "level": 0x0E,
    "at": 0x12,
    "df": 0x13,
    "x": 0x18,
    "y": 0x19,
    "name_id": 0x1A,
    "class_id": 0x1B,
    "mercenaries": 0x1E,
}

KOREAN_CLASS_NAMES = KOREAN_CLASS_LABELS
KOREAN_NAME_BY_ID = {
    0x01: "엘윈", 0x02: "리아나", 0x03: "라나", 0x04: "셰리",
    0x05: "헤인", 0x06: "스코트", 0x07: "키스", 0x08: "아론",
    0x09: "레스터", 0x0A: "제시카", 0x0B: "수수께끼의 기사",
    0x0D: "레온", 0x0E: "베른하르트", 0x0F: "발가스",
    0x10: "보젤", 0x11: "레아드", 0x12: "발드", 0x13: "졸름",
    0x14: "에그베르트", 0x15: "이멜다", 0x16: "모건",
    0x17: "기남", 0x18: "크레이머", 0x19: "세이갈",
    0x1A: "폴거", 0x1B: "병사", 0x1C: "지휘관", 0x1D: "지휘관",
    0x1E: "지휘관", 0x1F: "사제", 0x20: "주민", 0x21: "주민",
    0x22: "주민", 0x23: "해적", 0x24: "해적", 0x25: "민병대",
    0x26: "로렌", 0x27: "아돈", 0x28: "삼손", 0x29: "바란",
}
JAPANESE_NAME_BY_ID = {
    0x1B: "一般兵", 0x1C: "指揮官", 0x1D: "指揮官", 0x1E: "指揮官",
    0x1F: "プリースト", 0x20: "たみびと", 0x21: "たみびと",
    0x22: "たみびと", 0x23: "海賊", 0x24: "海賊", 0x25: "自警団",
}
for _name_id in range(0x2A, 0x34):
    KOREAN_NAME_BY_ID[_name_id] = "제국지휘관"

SCENARIO1_ROLES = {
    0: ("NPC", "주민"),
    1: ("NPC", "리아나"),
    2: ("아군 지원", "민병대"),
    3: ("아군 지원", "사제"),
    4: ("이벤트 대기", "로렌"),
    5: ("이벤트 대기", "지휘관 A"),
    6: ("이벤트 대기", "지휘관 B"),
    7: ("이벤트 대기", "스코트"),
    8: ("적군", "발드"),
    9: ("적군", "레온"),
    10: ("적군", "레아드"),
    11: ("적군", "제국지휘관"),
}


def be16(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def read_ff_string(data: bytes | bytearray, offset: int, limit: int = 48) -> bytes:
    end = bytes(data).find(b"\xff", offset, offset + limit)
    if end < 0:
        raise ValueError(f"missing FF terminator at 0x{offset:06X}")
    return bytes(data[offset:end])


def decode_halfwidth(data: bytes | bytearray, offset: int) -> str:
    return read_ff_string(data, offset).decode("cp932", errors="replace")


def class_names(reference_rom: bytes) -> list[dict[str, object]]:
    result = []
    for class_id in range(CLASS_COUNT):
        pointer = be32(reference_rom, CLASS_POINTER_TABLE + class_id * 4)
        result.append({
            "id": class_id,
            "jp": decode_halfwidth(reference_rom, pointer),
            "ko": KOREAN_CLASS_NAMES[class_id],
        })
    return result


def name_for_id(reference_rom: bytes, name_id: int) -> dict[str, object]:
    if not 0 <= name_id < NAME_COUNT:
        return {"id": name_id, "jp": "", "ko": f"이름 {name_id:02X}"}
    pointer = be32(reference_rom, NAME_POINTER_TABLE + name_id * 4)
    japanese = JAPANESE_NAME_BY_ID.get(name_id, decode_halfwidth(reference_rom, pointer))
    return {
        "id": name_id,
        "jp": japanese,
        "ko": KOREAN_NAME_BY_ID.get(name_id, f"이름 {name_id:02X}"),
    }


@dataclass(frozen=True)
class ScenarioLayout:
    number: int
    header_offset: int
    record_list_offset: int
    record_count: int
    records_offset: int


def scenario_layout(data: bytes | bytearray, number: int) -> ScenarioLayout:
    if not 1 <= number <= SCENARIO_COUNT:
        raise ValueError(f"scenario must be 1..{SCENARIO_COUNT}")
    header = be32(data, SCENARIO_POINTER_TABLE + (number - 1) * 4)
    record_list = be32(data, header + FIXED_LIST_POINTER_OFFSET)
    count = be16(data, record_list)
    records = record_list + 2
    if not (0 < count <= 64 and records + count * FIXED_RECORD_SIZE <= len(data)):
        raise ValueError(f"invalid Scenario {number} record list at 0x{record_list:06X}")
    return ScenarioLayout(number, header, record_list, count, records)


def read_scenario(data: bytes, reference_rom: bytes, number: int) -> dict[str, object]:
    layout = scenario_layout(data, number)
    classes = class_names(reference_rom)
    records = []
    for index in range(layout.record_count):
        offset = layout.records_offset + index * FIXED_RECORD_SIZE
        raw = data[offset : offset + FIXED_RECORD_SIZE]
        class_id = raw[FIELD_OFFSETS["class_id"]]
        name_id = raw[FIELD_OFFSETS["name_id"]]
        mercs = list(raw[FIELD_OFFSETS["mercenaries"] : FIELD_OFFSETS["mercenaries"] + 6])
        default_role = ("배치", name_for_id(reference_rom, name_id)["ko"])
        role, label = SCENARIO1_ROLES.get(index, default_role) if number == 1 else default_role
        records.append({
            "index": index,
            "offset": offset,
            "role": role,
            "label": label,
            "hidden": bool(raw[0] & 0x80),
            "level": raw[FIELD_OFFSETS["level"]],
            "at": raw[FIELD_OFFSETS["at"]],
            "df": raw[FIELD_OFFSETS["df"]],
            "x": raw[FIELD_OFFSETS["x"]],
            "y": raw[FIELD_OFFSETS["y"]],
            "name": name_for_id(reference_rom, name_id),
            "class_id": class_id,
            "class": classes[class_id],
            "mercenaries": mercs,
        })
    return {
        "number": number,
        "header_offset": layout.header_offset,
        "record_list_offset": layout.record_list_offset,
        "record_count": layout.record_count,
        "records": records,
        "classes": classes,
    }


def update_checksum(data: bytearray) -> int:
    checksum = sum(be16(data, offset) for offset in range(0x200, len(data), 2)) & 0xFFFF
    data[0x18E:0x190] = checksum.to_bytes(2, "big")
    return checksum


def patch_scenario(data: bytearray, number: int, records: list[dict[str, object]]) -> int:
    layout = scenario_layout(data, number)
    if len(records) != layout.record_count:
        raise ValueError(f"expected {layout.record_count} records, got {len(records)}")
    scalar_fields = ("level", "at", "df", "class_id")
    for expected_index, record in enumerate(records):
        if int(record["index"]) != expected_index:
            raise ValueError("record indexes must be ordered and unchanged")
        offset = layout.records_offset + expected_index * FIXED_RECORD_SIZE
        for field in scalar_fields:
            value = int(record[field])
            if not 0 <= value <= 0xFF:
                raise ValueError(f"{field} must be 0..255")
            if field == "class_id" and value >= CLASS_COUNT:
                raise ValueError(f"class_id must be 0..{CLASS_COUNT - 1}")
            data[offset + FIELD_OFFSETS[field]] = value
        mercenaries = [int(value) for value in record["mercenaries"]]
        if len(mercenaries) != 6 or any(value != 0xFF and not 0 <= value < CLASS_COUNT for value in mercenaries):
            raise ValueError(f"mercenaries must contain six class IDs or 255")
        start = offset + FIELD_OFFSETS["mercenaries"]
        data[start : start + 6] = bytes(mercenaries)
    return update_checksum(data)

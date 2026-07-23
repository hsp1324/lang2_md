#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass


ITEM_COUNT = 37
ITEM_EFFECT_TABLE = 0x060530
ITEM_EFFECT_RECORD_SIZE = 8
ITEM_EFFECT_SLOT_COUNT = 4
ITEM_PRICE_TABLE = 0x0A1D32

ITEM_EFFECT_TYPES = {
    0x00: "AT",
    0x01: "DF",
    0x02: "MV",
    0x03: "지휘범위",
    0x04: "A보정",
    0x05: "D보정",
    0x06: "마법 사거리",
    0x07: "마법 대미지",
    0x08: "마법저항(지휘관/용병)",
    0x09: "소환 ID",
    0x0A: "마법저항(지휘관)",
    0xFF: "없음",
}

SPECIAL_ITEM_BEHAVIOR = {
    9: ("진 랑그릿사 가격 표시 예외",),
    10: ("경험치 2배",),
    15: ("공격 사거리 1~3",),
    16: ("공격 사거리 1~6",),
    26: ("LV10에서 최하위 클래스로 복귀",),
    29: ("MP 2배",),
}


@dataclass(frozen=True)
class ItemEffect:
    effect_type: int
    value: int


@dataclass(frozen=True)
class ItemRecord:
    item_id: int
    price_units: int
    effects: tuple[ItemEffect, ...]


def _check_item_id(item_id: int) -> None:
    if not 1 <= item_id <= ITEM_COUNT:
        raise ValueError(f"item ID must be 1..{ITEM_COUNT}")


def effect_record_offset(item_id: int) -> int:
    _check_item_id(item_id)
    return ITEM_EFFECT_TABLE + item_id * ITEM_EFFECT_RECORD_SIZE


def price_offset(item_id: int) -> int:
    _check_item_id(item_id)
    return ITEM_PRICE_TABLE + (item_id - 1) * 2


def read_item(data: bytes | bytearray, item_id: int) -> ItemRecord:
    effect_offset = effect_record_offset(item_id)
    effects = []
    for slot in range(ITEM_EFFECT_SLOT_COUNT):
        offset = effect_offset + slot * 2
        effect_type = data[offset]
        raw_value = data[offset + 1]
        if effect_type not in ITEM_EFFECT_TYPES:
            raise ValueError(
                f"item {item_id} effect slot {slot} has unknown type "
                f"0x{effect_type:02X}"
            )
        if effect_type == 0xFF:
            value = 0
        elif effect_type == 0x09:
            value = raw_value
        else:
            value = int.from_bytes(bytes([raw_value]), "big", signed=True)
        effects.append(ItemEffect(effect_type, value))
    return ItemRecord(
        item_id=item_id,
        price_units=int.from_bytes(
            data[price_offset(item_id) : price_offset(item_id) + 2], "big"
        ),
        effects=tuple(effects),
    )


def read_items(data: bytes | bytearray) -> tuple[ItemRecord, ...]:
    return tuple(read_item(data, item_id) for item_id in range(1, ITEM_COUNT + 1))


def _encode_effect(item_id: int, slot: int, effect: ItemEffect) -> bytes:
    effect_type = int(effect.effect_type)
    value = int(effect.value)
    if effect_type not in ITEM_EFFECT_TYPES:
        raise ValueError(
            f"item {item_id} effect slot {slot} has unknown type "
            f"0x{effect_type:02X}"
        )
    if effect_type == 0xFF:
        return b"\xFF\xFF"
    if effect_type == 0x09:
        if not 0 <= value <= 0xFF:
            raise ValueError(
                f"item {item_id} summon ID must be 0..255"
            )
        raw_value = value
    else:
        if not -128 <= value <= 127:
            raise ValueError(
                f"item {item_id} effect value must be -128..127"
            )
        raw_value = value & 0xFF
    return bytes((effect_type, raw_value))


def patch_items(
    data: bytearray,
    records: list[dict[str, object]] | tuple[ItemRecord, ...],
) -> None:
    if len(records) != ITEM_COUNT:
        raise ValueError(f"expected {ITEM_COUNT} item records, got {len(records)}")
    for expected_id, source_record in enumerate(records, 1):
        if isinstance(source_record, ItemRecord):
            record = source_record
        else:
            effects = tuple(
                ItemEffect(
                    int(effect["effect_type"]),
                    int(effect.get("value", 0)),
                )
                for effect in source_record["effects"]
            )
            record = ItemRecord(
                int(source_record["item_id"]),
                int(source_record["price_units"]),
                effects,
            )
        if record.item_id != expected_id:
            raise ValueError("item IDs must be ordered and unchanged")
        if not 0 <= record.price_units <= 0xFFFF:
            raise ValueError(f"item {expected_id} price must be 0..65535")
        if len(record.effects) != ITEM_EFFECT_SLOT_COUNT:
            raise ValueError(
                f"item {expected_id} must contain {ITEM_EFFECT_SLOT_COUNT} effects"
            )

        price = price_offset(expected_id)
        data[price : price + 2] = record.price_units.to_bytes(2, "big")
        effect_offset = effect_record_offset(expected_id)
        payload = b"".join(
            _encode_effect(expected_id, slot, effect)
            for slot, effect in enumerate(record.effects)
        )
        data[
            effect_offset : effect_offset + ITEM_EFFECT_RECORD_SIZE
        ] = payload


def special_behavior(item_id: int) -> tuple[str, ...]:
    _check_item_id(item_id)
    return SPECIAL_ITEM_BEHAVIOR.get(item_id, ())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts import build_korean_jp_probe as builder
from tools import scenario_data


RESOURCE_TABLE = builder.BYTE_UI_FONT_RESOURCE_TABLE
RESOURCE_LOAD_ROUTINE = 0x0099B2
RESOURCE_DISPATCH_ROUTINE = 0x0099FA
RESOURCE_LOOKUP_ROUTINE = 0x009A0E
RESOURCE_DECODER_ROUTINES = {
    0: 0x009A20,
    1: 0x009A38,
    2: 0x009C10,
    3: 0x009DFE,
    4: 0x009AAA,
}
LIVE_OWNER_LABELS = {
    0: "sega_boot_logo",
    builder.BYTE_UI_FONT_RESOURCE_INDEX: "byte_ui_font",
    builder.BATTLE_UI_TERRAIN_RESOURCE_INDEX: "battle_ui_terrain",
    391: "item_icons",
    392: "masaya_publisher_logo",
    builder.TITLE_LOGO_RESOURCE_INDEX: "title_logo",
}
SOURCE_LOCKS = {
    "scenario_map_resource_table": (
        0x061C34,
        31 * 4,
        "fac42d9dffaca3143d0eb37deace4cf63df6b3f6cd0df868f1dd744eeccc5387",
    ),
    "scenario_map_loader": (
        0x01C5A0,
        0x28,
        "cff4956b11a2d008c283d14477d86d9e57035bc3eda5c17265a07b82d95e05e4",
    ),
    "battle_background_resource_table": (
        0x08654C,
        20 * 2,
        "c13a99f2a4eb4f6be32110af1d47438428266ea54760ae1cbdce43f21c407495",
    ),
    "battle_background_loader": (
        0x01CD10,
        0x16,
        "a1c2e0cd8ce636af2a22f0342e2debb24584bb33cb57487d9b81f73516dece62",
    ),
    "commander_combat_pointer_table": (
        0x087726,
        10 * 4,
        "ddf61f9404940f9c8520e3f9d5a7ddca2388170365e64b449654292652bf29c5",
    ),
    "commander_combat_records": (
        0x08774E,
        0x08840A - 0x08774E,
        "ad4260a2f63bbd2840a61440d118d7b9a9566298ae62a4b06fb1b105ae62bfe9",
    ),
    "generic_combat_descriptor_table": (
        0x08840A,
        scenario_data.CLASS_COUNT * 0x10,
        "f7ee226f64b6582e0117c962b573af1d19902b601aab19521c848930623e2e00",
    ),
    "map_combat_selector": (
        0x01B6FA,
        0x72,
        "0b6727402de682cda58c7f10210a50e98721491325a9f97669112c3098080811",
    ),
    "battle_combat_selector": (
        0x01DB34,
        0x66,
        "31034f724ea5dd91a4b739e01fd4a9c919126872dfdba49659d428a41a0269b5",
    ),
    "portrait_lookup_table": (
        0x0977A6,
        0x100,
        "31ce43a1127a9d2dd9d64a84479ec25cef34fbc0fc535b8d55f0a38cab17a1a5",
    ),
    "portrait_loader": (
        0x01CC7A,
        0x1C,
        "13fa5a04dbce2fa916c7e32b1fbae234d00081fcf7e733c9d5fe6f3f24916b72",
    ),
    "route_fragment_pointer_table": (
        0x0A1124,
        31 * 4,
        "ab633779c6700d176759c519c5417ebe1117db3f18727bb94dabf6e71e55462f",
    ),
    "route_fragment_descriptors": (
        0x0A11A0,
        0x0A14AC - 0x0A11A0,
        "adcd9be6748bb352dd81dff902098f22568234a88ef7e5227e440768be432148",
    ),
    "route_fragment_loader": (
        0x026056,
        0xB8,
        "1d83d7848116841bb9873262765ef55e265a6755e05001b69bb3c2ad2ecea582",
    ),
    "battle_variant_loader": (
        0x01E0D2,
        0x98,
        "d59a0ed676cf4e9329b4c49a5ea7b5f4c169712c1ac0794a88136a129578bb49",
    ),
    "common_battle_loader": (
        0x01C5EE,
        0x0E,
        "75331e1f4c613508950783bafea71e083036292679ba9b0ec19f6d277d4976c4",
    ),
}
SCENARIO_MAP_RESOURCE_TABLE = 0x061C34
BATTLE_BACKGROUND_RESOURCE_TABLE = 0x08654C
COMMANDER_COMBAT_POINTER_TABLE = 0x087726
GENERIC_COMBAT_DESCRIPTOR_TABLE = 0x08840A
PORTRAIT_LOOKUP_TABLE = 0x0977A6
ROUTE_FRAGMENT_POINTER_TABLE = 0x0A1124
COMMANDER_NAMES = {
    commander_id: scenario_data.KOREAN_NAME_BY_ID[commander_id]
    for commander_id in range(1, 11)
}
DYNAMIC_LOAD_CALL_OWNERS = {
    0x018220: "battle_background_selector_left",
    0x0182E6: "battle_background_selector_right",
    0x01840C: "battle_background_selector_shared",
    0x01B3F2: "character_portrait_map_status",
    0x01B47E: "combat_sprite_map_status",
    0x01C5C0: "scenario_map_tileset",
    0x01CC90: "character_portrait_battle_status",
    0x01CD20: "battle_background_selector_battle",
    0x01CE1C: "combat_sprite_battle_scene",
    0x021B8A: "character_portrait_menu",
    0x0260B8: "route_map_fragment",
}
BATTLE_VARIANT_CONDITIONS = {
    225: "battle_mode < 9, excluding 4 and 6",
    226: "9 <= battle_mode < 13",
    227: "battle_mode >= 13",
    228: "battle_mode == 4",
    229: "battle_mode == 6",
}
OPENING_ENDING_GROUPS = {
    394: "title_screen_group_02D672",
    395: "title_screen_group_02D672",
    396: "opening_ending_scene_group_02DEE2",
    397: "opening_ending_scene_group_02DEE2",
    398: "opening_ending_scene_group_02DEE2",
    399: "opening_ending_scene_group_02E434",
    400: "opening_ending_scene_group_02E434",
    401: "opening_ending_scene_group_02E434",
    402: "opening_ending_scene_group_02E63A",
    403: "opening_ending_scene_group_02E63A",
    404: "opening_ending_scene_group_02E63A",
    405: "opening_ending_scene_group_02E63A",
    406: "opening_ending_scene_group_02E972",
    407: "opening_ending_scene_group_02E972",
    408: "opening_ending_scene_group_02E972",
    409: "opening_ending_scene_group_02E972",
    410: "opening_ending_scene_group_02E972",
    411: "opening_ending_scene_group_02EF1E",
    412: "opening_ending_scene_group_02F17E",
    413: "opening_ending_scene_group_02F17E",
    414: "opening_ending_scene_group_02F17E",
    415: "title_screen_group_02D672",
    416: "opening_ending_scene_group_02F748",
    417: "opening_ending_scene_group_02FACA",
    418: "opening_ending_scene_group_02FACA",
    419: "opening_ending_scene_group_02FACA",
    420: "opening_ending_scene_group_02FACA",
    421: "opening_ending_scene_group_02F87E",
    422: "opening_ending_scene_group_030C72",
    423: "opening_ending_scene_group_030C72",
    424: "opening_ending_scene_group_02F87E",
    425: "opening_ending_scene_group_02FACA",
    426: "opening_ending_scene_group_02FACA",
    427: "opening_ending_scene_group_030C72",
    428: "opening_ending_scene_group_02F17E",
}
LIVE_VERIFIED_OWNERS = frozenset(
    {
        0,
        builder.BYTE_UI_FONT_RESOURCE_INDEX,
        builder.BATTLE_UI_TERRAIN_RESOURCE_INDEX,
        391,
        392,
        builder.TITLE_LOGO_RESOURCE_INDEX,
    }
)
ASSET_FAMILY_RANGES = (
    (0, 0, "platform_logo"),
    (1, 1, "ui_font"),
    (2, 25, "map_tileset"),
    (26, 46, "battle_background"),
    (47, 222, "combat_sprite"),
    (223, 223, "battle_ui"),
    (224, 230, "battle_scene_graphics"),
    (231, 362, "character_portrait"),
    (363, 389, "small_graphic_fragment"),
    (390, 390, "world_map_graphics"),
    (391, 391, "item_icon_graphics"),
    (392, 392, "publisher_logo"),
    (393, 393, "title_logo_graphics"),
    (394, 428, "opening_ending_graphics"),
)
RAW_TILE_TEXT_SIGNALS = {
    0: "platform_brand_lettering",
    1: "font_glyphs",
    223: "battle_ui_label_tiles",
    392: "publisher_brand_lettering",
    393: "title_lettering",
}


def asset_family(index: int) -> str:
    matches = [
        family
        for first, last, family in ASSET_FAMILY_RANGES
        if first <= index <= last
    ]
    if len(matches) != 1:
        raise ValueError(
            f"compressed resource {index} has {len(matches)} asset-family matches"
        )
    return matches[0]


def be32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def be16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def resource_pointers(data: bytes) -> list[int]:
    first_pointer = be32(data, RESOURCE_TABLE) & 0x00FFFFFF
    table_size = first_pointer - RESOURCE_TABLE
    if table_size <= 0 or table_size % 4:
        raise ValueError(
            f"invalid compressed resource table boundary: 0x{first_pointer:06X}"
        )
    count = table_size // 4
    pointers = [
        be32(data, RESOURCE_TABLE + index * 4) & 0x00FFFFFF
        for index in range(count)
    ]
    if pointers[0] != RESOURCE_TABLE + count * 4:
        raise ValueError("first compressed resource does not immediately follow its table")
    if any(left >= right for left, right in zip(pointers, pointers[1:])):
        raise ValueError("compressed resource pointers are not strictly increasing")
    if pointers[-1] >= len(data):
        raise ValueError("compressed resource table points beyond the ROM")
    return pointers


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def verify_source_locks(data: bytes) -> dict[str, dict[str, object]]:
    report = {}
    for name, (offset, length, expected_sha256) in SOURCE_LOCKS.items():
        actual_sha256 = sha256(data[offset : offset + length])
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"source lock {name} changed: expected {expected_sha256}, "
                f"got {actual_sha256}"
            )
        report[name] = {
            "offset": f"0x{offset:06X}",
            "length": length,
            "sha256": actual_sha256,
        }
    return report


def ownership_index(
    data: bytes,
    calls_by_index: dict[int, list[dict[str, object]]],
    dynamic_call_sites: set[int],
) -> tuple[dict[int, str], dict[int, list[dict[str, object]]], set[int]]:
    expected_dynamic_sites = set(DYNAMIC_LOAD_CALL_OWNERS)
    if dynamic_call_sites != expected_dynamic_sites:
        missing = sorted(expected_dynamic_sites - dynamic_call_sites)
        extra = sorted(dynamic_call_sites - expected_dynamic_sites)
        raise ValueError(
            f"dynamic loader call set changed; missing={missing}, extra={extra}"
        )

    owners: dict[int, str] = {}
    records: dict[int, list[dict[str, object]]] = {
        index: [] for index in range(429)
    }
    unreferenced_candidates = {2, 224}

    def add(index: int, owner: str, **details: object) -> None:
        if not 0 <= index < 429:
            raise ValueError(f"ownership record has invalid resource {index}")
        owners.setdefault(index, owner)
        records[index].append({"owner": owner, **details})

    for index, owner in LIVE_OWNER_LABELS.items():
        add(
            index,
            owner,
            source_kind="live_verified_resource",
            source=(
                f"compressed resource {index} and retained runtime evidence"
            ),
        )

    for scenario in range(1, 32):
        record_offset = SCENARIO_MAP_RESOURCE_TABLE + (scenario - 1) * 4
        for slot in range(2):
            raw_id = be16(data, record_offset + slot * 2)
            index = raw_id & 0x7FFF
            if not 3 <= index <= 25 or not raw_id & 0x8000:
                raise ValueError(
                    f"Scenario {scenario} map slot {slot} has invalid resource "
                    f"0x{raw_id:04X}"
                )
            add(
                index,
                "scenario_map_tileset",
                source_kind="scenario_map_resource_table",
                table_entry=f"0x{record_offset + slot * 2:06X}",
                scenario=scenario,
                slot=slot,
                raw_resource_id=f"0x{raw_id:04X}",
                dynamic_loader_call="0x01C5C0",
            )

    for selector in range(20):
        table_entry = BATTLE_BACKGROUND_RESOURCE_TABLE + selector * 2
        raw_id = be16(data, table_entry)
        index = raw_id & 0x7FFF
        if index != 26 + selector or not raw_id & 0x8000:
            raise ValueError(
                f"battle background selector {selector} changed: 0x{raw_id:04X}"
            )
        add(
            index,
            "battle_background_selector",
            source_kind="battle_background_resource_table",
            table_entry=f"0x{table_entry:06X}",
            selector=selector,
            raw_resource_id=f"0x{raw_id:04X}",
            dynamic_loader_calls=[
                f"0x{site:06X}"
                for site in (0x018220, 0x0182E6, 0x01840C, 0x01CD20)
            ],
        )

    add(
        46,
        "shared_battle_scene_tiles",
        source_kind="tail_call",
        call_site="0x01C5F6",
        raw_resource_id="0x802E",
        destination="0x8000",
    )

    classes = scenario_data.class_names(data)
    for class_id, class_row in enumerate(classes):
        record_offset = GENERIC_COMBAT_DESCRIPTOR_TABLE + class_id * 0x10
        raw_id = be16(data, record_offset)
        index = raw_id & 0x7FFF
        if not 47 <= index <= 154 or not raw_id & 0x8000:
            raise ValueError(
                f"generic combat descriptor class {class_id:02X} has invalid "
                f"resource 0x{raw_id:04X}"
            )
        add(
            index,
            "generic_combat_sprite",
            source_kind="generic_combat_descriptor",
            table_entry=f"0x{record_offset:06X}",
            class_id=class_id,
            class_id_hex=f"0x{class_id:02X}",
            class_jp=class_row["jp"],
            class_ko=class_row["ko"],
            raw_resource_id=f"0x{raw_id:04X}",
            dynamic_loader_calls=["0x01B47E", "0x01CE1C"],
        )

    for commander_id in range(1, 11):
        pointer_entry = COMMANDER_COMBAT_POINTER_TABLE + (commander_id - 1) * 4
        record_offset = be32(data, pointer_entry)
        while True:
            class_id = be16(data, record_offset)
            if class_id == 0xFFFF:
                break
            if not 0 <= class_id < scenario_data.CLASS_COUNT:
                raise ValueError(
                    f"commander {commander_id} combat override has invalid class "
                    f"0x{class_id:04X}"
                )
            raw_id = be16(data, record_offset + 2)
            index = raw_id & 0x7FFF
            if not 154 <= index <= 222 or not raw_id & 0x8000:
                raise ValueError(
                    f"commander {commander_id} class {class_id:02X} has invalid "
                    f"combat resource 0x{raw_id:04X}"
                )
            add(
                index,
                "commander_combat_sprite",
                source_kind="commander_combat_override",
                pointer_entry=f"0x{pointer_entry:06X}",
                table_entry=f"0x{record_offset:06X}",
                commander_id=commander_id,
                commander_name=COMMANDER_NAMES[commander_id],
                class_id=class_id,
                class_id_hex=f"0x{class_id:02X}",
                class_jp=classes[class_id]["jp"],
                class_ko=classes[class_id]["ko"],
                raw_resource_id=f"0x{raw_id:04X}",
                dynamic_loader_calls=["0x01B47E", "0x01CE1C"],
            )
            record_offset += 0x12

    add(
        builder.BATTLE_UI_TERRAIN_RESOURCE_INDEX,
        "battle_ui_terrain",
        source_kind="immediate_loader_calls",
        loader_calls=calls_by_index[builder.BATTLE_UI_TERRAIN_RESOURCE_INDEX],
    )
    for index, condition in BATTLE_VARIANT_CONDITIONS.items():
        add(
            index,
            "battle_scene_layout_variant",
            source_kind="battle_variant_loader",
            selector_address="0xFFFFAECC",
            condition=condition,
            loader_calls=calls_by_index[index],
        )
    add(
        230,
        "battle_scene_shared_overlay",
        source_kind="immediate_loader_calls",
        loader_calls=calls_by_index[230],
    )

    for lookup_id, lookup_value in enumerate(
        data[PORTRAIT_LOOKUP_TABLE : PORTRAIT_LOOKUP_TABLE + 0x100]
    ):
        index = 230 + lookup_value
        if not 231 <= index <= 362:
            raise ValueError(
                f"portrait lookup {lookup_id:02X} has invalid value {lookup_value}"
            )
        name = (
            scenario_data.name_for_id(data, lookup_id)
            if lookup_id < scenario_data.NAME_COUNT
            else {"jp": "", "ko": ""}
        )
        add(
            index,
            "character_portrait",
            source_kind="portrait_lookup_table",
            table_entry=f"0x{PORTRAIT_LOOKUP_TABLE + lookup_id:06X}",
            lookup_id=lookup_id,
            lookup_id_hex=f"0x{lookup_id:02X}",
            lookup_value=lookup_value,
            name_jp=name["jp"],
            name_ko=name["ko"],
            dynamic_loader_calls=["0x01B3F2", "0x01CC90", "0x021B8A"],
        )

    for scenario in range(1, 32):
        pointer_entry = ROUTE_FRAGMENT_POINTER_TABLE + (scenario - 1) * 4
        descriptor = be32(data, pointer_entry)
        raw_id = be16(data, descriptor)
        index = raw_id & 0x7FFF
        destination = be16(data, descriptor + 2)
        tile_run_count = be16(data, descriptor + 4)
        if not 363 <= index <= 387 or not raw_id & 0x8000:
            raise ValueError(
                f"route descriptor {scenario} has invalid resource 0x{raw_id:04X}"
            )
        add(
            index,
            "route_map_fragment",
            source_kind="route_fragment_descriptor",
            pointer_entry=f"0x{pointer_entry:06X}",
            descriptor=f"0x{descriptor:06X}",
            route_position=scenario,
            raw_resource_id=f"0x{raw_id:04X}",
            destination=f"0x{destination:04X}",
            tile_run_count=tile_run_count,
            dynamic_loader_call="0x0260B8",
        )

    add(
        388,
        "shared_ui_marker_tiles",
        source_kind="immediate_loader_calls",
        decoded_tile_count=4,
        loader_calls=calls_by_index[388],
    )
    add(
        389,
        "shared_ui_pattern_tiles",
        source_kind="immediate_loader_calls",
        decoded_tile_count=12,
        loader_calls=calls_by_index[389],
    )
    add(
        390,
        "world_map_graphics",
        source_kind="immediate_loader_call",
        loader_calls=calls_by_index[390],
    )
    add(
        391,
        "item_icons",
        source_kind="immediate_loader_call",
        loader_calls=calls_by_index[391],
    )
    add(
        392,
        "masaya_publisher_logo",
        source_kind="immediate_loader_call",
        loader_calls=calls_by_index[392],
    )
    add(
        393,
        "title_logo",
        source_kind="immediate_loader_call",
        loader_calls=calls_by_index[393],
    )
    for index, group in OPENING_ENDING_GROUPS.items():
        add(
            index,
            group,
            source_kind="immediate_opening_ending_loader_group",
            loader_calls=calls_by_index[index],
        )

    for index, owner in (
        (2, "unreferenced_map_graphic_candidate"),
        (224, "unreferenced_battle_graphic_candidate"),
    ):
        if calls_by_index.get(index):
            raise ValueError(f"unreferenced candidate {index} has an immediate call")
        add(
            index,
            owner,
            source_kind="loader_reachability_audit",
            direct_immediate_calls=[],
            reachable_dynamic_sources=[],
            audited_wrapper_call_count=75,
            status="no_reference_found",
        )

    missing = [index for index, rows in records.items() if not rows]
    if missing:
        raise ValueError(f"compressed resources lack ownership records: {missing}")
    return owners, records, unreferenced_candidates


def resource_output_size(data: bytes, pointer: int) -> int:
    resource_type = data[pointer]
    if resource_type in (1, 3):
        return be16(data, pointer + 1)
    if resource_type == 2:
        header = data[pointer + 1]
        width = header & 0x7F
        length_offset = pointer + 2 + (8 if header & 0x80 else 0)
        encoded_plane_length = be16(data, length_offset)
        return width * encoded_plane_length * 8
    raise ValueError(f"unsupported resource type {resource_type} at 0x{pointer:06X}")


def resource_encoded_end(data: bytes, pointer: int) -> int:
    """Return the first byte after one encoded resource."""
    resource_type = data[pointer]
    if resource_type == 1:
        remaining_nibbles = be16(data, pointer + 1) * 2
        pos = pointer + 3
        high_nibble = True
        previous = 0x7F
        output_nibbles = 0

        def read_nibble() -> int:
            nonlocal pos, high_nibble
            if high_nibble:
                value = data[pos] >> 4
                high_nibble = False
            else:
                value = data[pos] & 0x0F
                pos += 1
                high_nibble = True
            return value

        while output_nibbles < remaining_nibbles:
            value = read_nibble()
            if value == previous:
                output_nibbles += read_nibble() + 1
            else:
                previous = value
                output_nibbles += 1
        if output_nibbles != remaining_nibbles:
            raise ValueError(
                f"type 1 resource at 0x{pointer:06X} overruns its output size"
            )
        return pos if high_nibble else pos + 1

    if resource_type == 2:
        header = data[pointer + 1]
        width = header & 0x7F
        if width not in (1, 2, 4):
            raise ValueError(
                f"unsupported type 2 width {width} at 0x{pointer:06X}"
            )
        pos = pointer + 2 + (8 if header & 0x80 else 0)
        mask_length = be16(data, pos)
        mask_pos = pos + 2
        mask_end = mask_pos + mask_length
        value_pos = mask_end
        groups_per_tile = {1: 4, 2: 2, 4: 1}[width]
        while mask_pos < mask_end:
            for _ in range(groups_per_tile):
                mask = data[mask_pos]
                mask_pos += 1
                for _ in range(8):
                    if mask & 0x80:
                        value_pos += width
                    mask = (mask << 1) & 0xFF
        return value_pos

    if resource_type == 3:
        remaining = be16(data, pointer + 1)
        pos = pointer + 3
        while remaining > 0:
            flags = data[pos]
            pos += 1
            for _ in range(8):
                if flags & 1:
                    pos += 1
                    remaining -= 1
                else:
                    count = (data[pos + 1] & 0x0F) + 3
                    pos += 2
                    remaining -= min(count, remaining)
                flags >>= 1
                if remaining <= 0:
                    break
        return pos

    raise ValueError(
        f"unsupported resource type {resource_type} at 0x{pointer:06X}"
    )


def decompress_type1(data: bytes, pointer: int) -> bytes:
    expected_size = be16(data, pointer + 1)
    pos = pointer + 3
    high_nibble = True
    previous = 0x7F
    nibbles: list[int] = []

    def read_nibble() -> int:
        nonlocal pos, high_nibble
        if high_nibble:
            value = data[pos] >> 4
            high_nibble = False
        else:
            value = data[pos] & 0x0F
            pos += 1
            high_nibble = True
        return value

    while len(nibbles) < expected_size * 2:
        value = read_nibble()
        if value == previous:
            nibbles.extend([previous] * (read_nibble() + 1))
        else:
            previous = value
            nibbles.append(value)
    if len(nibbles) != expected_size * 2:
        raise ValueError(f"type 1 resource at 0x{pointer:06X} overruns its output size")
    return bytes(
        (nibbles[index] << 4) | nibbles[index + 1]
        for index in range(0, len(nibbles), 2)
    )


def decompress_type2(data: bytes, pointer: int) -> bytes:
    header = data[pointer + 1]
    width = header & 0x7F
    if width not in (1, 2, 4):
        raise ValueError(f"unsupported type 2 width {width} at 0x{pointer:06X}")
    pos = pointer + 2
    palette = None
    if header & 0x80:
        palette = []
        for value in data[pos : pos + 8]:
            palette.extend((value >> 4, value & 0x0F))
        pos += 8
    mask_length = be16(data, pos)
    pos += 2
    mask_pos = pos
    mask_end = mask_pos + mask_length
    value_pos = mask_end
    groups_per_tile = {1: 4, 2: 2, 4: 1}[width]
    output = bytearray()

    def shift_word(workspace: bytearray, offset: int) -> int:
        value = (workspace[offset] << 8) | workspace[offset + 1]
        carry = (value >> 15) & 1
        value = (value << 1) & 0xFFFF
        workspace[offset] = value >> 8
        workspace[offset + 1] = value & 0xFF
        return carry

    while mask_pos < mask_end:
        workspace = bytearray()
        for _ in range(groups_per_tile):
            mask = data[mask_pos]
            mask_pos += 1
            for _ in range(8):
                if mask & 0x80:
                    workspace.extend(data[value_pos : value_pos + width])
                    value_pos += width
                else:
                    workspace.extend(bytes(width))
                mask = (mask << 1) & 0xFF
        if len(workspace) != 32:
            raise ValueError(f"type 2 workspace length mismatch at 0x{pointer:06X}")

        for base in range(0, 8, 2):
            if palette is None:
                for _ in range(4):
                    value = 0
                    for _ in range(4):
                        for plane_offset in (24, 8, 16, 0):
                            value = (value << 1) | shift_word(workspace, base + plane_offset)
                    output.extend(value.to_bytes(2, "big"))
            else:
                for _ in range(4):
                    value = 0
                    for _ in range(4):
                        palette_index = 0
                        for plane_offset in (24, 8, 16, 0):
                            palette_index = (
                                (palette_index << 1)
                                | shift_word(workspace, base + plane_offset)
                            )
                        value = (value << 4) | palette[palette_index]
                    output.extend(value.to_bytes(2, "big"))

    expected_size = resource_output_size(data, pointer)
    if len(output) != expected_size:
        raise ValueError(
            f"type 2 resource at 0x{pointer:06X} produced {len(output)}, expected {expected_size}"
        )
    return bytes(output)


def decoded_payload(data: bytes, pointer: int) -> bytes | None:
    resource_type = data[pointer]
    if resource_type == 1:
        return decompress_type1(data, pointer)
    if resource_type == 2:
        return decompress_type2(data, pointer)
    if resource_type == 3:
        return builder.decompress_9dfe(data, pointer + 1)
    return None


def direct_load_calls(data: bytes) -> list[dict[str, object]]:
    jsr = bytes.fromhex("4E B9") + RESOURCE_LOAD_ROUTINE.to_bytes(4, "big")
    calls = []
    offset = 0
    while True:
        call_site = data.find(jsr, offset)
        if call_site < 0:
            return calls
        prefix = data[call_site - 8 : call_site]
        row: dict[str, object] = {
            "call_site": f"0x{call_site:06X}",
            "immediate_resource": False,
            "resource_index": None,
            "raw_resource_id": None,
            "high_bit_flag": None,
            "destination": None,
        }
        if (
            len(prefix) == 8
            and prefix[0:2] == bytes.fromhex("30 3C")
            and prefix[4:6] == bytes.fromhex("32 7C")
        ):
            raw_id = int.from_bytes(prefix[2:4], "big")
            row.update(
                {
                    "immediate_resource": True,
                    "resource_index": raw_id & 0x7FFF,
                    "raw_resource_id": f"0x{raw_id:04X}",
                    "high_bit_flag": bool(raw_id & 0x8000),
                    "destination": f"0x{int.from_bytes(prefix[6:8], 'big'):04X}",
                }
            )
        calls.append(row)
        offset = call_site + 1


def inventory(japanese: bytes, korean: bytes) -> dict[str, object]:
    source_locks = verify_source_locks(japanese)
    original_pointers = resource_pointers(japanese)
    count = len(original_pointers)
    if count != 429:
        raise ValueError(f"expected 429 compressed resources, got {count}")
    calls = direct_load_calls(japanese)
    calls_by_index: dict[int, list[dict[str, object]]] = {}
    for call in calls:
        if call["immediate_resource"]:
            calls_by_index.setdefault(int(call["resource_index"]), []).append(call)
    dynamic_call_sites = {
        int(str(call["call_site"]), 16)
        for call in calls
        if not call["immediate_resource"]
    }
    owners, ownership_records, unreferenced_candidates = ownership_index(
        japanese, calls_by_index, dynamic_call_sites
    )
    current_pointers = [
        be32(korean, RESOURCE_TABLE + index * 4) & 0x00FFFFFF
        for index in range(count)
    ]
    entries = []
    type_counts: dict[str, int] = {}
    total_output_bytes = 0
    decoded_counts: dict[str, int] = {}
    for index, (original_pointer, current_pointer) in enumerate(
        zip(original_pointers, current_pointers)
    ):
        original_type = japanese[original_pointer]
        current_type = korean[current_pointer]
        original_size = resource_output_size(japanese, original_pointer)
        current_size = resource_output_size(korean, current_pointer)
        original_payload = decoded_payload(japanese, original_pointer)
        current_payload = decoded_payload(korean, current_pointer)
        original_hash = None if original_payload is None else sha256(original_payload)
        current_hash = None if current_payload is None else sha256(current_payload)
        if original_payload is not None:
            if len(original_payload) != original_size:
                raise ValueError(f"resource {index} output length mismatch")
            type_key = str(original_type)
            decoded_counts[type_key] = decoded_counts.get(type_key, 0) + 1
        if current_payload is not None and len(current_payload) != current_size:
            raise ValueError(f"current resource {index} output length mismatch")
        pointer_modified = original_pointer != current_pointer
        if original_type != current_type or original_size != current_size:
            content_modified: bool | None = True
        elif original_hash is not None and current_hash is not None:
            content_modified = original_hash != current_hash
        elif pointer_modified:
            content_modified = None
        else:
            block_end = (
                original_pointers[index + 1]
                if index + 1 < count
                else len(japanese)
            )
            content_modified = (
                japanese[original_pointer:block_end]
                != korean[original_pointer:block_end]
            )
        type_key = str(original_type)
        type_counts[type_key] = type_counts.get(type_key, 0) + 1
        total_output_bytes += original_size
        entries.append(
            {
                "index": index,
                "table_entry": f"0x{RESOURCE_TABLE + index * 4:06X}",
                "original_pointer": f"0x{original_pointer:06X}",
                "current_pointer": f"0x{current_pointer:06X}",
                "original_type": original_type,
                "current_type": current_type,
                "decoder_routine": f"0x{RESOURCE_DECODER_ROUTINES[original_type]:06X}",
                "original_output_size": original_size,
                "current_output_size": current_size,
                "original_decoded_sha256": original_hash,
                "current_decoded_sha256": current_hash,
                "pointer_modified": pointer_modified,
                "content_modified": content_modified,
                "modified": pointer_modified or content_modified is True,
                "owner": owners.get(index),
                "owner_status": (
                    "unreferenced_candidate"
                    if index in unreferenced_candidates
                    else (
                        "live_verified"
                        if index in LIVE_VERIFIED_OWNERS
                        else "source_traced"
                    )
                ),
                "ownership_record_count": len(ownership_records[index]),
                "ownership_records": ownership_records[index],
                "structurally_verified": True,
                "asset_family": asset_family(index),
                "raw_tile_visual_reviewed": True,
                "raw_tile_text_signal": RAW_TILE_TEXT_SIGNALS.get(index),
                "direct_immediate_call_count": len(calls_by_index.get(index, [])),
                "direct_immediate_calls": calls_by_index.get(index, []),
                "reviewed": index in LIVE_VERIFIED_OWNERS,
                "live_verified": index in LIVE_VERIFIED_OWNERS,
            }
        )
    return {
        "warning": (
            "A valid resource record is not necessarily text or UI. Type 1 RLE, "
            "type 2 tile-plane, and type 3 LZSS records are decoded by this tool. "
            "Ownership is recorded only when established from source-locked tables, "
            "loader paths, or retained live evidence. Resources 2 and 224 are "
            "explicit no-reference candidates, not claimed runtime assets."
        ),
        "source_locks": source_locks,
        "resource_table": f"0x{RESOURCE_TABLE:06X}",
        "table_end": f"0x{original_pointers[0]:06X}",
        "entry_count": count,
        "type_counts": type_counts,
        "total_original_output_bytes": total_output_bytes,
        "decoded_counts": decoded_counts,
        "modified_count": sum(bool(entry["modified"]) for entry in entries),
        "known_owner_count": sum(entry["owner"] is not None for entry in entries),
        "unknown_owner_count": sum(entry["owner"] is None for entry in entries),
        "source_traced_owner_count": sum(
            entry["owner_status"] == "source_traced" for entry in entries
        ),
        "live_verified_owner_count": sum(
            entry["owner_status"] == "live_verified" for entry in entries
        ),
        "unreferenced_candidate_count": sum(
            entry["owner_status"] == "unreferenced_candidate" for entry in entries
        ),
        "ownership_record_count": sum(
            int(entry["ownership_record_count"]) for entry in entries
        ),
        "owner_counts": {
            owner: sum(entry["owner"] == owner for entry in entries)
            for owner in dict.fromkeys(str(entry["owner"]) for entry in entries)
        },
        "asset_family_counts": {
            family: sum(entry["asset_family"] == family for entry in entries)
            for family in dict.fromkeys(
                family for _, _, family in ASSET_FAMILY_RANGES
            )
        },
        "raw_tile_visual_reviewed_count": sum(
            bool(entry["raw_tile_visual_reviewed"]) for entry in entries
        ),
        "raw_tile_text_signal_count": sum(
            entry["raw_tile_text_signal"] is not None for entry in entries
        ),
        "loader_routines": {
            "load": f"0x{RESOURCE_LOAD_ROUTINE:06X}",
            "dispatch": f"0x{RESOURCE_DISPATCH_ROUTINE:06X}",
            "lookup": f"0x{RESOURCE_LOOKUP_ROUTINE:06X}",
            "decoders": {
                str(resource_type): f"0x{routine:06X}"
                for resource_type, routine in RESOURCE_DECODER_ROUTINES.items()
            },
        },
        "direct_load_call_count": len(calls),
        "immediate_load_call_count": sum(bool(call["immediate_resource"]) for call in calls),
        "dynamic_load_call_count": sum(not bool(call["immediate_resource"]) for call in calls),
        "dynamic_load_call_owners": {
            f"0x{call_site:06X}": owner
            for call_site, owner in DYNAMIC_LOAD_CALL_OWNERS.items()
        },
        "immediate_referenced_resource_count": len(calls_by_index),
        "direct_load_calls": calls,
        "entries": entries,
    }


def markdown_report(result: dict[str, object]) -> str:
    lines = [
        "# Compressed Resource Inventory",
        "",
        "Generated by `python3 tools/jp_compressed_resource_inventory.py`.",
        "",
        "The table boundary is derived from its first pointer. All records have a valid",
        "type and output size. Type 1 RLE, type 2 tile-plane, and type 3 `0x9DFE`",
        "records are all decoded and hashed with their format-specific routines.",
        "A valid record does not establish that it contains text or UI data.",
        "",
        f"- Resource table: `{result['resource_table']}`",
        f"- Table end / first resource: `{result['table_end']}`",
        f"- Entries: {result['entry_count']}",
        f"- Total calculated output bytes: {result['total_original_output_bytes']:,}",
        "- Decoded and hashed by type: "
        + ", ".join(
            f"type {resource_type}: {count}"
            for resource_type, count in sorted(result["decoded_counts"].items())
        ),
        f"- Modified resources in current build: {result['modified_count']}",
        f"- Known owners: {result['known_owner_count']}",
        f"- Unknown owners: {result['unknown_owner_count']}",
        f"- Source-traced owners: {result['source_traced_owner_count']}",
        f"- Retained live-verified owners: {result['live_verified_owner_count']}",
        f"- No-reference candidates: {result['unreferenced_candidate_count']}",
        f"- Exact ownership records: {result['ownership_record_count']}",
        f"- Broad asset families reviewed in raw tile order: "
        f"{result['raw_tile_visual_reviewed_count']}",
        f"- Raw tile text/lettering signals: {result['raw_tile_text_signal_count']}",
        f"- Direct loader calls: {result['direct_load_call_count']}",
        f"- Immediate-ID calls: {result['immediate_load_call_count']}",
        f"- Dynamic-ID calls: {result['dynamic_load_call_count']}",
        f"- Resources reached by immediate ID: {result['immediate_referenced_resource_count']}",
        "",
        "## Loader Code",
        "",
        f"- Load wrapper: `{result['loader_routines']['load']}`",
        f"- Type dispatcher: `{result['loader_routines']['dispatch']}`",
        f"- Table lookup: `{result['loader_routines']['lookup']}`",
        "- Decoder routines: "
        + ", ".join(
            f"type {resource_type} `{address}`"
            for resource_type, address in result["loader_routines"]["decoders"].items()
        ),
        "",
        "The lookup routine masks the high flag bit, multiplies the remaining ID by four,",
        "and reads `0x0B0000[index]`. Immediate calls are linked to resource entries; dynamic",
        "calls are tied to their source-locked selector tables and descriptor routines.",
        "",
        "## Source-Locked Ownership",
        "",
        "| Source range | Offset | Length | SHA-256 |",
        "| --- | --- | ---: | --- |",
    ]
    for name, row in result["source_locks"].items():
        lines.append(
            f"| `{name}` | `{row['offset']}` | {row['length']} | "
            f"`{row['sha256']}` |"
        )
    lines.extend(
        [
            "",
            "All 11 dynamic wrapper calls have an exact producer:",
            "",
            "| Call | Producer |",
            "| --- | --- |",
        ]
    )
    for call_site, owner in result["dynamic_load_call_owners"].items():
        lines.append(f"| `{call_site}` | `{owner}` |")
    lines.extend(
        [
            "",
            "The ownership records cover Scenario 1-31 map descriptors, all 20 battle",
            "background selectors, all 157 generic class combat descriptors, all ten",
            "commander override lists, all 256 portrait lookup IDs, all 31 route-map",
            "fragment descriptors, and every immediate opening/ending scene load.",
            "Resources 2 and 224 have no immediate call and do not occur in any of those",
            "dynamic producer tables. They remain explicit no-reference candidates instead",
            "of being assigned a guessed live purpose.",
            "",
            "### Primary Owner Counts",
            "",
            "| Owner | Resources |",
            "| --- | ---: |",
        ]
    )
    for owner, count in result["owner_counts"].items():
        lines.append(f"| `{owner}` | {count} |")
    lines.extend(
        [
            "",
            "## Raw Tile Atlas Review",
            "",
            "Run `python3 tools/render_compressed_resource_atlas.py` to render the 50",
            "resources reached by immediate-ID loader calls, or pass `--indices 0-428`",
            "to render the complete table. The atlas uses raw decompressed 4bpp tile order,",
            "so it can separate broad graphics families and expose obvious lettering but",
            "does not reconstruct tile maps, palettes, animation frames, or exact runtime",
            "ownership by itself. Exact ownership above comes from code and tables, not atlas",
            "appearance. Absence of readable Japanese in this view is not translation proof.",
            "",
            "| Asset family | Resources |",
            "| --- | ---: |",
        ]
    )
    for family, count in result["asset_family_counts"].items():
        lines.append(f"| `{family}` | {count} |")
    lines.extend(
        [
            "",
            "Obvious lettering/font signals in raw tile order:",
            "",
            "| Index | Family | Signal | Owner |",
            "| ---: | --- | --- | --- |",
        ]
    )
    for entry in result["entries"]:
        if entry["raw_tile_text_signal"] is None:
            continue
        owner_cell = f"`{entry['owner']}`" if entry["owner"] else ""
        lines.append(
            f"| {entry['index']} | `{entry['asset_family']}` | "
            f"`{entry['raw_tile_text_signal']}` | {owner_cell} |"
        )
    lines.extend(
        [
            "",
        "## Type Distribution",
        "",
        "| Type byte | Entries |",
        "| ---: | ---: |",
        ]
    )
    for resource_type, count in sorted(
        result["type_counts"].items(), key=lambda item: int(item[0])
    ):
        lines.append(f"| `0x{int(resource_type):02X}` | {count} |")
    lines.extend(
        [
            "",
            "## Per-Resource Ownership",
            "",
            "| Index | Owner | Status | Records | Original | Current | Type | Size | Modified |",
            "| ---: | --- | --- | ---: | --- | --- | ---: | ---: | --- |",
        ]
    )
    for entry in result["entries"]:
        lines.append(
            f"| {entry['index']} | `{entry['owner']}` | `{entry['owner_status']}` | "
            f"{entry['ownership_record_count']} | `{entry['original_pointer']}` | "
            f"`{entry['current_pointer']}` | `0x{entry['original_type']:02X}` | "
            f"{entry['original_output_size']} | {entry['modified']} |"
        )
    lines.extend(
        [
            "",
            "All pointers, output sizes, decoded hashes, ownership fields, and review flags",
            "are in `localization/compressed_resources.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory the typed compressed resource table")
    parser.add_argument("--jp-rom", type=Path, default=Path("roms/original/Langrisser II (Japan).md"))
    parser.add_argument(
        "--ko-rom",
        type=Path,
        default=Path("roms/builds/Langrisser II (Korean).md"),
    )
    parser.add_argument("--json", type=Path, default=Path("localization/compressed_resources.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/compressed_resource_inventory.md"))
    args = parser.parse_args()
    result = inventory(args.jp_rom.read_bytes(), args.ko_rom.read_bytes())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['entry_count']} resources inventoried; "
        f"{sum(result['decoded_counts'].values())} decoded; "
        f"{result['modified_count']} modified; {result['unknown_owner_count']} owners unknown"
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build a byte-locked Scenario 1 mounted-lord combat diagnostic ROM.

The probe changes only the stock end-turn class-change entry, its diagnostic
wrappers, the join visibility compare, and Bald's Scenario 1 placement.  It
never changes production class, sprite, combat, text, or event data.  The
returned manifest records every byte that differs from the exact input ROM so
the runtime runner can verify the derivative again immediately before launch.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import build_class_change_probe_rom as class_probe
from tools.class_change_data import read_class_change_chain
from tools.class_hire_data import CLASS_RECORD_SIZE, CLASS_RECORD_TABLE
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Mounted Lord Combat Probe).md"
)
DEFAULT_MANIFEST = DEFAULT_OUTPUT_ROM.with_suffix(".json")

SCENARIO_NUMBER = 1
BALD_RECORD_INDEX = 8
BALD_NAME_ID = 0x12
BALD_CLASS_ID = 0x2E
BALD_SIDE = 0x04
PROBE_BALD_X = 11
PROBE_BALD_Y = 16
PROBE_BALD_AT = 0
PROBE_BALD_DF = 0
PROBE_TRIGGER_CLASS = 0x01
PROBE_RUNTIME_RECORD_INDEX = 0
CHECKSUM_RANGE = range(0x18E, 0x190)


@dataclass(frozen=True)
class MountedLordCase:
    key: str
    commander_id: int
    commander_name: str
    class_id: int
    class_name: str
    source_class_id: int
    candidates: tuple[int, int, int]
    wrong_stats_class_id: int
    forbidden_generic_resource_id: int
    expected_commander_resource_id: int
    expected_runtime_stats: bytes


CASES = {
    "keith": MountedLordCase(
        key="keith",
        commander_id=7,
        commander_name="Keith",
        class_id=builder.JOIN_CLASS_CHOICE_HAWK_LORD,
        class_name="Hawk Lord",
        source_class_id=0x06,
        candidates=(0x04, builder.JOIN_CLASS_CHOICE_HAWK_LORD, 0x08),
        wrong_stats_class_id=0x0F,
        # The unused Japanese 0x2B generic row is the Cleric/Sister fallback
        # that v1.3.5 reached when the commander override lacked an alias.
        forbidden_generic_resource_id=0x8097,
        expected_commander_resource_id=0x80CE,
        # Runtime offsets 0x44..0x47: MV, auxiliary, A+, D+.
        expected_runtime_stats=bytes.fromhex("08 03 02 06"),
    ),
    "lester": MountedLordCase(
        key="lester",
        commander_id=9,
        commander_name="Lester",
        class_id=builder.JOIN_CLASS_CHOICE_CROCO_LORD,
        class_name="Croco Lord",
        source_class_id=0x07,
        candidates=(0x05, builder.JOIN_CLASS_CHOICE_CROCO_LORD, 0x0A),
        wrong_stats_class_id=0x10,
        # The unused Japanese 0x2C generic row is the Vampire fallback.
        forbidden_generic_resource_id=0x8096,
        expected_commander_resource_id=0x80DC,
        expected_runtime_stats=bytes.fromhex("06 03 05 05"),
    ),
}


@dataclass(frozen=True)
class WriteRegion:
    label: str
    start: int
    end: int

    def offsets(self) -> range:
        return range(self.start, self.end)


def sha256(payload: bytes | bytearray) -> str:
    return hashlib.sha256(payload).hexdigest()


def md_checksum(payload: bytes | bytearray) -> int:
    return builder.be16(payload, 0x18E)


def be16(payload: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(payload[offset : offset + 2], "big")


def commander_combat_records(
    payload: bytes | bytearray,
    commander_id: int,
) -> dict[int, tuple[int, bytes]]:
    pointer_offset = (
        builder.COMMANDER_COMBAT_POINTER_TABLE + (commander_id - 1) * 4
    )
    pointer = builder.be32(payload, pointer_offset)
    records: dict[int, tuple[int, bytes]] = {}
    for _ in range(64):
        class_id = be16(payload, pointer)
        if class_id == 0xFFFF:
            return records
        if class_id in records:
            raise ValueError(
                f"commander {commander_id} repeats combat class "
                f"0x{class_id:02X}"
            )
        end = pointer + builder.COMMANDER_COMBAT_RECORD_SIZE
        record = bytes(payload[pointer:end])
        if len(record) != builder.COMMANDER_COMBAT_RECORD_SIZE:
            raise ValueError("commander combat override is truncated")
        records[class_id] = (pointer, record)
        pointer = end
    raise ValueError("commander combat override lacks an FFFF sentinel")


def class_record(payload: bytes | bytearray, class_id: int) -> bytes:
    start = CLASS_RECORD_TABLE + class_id * CLASS_RECORD_SIZE
    return bytes(payload[start : start + CLASS_RECORD_SIZE])


def generic_combat_record(
    payload: bytes | bytearray,
    class_id: int,
) -> bytes:
    start = (
        builder.GENERIC_COMBAT_DESCRIPTOR_TABLE
        + class_id * builder.GENERIC_COMBAT_DESCRIPTOR_SIZE
    )
    return bytes(
        payload[start : start + builder.GENERIC_COMBAT_DESCRIPTOR_SIZE]
    )


def map_sprite_id(
    payload: bytes | bytearray,
    commander_id: int,
    class_id: int,
) -> int:
    record = builder.commander_sprite_record_offset(
        payload,
        commander_id,
        class_id,
    )
    return builder.be16(payload, record + 1)


def map_sprite_frames(payload: bytes | bytearray, sprite_id: int) -> tuple[bytes, ...]:
    return tuple(
        bytes(
            payload[
                base + sprite_id * builder.MAP_SPRITE_BYTES :
                base + (sprite_id + 1) * builder.MAP_SPRITE_BYTES
            ]
        )
        for base in builder.MAP_SPRITE_FRAME_BASES
    )


def production_contract(
    payload: bytes | bytearray,
    source: bytes | bytearray,
    case: MountedLordCase,
) -> dict[str, object]:
    """Validate every production surface that the runtime probe relies on."""
    if len(payload) != 0x400000:
        raise ValueError(
            f"input ROM must be an expanded 4 MiB build, got 0x{len(payload):X}"
        )
    if len(source) < 0x200000:
        raise ValueError("Japanese source ROM is truncated")

    transition = read_class_change_chain(payload, case.commander_id)[0]
    if transition.current_class != PROBE_TRIGGER_CLASS:
        raise ValueError(
            f"{case.commander_name} first transition no longer starts at Fighter"
        )
    if transition.candidates != case.candidates:
        raise ValueError(
            f"{case.commander_name} first candidates changed: "
            f"{transition.candidates!r}"
        )

    actual_class = class_record(payload, case.class_id)
    mounted_class = class_record(source, case.source_class_id)
    wrong_class = class_record(source, case.wrong_stats_class_id)
    if actual_class != mounted_class:
        raise ValueError(
            f"{case.class_name} class record no longer aliases mounted "
            f"source 0x{case.source_class_id:02X}"
        )
    if actual_class == wrong_class:
        raise ValueError(
            f"{case.class_name} still aliases wrong class "
            f"0x{case.wrong_stats_class_id:02X}"
        )

    actual_generic = generic_combat_record(payload, case.class_id)
    mounted_generic = generic_combat_record(source, case.source_class_id)
    if actual_generic != mounted_generic:
        raise ValueError(
            f"{case.class_name} generic combat descriptor is not mounted"
        )
    original_generic = generic_combat_record(source, case.class_id)
    if be16(original_generic, 0) != case.forbidden_generic_resource_id:
        raise ValueError(
            f"Japanese {case.class_name} fallback resource changed"
        )
    if actual_generic == original_generic:
        raise ValueError(f"{case.class_name} still uses its unrelated fallback")

    records = commander_combat_records(payload, case.commander_id)
    try:
        custom_offset, custom_combat = records[case.class_id]
        source_offset, source_combat = records[case.source_class_id]
    except KeyError as exc:
        raise ValueError(
            f"{case.commander_name} combat override lacks mounted alias"
        ) from exc
    if custom_combat[2:] != source_combat[2:]:
        raise ValueError(
            f"{case.commander_name} {case.class_name} combat override differs "
            "from its mounted source"
        )
    if be16(custom_combat, 2) != case.expected_commander_resource_id:
        raise ValueError(
            f"{case.commander_name} {case.class_name} combat resource changed"
        )

    custom_sprite = map_sprite_id(payload, case.commander_id, case.class_id)
    source_sprite = map_sprite_id(
        payload,
        case.commander_id,
        case.source_class_id,
    )
    wrong_sprite = map_sprite_id(
        payload,
        case.commander_id,
        case.wrong_stats_class_id,
    )
    if custom_sprite != source_sprite:
        raise ValueError(
            f"{case.class_name} map sprite is not its reviewed mounted design"
        )
    if custom_sprite == wrong_sprite:
        raise ValueError(
            f"{case.class_name} map sprite still aliases wrong class "
            f"0x{case.wrong_stats_class_id:02X}"
        )
    frames = map_sprite_frames(payload, custom_sprite)
    wrong_frames = map_sprite_frames(payload, wrong_sprite)
    if not all(any(frame) for frame in frames):
        raise ValueError(f"{case.class_name} map sprite frame is blank")
    if frames == wrong_frames:
        raise ValueError(f"{case.class_name} map frames equal the wrong class")

    layout = scenario_layout(payload, SCENARIO_NUMBER)
    if layout.record_count != 12:
        raise ValueError("Scenario 1 fixed-record count changed")
    bald = layout.records_offset + BALD_RECORD_INDEX * FIXED_RECORD_SIZE
    if payload[bald + FIELD_OFFSETS["name_id"]] != BALD_NAME_ID:
        raise ValueError("Scenario 1 Bald name changed")
    if payload[bald + FIELD_OFFSETS["class_id"]] != BALD_CLASS_ID:
        raise ValueError("Scenario 1 Bald class changed")
    if payload[bald + 0x08] != BALD_SIDE:
        raise ValueError("Scenario 1 Bald side changed")

    return {
        "commander_id": case.commander_id,
        "class_id": f"0x{case.class_id:02X}",
        "source_class_id": f"0x{case.source_class_id:02X}",
        "wrong_stats_class_id": f"0x{case.wrong_stats_class_id:02X}",
        "class_record_sha256": sha256(actual_class),
        "generic_combat_sha256": sha256(actual_generic),
        "commander_combat_record": f"0x{custom_offset:06X}",
        "commander_combat_resource_id": (
            f"0x{case.expected_commander_resource_id:04X}"
        ),
        "forbidden_generic_resource_id": (
            f"0x{case.forbidden_generic_resource_id:04X}"
        ),
        "map_sprite_id": f"0x{custom_sprite:04X}",
        "wrong_map_sprite_id": f"0x{wrong_sprite:04X}",
        "map_frame_sha256": [sha256(frame) for frame in frames],
        "scenario1_bald_record": f"0x{bald:06X}",
    }


def diagnostic_regions(
    payload: bytes | bytearray,
    source: bytes | bytearray,
    case: MountedLordCase,
) -> tuple[WriteRegion, ...]:
    wrapper = class_probe.wrapper_code(
        runtime_record_index=PROBE_RUNTIME_RECORD_INDEX,
        expected_class=PROBE_TRIGGER_CLASS,
        forced_commander_id=case.commander_id,
        probe_experience=class_probe.class_change_experience(
            source,
            PROBE_TRIGGER_CLASS,
        ),
    )
    post = class_probe.post_apply_wrapper_code(
        PROBE_RUNTIME_RECORD_INDEX,
        case.commander_id,
    )
    layout = scenario_layout(payload, SCENARIO_NUMBER)
    bald = layout.records_offset + BALD_RECORD_INDEX * FIXED_RECORD_SIZE
    return (
        WriteRegion(
            "md_checksum",
            CHECKSUM_RANGE.start,
            CHECKSUM_RANGE.stop,
        ),
        WriteRegion(
            "end_turn_level_up_operand",
            class_probe.END_TURN_LEVEL_UP_ENTRY_OPERAND,
            class_probe.END_TURN_LEVEL_UP_ENTRY_OPERAND + 4,
        ),
        WriteRegion(
            "join_visibility_compare",
            builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK,
            builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK
            + len(builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK_ORIGINAL),
        ),
        WriteRegion(
            "class_change_resume_operand",
            class_probe.CLASS_CHANGE_RESUME_OPERAND,
            class_probe.CLASS_CHANGE_RESUME_OPERAND + 4,
        ),
        WriteRegion(
            "level_up_probe_wrapper",
            class_probe.PROBE_WRAPPER,
            class_probe.PROBE_WRAPPER + len(wrapper),
        ),
        WriteRegion(
            "post_apply_probe_wrapper",
            class_probe.POST_APPLY_WRAPPER,
            class_probe.POST_APPLY_WRAPPER + len(post),
        ),
        WriteRegion(
            "scenario1_bald_at_df",
            bald + FIELD_OFFSETS["at"],
            bald + FIELD_OFFSETS["df"] + 1,
        ),
        WriteRegion(
            "scenario1_bald_xy",
            bald + FIELD_OFFSETS["x"],
            bald + FIELD_OFFSETS["y"] + 1,
        ),
        WriteRegion(
            "scenario1_bald_mercenaries",
            bald + FIELD_OFFSETS["mercenaries"],
            bald + FIELD_OFFSETS["mercenaries"] + 6,
        ),
    )


def patch_probe(
    probe: bytearray,
    source: bytes,
    case: MountedLordCase,
) -> tuple[int, dict[str, object]]:
    before = bytes(probe)
    contract = production_contract(before, source, case)

    class_probe.patch_probe(
        probe,
        source,
        commander_id=case.commander_id,
        current_class=PROBE_TRIGGER_CLASS,
        runtime_record_index=PROBE_RUNTIME_RECORD_INDEX,
        enable_start_menu_probe=False,
        force_runtime_context=True,
        restore_commander_id=case.commander_id,
    )

    hook = builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK
    installed = (
        bytes.fromhex("4E B9")
        + builder.JOIN_CLASS_CHOICE_VISIBILITY_GUARD.to_bytes(4, "big")
    )
    if probe[hook : hook + len(installed)] != installed:
        raise ValueError("join visibility guard is not installed")
    probe[
        hook : hook + len(builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK_ORIGINAL)
    ] = builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK_ORIGINAL

    layout = scenario_layout(before, SCENARIO_NUMBER)
    bald = layout.records_offset + BALD_RECORD_INDEX * FIXED_RECORD_SIZE
    probe[bald + FIELD_OFFSETS["at"]] = PROBE_BALD_AT
    probe[bald + FIELD_OFFSETS["df"]] = PROBE_BALD_DF
    probe[bald + FIELD_OFFSETS["x"]] = PROBE_BALD_X
    probe[bald + FIELD_OFFSETS["y"]] = PROBE_BALD_Y
    mercenaries = bald + FIELD_OFFSETS["mercenaries"]
    probe[mercenaries : mercenaries + 6] = b"\xFF" * 6
    checksum = builder.update_md_checksum(probe)

    manifest = delta_manifest(before, bytes(probe), source, case, contract)
    return checksum, manifest


def changed_offsets(before: bytes, after: bytes) -> set[int]:
    if len(before) != len(after):
        raise ValueError("diagnostic ROM size differs from its exact input")
    return {
        offset
        for offset, (left, right) in enumerate(zip(before, after))
        if left != right
    }


def region_model(region: WriteRegion, before: bytes, after: bytes) -> dict[str, object]:
    changed = [
        offset
        for offset in region.offsets()
        if before[offset] != after[offset]
    ]
    return {
        "label": region.label,
        "range": f"0x{region.start:06X}..0x{region.end - 1:06X}",
        "length": region.end - region.start,
        "before_hex": before[region.start : region.end].hex().upper(),
        "after_hex": after[region.start : region.end].hex().upper(),
        "before_sha256": sha256(before[region.start : region.end]),
        "after_sha256": sha256(after[region.start : region.end]),
        "changed_offsets": [f"0x{offset:06X}" for offset in changed],
    }


def byte_delta_model(before: bytes, after: bytes, offsets: Iterable[int]) -> list[dict[str, object]]:
    return [
        {
            "offset": f"0x{offset:06X}",
            "before": f"0x{before[offset]:02X}",
            "after": f"0x{after[offset]:02X}",
        }
        for offset in sorted(offsets)
    ]


def delta_manifest(
    before: bytes,
    after: bytes,
    source: bytes,
    case: MountedLordCase,
    contract: dict[str, object] | None = None,
) -> dict[str, object]:
    regions = diagnostic_regions(before, source, case)
    allowed = {offset for region in regions for offset in region.offsets()}
    changed = changed_offsets(before, after)
    unexpected = changed - allowed
    if unexpected:
        rendered = ", ".join(f"0x{offset:06X}" for offset in sorted(unexpected))
        raise ValueError(f"diagnostic changed undeclared bytes: {rendered}")
    uncovered = {
        offset
        for offset in changed
        if sum(offset in region.offsets() for region in regions) != 1
    }
    if uncovered:
        raise ValueError("diagnostic write regions overlap")

    expected_checksum = sum(
        be16(after, offset) for offset in range(0x200, len(after), 2)
    ) & 0xFFFF
    if md_checksum(after) != expected_checksum:
        raise ValueError("diagnostic ROM checksum is invalid")

    return {
        "schema_version": 1,
        "kind": "mounted_lord_combat_runtime_derivative",
        "case": case.key,
        "production_contract": (
            production_contract(before, source, case)
            if contract is None
            else contract
        ),
        "input_rom": {
            "size": len(before),
            "sha256": sha256(before),
            "md_checksum": f"{md_checksum(before):04X}",
        },
        "source_rom": {
            "size": len(source),
            "sha256": sha256(source),
        },
        "probe_rom": {
            "size": len(after),
            "sha256": sha256(after),
            "md_checksum": f"{md_checksum(after):04X}",
        },
        "scope": {
            "changed_byte_count": len(changed),
            "declared_region_count": len(regions),
            "production_class_sprite_combat_text_event_bytes_changed": False,
            "scenario1_target": {
                "record_index": BALD_RECORD_INDEX,
                "name_id": f"0x{BALD_NAME_ID:02X}",
                "class_id": f"0x{BALD_CLASS_ID:02X}",
                "coordinates": [PROBE_BALD_X, PROBE_BALD_Y],
                "at": PROBE_BALD_AT,
                "df": PROBE_BALD_DF,
                "mercenaries": [],
            },
        },
        "write_regions": [
            region_model(region, before, after) for region in regions
        ],
        "byte_deltas": byte_delta_model(before, after, changed),
    }


def verify_probe(
    input_rom: bytes,
    probe_rom: bytes,
    source: bytes,
    case: MountedLordCase,
    manifest: dict[str, object] | None = None,
) -> dict[str, object]:
    rebuilt = bytearray(input_rom)
    _, expected_manifest = patch_probe(rebuilt, source, case)
    if bytes(rebuilt) != probe_rom:
        raise ValueError("diagnostic ROM is not the exact reproducible derivative")
    actual_manifest = delta_manifest(input_rom, probe_rom, source, case)
    if actual_manifest != expected_manifest:
        raise ValueError("rebuilt diagnostic manifest is not deterministic")
    if manifest is not None and manifest != actual_manifest:
        raise ValueError("diagnostic manifest does not match the exact ROM pair")
    return actual_manifest


def parse_case(value: str) -> MountedLordCase:
    try:
        return CASES[value]
    except KeyError as exc:
        raise argparse.ArgumentTypeError(
            f"case must be one of {', '.join(CASES)}"
        ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=parse_case, required=True)
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    input_rom = args.input_rom.read_bytes()
    probe = bytearray(input_rom)
    checksum, manifest = patch_probe(probe, source, args.case)
    verify_probe(input_rom, bytes(probe), source, args.case, manifest)
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    manifest = {
        **manifest,
        "paths": {
            "input_rom": str(args.input_rom.resolve()),
            "source_rom": str(args.source_rom.resolve()),
            "probe_rom": str(args.output_rom.resolve()),
        },
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"{args.case.commander_name} {args.case.class_name} combat probe "
        f"{checksum:04X}; {manifest['scope']['changed_byte_count']} exact bytes"
    )
    print(args.output_rom)
    print(args.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

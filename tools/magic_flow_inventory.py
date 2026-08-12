#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from PIL import Image

from tools.capture_magic_application import runtime_mp, selected_list_row
from tools.class_ability_data import (
    MAGIC_ABILITY_COUNT,
    natural_class_paths,
    read_ability_definitions,
    read_class_ability_unlocks,
)
from tools.class_change_data import COMMANDER_COUNT
from tools.class_hire_data import CLASS_COUNT
from tools.scenario_data import (
    KOREAN_NAME_BY_ID,
    SCENARIO_COUNT,
    class_names,
    read_scenario,
)
from tools import verify_natural_magic_evidence as natural_evidence
from tools.verify_natural_summon_evidence import read_runtime


DEFAULT_SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
DEFAULT_KOREAN_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
DEFAULT_RUNTIME_INVENTORY = ROOT / "localization/runtime_verification.json"
DEFAULT_JSON = ROOT / "localization/magic_flow_inventory.json"
DEFAULT_MARKDOWN = ROOT / "docs/magic_flow_inventory.md"

CLASS_RECORD_TABLE = 0x05EDDC
CLASS_RECORD_SIZE = 0x1C
MAGIC_PARAMETER_TABLE = 0x08203C
MAGIC_PARAMETER_SIZE = 8

SOURCE_RANGES = (
    (
        "class_records",
        0x05EDDC,
        0x05FF08,
        "07efffd287c2a6787dc1cefee3b3ef3efae1481767117e3d899f2c65eeaaeebd",
    ),
    (
        "level_up_learning",
        0x014946,
        0x01498E,
        "2e0177dfd678207bcb3701b954b9c2d893ef7a98eb3dcd0ee2e35ec9ac250f4d",
    ),
    (
        "magic_command_gate",
        0x020DAE,
        0x020DC0,
        "a176129752052073e838579d646b42a1b34fdfef74e9f99b70c76e74348f1254",
    ),
    (
        "magic_list_builder",
        0x0211A2,
        0x02125A,
        "33139cb0ec237628bfcfdf90b85a029b5db8c922b138b326452a10139503a9b2",
    ),
    (
        "magic_selection",
        0x0213D0,
        0x021578,
        "3370433847d778fa3bd021a80fd791520373e4d67d937cd91c367975a54c5d87",
    ),
    (
        "magic_application",
        0x00E798,
        0x00EDB0,
        "a53bfcac3fac803fa38ab73c531167fb45d70acf1bf73b38340d43e9f5199824",
    ),
    (
        "magic_parameters",
        0x08203C,
        0x0820EC,
        "6b7eeb2782426146925e4541fada3c5e46d277ede13478188b56491e2782865c",
    ),
    (
        "ability_requirements",
        0x0829CC,
        0x0829FA,
        "5aa6300a3780d58a3375fff8379b54b4f665885547f414fe047b10aca412b1d9",
    ),
    (
        "ability_masks",
        0x0829FA,
        0x082A56,
        "5f2d087f77e236be888480b27918f533962b4ba3c787aa3755fa216aa0361599",
    ),
)

# v1.3.6 deliberately installs two named tier-2 aliases.  Their complete
# class records must remain byte-for-byte copies of the declared Japanese
# source classes; every other byte in the class table remains locked to the
# same class record in the Japanese ROM.
DECLARED_CLASS_RECORD_ALIASES = dict(
    builder.JOIN_CLASS_CHOICE_CUSTOM_CLASS_SOURCES
)

SEMANTIC_ANCHORS = {
    0x01494A: bytes.fromhex("18 31 10 16"),
    0x014952: bytes.fromhex("49 F9 00 08 29 CC"),
    0x014964: bytes.fromhex("49 F9 00 08 29 FA"),
    0x01497A: bytes.fromhex("00 06 00 01"),
    0x01497E: bytes.fromhex("8D A8 00 50"),
    0x020DAE: bytes.fromhex("20 29 00 50"),
    0x020DB2: bytes.fromhex("08 00 00 00"),
    0x0211C2: bytes.fromhex("41 F9 00 05 ED DC"),
    0x021202: bytes.fromhex("22 78 A6 28"),
    0x021206: bytes.fromhex("2E 29 00 50"),
    0x021228: bytes.fromhex("67 00 00 08"),
    0x021232: bytes.fromhex("7C 01"),
    0x021246: bytes.fromhex("0C 86 00 00 00 17"),
    0x021554: bytes.fromhex("41 F8 BD 74"),
    0x021560: bytes.fromhex("31 C0 A9 58"),
    0x021564: bytes.fromhex("21 FC 00 00 E7 98 80 04"),
    0x00E7C6: bytes.fromhex("30 38 A9 58"),
    0x00E7FA: bytes.fromhex("D0 40 D0 40 D0 40"),
    0x00E800: bytes.fromhex("41 F9 00 08 20 3C"),
    0x00EAA4: bytes.fromhex("30 38 A9 58"),
    0x00EAC6: bytes.fromhex("E7 48"),
    0x00EAC8: bytes.fromhex("43 F9 00 08 20 3C"),
    0x00EACE: bytes.fromhex("32 31 00 04"),
}


def sha256(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def verify_source_ranges(
    source: bytes,
    korean: bytes,
) -> list[dict[str, object]]:
    rows = []
    for name, start, end, expected_sha256 in SOURCE_RANGES:
        source_data = source[start:end]
        actual_sha256 = sha256(source_data)
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"{name} source range changed: {actual_sha256} "
                f"!= {expected_sha256}"
            )
        aliases: list[dict[str, object]] = []
        expected_production = source_data
        if name == "class_records":
            expected = bytearray(source_data)
            for custom_class, source_class in sorted(
                DECLARED_CLASS_RECORD_ALIASES.items()
            ):
                custom_relative = custom_class * CLASS_RECORD_SIZE
                source_offset = (
                    CLASS_RECORD_TABLE + source_class * CLASS_RECORD_SIZE
                )
                expected[custom_relative : custom_relative + CLASS_RECORD_SIZE] = (
                    source[source_offset : source_offset + CLASS_RECORD_SIZE]
                )
                aliases.append(
                    {
                        "class_id": custom_class,
                        "source_class_id": source_class,
                        "offset": f"0x{start + custom_relative:06X}",
                        "size": CLASS_RECORD_SIZE,
                    }
                )
            expected_production = bytes(expected)
        if korean[start:end] != expected_production:
            mismatch = next(
                index
                for index, (old, new) in enumerate(
                    zip(expected_production, korean[start:end])
                )
                if old != new
            )
            raise ValueError(
                f"{name} production logic/data differs from source at "
                f"0x{start + mismatch:06X}"
            )
        rows.append(
            {
                "name": name,
                "start": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "size": end - start,
                "source_sha256": actual_sha256,
                "production_source_equivalent": not aliases,
                "production_matches_declared_policy": True,
                "declared_class_record_aliases": aliases,
            }
        )
    return rows


def verify_semantic_anchors(source: bytes) -> dict[str, object]:
    for offset, expected in SEMANTIC_ANCHORS.items():
        if source[offset : offset + len(expected)] != expected:
            raise ValueError(
                f"magic semantic anchor changed at 0x{offset:06X}"
            )
    return {
        "class_record_table": f"0x{CLASS_RECORD_TABLE:06X}",
        "class_record_size": CLASS_RECORD_SIZE,
        "class_ability_offsets": ["0x16", "0x17", "0x18", "0x19"],
        "runtime_ability_flags_offset": "0x50",
        "selected_magic_word": "0xFFFFA958",
        "magic_parameter_table": f"0x{MAGIC_PARAMETER_TABLE:06X}",
        "magic_parameter_record_size": MAGIC_PARAMETER_SIZE,
        "semantic_anchor_count": len(SEMANTIC_ANCHORS),
    }


def fixed_class_usage(source: bytes) -> dict[int, int]:
    result = {class_id: 0 for class_id in range(CLASS_COUNT)}
    for scenario_number in range(1, SCENARIO_COUNT + 1):
        scenario = read_scenario(source, source, scenario_number)
        for record in scenario["records"]:
            result[record["class_id"]] += 1
    return result


def magic_cost(source: bytes, magic_id: int) -> int:
    offset = MAGIC_PARAMETER_TABLE + magic_id * MAGIC_PARAMETER_SIZE + 4
    return int.from_bytes(source[offset : offset + 2], "big")


def runtime_evidence_rows(
    runtime_inventory: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    by_surface = {
        row["surface"]: row
        for row in runtime_inventory["global_evidence"]
    }
    required = (
        "magic_targeting_results",
        "natural_magic_ownership_application",
    )
    missing = [surface for surface in required if surface not in by_surface]
    if missing:
        raise ValueError(
            "runtime verification lost magic surfaces: " + ", ".join(missing)
        )
    diagnostic = by_surface["magic_targeting_results"]
    natural = by_surface["natural_magic_ownership_application"]
    if diagnostic["state"] != "verified_probe":
        raise ValueError("diagnostic magic application is no longer verified")
    if natural["state"] != "verified_probe":
        raise ValueError("natural magic application is no longer verified")
    return diagnostic, natural


def diagnostic_paths(magic_id: int) -> tuple[str, Path, Path, Path]:
    if magic_id == 0:
        stem = "49a2_magic_00"
    elif magic_id == 16:
        stem = "797c_magic_16"
    else:
        stem = f"e72d_magic_{magic_id:02d}"
    selected = ROOT / "captures/run" / f"{stem}_selected.png"
    stable = ROOT / "captures/run" / f"{stem}_result_stable.png"
    state = ROOT / "captures/analysis" / f"{stem}.gst"
    return stem[:4].upper(), selected, stable, state


def verify_capture(path: Path) -> None:
    with Image.open(path) as raw:
        image = raw.convert("RGB")
    if image.size != (320, 240):
        raise ValueError(
            f"magic capture has unexpected size {image.size}: {path}"
        )
    extrema = image.getextrema()
    if all(low == high for low, high in extrema):
        raise ValueError(f"magic capture is blank: {path}")


def verify_diagnostic_evidence(
    source: bytes,
    runtime_inventory: dict[str, object],
) -> list[dict[str, object]]:
    diagnostic, _ = runtime_evidence_rows(runtime_inventory)
    registered = set(diagnostic["captures"])
    rows = []
    for magic_id in range(MAGIC_ABILITY_COUNT):
        checksum, selected, stable, state = diagnostic_paths(magic_id)
        for path in (selected, stable, state):
            if not path.is_file():
                raise ValueError(f"missing retained magic evidence: {path}")
        for path in (selected, stable):
            verify_capture(path)
        page, row = divmod(magic_id, 6)
        actual_row = selected_list_row(selected)
        if actual_row != row:
            raise ValueError(
                f"magic {magic_id} selected row changed: "
                f"{actual_row} != {row}"
            )
        for path in (selected, stable):
            if relative(path) not in registered:
                raise ValueError(
                    f"runtime inventory does not register {relative(path)}"
                )
        current_mp, max_mp = runtime_mp(state.read_bytes())
        cost = magic_cost(source, magic_id)
        if max_mp != 12 or current_mp != max(0, max_mp - cost):
            raise ValueError(
                f"magic {magic_id} MP evidence changed: "
                f"{current_mp}/{max_mp}, source cost {cost}"
            )
        rows.append(
            {
                "magic_id": magic_id,
                "checksum": checksum,
                "selected_capture": relative(selected),
                "stable_capture": relative(stable),
                "state": relative(state),
                "mp_before": max_mp,
                "mp_after": current_mp,
                "source_mp_cost": cost,
                "list_page": page,
                "list_row": row,
                "application_verified": True,
            }
        )
    return rows


def verify_natural_evidence(
    runtime_inventory: dict[str, object],
) -> dict[str, object]:
    _, registered = runtime_evidence_rows(runtime_inventory)
    registered_paths = set(registered["captures"])
    before_path = natural_evidence.DEFAULT_BEFORE
    after_path = natural_evidence.DEFAULT_AFTER
    before = read_runtime(before_path.read_bytes())
    after = read_runtime(after_path.read_bytes())
    natural_evidence.verify(before, after)
    for path in (before_path, after_path):
        if relative(path) not in registered_paths:
            raise ValueError(
                f"runtime inventory does not register {relative(path)}"
            )
    return {
        "checksum": "7256",
        "commander_id": natural_evidence.HEIN_COMMANDER_ID,
        "commander": "헤인",
        "class_id": natural_evidence.SUMMONER_CLASS,
        "class": "서머너",
        "level": before.level,
        "learned_magic_ids": list(natural_evidence.NATURAL_MAGIC_IDS),
        "applied_magic_id": natural_evidence.ATTACK_MAGIC_ID,
        "mp_before": before.current_mp,
        "mp_after": after.current_mp,
        "before_state": relative(before_path),
        "after_state": relative(after_path),
        "natural_application_verified": True,
    }


def natural_magic_rows(
    source: bytes,
    diagnostic_rows: list[dict[str, object]],
    natural_live: dict[str, object],
) -> list[dict[str, object]]:
    classes = class_names(source)
    definitions = read_ability_definitions(source)
    fixed_usage = fixed_class_usage(source)
    paths_by_commander = {
        commander_id: natural_class_paths(source, commander_id)
        for commander_id in range(1, COMMANDER_COUNT + 1)
    }
    class_abilities = {
        class_id: read_class_ability_unlocks(source, class_id).ability_ids
        for class_id in range(CLASS_COUNT)
    }
    live_ids = set(natural_live["learned_magic_ids"])
    rows = []

    for magic_id in range(MAGIC_ABILITY_COUNT):
        owner_class_ids = [
            class_id
            for class_id, ability_ids in class_abilities.items()
            if magic_id in ability_ids
        ]
        candidates = []
        reachable_commanders = set()
        reachable_owner_classes = set()
        for commander_id, paths in paths_by_commander.items():
            for path in paths:
                owners = [
                    class_id
                    for class_id in path
                    if magic_id in class_abilities[class_id]
                ]
                if not owners:
                    continue
                reachable_commanders.add(commander_id)
                reachable_owner_classes.update(owners)
                owner = min(owners, key=path.index)
                candidates.append(
                    (
                        path.index(owner),
                        commander_id,
                        path,
                        owner,
                    )
                )

        witness = None
        if candidates:
            _, commander_id, path, owner = min(
                candidates,
                key=lambda row: (row[0], row[1], row[2], row[3]),
            )
            witness = {
                "commander_id": commander_id,
                "commander": KOREAN_NAME_BY_ID[commander_id],
                "owner_class_id": owner,
                "owner_class": classes[owner]["ko"],
                "path_class_ids": list(path),
                "path_classes": [
                    classes[class_id]["ko"] for class_id in path
                ],
            }

        evidence = diagnostic_rows[magic_id]
        rows.append(
            {
                "magic_id": magic_id,
                "name": builder.MAGIC_LIST_NAMES[magic_id],
                "required_level": definitions[magic_id].required_level,
                "runtime_mask": f"0x{definitions[magic_id].runtime_mask:08X}",
                "source_mp_cost": magic_cost(source, magic_id),
                "owner_class_ids": owner_class_ids,
                "owner_classes": [
                    classes[class_id]["ko"] for class_id in owner_class_ids
                ],
                "natural_owner_class_ids": sorted(reachable_owner_classes),
                "natural_reachable_commander_ids": sorted(
                    reachable_commanders
                ),
                "natural_reachable_commanders": [
                    KOREAN_NAME_BY_ID[commander_id]
                    for commander_id in sorted(reachable_commanders)
                ],
                "natural_learnable": witness is not None,
                "natural_witness": witness,
                "live_natural_ownership_evidence": magic_id in live_ids,
                "fixed_scenario_owner_record_count": sum(
                    fixed_usage[class_id] for class_id in owner_class_ids
                ),
                "diagnostic_application": evidence,
            }
        )
    return rows


def inventory(
    source: bytes,
    korean: bytes,
    runtime_inventory: dict[str, object],
) -> dict[str, object]:
    ranges = verify_source_ranges(source, korean)
    control_flow = verify_semantic_anchors(source)
    diagnostic = verify_diagnostic_evidence(source, runtime_inventory)
    natural_live = verify_natural_evidence(runtime_inventory)
    magic = natural_magic_rows(source, diagnostic, natural_live)

    reachable = [row for row in magic if row["natural_learnable"]]
    unreachable = [row for row in magic if not row["natural_learnable"]]
    if len(reachable) != 21:
        raise ValueError(
            f"natural magic reachability changed: {len(reachable)}/22"
        )
    if [row["magic_id"] for row in unreachable] != [18]:
        raise ValueError(
            "source-unreachable magic exception changed: "
            f"{[row['magic_id'] for row in unreachable]!r}"
        )
    teleport = unreachable[0]
    if (
        teleport["owner_class_ids"] != [0x25]
        or teleport["fixed_scenario_owner_record_count"] != 0
    ):
        raise ValueError("Teleport source exception no longer matches Agent 25")
    if len(diagnostic) != MAGIC_ABILITY_COUNT:
        raise ValueError("diagnostic application evidence is incomplete")

    return {
        "scope": {
            "magic_count": len(magic),
            "source_natural_learnable_magic_count": len(reachable),
            "source_unreachable_magic_count": len(unreachable),
            "source_unreachable_magic_ids": [
                row["magic_id"] for row in unreachable
            ],
            "diagnostic_application_evidence_count": len(diagnostic),
            "live_natural_learned_magic_count": len(
                natural_live["learned_magic_ids"]
            ),
            "source_locked_range_count": len(ranges),
        },
        "conclusion": (
            "Twenty-one of 22 magic IDs have at least one source class-change "
            "ownership path. Teleport is the bounded source exception: only "
            "Agent 25 owns it, and that class is absent from all ten player "
            "trees and all fixed scenario records. Every ID still shares the "
            "source-locked production list, selection, parameter, and "
            "application path and has retained diagnostic application "
            "evidence. The v1.3.6 Hawk Lord and Croco Lord class records are "
            "bounded aliases of their declared Japanese mounted source "
            "records; every other class-record byte remains source-locked. "
            "This is structural coverage, not a claim that every "
            "commander/class ownership combination was naturally played."
        ),
        "source_locked_ranges": ranges,
        "control_flow": control_flow,
        "natural_live_evidence": natural_live,
        "magic": magic,
    }


def markdown_report(result: dict[str, object]) -> str:
    scope = result["scope"]
    lines = [
        "# Magic Ownership And Application Flow Inventory",
        "",
        "Generated by `python3 tools/magic_flow_inventory.py`.",
        "",
        "## Coverage",
        "",
        f"- Magic IDs: {scope['magic_count']}/22",
        "- Source-natural learnability: "
        f"{scope['source_natural_learnable_magic_count']}/22",
        "- Explicit source-unreachable exception: "
        + ", ".join(
            f"`{magic_id:02X}`"
            for magic_id in scope["source_unreachable_magic_ids"]
        ),
        "- Retained diagnostic applications: "
        f"{scope['diagnostic_application_evidence_count']}/22",
        "- Naturally accumulated live list: "
        f"{scope['live_natural_learned_magic_count']} magic IDs",
        "",
        result["conclusion"],
        "",
        "## Source-Locked Control Flow",
        "",
        "| Range | Address | Bytes | Production |",
        "| --- | --- | ---: | --- |",
    ]
    for row in result["source_locked_ranges"]:
        aliases = row["declared_class_record_aliases"]
        if aliases:
            production = "declared aliases; all other records source-equivalent"
        else:
            production = "source-equivalent"
        lines.append(
            f"| {row['name']} | `{row['start']}..{row['end']}` | "
            f"{row['size']} | {production} |"
        )
    aliases = result["source_locked_ranges"][0][
        "declared_class_record_aliases"
    ]
    if aliases:
        lines.extend(
            [
                "",
                "Declared v1.3.6 class-record aliases: "
                + ", ".join(
                    f"`{row['class_id']:02X}` <- `{row['source_class_id']:02X}`"
                    for row in aliases
                )
                + ".",
            ]
        )

    lines.extend(
        [
            "",
            "The stock level-up scan reads the current class's four ability "
            "bytes, required level, and runtime mask. The list builder reads "
            "the accumulated runtime flags, selection stores the magic ID at "
            "`0xFFFFA958`, and the application handler indexes the shared "
            "`0x08203C` eight-byte parameter records for every magic ID.",
            "",
            "## Magic Matrix",
            "",
            "| ID | Name | LV | MP | Natural owners | Witness | Live natural | Apply |",
            "| --- | --- | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for row in result["magic"]:
        witness = row["natural_witness"]
        if witness is None:
            witness_text = "none (Agent 25 only)"
        else:
            witness_text = (
                f"{witness['commander']} / "
                f"{witness['owner_class']} `{witness['owner_class_id']:02X}`"
            )
        owners = ", ".join(
            f"{name} `{class_id:02X}`"
            for class_id, name in zip(
                row["natural_owner_class_ids"],
                [
                    row["owner_classes"][row["owner_class_ids"].index(class_id)]
                    for class_id in row["natural_owner_class_ids"]
                ],
            )
        )
        if not owners:
            owners = "none"
        application = row["diagnostic_application"]
        lines.append(
            f"| `{row['magic_id']:02X}` | {row['name']} | "
            f"{row['required_level']} | {row['source_mp_cost']} | "
            f"{owners} | {witness_text} | "
            f"{'yes' if row['live_natural_ownership_evidence'] else 'no'} | "
            f"`{application['checksum']}` "
            f"{application['mp_before']}->{application['mp_after']} |"
        )

    natural = result["natural_live_evidence"]
    lines.extend(
        [
            "",
            "## Retained Natural Evidence",
            "",
            f"- `{natural['checksum']}`: {natural['commander']}/"
            f"{natural['class']} LV{natural['level']}",
            "- Learned magic IDs: "
            + ", ".join(
                f"`{magic_id:02X}`"
                for magic_id in natural["learned_magic_ids"]
            ),
            f"- Natural application: `10` 어택, MP "
            f"{natural['mp_before']}->{natural['mp_after']}",
            f"- Before GST: `{natural['before_state']}`",
            f"- After GST: `{natural['after_state']}`",
            "",
            "Each matrix row also records a tracked selected screen, stable "
            "result screen, and post-application GST. The all-magic probe "
            "forces list visibility and MP acceptance only; the source-locked "
            "parameter and application routines remain the production path.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the source-locked natural magic ownership and "
            "application flow inventory"
        )
    )
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--korean-rom", type=Path, default=DEFAULT_KOREAN_ROM)
    parser.add_argument(
        "--runtime-inventory",
        type=Path,
        default=DEFAULT_RUNTIME_INVENTORY,
    )
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = inventory(
        args.source_rom.read_bytes(),
        args.korean_rom.read_bytes(),
        json.loads(args.runtime_inventory.read_text(encoding="utf-8")),
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['scope']['source_natural_learnable_magic_count']}/22 "
        "source-natural magic IDs; "
        f"{result['scope']['diagnostic_application_evidence_count']}/22 "
        "applications; "
        f"{result['scope']['source_unreachable_magic_count']} bounded exception"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

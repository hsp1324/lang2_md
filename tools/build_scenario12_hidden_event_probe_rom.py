#!/usr/bin/env python3
"""Build a non-release Scenario 12 ROM for the two hidden-tile events.

The diagnostic moves only Elwin's initial deployment near one selected hidden
tile. The Muscle Temple placement normalizes onto its target, so verification
leaves the tile and returns on the next turn. The Carbunkle placement remains
immediately left of its target and enters it directly.
The stock event records, handlers, dialogue pointers, and every other
deployment remain byte-identical to the Japanese source.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = ROOT / "tmp/scenario12-hidden-event-probe.md"

SCENARIO_HEADER = 0x181554
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x181574
FIRST_PLAYER_DEPLOYMENT = DEPLOYMENT_TABLE + 0x02
SOURCE_ELWIN_DEPLOYMENT = bytes.fromhex("00 0F 00 17")
PROBE_ELWIN_DEPLOYMENTS = {
    "muscle": bytes.fromhex("00 03 00 06"),
    "carbunkle": bytes.fromhex("00 0E 00 06"),
}

TRIGGER_TABLE_START = 0x198F06
TRIGGER_TABLE_END = 0x198F2A
MUSCLE_TRIGGER = 0x198F12
MUSCLE_HANDLER = 0x199074
MUSCLE_DIALOGUE_POINTER = 0x199078
MUSCLE_DIALOGUE = 0x199ABA
CARBUNKLE_TRIGGER = 0x198F1E
CARBUNKLE_HANDLER = 0x199082
CARBUNKLE_GUARD_BRANCH_POINTER = 0x199084
CARBUNKLE_GUARD_SOURCE_TARGET = 0x199096
CARBUNKLE_GUARD_FORCED_TARGET = 0x199088
CARBUNKLE_DIALOGUE_POINTER = 0x19908C
CARBUNKLE_DIALOGUE = 0x199AF8


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def validate_source_contract(source: bytes) -> None:
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Scenario 12 deployment table")
    if source[FIRST_PLAYER_DEPLOYMENT:FIRST_PLAYER_DEPLOYMENT + 4] != SOURCE_ELWIN_DEPLOYMENT:
        raise ValueError("unexpected Scenario 12 Elwin deployment")
    if source[MUSCLE_TRIGGER:MUSCLE_TRIGGER + 12] != bytes.fromhex(
        "07 01 00 00 04 06 04 06 00 19 90 74"
    ):
        raise ValueError("unexpected Scenario 12 Muscle Temple trigger")
    if source[CARBUNKLE_TRIGGER:CARBUNKLE_TRIGGER + 12] != bytes.fromhex(
        "08 F0 00 00 0F 06 0F 06 00 19 90 82"
    ):
        raise ValueError("unexpected Scenario 12 Carbunkle trigger")
    if be32(source, MUSCLE_DIALOGUE_POINTER) != MUSCLE_DIALOGUE:
        raise ValueError("unexpected Muscle Temple dialogue pointer")
    if be32(source, CARBUNKLE_DIALOGUE_POINTER) != CARBUNKLE_DIALOGUE:
        raise ValueError("unexpected Carbunkle dialogue pointer")


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    event: str = "carbunkle",
    force_carbunkle_event: bool = False,
) -> int:
    validate_source_contract(source)
    if event not in PROBE_ELWIN_DEPLOYMENTS:
        raise ValueError(f"unsupported hidden event: {event}")
    if force_carbunkle_event and event != "carbunkle":
        raise ValueError("the one-time guard override is Carbunkle-only")
    if probe[FIRST_PLAYER_DEPLOYMENT:FIRST_PLAYER_DEPLOYMENT + 4] != SOURCE_ELWIN_DEPLOYMENT:
        raise ValueError("input Scenario 12 Elwin deployment differs from source")
    if probe[TRIGGER_TABLE_START:TRIGGER_TABLE_END] != source[TRIGGER_TABLE_START:TRIGGER_TABLE_END]:
        raise ValueError("input Scenario 12 hidden-event triggers differ from source")
    if probe[MUSCLE_HANDLER:CARBUNKLE_DIALOGUE_POINTER + 4] != source[
        MUSCLE_HANDLER:CARBUNKLE_DIALOGUE_POINTER + 4
    ]:
        raise ValueError("input Scenario 12 hidden-event handlers differ from source")

    probe[FIRST_PLAYER_DEPLOYMENT:FIRST_PLAYER_DEPLOYMENT + 4] = (
        PROBE_ELWIN_DEPLOYMENTS[event]
    )
    if force_carbunkle_event:
        if (
            be32(source, CARBUNKLE_GUARD_BRANCH_POINTER)
            != CARBUNKLE_GUARD_SOURCE_TARGET
        ):
            raise ValueError("unexpected Carbunkle one-time guard target")
        probe[
            CARBUNKLE_GUARD_BRANCH_POINTER:
            CARBUNKLE_GUARD_BRANCH_POINTER + 4
        ] = CARBUNKLE_GUARD_FORCED_TARGET.to_bytes(4, "big")
    return builder.update_md_checksum(probe)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--event",
        choices=tuple(PROBE_ELWIN_DEPLOYMENTS),
        default="carbunkle",
    )
    parser.add_argument(
        "--force-carbunkle-event",
        action="store_true",
        help=(
            "diagnostic only: make the Carbunkle one-time guard continue at "
            "the untouched item/dialogue body even when flag 6 is already set"
        ),
    )
    args = parser.parse_args()

    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = patch_probe(
        probe,
        source,
        event=args.event,
        force_carbunkle_event=args.force_carbunkle_event,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print(f"wrote {args.output_rom}")
    if args.event == "muscle":
        print(
            "Elwin deployment: (15,23) -> muscle target (4,6); "
            "move down, end the turn, then return up"
        )
    else:
        print(
            "Elwin deployment: (15,23) -> (14,6); move right to "
            "Carbunkle target (15,6)"
        )
        if args.force_carbunkle_event:
            print(
                "diagnostic guard override: flag-6 branch target "
                "0x199096 -> 0x199088"
            )
    print(f"checksum: {checksum:04X}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_class_change_probe_rom as probe_builder
from tools.run_blastem_sequence import GST_WORK_RAM_FILE_OFFSET


DEFAULT_BEFORE = (
    ROOT / "captures/analysis/1d47_liana_natural_class_change_before.gst"
)
DEFAULT_AFTER = (
    ROOT / "captures/analysis/1d47_liana_natural_class_change_after.gst"
)
DEFAULT_SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
PROBE_CHECKSUM = 0x1D47
LIANA_RUNTIME_RECORD = 7
LIANA_COMMANDER_ID = 2
CLERIC_CLASS = 0x02
SHAMAN_CLASS = 0x0A


@dataclass(frozen=True)
class RuntimeIdentity:
    class_id: int
    commander_id: int
    level: int
    experience: int


def read_identities(gst: bytes) -> tuple[RuntimeIdentity, ...]:
    identities = []
    for index in range(probe_builder.PLAYER_RUNTIME_RECORD_COUNT):
        record = probe_builder.runtime_record_address(index) & 0xFFFF
        offset = GST_WORK_RAM_FILE_OFFSET + record
        end = offset + probe_builder.RUNTIME_RECORD_SIZE
        if len(gst) < end:
            raise ValueError(
                f"GST is too short to contain runtime record {index}"
            )
        data = gst[offset:end]
        identities.append(
            RuntimeIdentity(
                class_id=data[probe_builder.ELWIN_CLASS_OFFSET],
                commander_id=data[0x01],
                level=data[probe_builder.ELWIN_LEVEL_OFFSET],
                experience=data[probe_builder.ELWIN_EXPERIENCE_OFFSET],
            )
        )
    return tuple(identities)


def verify(
    before: tuple[RuntimeIdentity, ...],
    after: tuple[RuntimeIdentity, ...],
) -> None:
    expected_before = RuntimeIdentity(
        CLERIC_CLASS,
        LIANA_COMMANDER_ID,
        3,
        0,
    )
    expected_after = RuntimeIdentity(
        SHAMAN_CLASS,
        LIANA_COMMANDER_ID,
        1,
        0,
    )
    if before[LIANA_RUNTIME_RECORD] != expected_before:
        raise ValueError(
            "expected natural Liana Cleric/ID2/LV3/EXP0 before class change, "
            f"found {before[LIANA_RUNTIME_RECORD]!r}"
        )
    if after[LIANA_RUNTIME_RECORD] != expected_after:
        raise ValueError(
            "expected natural Liana Shaman/ID2/LV1/EXP0 after class change, "
            f"found {after[LIANA_RUNTIME_RECORD]!r}"
        )
    changed_other_records = [
        index
        for index, (old, new) in enumerate(zip(before, after))
        if index != LIANA_RUNTIME_RECORD and old != new
    ]
    if changed_other_records:
        raise ValueError(
            "unrelated player runtime identities changed: "
            + ", ".join(str(index) for index in changed_other_records)
        )


def verify_probe_rom(
    probe: bytes | bytearray,
    source: bytes | bytearray,
) -> None:
    checksum = int.from_bytes(probe[0x18E:0x190], "big")
    if checksum != PROBE_CHECKSUM:
        raise ValueError(
            f"expected Liana probe checksum 0x{PROBE_CHECKSUM:04X}, "
            f"found 0x{checksum:04X}"
        )
    transition = probe_builder.selected_transition(
        source,
        LIANA_COMMANDER_ID,
        CLERIC_CLASS,
    )
    if transition.candidates != (SHAMAN_CLASS, 0x08, 0x04):
        raise ValueError(
            f"Japanese Liana initial candidates changed: {transition.candidates!r}"
        )
    operand = probe_builder.END_TURN_LEVEL_UP_ENTRY_OPERAND
    if (
        int.from_bytes(probe[operand : operand + 4], "big")
        != probe_builder.PROBE_WRAPPER
    ):
        raise ValueError("Liana probe no longer redirects the stock level-up entry")
    code = probe_builder.wrapper_code(
        runtime_record_index=LIANA_RUNTIME_RECORD,
        expected_class=CLERIC_CLASS,
        probe_experience=probe_builder.class_change_experience(
            source,
            CLERIC_CLASS,
        ),
    )
    wrapper = probe_builder.PROBE_WRAPPER
    if probe[wrapper : wrapper + len(code)] != code:
        raise ValueError("Liana probe wrapper bytes changed")
    start = probe_builder.START_MENU_ENTRY_OPERAND
    if probe[start : start + 4] != source[start : start + 4]:
        raise ValueError("natural Liana probe changed the stock Start menu")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify retained same-ROM GST evidence for Liana's natural "
            "Cleric-to-Shaman class change."
        )
    )
    parser.add_argument("--before", type=Path, default=DEFAULT_BEFORE)
    parser.add_argument("--after", type=Path, default=DEFAULT_AFTER)
    parser.add_argument("--probe-rom", type=Path)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.probe_rom is not None:
        verify_probe_rom(
            args.probe_rom.read_bytes(),
            args.source_rom.read_bytes(),
        )
    before = read_identities(args.before.read_bytes())
    after = read_identities(args.after.read_bytes())
    verify(before, after)
    print(
        "verified runtime record 7: Liana Cleric/ID2/LV3/EXP0 -> "
        "Shaman/ID2/LV1/EXP0; all other player identities unchanged"
        + (
            "; exact probe checksum, source candidates, wrapper, and stock "
            "Start menu also verified"
            if args.probe_rom is not None
            else ""
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

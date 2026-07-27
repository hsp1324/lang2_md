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


DEFAULT_SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


@dataclass(frozen=True)
class RuntimeIdentity:
    class_id: int
    commander_id: int
    level: int
    experience: int


@dataclass(frozen=True)
class NaturalClassChangeProof:
    slug: str
    character: str
    before_class: str
    after_class: str
    before_path: Path
    after_path: Path
    probe_checksum: int
    runtime_record: int
    before: RuntimeIdentity
    after: RuntimeIdentity
    candidates: tuple[int, ...]


LIANA_PROOF = NaturalClassChangeProof(
    slug="liana",
    character="Liana",
    before_class="Cleric",
    after_class="Shaman",
    before_path=(
        ROOT / "captures/analysis/1d47_liana_natural_class_change_before.gst"
    ),
    after_path=(
        ROOT / "captures/analysis/1d47_liana_natural_class_change_after.gst"
    ),
    probe_checksum=0x1D47,
    runtime_record=7,
    before=RuntimeIdentity(0x02, 2, 3, 0),
    after=RuntimeIdentity(0x0A, 2, 1, 0),
    candidates=(0x0A, 0x08, 0x04),
)
SHERRY_PROOF = NaturalClassChangeProof(
    slug="sherry",
    character="Sherry",
    before_class="Fighter",
    after_class="Lord",
    before_path=(
        ROOT / "captures/analysis/17a6_sherry_natural_class_change_before.gst"
    ),
    after_path=(
        ROOT / "captures/analysis/17a6_sherry_natural_class_change_after.gst"
    ),
    probe_checksum=0x17A6,
    runtime_record=2,
    before=RuntimeIdentity(0x01, 4, 9, 15),
    after=RuntimeIdentity(0x04, 4, 1, 0),
    candidates=(0x04, 0x06, 0x0A),
)
AARON_PROOF = NaturalClassChangeProof(
    slug="aaron",
    character="Aaron",
    before_class="Fighter",
    after_class="Lord",
    before_path=(
        ROOT / "captures/analysis/18c6_aaron_natural_class_change_before.gst"
    ),
    after_path=(
        ROOT / "captures/analysis/18c6_aaron_natural_class_change_after.gst"
    ),
    probe_checksum=0x18C6,
    runtime_record=3,
    before=RuntimeIdentity(0x01, 8, 8, 6),
    after=RuntimeIdentity(0x04, 8, 1, 0),
    candidates=(0x04, 0x05, 0x0A),
)
SCOTT_PROOF = NaturalClassChangeProof(
    slug="scott",
    character="Scott",
    before_class="Fighter",
    after_class="Hawk Knight",
    before_path=(
        ROOT / "captures/analysis/1c26_scott_natural_class_change_before.gst"
    ),
    after_path=(
        ROOT / "captures/analysis/1c26_scott_natural_class_change_after.gst"
    ),
    probe_checksum=0x1C26,
    runtime_record=6,
    before=RuntimeIdentity(0x01, 6, 1, 0),
    after=RuntimeIdentity(0x06, 6, 1, 0),
    candidates=(0x06, 0x05, 0x04),
)
PROOFS = {
    proof.slug: proof
    for proof in (LIANA_PROOF, SHERRY_PROOF, AARON_PROOF, SCOTT_PROOF)
}

# Keep the original public constants for callers that use the default Liana
# proof directly.
DEFAULT_BEFORE = LIANA_PROOF.before_path
DEFAULT_AFTER = LIANA_PROOF.after_path
PROBE_CHECKSUM = LIANA_PROOF.probe_checksum
LIANA_RUNTIME_RECORD = LIANA_PROOF.runtime_record
LIANA_COMMANDER_ID = LIANA_PROOF.before.commander_id
CLERIC_CLASS = LIANA_PROOF.before.class_id
SHAMAN_CLASS = LIANA_PROOF.after.class_id


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
    proof: NaturalClassChangeProof = LIANA_PROOF,
) -> None:
    if before[proof.runtime_record] != proof.before:
        raise ValueError(
            f"expected natural {proof.character} {proof.before_class}/"
            f"ID{proof.before.commander_id}/LV{proof.before.level}/"
            f"EXP{proof.before.experience} before class change, "
            f"found {before[proof.runtime_record]!r}"
        )
    if after[proof.runtime_record] != proof.after:
        raise ValueError(
            f"expected natural {proof.character} {proof.after_class}/"
            f"ID{proof.after.commander_id}/LV{proof.after.level}/"
            f"EXP{proof.after.experience} after class change, "
            f"found {after[proof.runtime_record]!r}"
        )
    changed_other_records = [
        index
        for index, (old, new) in enumerate(zip(before, after))
        if index != proof.runtime_record and old != new
    ]
    if changed_other_records:
        raise ValueError(
            "unrelated player runtime identities changed: "
            + ", ".join(str(index) for index in changed_other_records)
        )


def verify_probe_rom(
    probe: bytes | bytearray,
    source: bytes | bytearray,
    proof: NaturalClassChangeProof = LIANA_PROOF,
) -> None:
    checksum = int.from_bytes(probe[0x18E:0x190], "big")
    if checksum != proof.probe_checksum:
        raise ValueError(
            f"expected {proof.character} probe checksum "
            f"0x{proof.probe_checksum:04X}, "
            f"found 0x{checksum:04X}"
        )
    transition = probe_builder.selected_transition(
        source,
        proof.before.commander_id,
        proof.before.class_id,
    )
    if transition.candidates != proof.candidates:
        raise ValueError(
            f"Japanese {proof.character} initial candidates changed: "
            f"{transition.candidates!r}"
        )
    operand = probe_builder.END_TURN_LEVEL_UP_ENTRY_OPERAND
    if (
        int.from_bytes(probe[operand : operand + 4], "big")
        != probe_builder.PROBE_WRAPPER
    ):
        raise ValueError(
            f"{proof.character} probe no longer redirects the stock level-up entry"
        )
    code = probe_builder.wrapper_code(
        runtime_record_index=proof.runtime_record,
        expected_class=proof.before.class_id,
        probe_experience=probe_builder.class_change_experience(
            source,
            proof.before.class_id,
        ),
    )
    wrapper = probe_builder.PROBE_WRAPPER
    if probe[wrapper : wrapper + len(code)] != code:
        raise ValueError(f"{proof.character} probe wrapper bytes changed")
    start = probe_builder.START_MENU_ENTRY_OPERAND
    if probe[start : start + 4] != source[start : start + 4]:
        raise ValueError(
            f"natural {proof.character} probe changed the stock Start menu"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify retained same-ROM GST evidence for a natural player "
            "class change."
        )
    )
    parser.add_argument("--proof", choices=sorted(PROOFS), default="liana")
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after", type=Path)
    parser.add_argument("--probe-rom", type=Path)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    proof = PROOFS[args.proof]
    if args.probe_rom is not None:
        verify_probe_rom(
            args.probe_rom.read_bytes(),
            args.source_rom.read_bytes(),
            proof,
        )
    before_path = args.before or proof.before_path
    after_path = args.after or proof.after_path
    before = read_identities(before_path.read_bytes())
    after = read_identities(after_path.read_bytes())
    verify(before, after, proof)
    print(
        f"verified runtime record {proof.runtime_record}: "
        f"{proof.character} {proof.before_class}/ID{proof.before.commander_id}/"
        f"LV{proof.before.level}/EXP{proof.before.experience} -> "
        f"{proof.after_class}/ID{proof.after.commander_id}/"
        f"LV{proof.after.level}/EXP{proof.after.experience}; "
        "all other player identities unchanged"
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

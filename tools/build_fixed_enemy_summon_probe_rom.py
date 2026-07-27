#!/usr/bin/env python3
"""Build a non-distribution probe for fixed-enemy summon compatibility.

This is not a hard-mode build. It changes two existing enemy mercenary slots
in an exact clone of the immutable Korean release so emulator testing can
determine whether summon classes remain safe when loaded as fixed soldiers.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import hard_mode_baseline
from tools.scenario_data import (
    FIELD_OFFSETS,
    FIXED_RECORD_SIZE,
    SIDE_OFFSET,
    scenario_layout,
    update_checksum,
)


DEFAULT_SOURCE = hard_mode_baseline.DEFAULT_NORMAL_ROM
DEFAULT_OUTPUT = ROOT / "tmp/fixed_enemy_summon_probe.md"

CHECKSUM_OFFSETS = frozenset((0x18E, 0x18F))


@dataclass(frozen=True)
class ProbeCase:
    name: str
    purpose: str
    scenario: int
    record_index: int
    record_offset: int
    side: int
    expected_mercenaries: bytes
    slots: tuple[int, ...]
    class_id: int
    expected_checksum: int
    expected_sha256: str


PROBE_CASES = {
    "loading": ProbeCase(
        name="loading",
        purpose="fixed loading, coordinates, and command-menu compatibility",
        scenario=27,
        record_index=7,
        record_offset=0x18321A,
        side=0x04,
        expected_mercenaries=bytes(
            (0x89, 0x89, 0x89, 0x89, 0x87, 0x87)
        ),
        slots=(4, 5),
        class_id=0x8F,
        expected_checksum=0xA205,
        expected_sha256=(
            "17b1f11927187d093db5b2c72de0b22f602ceb5dd67bcc22363743eeafddfa24"
        ),
    ),
    "ordinary-ai": ProbeCase(
        name="ordinary-ai",
        purpose="ordinary enemy movement and first-turn event compatibility",
        scenario=26,
        record_index=0,
        record_offset=0x182F64,
        side=0x04,
        expected_mercenaries=bytes(
            (0x76, 0x76, 0x76, 0x76, 0x77, 0x77)
        ),
        slots=(5,),
        class_id=0x8F,
        expected_checksum=0x9A15,
        expected_sha256=(
            "66e3b730740c1cd71125eef9cfe9987c2b81050aa63bb5cad02b91eaeec2d39c"
        ),
    ),
}

# Preserve the original public constants for callers that build the loading
# probe without selecting a case.
DEFAULT_CASE = PROBE_CASES["loading"]
PROBE_SCENARIO = DEFAULT_CASE.scenario
PROBE_RECORD_INDEX = DEFAULT_CASE.record_index
PROBE_RECORD_OFFSET = DEFAULT_CASE.record_offset
PROBE_SIDE = DEFAULT_CASE.side
EXPECTED_MERCENARIES = DEFAULT_CASE.expected_mercenaries
PROBE_SLOTS = DEFAULT_CASE.slots
PROBE_CLASS_ID = DEFAULT_CASE.class_id


def _verify_immutable_source(source: bytes) -> None:
    if len(source) != hard_mode_baseline.NORMAL_SIZE:
        raise ValueError(
            "probe source must be the immutable 4 MiB Korean release"
        )
    digest = hashlib.sha256(source).hexdigest()
    if digest != hard_mode_baseline.NORMAL_SHA256:
        raise ValueError(
            "probe source SHA-256 does not match the immutable Korean release"
        )
    if source[0x18E:0x190].hex().upper() != hard_mode_baseline.NORMAL_CHECKSUM:
        raise ValueError(
            "probe source header checksum does not match the immutable release"
        )


def patch_probe(
    source: bytes,
    case_name: str = DEFAULT_CASE.name,
) -> tuple[bytes, dict[str, object]]:
    """Return the checksum-valid diagnostic clone and its exact change report."""

    _verify_immutable_source(source)
    try:
        case = PROBE_CASES[case_name]
    except KeyError as exc:
        raise ValueError(f"unknown fixed-enemy probe case: {case_name}") from exc

    layout = scenario_layout(source, case.scenario)
    record_offset = (
        layout.records_offset + case.record_index * FIXED_RECORD_SIZE
    )
    if record_offset != case.record_offset:
        raise ValueError(
            f"Scenario {case.scenario} record {case.record_index} moved: "
            f"expected 0x{case.record_offset:06X}, "
            f"got 0x{record_offset:06X}"
        )
    if source[record_offset + SIDE_OFFSET] != case.side:
        raise ValueError("probe target is no longer an enemy-side record")

    mercenary_offset = record_offset + FIELD_OFFSETS["mercenaries"]
    current = source[mercenary_offset : mercenary_offset + 6]
    if current != case.expected_mercenaries:
        raise ValueError(
            "probe target mercenary layout changed: "
            f"expected {case.expected_mercenaries.hex().upper()}, "
            f"got {current.hex().upper()}"
        )

    output = bytearray(source)
    target_offsets = frozenset(
        mercenary_offset + slot for slot in case.slots
    )
    for offset in target_offsets:
        output[offset] = case.class_id
    checksum = update_checksum(output)
    output_sha256 = hashlib.sha256(output).hexdigest()

    changed_offsets = frozenset(
        index
        for index, (before, after) in enumerate(zip(source, output))
        if before != after
    )
    allowed_offsets = target_offsets | CHECKSUM_OFFSETS
    if not target_offsets.issubset(changed_offsets):
        raise AssertionError("probe did not change every requested soldier slot")
    if changed_offsets - allowed_offsets:
        unexpected = ", ".join(
            f"0x{offset:06X}" for offset in sorted(changed_offsets - allowed_offsets)
        )
        raise AssertionError(f"probe changed unexpected offsets: {unexpected}")
    if checksum != case.expected_checksum:
        raise AssertionError(
            f"{case.name} probe checksum changed: "
            f"expected {case.expected_checksum:04X}, got {checksum:04X}"
        )
    if output_sha256 != case.expected_sha256:
        raise AssertionError(
            f"{case.name} probe SHA-256 changed: "
            f"expected {case.expected_sha256}, got {output_sha256}"
        )

    report = {
        "status": "diagnostic_only_not_for_distribution",
        "case": case.name,
        "purpose": case.purpose,
        "source_sha256": hard_mode_baseline.NORMAL_SHA256,
        "scenario": case.scenario,
        "record_index": case.record_index,
        "record_offset": f"0x{record_offset:06X}",
        "side": f"{case.side:02X}",
        "source_mercenaries": [
            f"{class_id:02X}" for class_id in case.expected_mercenaries
        ],
        "patched_slots": list(case.slots),
        "patched_class_id": f"{case.class_id:02X}",
        "target_offsets": [
            f"0x{offset:06X}" for offset in sorted(target_offsets)
        ],
        "changed_offsets": [
            f"0x{offset:06X}" for offset in sorted(changed_offsets)
        ],
        "header_checksum": f"{checksum:04X}",
        "output_sha256": output_sha256,
    }
    return bytes(output), report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--case",
        choices=tuple(PROBE_CASES),
        default=DEFAULT_CASE.name,
        help="exact diagnostic case to build",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    if source == output:
        raise SystemExit("refusing to overwrite the immutable source ROM")

    probe, report = patch_probe(source.read_bytes(), args.case)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(probe)
    print(
        f"wrote diagnostic probe: {output}\n"
        f"Scenario {report['scenario']} record {report['record_index']} "
        f"slots {report['patched_slots']} -> class "
        f"{report['patched_class_id']}\n"
        f"checksum {report['header_checksum']}; "
        f"SHA-256 {report['output_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a non-distribution probe for fixed-enemy summon compatibility.

This is not a hard-mode build. It changes two existing enemy mercenary slots
in an exact clone of the immutable Korean release so emulator testing can
determine whether summon classes remain safe when loaded as fixed soldiers.
"""

from __future__ import annotations

import argparse
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

PROBE_SCENARIO = 27
PROBE_RECORD_INDEX = 7
PROBE_RECORD_OFFSET = 0x18321A
PROBE_SIDE = 0x04
EXPECTED_MERCENARIES = bytes((0x89, 0x89, 0x89, 0x89, 0x87, 0x87))
PROBE_SLOTS = (4, 5)
PROBE_CLASS_ID = 0x8F
CHECKSUM_OFFSETS = frozenset((0x18E, 0x18F))


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


def patch_probe(source: bytes) -> tuple[bytes, dict[str, object]]:
    """Return the checksum-valid diagnostic clone and its exact change report."""

    _verify_immutable_source(source)
    layout = scenario_layout(source, PROBE_SCENARIO)
    record_offset = (
        layout.records_offset + PROBE_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if record_offset != PROBE_RECORD_OFFSET:
        raise ValueError(
            f"Scenario {PROBE_SCENARIO} record {PROBE_RECORD_INDEX} moved: "
            f"expected 0x{PROBE_RECORD_OFFSET:06X}, got 0x{record_offset:06X}"
        )
    if source[record_offset + SIDE_OFFSET] != PROBE_SIDE:
        raise ValueError("probe target is no longer an enemy-side record")

    mercenary_offset = record_offset + FIELD_OFFSETS["mercenaries"]
    current = source[mercenary_offset : mercenary_offset + 6]
    if current != EXPECTED_MERCENARIES:
        raise ValueError(
            "probe target mercenary layout changed: "
            f"expected {EXPECTED_MERCENARIES.hex().upper()}, "
            f"got {current.hex().upper()}"
        )

    output = bytearray(source)
    target_offsets = frozenset(mercenary_offset + slot for slot in PROBE_SLOTS)
    for offset in target_offsets:
        output[offset] = PROBE_CLASS_ID
    checksum = update_checksum(output)

    changed_offsets = frozenset(
        index
        for index, (before, after) in enumerate(zip(source, output))
        if before != after
    )
    allowed_offsets = target_offsets | CHECKSUM_OFFSETS
    if not target_offsets.issubset(changed_offsets):
        raise AssertionError("probe did not change both requested soldier slots")
    if changed_offsets - allowed_offsets:
        unexpected = ", ".join(
            f"0x{offset:06X}" for offset in sorted(changed_offsets - allowed_offsets)
        )
        raise AssertionError(f"probe changed unexpected offsets: {unexpected}")

    report = {
        "status": "diagnostic_only_not_for_distribution",
        "source_sha256": hard_mode_baseline.NORMAL_SHA256,
        "scenario": PROBE_SCENARIO,
        "record_index": PROBE_RECORD_INDEX,
        "record_offset": f"0x{record_offset:06X}",
        "side": f"{PROBE_SIDE:02X}",
        "source_mercenaries": [
            f"{class_id:02X}" for class_id in EXPECTED_MERCENARIES
        ],
        "patched_slots": list(PROBE_SLOTS),
        "patched_class_id": f"{PROBE_CLASS_ID:02X}",
        "target_offsets": [
            f"0x{offset:06X}" for offset in sorted(target_offsets)
        ],
        "changed_offsets": [
            f"0x{offset:06X}" for offset in sorted(changed_offsets)
        ],
        "header_checksum": f"{checksum:04X}",
        "output_sha256": hashlib.sha256(output).hexdigest(),
    }
    return bytes(output), report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    if source == output:
        raise SystemExit("refusing to overwrite the immutable source ROM")

    probe, report = patch_probe(source.read_bytes())
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

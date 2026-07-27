#!/usr/bin/env python3
"""Prove ownership of every byte changed after the 5ED9 full-game baseline."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder


DEFAULT_CANDIDATE = ROOT / "roms/builds/Langrisser II (Korean).md"
DEFAULT_JSON = ROOT / "localization/release_delta_5ed9_to_99fd.json"
DEFAULT_MARKDOWN = ROOT / "docs/release_delta_5ed9_to_99fd.md"

BASELINE_SOURCE_COMMIT = "3e4954a8a493344cb31fb29b91e71f3a5c61ef54"
LAST_ROM_CHANGE_COMMIT = "ed82c841a710125d90b371f81fb12a76db873a61"
BASELINE_SHA256 = "ba9d3ae0f481a3f1421a1286d5e215fe4d49143d49fc1e32737c9868b66d4d27"
CANDIDATE_SHA256 = "526237277c8f46a4400c00980da704e6ebea23e74d967d89b6d223db28dd54d3"
BASELINE_CHECKSUM = "5ED9"
CANDIDATE_CHECKSUM = "99FD"

LIVE_EVIDENCE = (
    {
        "owner": "villain_montage_records",
        "role": "cold-boot Alhazard line",
        "path": "captures/run/99fd_opening_villain_alhazard.png",
    },
    {
        "owner": "villain_montage_records",
        "role": "cold-boot power line",
        "path": "captures/run/99fd_opening_villain_power.png",
    },
    {
        "owner": "villain_montage_records",
        "role": "cold-boot world line",
        "path": "captures/run/99fd_opening_villain_world.png",
    },
    {
        "owner": "villain_montage_records",
        "role": "return to intact title",
        "path": "captures/run/99fd_opening_villain_title_return.png",
    },
    {
        "owner": "shaman_generic_sprite",
        "role": "source candidate screen",
        "path": "captures/run/99fd_release_shaman_candidate1.png",
    },
    {
        "owner": "shaman_commander_sprites",
        "role": "applied Shaman stable map",
        "path": "captures/run/99fd_release_shaman_stable_map.png",
    },
    {
        "owner": "shaman_commander_sprites",
        "role": "applied Shaman command and status panel",
        "path": "captures/run/99fd_release_shaman_applied_status.png",
    },
    {
        "owner": "shaman_sprite_pointers",
        "role": "applied class 0A / commander 1 / LV1 GST",
        "path": "captures/analysis/99fd_release_shaman.gst",
    },
    {
        "owner": "loren_custom_sprite",
        "role": "Scenario 2 Loren map and status row",
        "path": "captures/run/99fd_release_loren_status.png",
    },
    {
        "owner": "loren_custom_sprite",
        "role": "Scenario 2 Loren popup",
        "path": "captures/run/99fd_release_loren_popup.png",
    },
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _range(name: str, start: int, end: int) -> dict[str, object]:
    return {
        "owner": name,
        "start": start,
        "end": end,
    }


def ownership_ranges(baseline: bytes) -> list[dict[str, object]]:
    ranges = [
        _range("header_checksum", 0x00018E, 0x000190),
        _range(
            "shaman_sprite_pointers",
            builder.GENERIC_CLASS_SPRITE_TABLE + builder.SHAMAN_CLASS_ID * 2,
            builder.GENERIC_CLASS_SPRITE_TABLE
            + builder.SHAMAN_CLASS_ID * 2
            + 2,
        ),
        _range("villain_montage_records", 0x0A6B20, 0x0A6BA8),
    ]
    for commander_id in builder.SHAMAN_COMMANDER_SOURCE_SPRITE_IDS:
        start = (
            builder.commander_sprite_record_offset(
                baseline,
                commander_id,
                builder.SHAMAN_CLASS_ID,
            )
            + 1
        )
        ranges.append(_range("shaman_sprite_pointers", start, start + 2))

    sprite_groups = (
        ("bald_custom_sprite", builder.BALD_CUSTOM_FRAME_OFFSETS),
        ("loren_custom_sprite", builder.LOREN_CUSTOM_FRAME_OFFSETS),
        ("shaman_generic_sprite", builder.SHAMAN_CUSTOM_FRAME_OFFSETS),
        (
            "shaman_commander_sprites",
            tuple(
                offset
                for offsets in builder.SHAMAN_COMMANDER_CUSTOM_FRAME_OFFSETS.values()
                for offset in offsets
            ),
        ),
    )
    for owner, offsets in sprite_groups:
        for start in offsets:
            ranges.append(
                _range(owner, start, start + builder.MAP_SPRITE_BYTES)
            )

    occupied: dict[int, str] = {}
    for row in ranges:
        owner = str(row["owner"])
        for offset in range(int(row["start"]), int(row["end"])):
            previous = occupied.setdefault(offset, owner)
            if previous != owner:
                raise ValueError(
                    f"release ownership overlap at 0x{offset:06X}: "
                    f"{previous} and {owner}"
                )
    return ranges


def analyze_delta(
    baseline: bytes,
    candidate: bytes,
    ranges: list[dict[str, object]],
) -> dict[str, object]:
    if len(baseline) != len(candidate):
        raise ValueError(
            f"ROM sizes differ: {len(baseline)} != {len(candidate)}"
        )

    owner_by_offset: dict[int, str] = {}
    owner_capacity = Counter()
    for row in ranges:
        owner = str(row["owner"])
        start = int(row["start"])
        end = int(row["end"])
        if not 0 <= start <= end <= len(baseline):
            raise ValueError(f"invalid {owner} range: 0x{start:X}..0x{end:X}")
        owner_capacity[owner] += end - start
        for offset in range(start, end):
            previous = owner_by_offset.setdefault(offset, owner)
            if previous != owner:
                raise ValueError(
                    f"release ownership overlap at 0x{offset:06X}: "
                    f"{previous} and {owner}"
                )

    changed = [
        offset
        for offset, (before, after) in enumerate(zip(baseline, candidate))
        if before != after
    ]
    changed_by_owner = Counter(
        owner_by_offset.get(offset, "unclassified") for offset in changed
    )

    contiguous = []
    if changed:
        start = previous = changed[0]
        owner = owner_by_offset.get(start, "unclassified")
        for offset in changed[1:]:
            next_owner = owner_by_offset.get(offset, "unclassified")
            if offset == previous + 1 and next_owner == owner:
                previous = offset
                continue
            contiguous.append(
                {
                    "owner": owner,
                    "start": f"0x{start:06X}",
                    "end": f"0x{previous + 1:06X}",
                    "size": previous + 1 - start,
                }
            )
            start = previous = offset
            owner = next_owner
        contiguous.append(
            {
                "owner": owner,
                "start": f"0x{start:06X}",
                "end": f"0x{previous + 1:06X}",
                "size": previous + 1 - start,
            }
        )

    owner_names = sorted(set(owner_capacity) | set(changed_by_owner))
    return {
        "rom_size": len(baseline),
        "changed_byte_count": len(changed),
        "unchanged_byte_count": len(baseline) - len(changed),
        "contiguous_changed_range_count": len(contiguous),
        "unclassified_changed_byte_count": changed_by_owner["unclassified"],
        "owners": [
            {
                "owner": owner,
                "permitted_byte_count": owner_capacity[owner],
                "changed_byte_count": changed_by_owner[owner],
                "changed_range_count": sum(
                    row["owner"] == owner for row in contiguous
                ),
            }
            for owner in owner_names
            if owner != "unclassified"
        ],
        "changed_ranges": contiguous,
    }


def inventory(baseline: bytes, candidate: bytes) -> dict[str, object]:
    baseline_hash = sha256(baseline)
    candidate_hash = sha256(candidate)
    if baseline_hash != BASELINE_SHA256:
        raise ValueError(
            f"baseline SHA-256 changed: {baseline_hash} != {BASELINE_SHA256}"
        )
    if candidate_hash != CANDIDATE_SHA256:
        raise ValueError(
            f"candidate SHA-256 changed: {candidate_hash} != {CANDIDATE_SHA256}"
        )
    baseline_checksum = baseline[0x18E:0x190].hex().upper()
    candidate_checksum = candidate[0x18E:0x190].hex().upper()
    if baseline_checksum != BASELINE_CHECKSUM:
        raise ValueError(
            f"baseline checksum changed: {baseline_checksum} != "
            f"{BASELINE_CHECKSUM}"
        )
    if candidate_checksum != CANDIDATE_CHECKSUM:
        raise ValueError(
            f"candidate checksum changed: {candidate_checksum} != "
            f"{CANDIDATE_CHECKSUM}"
        )

    ranges = ownership_ranges(baseline)
    delta = analyze_delta(baseline, candidate, ranges)
    owner_counts = {
        str(row["owner"]): int(row["changed_byte_count"])
        for row in delta["owners"]
    }
    expected_counts = {
        "header_checksum": 2,
        "shaman_sprite_pointers": 16,
        "villain_montage_records": 88,
        "bald_custom_sprite": 0,
        "loren_custom_sprite": 94,
        "shaman_generic_sprite": 256,
        "shaman_commander_sprites": 1788,
    }
    if owner_counts != expected_counts:
        raise ValueError(
            f"release delta owner counts changed: {owner_counts!r} "
            f"!= {expected_counts!r}"
        )
    if delta["unclassified_changed_byte_count"]:
        raise ValueError(
            "release delta contains "
            f"{delta['unclassified_changed_byte_count']} unclassified bytes"
        )

    live_evidence = []
    for row in LIVE_EVIDENCE:
        path = ROOT / str(row["path"])
        if not path.is_file():
            raise ValueError(f"release live evidence is missing: {path}")
        live_evidence.append(
            {
                **row,
                "sha256": sha256(path.read_bytes()),
            }
        )

    return {
        "baseline": {
            "source_commit": BASELINE_SOURCE_COMMIT,
            "header_checksum": baseline_checksum,
            "sha256": baseline_hash,
        },
        "candidate": {
            "last_rom_change_commit": LAST_ROM_CHANGE_COMMIT,
            "header_checksum": candidate_checksum,
            "sha256": candidate_hash,
        },
        "scope": {
            "purpose": (
                "prove that post-full-game changes are limited to the "
                "reviewed villain montage and custom class sprites"
            ),
            "normal_game_balance_changed": False,
            "scenario_event_or_ui_code_changed": False,
        },
        "delta": delta,
        "live_evidence": live_evidence,
        "complete": True,
    }


def markdown_report(result: dict[str, object]) -> str:
    baseline = result["baseline"]
    candidate = result["candidate"]
    delta = result["delta"]
    lines = [
        "# Release Delta: 5ED9 to 99FD",
        "",
        "This inventory compares the last full-game runtime baseline with the",
        "current source-reproducible Korean ROM and assigns every changed byte",
        "to an explicit owner.",
        "",
        f"- Baseline commit: `{baseline['source_commit']}`",
        f"- Baseline checksum / SHA-256: `{baseline['header_checksum']}` / "
        f"`{baseline['sha256']}`",
        f"- Candidate last ROM change: `{candidate['last_rom_change_commit']}`",
        f"- Candidate checksum / SHA-256: `{candidate['header_checksum']}` / "
        f"`{candidate['sha256']}`",
        f"- Changed bytes: `{delta['changed_byte_count']}`",
        f"- Unclassified changed bytes: "
        f"`{delta['unclassified_changed_byte_count']}`",
        "",
        "| Owner | Permitted bytes | Changed bytes | Changed ranges |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in delta["owners"]:
        lines.append(
            f"| `{row['owner']}` | {row['permitted_byte_count']} | "
            f"{row['changed_byte_count']} | {row['changed_range_count']} |"
        )
    lines.extend(
        [
            "",
            "The two checksum bytes are derived metadata. The 16 pointer bytes",
            "select separate expanded-ROM Shaman sprites. The 88 montage bytes",
            "are confined to the overlapping `0x0A6B20..0x0A6BA8` records.",
            "All remaining changes are map-sprite pixels in reserved expanded-ROM",
            "frames. No scenario event, shared UI code, text pointer, unit stat,",
            "or balance record changed between these builds.",
            "",
            "## Live Evidence",
            "",
        ]
    )
    for row in result["live_evidence"]:
        lines.append(
            f"- `{row['owner']}`: {row['role']} — `{row['path']}` "
            f"(`{row['sha256']}`)"
        )
    lines.extend(
        [
            "",
            "The baseline can be reproduced by checking out the recorded detached",
            "commit in a temporary worktree, copying the same Japanese source ROM",
            "to `roms/original/`, and running `scripts/build_korean_jp_probe.py`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "baseline",
        type=Path,
        help="source-built 5ED9 Korean baseline ROM",
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        default=DEFAULT_CANDIDATE,
        help="current 99FD Korean ROM",
    )
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    result = inventory(
        args.baseline.read_bytes(),
        args.candidate.read_bytes(),
    )
    args.json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['delta']['changed_byte_count']} changed bytes, "
        f"{result['delta']['unclassified_changed_byte_count']} unclassified"
    )


if __name__ == "__main__":
    main()

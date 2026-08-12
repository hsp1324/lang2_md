#!/usr/bin/env python3
"""Aggregate the fail-closed v1.3.7 mercenary-cache boundary evidence."""

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
from tools import class_hire_data
from tools import run_blastem_sequence as sequence
from tools import scenario_data
from tools.v137_release_identity import RELEASE_ROM_PATHS, RELEASE_ROM_SHA256


GST_WORK_RAM_OFFSET = 0x2478
FIXED_CACHE_TABLE = 0xA84E
FIXED_CACHE_COUNT = 16
DYNAMIC_CACHE_TABLE = 0xA88E
DYNAMIC_CACHE_COUNT = 10
CACHE_ROW_BYTES = 4
FOLLOWING_OWNER_BYTES = 16

DEFAULT_EVIDENCE_ROOT = ROOT / "captures/run/v137-s13-cache-formal/hover"
DEFAULT_OUTPUT = ROOT / "captures/run/v137-s13-cache-formal/summary.json"
REFERENCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"

FRESH_SEEDS = {
    "pure": {
        "path": ROOT / (
            "captures/run/v137-s13-cache-formal/fresh-seeds/pure/"
            "v137-s13-cache-current-20260812/fresh_s1_preparation.gst"
        ),
        "report": ROOT / (
            "captures/run/v137-s13-cache-formal/fresh-seeds/pure/"
            "v137-s13-cache-current-20260812/report.json"
        ),
        "sha256": (
            "76c947b896faa2906132a9eb7491798922d43f92c75e90971ae8bcd6ea5e1980"
        ),
    },
    "normal": {
        "path": ROOT / (
            "captures/run/v137-s13-cache-formal/fresh-seeds/normal/"
            "v137-s13-cache-current-20260812/fresh_s1_preparation.gst"
        ),
        "report": ROOT / (
            "captures/run/v137-s13-cache-formal/fresh-seeds/normal/"
            "v137-s13-cache-current-20260812/report.json"
        ),
        "sha256": (
            "fe8460ba8055e64e69c1e364e86db179791041ab33f243413eebfc3c4c223567"
        ),
    },
    "hard": {
        "path": ROOT / (
            "captures/run/v137-s13-cache-formal/fresh-seeds/hard/"
            "v137-s13-cache-current-20260812/fresh_s1_preparation.gst"
        ),
        "report": ROOT / (
            "captures/run/v137-s13-cache-formal/fresh-seeds/hard/"
            "v137-s13-cache-current-20260812/report.json"
        ),
        "sha256": (
            "a91b5cfaac1573e9d86a4c4544963f79071bbe447b25e4c5787e0470427fbe3e"
        ),
    },
}

RELEASES = {
    "pure": {
        "path": RELEASE_ROM_PATHS["pure"],
        "sha256": RELEASE_ROM_SHA256["pure"],
    },
    "normal": {
        "path": RELEASE_ROM_PATHS["normal"],
        "sha256": RELEASE_ROM_SHA256["normal"],
    },
    "hard": {
        "path": RELEASE_ROM_PATHS["hard"],
        "sha256": RELEASE_ROM_SHA256["hard"],
    },
}

HOVER_CASES = (
    {
        "name": "stock-pure-s13-74-current-20260812-01",
        "profile": "pure",
        "scenario": 13,
        "class_id": 0x74,
        "owner": "dynamic",
        "index": 2,
        "tile": 0x390,
        "runtime_key": (9, 1),
        "kind": "exact_release",
    },
    {
        "name": "stock-normal-s13-74-current-20260812-01",
        "profile": "normal",
        "scenario": 13,
        "class_id": 0x74,
        "owner": "dynamic",
        "index": 2,
        "tile": 0x390,
        "runtime_key": (9, 1),
        "kind": "exact_release",
    },
    {
        "name": "stock-hard-s13-74-current-20260812-01",
        "profile": "hard",
        "scenario": 13,
        "class_id": 0x74,
        "owner": "dynamic",
        "index": 4,
        "tile": 0x398,
        "runtime_key": (9, 3),
        "kind": "exact_release",
    },
    {
        "name": "stock-hard-s13-63-current-20260812-01",
        "profile": "hard",
        "scenario": 13,
        "class_id": 0x63,
        "owner": "fixed",
        "index": 1,
        "tile": 0x34C,
        "runtime_key": (12, 1),
        "kind": "exact_release_ordinary_reuse",
    },
    {
        "name": "stock-pure-s16-73-current-20260812-01",
        "profile": "pure",
        "scenario": 16,
        "class_id": 0x73,
        "owner": "dynamic",
        "index": 6,
        "tile": 0x3A0,
        "runtime_key": (13, 5),
        "kind": "exact_release",
    },
    {
        "name": "stock-normal-s16-73-current-20260812-01",
        "profile": "normal",
        "scenario": 16,
        "class_id": 0x73,
        "owner": "dynamic",
        "index": 6,
        "tile": 0x3A0,
        "runtime_key": (13, 5),
        "kind": "exact_release",
    },
    {
        "name": "overflow-normal-s13-72-current-20260812-01",
        "profile": "normal",
        "scenario": 13,
        "class_id": 0x72,
        "owner": "dynamic",
        "index": 1,
        "tile": 0x38C,
        "runtime_key": (10, 5),
        "kind": "source_locked_diagnostic",
        "rom_sha256": "0769ec812257dcca555a3799a28f60dce4d0c1b111360da052d7c5926048e11b",
    },
    {
        "name": "overflow-hard-s13-72-current-20260812-01",
        "profile": "hard",
        "scenario": 13,
        "class_id": 0x72,
        "owner": "dynamic",
        "index": 2,
        "tile": 0x390,
        "runtime_key": (7, 5),
        "kind": "source_locked_diagnostic",
        "rom_sha256": "9d46c40f5dd41a1c482db1782e3bcf192acb969e8f169df23e5b503479aa4cbb",
    },
    {
        "name": "overflow-hard-s13-7c-current-20260812-01",
        "profile": "hard",
        "scenario": 13,
        "class_id": 0x7C,
        "owner": "fixed",
        "index": 15,
        "tile": 0x384,
        "runtime_key": (16, 1),
        "kind": "source_locked_diagnostic_borrowed_fixed",
        "rom_sha256": "9d46c40f5dd41a1c482db1782e3bcf192acb969e8f169df23e5b503479aa4cbb",
    },
)

BOUNDARIES = (
    ("pure", 13, "stock-pure-s13-74-current-20260812-01"),
    ("normal", 13, "stock-normal-s13-74-current-20260812-01"),
    ("hard", 13, "stock-hard-s13-74-current-20260812-01"),
    ("pure", 16, "stock-pure-s16-73-current-20260812-01"),
    ("normal", 16, "stock-normal-s16-73-current-20260812-01"),
)

DIAGNOSTIC_TABLES = {
    "normal": {
        "evidence": "overflow-normal-s13-72-current-20260812-01",
        "manifest": ROOT / (
            "captures/analysis/v137-s13-cache-formal/"
            "normal-s13-overflow.manifest.json"
        ),
        "fixed": tuple(range(0x62, 0x70)) + (0x7B, 0x7A),
        "dynamic": (0x79, 0x72, 0x74, 0x76, 0x77, 0x7F, 0x7E, 0x7D, 0x7C, 0x73),
    },
    "hard": {
        "evidence": "overflow-hard-s13-72-current-20260812-01",
        "manifest": ROOT / (
            "captures/analysis/v137-s13-cache-formal/"
            "hard-s13-overflow.manifest.json"
        ),
        "fixed": tuple(range(0x62, 0x70)) + (0x7B, 0x7C),
        "dynamic": (0x7A, 0x79, 0x72, 0x73, 0x74, 0x76, 0x77, 0x7F, 0x7E, 0x7D),
    },
}

PURE_STRESS_EVIDENCE = ROOT / (
    "tmp/v137-s13-cache-supplement/overflow-final/pure/0x72/"
    "v137-s13-overflow-final-pure-72/evidence.json"
)


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def work_ram(path: Path) -> bytes:
    payload = path.read_bytes()
    ram = payload[GST_WORK_RAM_OFFSET:GST_WORK_RAM_OFFSET + 0x10000]
    if len(ram) != 0x10000:
        raise ValueError(f"GST is missing work RAM: {path}")
    return ram


def cache_rows(ram: bytes, base: int, count: int) -> list[dict[str, int]]:
    rows = []
    for index in range(count):
        offset = base + index * CACHE_ROW_BYTES
        rows.append(
            {
                "index": index,
                "class_id": int.from_bytes(ram[offset:offset + 2], "big"),
                "tile": int.from_bytes(ram[offset + 2:offset + 4], "big"),
            }
        )
    return rows


def format_rows(rows: list[dict[str, int]]) -> list[dict[str, object]]:
    return [
        {
            "index": row["index"],
            "class_id": f"0x{row['class_id']:02X}",
            "tile": f"0x{row['tile']:04X}",
        }
        for row in rows
    ]


def fresh_seed_report(profile: str) -> dict[str, object]:
    spec = FRESH_SEEDS[profile]
    path = Path(spec["path"])
    report_path = Path(spec["report"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    expected_rom = RELEASES[profile]
    checks = {
        "fresh_new_game_report_passed": report.get("status") == "pass",
        "profile_source_locked": report.get("profile") == profile,
        "release_rom_source_locked": (
            report.get("rom", {}).get("path") == relative(Path(expected_rom["path"]))
            and report.get("rom", {}).get("sha256") == expected_rom["sha256"]
        ),
        "fresh_runtime_had_no_imported_sram_or_gst": (
            report.get("isolation", {}).get("manual_sram_seed") is None
            and report.get("isolation", {}).get("manual_gst_seed") is None
            and report.get("isolation", {}).get("empty_runtime_verified") is True
        ),
        "scenario_1_source_locked": report.get("snapshot", {}).get("scenario") == 1,
        "gst_path_source_locked": (
            report.get("scenario_1_gst", {}).get("path") == relative(path)
        ),
        "gst_hash_source_locked": (
            sha256(path)
            == report.get("scenario_1_gst", {}).get("sha256")
            == spec["sha256"]
        ),
    }
    return {
        "profile": profile,
        "report": relative(report_path),
        "gst": relative(path),
        "gst_sha256": spec["sha256"],
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def fixed_record_classes(rom: bytes, number: int) -> tuple[set[int], set[int]]:
    reference = REFERENCE_ROM.read_bytes()
    model = scenario_data.read_scenario(rom, reference, number)
    ordinary: set[int] = set()
    advanced: set[int] = set()
    for record in model["records"]:
        if int(record["side_id"]) == 0:
            continue
        for class_id in record["mercenaries"]:
            if class_id == 0xFF:
                continue
            if 0x62 <= class_id <= 0x71:
                ordinary.add(class_id)
            else:
                advanced.add(class_id)
    return ordinary, advanced


def hover_case_report(root: Path, spec: dict[str, object]) -> dict[str, object]:
    path = root / str(spec["name"]) / "evidence.json"
    evidence = json.loads(path.read_text(encoding="utf-8"))
    expected_rom = str(
        spec.get("rom_sha256", RELEASES[str(spec["profile"])]["sha256"])
    )
    expected_seed = str(FRESH_SEEDS[str(spec["profile"])]["sha256"])
    group_index, member_index = spec["runtime_key"]
    contract = evidence.get("acceptance_contract", {})
    before = evidence.get("before_cache", {})
    hover = evidence.get("hover_cache", {})
    checks = {
        "runner_status_pass": evidence.get("status") == "pass",
        "all_runner_checks_pass": bool(evidence.get("checks"))
        and all(evidence["checks"].values()),
        "rom_hash_source_locked": evidence.get("rom", {}).get("sha256")
        == expected_rom,
        "fresh_seed_hash_source_locked": evidence.get("seed_gst", {}).get(
            "sha256"
        )
        == expected_seed,
        "scenario_source_locked": evidence.get("scenario") == spec["scenario"],
        "class_source_locked": evidence.get("target", {}).get("class_id")
        == f"0x{int(spec['class_id']):02X}",
        "runtime_key_source_locked": (
            evidence.get("target", {}).get("group_index"),
            evidence.get("target", {}).get("member_index"),
        )
        == (group_index, member_index),
        "declared_contract_source_locked": (
            contract.get("cache_owner") == spec["owner"]
            and contract.get("runtime_key")
            == {"group_index": group_index, "member_index": member_index}
            and contract.get("rom_sha256") == expected_rom
        ),
        "declared_fresh_seed_contract_source_locked": contract.get(
            "seed_gst_sha256"
        )
        == expected_seed,
        "before_owner_index_tile_source_locked": (
            before.get("cache_owner") == spec["owner"]
            and before.get("cache_index") == spec["index"]
            and before.get("base_tile") == f"0x{int(spec['tile']):04X}"
        ),
        "hover_owner_index_tile_source_locked": (
            hover.get("cache_owner") == spec["owner"]
            and hover.get("cache_index") == spec["index"]
            and hover.get("base_tile") == f"0x{int(spec['tile']):04X}"
        ),
        "both_frames_match_exact_rom_source": (
            before.get("both_frames_match_rom_source") is True
            and hover.get("both_frames_match_rom_source") is True
        ),
        "hover_plane_a_links_complete_sprite": hover.get(
            "one_animation_frame_referenced_by_plane_a"
        )
        is True,
        "cursor_reached_source_locked_target": evidence.get("cursor", {}).get(
            "after_navigation"
        )
        == evidence.get("cursor", {}).get("target"),
        "rom_and_seed_inputs_unchanged": (
            evidence.get("checks", {}).get("rom_input_unchanged") is True
            and evidence.get("checks", {}).get("seed_gst_input_unchanged")
            is True
        ),
    }
    return {
        "name": spec["name"],
        "kind": spec["kind"],
        "profile": spec["profile"],
        "scenario": spec["scenario"],
        "class_id": f"0x{int(spec['class_id']):02X}",
        "expected_owner": spec["owner"],
        "expected_index": spec["index"],
        "expected_tile": f"0x{int(spec['tile']):04X}",
        "expected_runtime_key": {
            "group_index": group_index,
            "member_index": member_index,
        },
        "evidence": relative(path),
        "evidence_sha256": sha256(path),
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def boundary_report(
    root: Path,
    profile: str,
    number: int,
    evidence_name: str,
) -> dict[str, object]:
    release = RELEASES[profile]
    rom_path = Path(release["path"])
    rom = rom_path.read_bytes()
    evidence_path = root / evidence_name / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    gst = ROOT / evidence["before_gst"]
    ram = work_ram(gst)
    fixed = cache_rows(ram, FIXED_CACHE_TABLE, FIXED_CACHE_COUNT)
    dynamic = cache_rows(ram, DYNAMIC_CACHE_TABLE, DYNAMIC_CACHE_COUNT)
    ordinary, advanced = fixed_record_classes(rom, number)
    following = ram[
        DYNAMIC_CACHE_TABLE + DYNAMIC_CACHE_COUNT * CACHE_ROW_BYTES:
        DYNAMIC_CACHE_TABLE + DYNAMIC_CACHE_COUNT * CACHE_ROW_BYTES
        + FOLLOWING_OWNER_BYTES
    ]
    observed_dynamic = {row["class_id"] for row in dynamic}
    checks = {
        "exact_release_hash": sha256(rom_path) == release["sha256"],
        "all_16_fixed_rows_are_ordinary": [row["class_id"] for row in fixed]
        == list(range(0x62, 0x72)),
        "dynamic_capacity_is_exactly_10": len(dynamic) == 10,
        "dynamic_rows_match_all_advanced_fixed_record_classes": (
            observed_dynamic == advanced and len(advanced) == 10
        ),
        "ordinary_fixed_record_classes_are_not_dynamic": not (
            ordinary & observed_dynamic
        ),
        "following_wram_owner_is_not_overwritten": following
        == bytes(FOLLOWING_OWNER_BYTES),
        "hover_case_passed": evidence.get("status") == "pass",
    }
    return {
        "profile": profile,
        "scenario": number,
        "classification": "exact_release_capacity_boundary",
        "rom": {"path": relative(rom_path), "sha256": release["sha256"]},
        "fixed_record_ordinary_class_ids": [
            f"0x{value:02X}" for value in sorted(ordinary)
        ],
        "fixed_record_advanced_class_ids": [
            f"0x{value:02X}" for value in sorted(advanced)
        ],
        "fixed_cache": format_rows(fixed),
        "dynamic_cache": format_rows(dynamic),
        "following_owner_hex": following.hex(),
        "evidence": relative(evidence_path),
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def diagnostic_report(root: Path, profile: str) -> dict[str, object]:
    spec = DIAGNOSTIC_TABLES[profile]
    evidence_path = root / str(spec["evidence"]) / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    manifest_path = Path(spec["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    gst = ROOT / evidence["before_gst"]
    ram = work_ram(gst)
    fixed = cache_rows(ram, FIXED_CACHE_TABLE, FIXED_CACHE_COUNT)
    dynamic = cache_rows(ram, DYNAMIC_CACHE_TABLE, DYNAMIC_CACHE_COUNT)
    following = ram[
        DYNAMIC_CACHE_TABLE + DYNAMIC_CACHE_COUNT * CACHE_ROW_BYTES:
        DYNAMIC_CACHE_TABLE + DYNAMIC_CACHE_COUNT * CACHE_ROW_BYTES
        + FOLLOWING_OWNER_BYTES
    ]
    requested_advanced = {
        row["class_id"] for row in fixed if row["class_id"] >= 0x72
    } | {row["class_id"] for row in dynamic if row["class_id"] >= 0x72}
    expected_fixed = list(spec["fixed"])
    expected_dynamic = list(spec["dynamic"])
    checks = {
        "manifest_status_pass": manifest.get("status") == "pass",
        "diagnostic_hash_matches_manifest": evidence["rom"]["sha256"]
        == manifest["output"]["sha256"]
        == manifest["output"]["expected_sha256"],
        "diagnostic_is_exact_seven_byte_delta": len(
            manifest.get("changed_bytes", [])
        )
        == 7,
        "fixed_table_source_locked": [row["class_id"] for row in fixed]
        == expected_fixed,
        "dynamic_table_source_locked": [row["class_id"] for row in dynamic]
        == expected_dynamic,
        "all_12_advanced_classes_have_a_bounded_owner": len(
            requested_advanced
        )
        == 12,
        "dynamic_table_stays_at_capacity_10": len(dynamic) == 10,
        "following_wram_owner_is_not_overwritten": following
        == bytes(FOLLOWING_OWNER_BYTES),
        "hover_case_passed": evidence.get("status") == "pass",
    }
    return {
        "profile": profile,
        "classification": "source_locked_diagnostic_not_natural_gameplay",
        "manifest": relative(manifest_path),
        "evidence": relative(evidence_path),
        "advanced_class_count": len(requested_advanced),
        "fixed_cache": format_rows(fixed),
        "dynamic_cache": format_rows(dynamic),
        "following_owner_hex": following.hex(),
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def pure_stress_classification() -> dict[str, object]:
    evidence = json.loads(PURE_STRESS_EVIDENCE.read_text(encoding="utf-8"))
    gst = ROOT / evidence["before_gst"]
    ram = work_ram(gst)
    overflow = cache_rows(
        ram,
        DYNAMIC_CACHE_TABLE + DYNAMIC_CACHE_COUNT * CACHE_ROW_BYTES,
        2,
    )
    save_ranges = tuple(sequence.MANUAL_SLOT_WORK_RAM_SEGMENTS)
    runtime_start = 0x603C
    runtime_end = runtime_start + 20 * 0x60
    save_overlaps_runtime = any(
        start < runtime_end and runtime_start < start + size
        for start, size in save_ranges
    )
    checks = {
        "pure_release_omits_cache_hooks": all(
            Path(RELEASES["pure"]["path"]).read_bytes()[
                offset:offset + len(builder.ENEMY_ORDINARY_MERCENARY_CACHE_HOOK_ORIGINAL)
            ]
            == builder.ENEMY_ORDINARY_MERCENARY_CACHE_HOOK_ORIGINAL
            for offset in (
                builder.ENEMY_ORDINARY_MERCENARY_CACHE_LOADER_HOOK,
                builder.ENEMY_ORDINARY_MERCENARY_CACHE_LOOKUP_HOOK,
            )
        ),
        "synthetic_rows_11_and_12_overwrite_following_owner": [
            (row["class_id"], row["tile"]) for row in overflow
        ]
        == [(0x7A, 0x3B0), (0x7B, 0x3B4)],
        "battery_sram_does_not_serialize_runtime_groups": not save_overlaps_runtime,
        "allied_hire_mask_only_addresses_ordinary_classes": (
            class_hire_data.MERCENARY_CLASS_BASE == 0x62
            and class_hire_data.MERCENARY_CLASS_COUNT == 16
        ),
    }
    return {
        "profile": "pure",
        "classification": "unsupported_out_of_domain_synthetic_stress",
        "acceptance_blocker": False,
        "reason": (
            "Exact v1.3.7 fixed records never exceed ten advanced classes; "
            "battery SRAM does not save enemy runtime groups, allied hires are "
            "ordinary 0x62..0x71, and cross-ROM emulator savestates are unsupported."
        ),
        "evidence": relative(PURE_STRESS_EVIDENCE),
        "overflow_rows": format_rows(overflow),
        "checks": checks,
        "status": "classified" if all(checks.values()) else "fail",
    }


def build_report(evidence_root: Path) -> dict[str, object]:
    fresh_seeds = [fresh_seed_report(profile) for profile in RELEASES]
    hover = [hover_case_report(evidence_root, spec) for spec in HOVER_CASES]
    boundaries = [
        boundary_report(evidence_root, profile, scenario, evidence)
        for profile, scenario, evidence in BOUNDARIES
    ]
    diagnostics = [
        diagnostic_report(evidence_root, profile) for profile in ("normal", "hard")
    ]
    pure_stress = pure_stress_classification()
    status = "pass" if (
        all(row["status"] == "pass" for row in fresh_seeds)
        and all(row["status"] == "pass" for row in hover)
        and all(row["status"] == "pass" for row in boundaries)
        and all(row["status"] == "pass" for row in diagnostics)
        and pure_stress["status"] == "classified"
    ) else "fail"
    return {
        "schema_version": 1,
        "status": status,
        "scope": "v1.3.7_s13_s16_mercenary_cache_fail_closed_matrix",
        "acceptance_policy": {
            "pure": (
                "Exact release S13 and S16 capacity=10 boundaries are required. "
                "The 12-class diagnostic is out-of-domain and is not a release pass."
            ),
            "normal": (
                "Exact release boundaries plus source-locked overflow diagnostics."
            ),
            "hard": (
                "Exact S13 ordinary fixed-cache reuse plus dynamic capacity=10, "
                "then source-locked overflow diagnostics."
            ),
        },
        "fresh_seed_lineage": fresh_seeds,
        "hover_cases": hover,
        "exact_release_boundaries": boundaries,
        "source_locked_diagnostics": diagnostics,
        "pure_synthetic_stress": pure_stress,
        "limitations": [
            "The overflow ROMs are seven-byte source-locked diagnostics, not release gameplay.",
            "The Pure synthetic 12-class roster is deliberately excluded from release acceptance.",
            "This matrix checks map-cache rendering; side-view combat animation is covered separately.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    evidence_root = args.evidence_root.resolve()
    output = args.output.resolve()
    report = build_report(evidence_root)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise ValueError(f"checked S13 cache matrix is stale: {output}")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(output)
    print(f"status={report['status']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

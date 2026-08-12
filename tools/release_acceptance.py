#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.class_change_data import (
    COMMANDER_COUNT,
    patch_class_change_chains,
    read_class_change_chain,
)
from tools.class_hire_data import (
    CLASS_COUNT,
    patch_class_hire_unlocks,
    read_class_hire_unlocks,
)
from tools.item_data import patch_items, read_items
from tools.scenario_data import (
    SCENARIO_COUNT,
    patch_scenario,
    read_scenario,
    update_checksum,
)


DEFAULT_ROM = (
    ROOT / "roms/builds/Langrisser II (Korean Normal v1.3.6).md"
)
REFERENCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
JSON_OUTPUT = ROOT / "localization/release_acceptance.json"
MARKDOWN_OUTPUT = ROOT / "docs/release_acceptance.md"
RELEASE_MANIFEST = ROOT / "patches/v1.3.6.json"
EXPECTED_CHECKSUM = "1F84"
EXPECTED_SHA256 = (
    "b74359800a697eea5e85d7942ac712b74360bbd8b43ff2082b88d009e94a370a"
)


def load_json(name: str) -> dict[str, object]:
    return json.loads(
        (ROOT / "localization" / name).read_text(encoding="utf-8")
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def check(
    label: str,
    passed: bool,
    actual: object,
    expected: object,
) -> dict[str, object]:
    return {
        "label": label,
        "passed": bool(passed),
        "actual": actual,
        "expected": expected,
    }


def requirement(
    requirement_id: int,
    title: str,
    checks: list[dict[str, object]],
    evidence: list[str],
) -> dict[str, object]:
    return {
        "id": requirement_id,
        "title": title,
        "passed": all(row["passed"] for row in checks),
        "checks": checks,
        "evidence": evidence,
    }


def editor_noop_roundtrip(
    production: bytes,
    reference: bytes,
) -> bytes:
    result = bytearray(production)
    for scenario_number in range(1, SCENARIO_COUNT + 1):
        model = read_scenario(production, reference, scenario_number)
        patch_scenario(result, scenario_number, model["records"])
    patch_items(result, read_items(production))
    patch_class_change_chains(
        result,
        [
            {
                "commander_id": commander_id,
                "transitions": read_class_change_chain(
                    production,
                    commander_id,
                ),
            }
            for commander_id in range(1, COMMANDER_COUNT + 1)
        ],
    )
    patch_class_hire_unlocks(
        result,
        [
            read_class_hire_unlocks(production, class_id).__dict__
            for class_id in range(CLASS_COUNT)
        ],
    )
    update_checksum(result)
    return bytes(result)


def build_inventory(rom_path: Path = DEFAULT_ROM) -> dict[str, object]:
    production = rom_path.read_bytes()
    reference = REFERENCE_ROM.read_bytes()
    checksum = production[0x18E:0x190].hex().upper()
    production_sha = sha256_bytes(production)

    runtime = load_json("runtime_verification.json")
    event_pages = load_json("event_pages.json")
    ui = load_json("ui_patch_surfaces.json")
    name_entry = load_json("name_entry_flow_inventory.json")
    items = load_json("item_shop_inventory.json")
    global_strings = load_json("global_strings.json")
    class_change = load_json("class_change_flow_inventory.json")
    magic = load_json("magic_flow_inventory.json")
    endings = load_json("ending_credits_inventory.json")
    direct_words = load_json("direct_word_candidates.json")
    direct_bytes = load_json("direct_byte_string_candidates.json")
    inline_bytes = load_json("inline_byte_strings.json")
    short_inline = load_json("short_inline_byte_candidates.json")
    compressed = load_json("compressed_resources.json")
    previous_release = load_json("v135_release_validation.json")
    current_release = load_json("v136_release_validation.json")
    release_manifest = json.loads(
        RELEASE_MANIFEST.read_text(encoding="utf-8")
    )
    previous_normal = previous_release["release_roms"]["normal"]
    current_normal = current_release["release_roms"]["normal"]
    current_delta = current_release["release_delta"]
    manifest_normal = next(
        row for row in release_manifest["targets"] if row["id"] == "normal"
    )

    runtime_rows = [
        entry[surface]
        for entry in runtime["scenarios"]
        for surface in runtime["surfaces"]
    ]
    accepted_runtime_rows = sum(
        state in {"verified_current", "verified_probe"}
        for state in runtime_rows
    )
    unchanged_ui = [
        row for row in ui["declared_patches"] if not row["modified"]
    ]
    non_live_ui = [
        row for row in ui["declared_patches"] if not row["live_verified"]
    ]
    global_tables = global_strings["tables"]
    accepted_items = sum(
        row["runtime_status"] == "accepted" for row in items["items"]
    )

    short_banks = [
        value
        for key, value in short_inline.items()
        if key.endswith("_bank")
    ]
    short_candidate_count = sum(
        bank["candidate_count"] for bank in short_banks
    )
    short_unclassified_count = sum(
        bank["unclassified_count"] for bank in short_banks
    )

    no_op = editor_noop_roundtrip(production, reference)
    no_op_sha = sha256_bytes(no_op)

    requirements = [
        requirement(
            1,
            "31 scenarios, dialogue, branches, and endings",
            [
                check(
                    "scenario count",
                    event_pages["scenario_count"] == SCENARIO_COUNT,
                    event_pages["scenario_count"],
                    SCENARIO_COUNT,
                ),
                check(
                    "all logical text pages modified",
                    event_pages["modified_text_page_count"]
                    == event_pages["text_page_count"],
                    event_pages["modified_text_page_count"],
                    event_pages["text_page_count"],
                ),
                check(
                    "all physical text pages modified",
                    event_pages["modified_text_physical_page_count"]
                    == event_pages["text_physical_page_count"],
                    event_pages["modified_text_physical_page_count"],
                    event_pages["text_physical_page_count"],
                ),
                check(
                    "all scenario runtime surfaces accepted",
                    accepted_runtime_rows == SCENARIO_COUNT * 8,
                    accepted_runtime_rows,
                    SCENARIO_COUNT * 8,
                ),
                check(
                    "ending and credits inventory complete",
                    endings["complete"] is True,
                    endings["complete"],
                    True,
                ),
            ],
            [
                "localization/event_pages.json",
                "localization/runtime_verification.json",
                "docs/runtime_verification_inventory.md",
                "localization/ending_credits_inventory.json",
            ],
        ),
        requirement(
            2,
            "shared UI and interactive flows",
            [
                check(
                    "all declared UI surfaces reviewed",
                    sum(
                        row["reviewed"]
                        for row in ui["declared_patches"]
                    )
                    == ui["declared_patch_count"],
                    sum(
                        row["reviewed"]
                        for row in ui["declared_patches"]
                    ),
                    ui["declared_patch_count"],
                ),
                check(
                    "no explicit UI inventory gaps",
                    not ui["remaining_inventory_gaps"],
                    len(ui["remaining_inventory_gaps"]),
                    0,
                ),
                check(
                    "only retained NPC abbreviation is unmodified",
                    [
                        (row["group"], row["target_korean"])
                        for row in unchanged_ui
                    ]
                    == [("fixed_byte_strings", "NPC")],
                    [
                        (row["group"], row["target_korean"])
                        for row in unchanged_ui
                    ],
                    [("fixed_byte_strings", "NPC")],
                ),
                check(
                    "only superseded load fallback lacks live evidence",
                    [
                        (row["group"], row["address"])
                        for row in non_live_ui
                    ]
                    == [("title_load_header_fallback", "0x0A3138")],
                    [
                        (row["group"], row["address"])
                        for row in non_live_ui
                    ],
                    [("title_load_header_fallback", "0x0A3138")],
                ),
                check(
                    "name-entry flow complete",
                    name_entry["complete"] is True,
                    name_entry["complete"],
                    True,
                ),
                check(
                    "all item and shop rows accepted",
                    accepted_items == 37,
                    accepted_items,
                    37,
                ),
            ],
            [
                "localization/ui_patch_surfaces.json",
                "docs/ui_patch_surface_inventory.md",
                "localization/name_entry_flow_inventory.json",
                "localization/item_shop_inventory.json",
            ],
        ),
        requirement(
            3,
            "names, classes, mercenaries, items, magic, and summons",
            [
                check(
                    "class names have Korean targets",
                    global_tables["classes"]["known_korean_target_count"]
                    == global_tables["classes"]["entry_count"]
                    == 157,
                    global_tables["classes"]["known_korean_target_count"],
                    157,
                ),
                check(
                    "commander and NPC names have Korean targets",
                    global_tables["names"]["known_korean_target_count"]
                    == global_tables["names"]["entry_count"]
                    == 117,
                    global_tables["names"]["known_korean_target_count"],
                    117,
                ),
                check(
                    "item names have Korean targets",
                    global_tables["items"]["known_korean_target_count"]
                    == global_tables["items"]["entry_count"]
                    == 38,
                    global_tables["items"]["known_korean_target_count"],
                    38,
                ),
                check(
                    "all class-change transitions structurally covered",
                    class_change["scope"][
                        "structurally_covered_application_transition_count"
                    ]
                    == class_change["scope"]["source_transition_count"]
                    == 100,
                    class_change["scope"][
                        "structurally_covered_application_transition_count"
                    ],
                    100,
                ),
                check(
                    "all magic IDs have application evidence",
                    magic["scope"][
                        "diagnostic_application_evidence_count"
                    ]
                    == magic["scope"]["magic_count"]
                    == 22,
                    magic["scope"][
                        "diagnostic_application_evidence_count"
                    ],
                    22,
                ),
                check(
                    "source-unreachable magic is bounded",
                    magic["scope"]["source_unreachable_magic_ids"] == [18],
                    magic["scope"]["source_unreachable_magic_ids"],
                    [18],
                ),
            ],
            [
                "localization/global_strings.json",
                "localization/class_change_flow_inventory.json",
                "localization/magic_flow_inventory.json",
                "localization/class_abilities.json",
            ],
        ),
        requirement(
            4,
            "patch ownership and regression safety",
            [
                check(
                    "release delta is complete",
                    current_delta["status"] == "pass",
                    current_delta["status"],
                    "pass",
                ),
                check(
                    "release delta has no unclassified bytes",
                    current_delta["unexpected_changed_bytes"] == 0,
                    current_delta["unexpected_changed_bytes"],
                    0,
                ),
                check(
                    "all current release evidence hashes match",
                    current_release["runtime_checks"]["status"] == "pass"
                    and current_release["runtime_checks"]["runestone_matrix"][
                        "passed"
                    ]
                    == current_release["runtime_checks"]["runestone_matrix"][
                        "total"
                    ]
                    == 12
                    and current_release["runtime_checks"]["runestone_matrix"][
                        "item_consumed_in_all_runs"
                    ],
                    current_release["runtime_checks"]["status"],
                    "pass",
                ),
                check(
                    "all compressed resources have owners",
                    compressed["unknown_owner_count"] == 0
                    and compressed["known_owner_count"]
                    == compressed["entry_count"],
                    compressed["known_owner_count"],
                    compressed["entry_count"],
                ),
            ],
            [
                "localization/v136_release_validation.json",
                "docs/v1.3.6_validation.md",
                "localization/compressed_resources.json",
            ],
        ),
        requirement(
            5,
            "static residue inventory and live verification matrix",
            [
                check(
                    "direct-word candidates classified",
                    direct_words["ownership_counts"][
                        "unclassified_candidate"
                    ]
                    == 0,
                    direct_words["ownership_counts"][
                        "unclassified_candidate"
                    ],
                    0,
                ),
                check(
                    "direct-byte candidates classified",
                    direct_bytes["unclassified_count"] == 0,
                    direct_bytes["unclassified_count"],
                    0,
                ),
                check(
                    "inline-byte candidates classified",
                    inline_bytes["unclassified_count"] == 0,
                    inline_bytes["unclassified_count"],
                    0,
                ),
                check(
                    "short inline candidates classified",
                    short_candidate_count
                    == short_inline["candidate_count"]
                    and short_unclassified_count == 0,
                    {
                        "candidate_count": short_candidate_count,
                        "unclassified_count": short_unclassified_count,
                    },
                    {
                        "candidate_count": short_inline[
                            "candidate_count"
                        ],
                        "unclassified_count": 0,
                    },
                ),
                check(
                    "runtime matrix contains only accepted states",
                    accepted_runtime_rows == len(runtime_rows),
                    accepted_runtime_rows,
                    len(runtime_rows),
                ),
            ],
            [
                "localization/direct_word_candidates.json",
                "localization/direct_byte_string_candidates.json",
                "localization/inline_byte_strings.json",
                "localization/short_inline_byte_candidates.json",
                "localization/runtime_verification.json",
            ],
        ),
        requirement(
            6,
            "source-identified editor data",
            [
                check(
                    "scenario editor covers all scenarios",
                    event_pages["scenario_count"] == SCENARIO_COUNT,
                    event_pages["scenario_count"],
                    SCENARIO_COUNT,
                ),
                check(
                    "class editor covers every class",
                    global_tables["classes"]["entry_count"] == CLASS_COUNT,
                    global_tables["classes"]["entry_count"],
                    CLASS_COUNT,
                ),
                check(
                    "no-op editor build is byte-identical",
                    no_op == production,
                    no_op_sha,
                    production_sha,
                ),
            ],
            [
                "docs/editor_data_model.md",
                "tools/scenario_data.py",
                "editor/model.py",
                "editor/server.py",
            ],
        ),
        requirement(
            7,
            "handoff and reproducibility records",
            [
                check(
                    "required handoff documents exist",
                    all(
                        (ROOT / path).is_file()
                        for path in (
                            "README.md",
                            "HANDOFF.md",
                            "docs/full_localization_plan.md",
                            "docs/editor_data_model.md",
                        )
                    ),
                    True,
                    True,
                ),
                check(
                    "release delta records both build identities",
                    bool(previous_normal["sha256"])
                    and current_delta["previous_release"] == "v1.3.5"
                    and current_normal["sha256"] == production_sha,
                    current_normal["sha256"],
                    production_sha,
                ),
            ],
            [
                "README.md",
                "HANDOFF.md",
                "docs/full_localization_plan.md",
                "docs/editor_data_model.md",
            ],
        ),
        requirement(
            8,
            "canonical release ROM",
            [
                check(
                    "ROM size",
                    len(production) == 0x400000,
                    len(production),
                    0x400000,
                ),
                check(
                    "header checksum",
                    checksum == EXPECTED_CHECKSUM,
                    checksum,
                    EXPECTED_CHECKSUM,
                ),
                check(
                    "SHA-256",
                    production_sha == EXPECTED_SHA256,
                    production_sha,
                    EXPECTED_SHA256,
                ),
                check(
                    "public manifest uses canonical ROM",
                    manifest_normal["output_sha256"] == production_sha
                    and manifest_normal["output_size"] == len(production),
                    manifest_normal["output_sha256"],
                    production_sha,
                ),
            ],
            [
                "roms/builds/Langrisser II (Korean Normal v1.3.6).md",
                "patches/v1.3.6.json",
                "localization/v136_release_validation.json",
            ],
        ),
    ]

    complete = all(row["passed"] for row in requirements)
    return {
        "schema_version": 1,
        "release": {
            "path": display_path(rom_path),
            "size": len(production),
            "header_checksum": checksum,
            "sha256": production_sha,
        },
        "verification_lineage": {
            "runtime_matrix_checksum": runtime["production_checksum"],
            "last_full_game_baseline_checksum": previous_normal["md_checksum"],
            "candidate_checksum": current_normal["md_checksum"],
            "candidate_delta_changed_bytes": current_delta[
                "normal_changed_bytes"
            ],
            "candidate_delta_unclassified_bytes": current_delta[
                "unexpected_changed_bytes"
            ],
        },
        "requirements": requirements,
        "complete": complete,
        "hard_mode_follow_up": {
            "required": True,
            "status": "balance_discussion_required",
            "normal_release_must_remain_unchanged": True,
            "implementation_started": False,
            "policy": "docs/editor_data_model.md#후속-하드-모드-빌드",
        },
    }


def render_markdown(data: dict[str, object]) -> str:
    release = data["release"]
    lineage = data["verification_lineage"]
    lines = [
        "# Release Acceptance",
        "",
        "Generated by `python3 tools/release_acceptance.py --write`.",
        "",
        f"- ROM: `{release['path']}`",
        f"- Header checksum: `{release['header_checksum']}`",
        f"- SHA-256: `{release['sha256']}`",
        f"- Complete: `{str(data['complete']).lower()}`",
        "",
        "The scenario runtime matrix retains the checksum at which each accepted",
        "playback body was recorded. It is not relabeled as current evidence.",
        f"The lineage is `{lineage['runtime_matrix_checksum']}` runtime evidence,",
        f"`{lineage['last_full_game_baseline_checksum']}` last full-game baseline,",
        f"and `{lineage['candidate_checksum']}` release candidate. The final delta",
        f"contains {lineage['candidate_delta_changed_bytes']} owned changed bytes",
        f"and {lineage['candidate_delta_unclassified_bytes']} unclassified bytes.",
        "",
        "| Goal | Result | Checks |",
        "| ---: | --- | ---: |",
    ]
    for row in data["requirements"]:
        result = "pass" if row["passed"] else "fail"
        passed = sum(check_row["passed"] for check_row in row["checks"])
        lines.append(
            f"| {row['id']}. {row['title']} | {result} | "
            f"{passed}/{len(row['checks'])} |"
        )

    lines.extend(["", "## Checks", ""])
    for row in data["requirements"]:
        lines.append(f"### {row['id']}. {row['title']}")
        lines.append("")
        for check_row in row["checks"]:
            marker = "x" if check_row["passed"] else " "
            lines.append(
                f"- [{marker}] {check_row['label']}: "
                f"`{check_row['actual']}`"
            )
        lines.append("")
        lines.append("Evidence:")
        lines.extend(f"- `{path}`" for path in row["evidence"])
        lines.append("")

    hard_mode = data["hard_mode_follow_up"]
    lines.extend(
        [
            "## Hard Mode Follow-up",
            "",
            f"- Required: `{str(hard_mode['required']).lower()}`",
            f"- Status: `{hard_mode['status']}`",
            "- No hard-mode ROM or balance values may be produced until the",
            "  normal release is accepted and the user approves the balance policy.",
            "- The normal Korean ROM remains an immutable baseline for that work.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the canonical Korean release against Goal criteria"
    )
    parser.add_argument(
        "--rom",
        type=Path,
        default=DEFAULT_ROM,
        help="canonical Korean ROM",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write JSON and Markdown acceptance inventories",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = build_inventory(args.rom)
    if args.write:
        JSON_OUTPUT.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        MARKDOWN_OUTPUT.write_text(
            render_markdown(data),
            encoding="utf-8",
        )
        print(JSON_OUTPUT.relative_to(ROOT))
        print(MARKDOWN_OUTPUT.relative_to(ROOT))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if data["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

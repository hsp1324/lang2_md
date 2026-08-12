#!/usr/bin/env python3
"""Plan and verify the v1.3.1-v1.3.6 historical-save matrix.

This acceptance surface is deliberately read-only with respect to emulator
state and cartridge SRAM.  A controller-only execution driver must create the
save in game, stop the emulator so BlastEm flushes the cartridge SRAM, and
feed this verifier the captured bytes and visual evidence.  The verifier never
manufactures or repairs a save.

The public corpus has 17 historical patch targets.  Keith, Lester, and Jessica
produce one case per target, for 51 cases total.  The Keith and Lester cases
for v1.3.2 and v1.3.3 deliberately begin on matching v1.3.1 media and reach
Fighter LV11+ through ordinary historical gameplay before the target ROM
loads and re-saves the same cartridge SRAM.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rom_update import bps_apply  # noqa: E402
from tools.v137_release_identity import (  # noqa: E402
    JAPANESE_SOURCE_ROM_SHA256,
    RELEASE_ROM_PATHS,
    RELEASE_ROM_SHA256,
    require_final_release_identity,
)


SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
SOURCE_ROM_BYTES = 0x200000
SRAM_BYTES = 0x2000
SRAM_FORMAT_MARKER_OFFSET = 0x1FEE
SRAM_FORMAT_MARKER = 0x07CA
SRAM_VALID_FLAGS_OFFSET = 0x1FF0
MANUAL_SLOT_BASE = 0x194E
MANUAL_SLOT_VALID_BIT = 1 << 1
MANUAL_SLOT_CHECKSUM_DATA_SIZE = 0x1A6
MANUAL_SLOT_CHECKSUM_OFFSET = 0x1A6
MANUAL_SLOT_COMMANDER_ROSTER_OFFSET = 0x30
MANUAL_SLOT_COMMANDER_RECORD_SIZE = 0x18
MANUAL_SLOT_COMMANDER_COUNT = 10

SCHEMA_VERSION = 1
PLAN_KIND = "langrisser_ii_historical_save_version_matrix_plan"
EVIDENCE_KIND = "langrisser_ii_historical_save_version_matrix_evidence"
REPORT_KIND = "langrisser_ii_historical_save_version_matrix_verification"
VERIFIER_ID = "historical_save_version_matrix_v1"
EXPECTED_TARGET_COUNT = 17
EXPECTED_CASE_COUNT = 51
HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class HistoricalTarget:
    release: str
    profile: str
    patch_filename: str
    patch_sha256: str
    patch_size: int
    output_filename: str
    output_sha256: str
    output_size: int = 0x400000


@dataclass(frozen=True)
class Commander:
    key: str
    commander_id: int
    first_player_scenario: int


COMMANDERS = (
    Commander("keith", 7, 8),
    Commander("lester", 9, 11),
    Commander("jessica", 10, 12),
)


EXPECTED_MANIFEST_SHA256 = {
    "v1.3.1": "a12f26d5d751fefcdcb959cec5bed6aad421f7dfead6c12238debb2bea874af8",
    "v1.3.2": "0464f2f3afa76f09b21b9728c4a4e8ece18889d9703e32b3e0c0ddb30188a30d",
    "v1.3.3": "c7417b37e79cc254a571f5fced7fa5ec7a7b06925cedd666156c42842ac8e9d7",
    "v1.3.4": "18d4fa62c7ad8cf87fdc4caeca3bd1db37c10b475fa3f2efc7abf93b2807dea0",
    "v1.3.5": "c99102252a412ee4a9cd8d0bd0f192fe37511c5691aa94792f54cf00976edd33",
    "v1.3.6": "41d37b46925db5c0bef0e49180a74f77f839eb2faaeacd0bb19a382c859a588a",
}


HISTORICAL_TARGETS = (
    HistoricalTarget(
        "v1.3.1", "normal", "normal-v1.3.1.bps",
        "bb277d3e4b436ecca9f3197d51c4f510868a294d803a5ed929d4c38c694c8e07",
        2286153, "Langrisser II (Korean v1.3.1).md",
        "e603287d92e50f0724d69395bfcdbf9215104bb052f02c3112f9c9886f44adea",
    ),
    HistoricalTarget(
        "v1.3.1", "hard", "hard-t1.3.1-b1.3.1.bps",
        "3a29c14b03d1228e8b19269d4ef3aebe2d54c844b037980ddd1c03b582aee414",
        2286162, "Langrisser II (Korean Hard T1.3.1 B1.3.1).md",
        "0b2ae6394b723aef4599a4cc8ad60c76d7f1b78e8170de17e43b49c6f61b8df1",
    ),
    HistoricalTarget(
        "v1.3.2", "pure", "original-design-v1.3.2.bps",
        "7687cbb2704581747efcdcd188d956b1b7437f3605aa63a693587914a26cfba9",
        2286050, "Langrisser II (Original v1.3.2).md",
        "289ca7d5b5c335f0284bd5e88edb48395726b915c37b0d3dfac6252d3a3a97ea",
    ),
    HistoricalTarget(
        "v1.3.2", "normal", "new-design-normal-v1.3.2.bps",
        "b34522e1842a81da76fbb2e506941173e119e52d4648113cbe53f230a78e4c60",
        2286575, "Langrisser II (Normal v1.3.2).md",
        "ad66810801cf0e08dbc4be7aae0e96d71509327724ef2bdedd7245395652c88c",
    ),
    HistoricalTarget(
        "v1.3.2", "hard", "new-design-hard-t1.3.2-b1.3.2.bps",
        "824a70a791d80ae8c39a563e778532ea2c7193ebc659d9aaa0bdc0969f43fe1e",
        2289077, "Langrisser II (Hard v1.3.2).md",
        "df4d40b9f9f1832fd42f49f495d85aafb1e9544732cac9bbc448a774f2e18608",
    ),
    HistoricalTarget(
        "v1.3.3", "pure", "original-v1.3.3.bps",
        "a778ecd35dd999c63db3629c33513e95dd6c769c44945392dc29e5e8b7378cb7",
        2286057, "Langrisser II (Korean Original v1.3.3).md",
        "b090a4cef0940211cea412c972f872927f6dbebea3b297583592b06ddc24ad77",
    ),
    HistoricalTarget(
        "v1.3.3", "normal", "normal-v1.3.3.bps",
        "11f8c45b384c3a2e89d7fa6e83f54c7ce2bc6c65fe3da26dbb2602b3adc43a2a",
        2286582, "Langrisser II (Korean Normal v1.3.3).md",
        "085c65fed8c2de286e3a6b3260173a573cae0d6e4102afba0ee7debfc6bc04a5",
    ),
    HistoricalTarget(
        "v1.3.3", "hard", "hard-v1.3.3.bps",
        "c7dea6bcfeac78c6b3c2cf797fd6b6b89d7364b86ff9e1a2feb06214137d48ae",
        2286589, "Langrisser II (Korean Hard v1.3.3).md",
        "15b07113d00c993fd79fded4add0f1dbdca913f1de9dd5f6eb8219de232a146c",
    ),
    HistoricalTarget(
        "v1.3.4", "pure", "original-v1.3.4.bps",
        "598a22ad2fa35ed3a0fefc9f460ad6bec998bf675c0fb64e7b07740d76626aaa",
        2286057, "Langrisser II (Korean Original v1.3.4).md",
        "96ebbdd3970ae21f78067f83d077062657fd7757b7dc45c6f6257b150e19682d",
    ),
    HistoricalTarget(
        "v1.3.4", "normal", "normal-v1.3.4.bps",
        "156f39bb8f2c23ac2ec8a1af6af07e41ce6bae5b2f8d5af2116eb9d073aced2e",
        2286582, "Langrisser II (Korean Normal v1.3.4).md",
        "65d7458a3e4aa993c107ff15cda9152b206cf96c0a7ac3e32dfcf6365f4d99a4",
    ),
    HistoricalTarget(
        "v1.3.4", "hard", "hard-v1.3.4.bps",
        "13e3eae045207f239fd971a15122a163a2b2f1034cd4050d34b487c3ae20192d",
        2289084, "Langrisser II (Korean Hard v1.3.4).md",
        "5dc9b5502210b2eb86ea16eff3bd8d047fa4b952f817a3366c4cbd6dd3b49dcf",
    ),
    HistoricalTarget(
        "v1.3.5", "pure", "original-v1.3.5.bps",
        "c5c860a9ae9e5a277055634f9f3ba74c96a004d5a274edb129b6f0c12de8d364",
        2286083, "Langrisser II (Korean Original v1.3.5).md",
        "f1ed872dbe191e836f4414ae204994f096c1fb8568aa0449e80a7d4b9e804110",
    ),
    HistoricalTarget(
        "v1.3.5", "normal", "normal-v1.3.5.bps",
        "d546de7d84a85a9fbf23a124abde8168be0ab0ccdc014da770c140cff940688a",
        2286530, "Langrisser II (Korean Normal v1.3.5).md",
        "724304a728ad9b3202b8d69b4c2afff284291c02e3bc419891e22e5e7f535abd",
    ),
    HistoricalTarget(
        "v1.3.5", "hard", "hard-v1.3.5.bps",
        "4fb2836cffb022d5c38d23b643cb676342f047ff1f5e213e5aa70fe4dd6eb594",
        2289031, "Langrisser II (Korean Hard v1.3.5).md",
        "792ea989db144625902e4c9e9f4b50740cf0ced17ca7ccbda46cea3a4671a086",
    ),
    HistoricalTarget(
        "v1.3.6", "pure", "original-v1.3.6.bps",
        "4cbf054c97ad6b358998279357c42e0e048a920e88cbbd2f09307f96da3bfaa9",
        2286127, "Langrisser II (Korean Original v1.3.6).md",
        "05e6c77e138040f2c3b2cf7fe8cd6c1b1f05247a2afca1f1b36b4c838d406a03",
    ),
    HistoricalTarget(
        "v1.3.6", "normal", "normal-v1.3.6.bps",
        "34fe8f8489383e639c2c98671220165f58beb26819971de0a8219aa5b85714ff",
        2286574, "Langrisser II (Korean Normal v1.3.6).md",
        "b74359800a697eea5e85d7942ac712b74360bbd8b43ff2082b88d009e94a370a",
    ),
    HistoricalTarget(
        "v1.3.6", "hard", "hard-v1.3.6.bps",
        "09ccc8d6d88b0a6956983222aec70946b3544722685c98604faa5556c89e19cb",
        2289075, "Langrisser II (Korean Hard v1.3.6).md",
        "a9e607aa0d117742f8bbb2f3a3d756205b14ff33a72d18f3dc4bdccc15525aa1",
    ),
)


FINAL_MANIFEST_SHA256 = (
    "6eddb0fb48579da8907136015b7ff08a73d9228e297b959617d4200857911999"
)
FINAL_PATCH_IDENTITIES = {
    "pure": {
        "filename": "original-v1.3.7.bps",
        "sha256": "a12cb6434312e4ba330e0e2d89be3ae9f8f9892f87518b0a64a49d0eb5d1261a",
        "bytes": 2286139,
    },
    "normal": {
        "filename": "normal-v1.3.7.bps",
        "sha256": "c17d2b86af34eccd019eea23a430982d08f04cde95ac0b714766ec48db90a658",
        "bytes": 2286586,
    },
    "hard": {
        "filename": "hard-v1.3.7.bps",
        "sha256": "2c13a6ea841ce99825c2b1ab281a02d442f2333fe78cf0f69ebd1fd8518eaed3",
        "bytes": 2289214,
    },
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(payload)


def _target_key(target: HistoricalTarget) -> tuple[str, str]:
    return target.release, target.profile


def historical_target_map() -> dict[tuple[str, str], HistoricalTarget]:
    targets = {_target_key(target): target for target in HISTORICAL_TARGETS}
    if len(targets) != EXPECTED_TARGET_COUNT:
        raise AssertionError("historical target identities are not unique")
    return targets


def _require_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}: {actual!r} != {expected!r}")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


@lru_cache(maxsize=None)
def target_provenance(release: str, profile: str) -> dict[str, object]:
    """Reconstruct one immutable public historical ROM entirely in memory."""

    target = historical_target_map().get((release, profile))
    if target is None:
        raise ValueError(f"unknown historical target {release}/{profile}")

    manifest_path = ROOT / "patches" / f"{release}.json"
    manifest_payload = manifest_path.read_bytes()
    _require_equal(
        sha256_bytes(manifest_payload),
        EXPECTED_MANIFEST_SHA256[release],
        f"{release} manifest SHA-256",
    )
    manifest = json.loads(manifest_payload.decode("utf-8"))
    _require_equal(manifest.get("release"), release, "manifest release")
    _require_equal(
        manifest.get("source"),
        {
            "headered_size": 0x200200,
            "label": "Langrisser II (Japan)",
            "sha256": JAPANESE_SOURCE_ROM_SHA256,
            "size": SOURCE_ROM_BYTES,
        },
        f"{release} source record",
    )

    records = [row for row in manifest.get("targets", []) if row.get("id") == profile]
    if len(records) != 1:
        raise ValueError(f"{release}/{profile} manifest target is not unique")
    record = records[0]
    expected_fields = {
        "id": target.profile,
        "patch_filename": target.patch_filename,
        "patch_sha256": target.patch_sha256,
        "patch_size": target.patch_size,
        "output_filename": target.output_filename,
        "output_sha256": target.output_sha256,
        "output_size": target.output_size,
    }
    for key, expected in expected_fields.items():
        _require_equal(record.get(key), expected, f"{release}/{profile} {key}")

    source_payload = SOURCE_ROM.read_bytes()
    _require_equal(len(source_payload), SOURCE_ROM_BYTES, "source ROM bytes")
    _require_equal(
        sha256_bytes(source_payload),
        JAPANESE_SOURCE_ROM_SHA256,
        "source ROM SHA-256",
    )
    patch_path = ROOT / "patches" / target.patch_filename
    patch_payload = patch_path.read_bytes()
    _require_equal(len(patch_payload), target.patch_size, "patch bytes")
    _require_equal(
        sha256_bytes(patch_payload), target.patch_sha256, "patch SHA-256"
    )
    output_payload = bps_apply(patch_payload, source_payload)
    _require_equal(len(output_payload), target.output_size, "output ROM bytes")
    _require_equal(
        sha256_bytes(output_payload), target.output_sha256, "output ROM SHA-256"
    )

    result: dict[str, object] = {
        "release": release,
        "profile": profile,
        "manifest": {
            "path": str(manifest_path),
            "sha256": EXPECTED_MANIFEST_SHA256[release],
        },
        "source": {
            "path": str(SOURCE_ROM),
            "bytes": SOURCE_ROM_BYTES,
            "sha256": JAPANESE_SOURCE_ROM_SHA256,
        },
        "patch": {
            "path": str(patch_path),
            "filename": target.patch_filename,
            "bytes": target.patch_size,
            "sha256": target.patch_sha256,
        },
        "reconstructed_rom": {
            "filename": target.output_filename,
            "bytes": target.output_size,
            "sha256": target.output_sha256,
            "materialization": "in_memory_bps_verification_only",
        },
    }
    result["provenance_sha256"] = canonical_sha256(result)
    return result


def verify_historical_corpus() -> list[dict[str, object]]:
    target_map = historical_target_map()
    if any(release == "v1.3.0" for release, _ in target_map):
        raise AssertionError("the non-public v1.3.0 tag entered the corpus")
    expected_layout = {
        "v1.3.1": ("normal", "hard"),
        "v1.3.2": ("pure", "normal", "hard"),
        "v1.3.3": ("pure", "normal", "hard"),
        "v1.3.4": ("pure", "normal", "hard"),
        "v1.3.5": ("pure", "normal", "hard"),
        "v1.3.6": ("pure", "normal", "hard"),
    }
    for release, profiles in expected_layout.items():
        manifest = _read_json(ROOT / "patches" / f"{release}.json")
        observed = tuple(row.get("id") for row in manifest.get("targets", []))
        _require_equal(observed, profiles, f"{release} public target layout")
    return [
        deepcopy(target_provenance(target.release, target.profile))
        for target in HISTORICAL_TARGETS
    ]


@lru_cache(maxsize=None)
def final_provenance(profile: str) -> dict[str, object]:
    require_final_release_identity()
    if profile not in FINAL_PATCH_IDENTITIES:
        raise ValueError(f"unknown final profile {profile}")
    manifest_path = ROOT / "patches/v1.3.7.json"
    _require_equal(
        sha256_path(manifest_path), FINAL_MANIFEST_SHA256, "v1.3.7 manifest SHA-256"
    )
    manifest = _read_json(manifest_path)
    rows = [row for row in manifest.get("targets", []) if row.get("id") == profile]
    if len(rows) != 1:
        raise ValueError(f"v1.3.7/{profile} manifest target is not unique")
    row = rows[0]
    expected_patch = FINAL_PATCH_IDENTITIES[profile]
    for key, expected in (
        ("patch_filename", expected_patch["filename"]),
        ("patch_sha256", expected_patch["sha256"]),
        ("patch_size", expected_patch["bytes"]),
        ("output_sha256", RELEASE_ROM_SHA256[profile]),
        ("output_size", 0x400000),
    ):
        _require_equal(row.get(key), expected, f"v1.3.7/{profile} {key}")

    source_payload = SOURCE_ROM.read_bytes()
    patch_path = ROOT / "patches" / str(expected_patch["filename"])
    patch_payload = patch_path.read_bytes()
    _require_equal(
        sha256_bytes(patch_payload), expected_patch["sha256"], "final patch SHA-256"
    )
    reconstructed = bps_apply(patch_payload, source_payload)
    _require_equal(
        sha256_bytes(reconstructed),
        RELEASE_ROM_SHA256[profile],
        "final reconstructed ROM SHA-256",
    )
    rom_path = RELEASE_ROM_PATHS[profile]
    _require_equal(rom_path.stat().st_size, 0x400000, "final ROM bytes")
    _require_equal(
        sha256_path(rom_path), RELEASE_ROM_SHA256[profile], "final ROM SHA-256"
    )
    result: dict[str, object] = {
        "release": "v1.3.7",
        "profile": profile,
        "manifest": {
            "path": str(manifest_path),
            "sha256": FINAL_MANIFEST_SHA256,
        },
        "patch": {
            "path": str(patch_path),
            "filename": expected_patch["filename"],
            "bytes": expected_patch["bytes"],
            "sha256": expected_patch["sha256"],
        },
        "rom": {
            "path": str(rom_path),
            "bytes": 0x400000,
            "sha256": RELEASE_ROM_SHA256[profile],
        },
    }
    result["provenance_sha256"] = canonical_sha256(result)
    return result


def predecessor_profile(profile: str) -> str:
    """Map v1.3.2/v1.3.3 cases onto a real v1.3.1 public parent."""

    if profile == "hard":
        return "hard"
    return "normal"


def expected_behavior(target: HistoricalTarget, commander: Commander) -> dict[str, object]:
    damaged_fighter = (
        target.release in {"v1.3.2", "v1.3.3"}
        and commander.key in {"keith", "lester"}
    )
    v131_lester = target.release == "v1.3.1" and commander.key == "lester"
    missed_lester_join = (
        target.release in {"v1.3.4", "v1.3.5", "v1.3.6"}
        and commander.key == "lester"
    )
    if not damaged_fighter and not v131_lester and not missed_lester_join:
        return {
            "kind": "preserve_existing_progress",
            "historical_predicate": "naturally_saved_nonlegacy_state",
            "expected_current_transition_count": 0,
            "expected_current_join_exp_grant_count": 0,
            "expected_current_join_raw_experience": 0,
        }
    if missed_lester_join:
        return {
            "kind": "recover_unselected_tier1_once",
            "historical_predicate": {
                "class_id": 7,
                "level": {"operator": "equal", "value": 10},
                "origin": "fresh_historical_scenario10_result_without_choice",
            },
            "expected_selected_class_id": 5,
            "expected_selected_level": 5,
            "expected_selected_experience": 16,
            "expected_current_transition_count": 1,
            "expected_current_join_exp_grant_count": 1,
            "expected_current_join_raw_experience": 0x90,
        }
    if v131_lester:
        level_rule = {"operator": "equal", "value": 10}
        source = "fresh_v1.3.1_scenario10_result"
    else:
        level_rule = {"operator": "at_least", "value": 11}
        source = "v1.3.1_natural_fighter_progress_then_historical_target_load"
    selected = {
        "keith": {"class_id": 4, "level": 1, "experience": 0},
        "lester": {"class_id": 5, "level": 5, "experience": 16},
    }[commander.key]
    return {
        "kind": "recover_legacy_fighter_once",
        "historical_predicate": {
            "class_id": 1,
            "level": level_rule,
            "origin": source,
        },
        "expected_selected_class_id": selected["class_id"],
        "expected_selected_level": selected["level"],
        "expected_selected_experience": selected["experience"],
        "expected_current_transition_count": 1,
        "expected_current_join_exp_grant_count": 1,
        "expected_current_join_raw_experience": (
            0x00 if commander.key == "keith" else 0x90
        ),
    }


def route_contract(target: HistoricalTarget, commander: Commander) -> dict[str, object]:
    lineage = (
        commander.key in {"keith", "lester"}
        and target.release in {"v1.3.2", "v1.3.3"}
    )
    stages: list[str] = []
    if lineage:
        stages.extend(
            [
                "predecessor_fresh_process_title_new_game",
                "predecessor_controller_only_natural_play_to_released_fighter_save",
                "predecessor_stock_in_game_save",
                "predecessor_process_exit_and_8kib_sram_flush",
                "stopped_process_stable_media_switch_to_historical_target",
                "historical_target_fresh_process_title_load",
                "historical_target_controller_only_natural_play_to_fighter_lv11_plus",
                "historical_target_stock_in_game_resave",
                "historical_target_process_exit_and_8kib_sram_flush",
            ]
        )
    else:
        stages.extend(
            [
                "historical_target_fresh_process_title_new_game",
                "historical_target_controller_only_natural_play",
                "historical_target_stock_in_game_save",
                "historical_target_process_exit_and_8kib_sram_flush",
            ]
        )
    stages.extend(
        [
            "stopped_process_stable_media_switch_to_final_exact_release",
            "current_first_fresh_process_cold_title_load",
            "current_first_controller_only_progress_and_stock_resave",
            "current_first_process_exit_and_8kib_sram_flush",
            "current_second_fresh_process_title_load",
            "current_second_controller_visible_status_confirmation",
            "current_second_process_exit",
        ]
    )
    result: dict[str, object] = {
        "historical_lineage": (
            "v1.3.1_natural_damaged_fighter_lineage"
            if lineage
            else "target_fresh_new_game_lineage"
        ),
        "stable_media_rule": (
            "one_game_rom_path_and_one_naturally_created_sram_path_per_case; "
            "ROM link target changes only after the prior emulator exits"
        ),
        "first_player_scenario": commander.first_player_scenario,
        "stages": stages,
        "required_input_surface": "controller_only",
        "historical_save_surface": "stock_in_game_save",
        "historical_flush_surface": "normal_emulator_process_exit",
        "current_load_surface": "cold_title_load_manual_slot_ui",
        "current_second_load_surface": "fresh_process_title_load_manual_slot_ui",
        "state_artifact_inputs": 0,
        "external_save_inputs": 0,
        "direct_memory_mutations": 0,
        "scenario_selector_entries": 0,
    }
    result["contract_sha256"] = canonical_sha256(result)
    return result


def build_plan(run_id: str, artifact_root: Path) -> dict[str, object]:
    if not run_id.strip():
        raise ValueError("run_id cannot be empty")
    historical = verify_historical_corpus()
    final = {profile: deepcopy(final_provenance(profile)) for profile in ("pure", "normal", "hard")}
    provenance_by_key = {
        (row["release"], row["profile"]): row for row in historical
    }
    cases: list[dict[str, object]] = []
    for target in HISTORICAL_TARGETS:
        for commander in COMMANDERS:
            case_id = f"{target.release}-{target.profile}-{commander.key}"
            contract = route_contract(target, commander)
            case_root = artifact_root / case_id
            predecessor: dict[str, object] | None = None
            if (
                commander.key in {"keith", "lester"}
                and target.release in {"v1.3.2", "v1.3.3"}
            ):
                parent_profile = predecessor_profile(target.profile)
                predecessor = deepcopy(
                    provenance_by_key[("v1.3.1", parent_profile)]
                )
            cases.append(
                {
                    "case_id": case_id,
                    "release": target.release,
                    "profile": target.profile,
                    "character": asdict(commander),
                    "historical_target": deepcopy(
                        provenance_by_key[(target.release, target.profile)]
                    ),
                    "predecessor": predecessor,
                    "final_target": deepcopy(final[target.profile]),
                    "expected_behavior": expected_behavior(target, commander),
                    "route_contract": contract,
                    "runtime_paths": {
                        "case_root": str(case_root),
                        "stable_rom_path": str(case_root / "media/game.md"),
                        "runtime_home": str(case_root / "runtime-home"),
                        "runtime_sram_identity": (
                            "runtime-home/.local/share/blastem/game/save.sram"
                        ),
                    },
                    "required_visual_artifact_phases": [
                        "historical_save_confirmation",
                        "current_first_title_load",
                        "current_first_post_progress_status",
                        "current_second_title_load",
                        "current_second_post_load_status",
                    ],
                }
            )
    if len(cases) != EXPECTED_CASE_COUNT:
        raise AssertionError("historical-save case cardinality changed")
    plan: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "kind": PLAN_KIND,
        "verifier_id": VERIFIER_ID,
        "run_id": run_id,
        "runtime_status": "pending_controller_execution",
        "acceptance_claimed": False,
        "historical_target_count": EXPECTED_TARGET_COUNT,
        "case_count": EXPECTED_CASE_COUNT,
        "source_rom": {
            "path": str(SOURCE_ROM),
            "bytes": SOURCE_ROM_BYTES,
            "sha256": JAPANESE_SOURCE_ROM_SHA256,
        },
        "historical_targets": historical,
        "final_targets": final,
        "policy": {
            "public_releases": [
                "v1.3.1", "v1.3.2", "v1.3.3", "v1.3.4", "v1.3.5", "v1.3.6"
            ],
            "excluded_development_tags": ["v1.3.0"],
            "save_origin": "actual_stock_in_game_save_then_process_exit",
            "load_origin": "actual_title_load_in_a_fresh_process",
            "emulator_state_input_allowed": False,
            "external_save_input_allowed": False,
            "direct_memory_or_save_mutation_allowed": False,
            "high_numbered_isolated_virtual_display_required": True,
        },
        "cases": cases,
    }
    digest_basis = deepcopy(plan)
    plan["plan_sha256"] = canonical_sha256(digest_basis)
    return plan


def manual_slot_checksum(payload: bytes) -> int:
    end = MANUAL_SLOT_BASE + MANUAL_SLOT_CHECKSUM_DATA_SIZE
    return (
        sum(
            int.from_bytes(payload[offset : offset + 2], "big")
            for offset in range(MANUAL_SLOT_BASE, end, 2)
        )
        + 1
    ) & 0xFFFF


def sram_snapshot(payload: bytes, commander: Commander) -> dict[str, object]:
    """Validate and summarize a cartridge SRAM captured after process exit."""

    if len(payload) != SRAM_BYTES:
        raise ValueError(f"cartridge SRAM must be {SRAM_BYTES} bytes")
    marker = int.from_bytes(
        payload[SRAM_FORMAT_MARKER_OFFSET : SRAM_FORMAT_MARKER_OFFSET + 2],
        "big",
    )
    _require_equal(marker, SRAM_FORMAT_MARKER, "SRAM format marker")
    flags = int.from_bytes(
        payload[SRAM_VALID_FLAGS_OFFSET : SRAM_VALID_FLAGS_OFFSET + 2], "big"
    )
    if not flags & MANUAL_SLOT_VALID_BIT:
        raise ValueError("manual slot 1 is not marked valid")
    checksum_at = MANUAL_SLOT_BASE + MANUAL_SLOT_CHECKSUM_OFFSET
    stored = int.from_bytes(payload[checksum_at : checksum_at + 2], "big")
    calculated = manual_slot_checksum(payload)
    _require_equal(stored, calculated, "manual slot checksum")
    scenario = int.from_bytes(payload[MANUAL_SLOT_BASE : MANUAL_SLOT_BASE + 2], "big")
    if not 1 <= scenario <= 31:
        raise ValueError(f"manual slot scenario {scenario} is invalid")

    roster_at = MANUAL_SLOT_BASE + MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
    roster_size = MANUAL_SLOT_COMMANDER_COUNT * MANUAL_SLOT_COMMANDER_RECORD_SIZE
    roster = payload[roster_at : roster_at + roster_size]
    row_hashes: dict[str, str] = {}
    for commander_id in range(1, MANUAL_SLOT_COMMANDER_COUNT + 1):
        start = (commander_id - 1) * MANUAL_SLOT_COMMANDER_RECORD_SIZE
        row_hashes[str(commander_id)] = sha256_bytes(
            roster[start : start + MANUAL_SLOT_COMMANDER_RECORD_SIZE]
        )
    selected_at = (commander.commander_id - 1) * MANUAL_SLOT_COMMANDER_RECORD_SIZE
    selected = roster[selected_at : selected_at + MANUAL_SLOT_COMMANDER_RECORD_SIZE]
    return {
        "bytes": SRAM_BYTES,
        "sha256": sha256_bytes(payload),
        "format_marker": marker,
        "valid_flags": flags,
        "manual_slot": 1,
        "scenario": scenario,
        "manual_slot_checksum": stored,
        "manual_slot_record_sha256": sha256_bytes(
            payload[
                MANUAL_SLOT_BASE : MANUAL_SLOT_BASE + MANUAL_SLOT_CHECKSUM_DATA_SIZE
            ]
        ),
        "roster_sha256": sha256_bytes(roster),
        "commander_rows_sha256": row_hashes,
        "selected_commander": {
            "commander_id": commander.commander_id,
            "class_id": selected[0],
            "level": selected[2],
            "experience": selected[3],
            "record_sha256": sha256_bytes(selected),
        },
    }


def _decode_checkpoint(
    checkpoint: Mapping[str, object], commander: Commander, label: str
) -> dict[str, object]:
    _require_equal(
        checkpoint.get("captured_after_process_exit"), True, f"{label} exit capture"
    )
    payload_hex = checkpoint.get("payload_hex")
    if not isinstance(payload_hex, str):
        raise ValueError(f"{label} payload_hex is missing")
    try:
        payload = bytes.fromhex(payload_hex)
    except ValueError as error:
        raise ValueError(f"{label} payload_hex is invalid") from error
    observed = sram_snapshot(payload, commander)
    _require_equal(checkpoint.get("snapshot"), observed, f"{label} SRAM snapshot")
    return observed


def _progress(snapshot: Mapping[str, object]) -> tuple[int, int, int]:
    selected = snapshot["selected_commander"]
    if not isinstance(selected, Mapping):
        raise ValueError("selected commander snapshot is malformed")
    return (
        int(selected["class_id"]),
        int(selected["level"]),
        int(selected["experience"]),
    )


def _verify_artifact(artifact: Mapping[str, object], label: str) -> None:
    path_value = artifact.get("path")
    if not isinstance(path_value, str):
        raise ValueError(f"{label} path is missing")
    path = Path(path_value)
    if not path.is_file() or path.stat().st_size <= 0:
        raise ValueError(f"{label} artifact is absent or empty: {path}")
    expected = artifact.get("sha256")
    if not isinstance(expected, str) or not HEX_SHA256.fullmatch(expected):
        raise ValueError(f"{label} SHA-256 is malformed")
    _require_equal(sha256_path(path), expected, f"{label} SHA-256")


def _verify_processes(
    row: Mapping[str, object], case: Mapping[str, object]
) -> None:
    process = row.get("processes")
    if not isinstance(process, Mapping):
        raise ValueError("process evidence is missing")
    historical = process.get("historical")
    if not isinstance(historical, list):
        raise ValueError("historical process evidence is missing")
    expected_historical_count = 2 if case["predecessor"] is not None else 1
    _require_equal(
        len(historical), expected_historical_count, "historical process count"
    )
    expected_roles = (
        ["predecessor", "historical_target"]
        if expected_historical_count == 2
        else ["historical_target"]
    )
    expected_hashes = []
    if case["predecessor"] is not None:
        expected_hashes.append(
            case["predecessor"]["reconstructed_rom"]["sha256"]
        )
    expected_hashes.append(case["historical_target"]["reconstructed_rom"]["sha256"])
    pids: list[int] = []
    for entry, role, rom_hash in zip(historical, expected_roles, expected_hashes):
        if not isinstance(entry, Mapping):
            raise ValueError("historical process row is malformed")
        _require_equal(entry.get("role"), role, "historical process role")
        _require_equal(entry.get("rom_sha256"), rom_hash, "historical process ROM")
        _require_equal(entry.get("fresh_process"), True, "historical fresh process")
        _require_equal(entry.get("exited_before_next"), True, "historical process exit")
        pid = entry.get("pid")
        if not isinstance(pid, int) or pid <= 0:
            raise ValueError("historical process PID is invalid")
        pids.append(pid)

    final_hash = case["final_target"]["rom"]["sha256"]
    for key in ("current_first", "current_second"):
        entry = process.get(key)
        if not isinstance(entry, Mapping):
            raise ValueError(f"{key} process evidence is missing")
        _require_equal(entry.get("rom_sha256"), final_hash, f"{key} ROM")
        _require_equal(entry.get("fresh_process"), True, f"{key} fresh process")
        _require_equal(entry.get("title_load_ui"), True, f"{key} title LOAD")
        _require_equal(entry.get("cold_runtime_start"), True, f"{key} cold start flag")
        _require_equal(entry.get("exited_before_next"), True, f"{key} process exit")
        pid = entry.get("pid")
        if not isinstance(pid, int) or pid <= 0:
            raise ValueError(f"{key} process PID is invalid")
        pids.append(pid)
    if len(set(pids)) != len(pids):
        raise ValueError("accepted stages did not use distinct emulator processes")


def _verify_behavior(
    row: Mapping[str, object],
    case: Mapping[str, object],
    historical: Mapping[str, object],
    current: Mapping[str, object],
) -> None:
    expected = case["expected_behavior"]
    proof = row.get("progression_proof")
    if not isinstance(proof, Mapping):
        raise ValueError("progression proof is missing")
    _require_equal(
        proof.get("current_transition_count"),
        expected["expected_current_transition_count"],
        "current transition count",
    )
    _require_equal(
        proof.get("current_join_exp_grant_count"),
        expected["expected_current_join_exp_grant_count"],
        "current join EXP grant count",
    )
    _require_equal(
        proof.get("current_join_raw_experience"),
        expected["expected_current_join_raw_experience"],
        "current join raw EXP",
    )
    _require_equal(proof.get("duplicate_exp_grant_count"), 0, "duplicate EXP grant count")
    _require_equal(
        proof.get("second_load_visible_progress"),
        {
            "class_id": _progress(current)[0],
            "level": _progress(current)[1],
            "experience": _progress(current)[2],
        },
        "fresh-process visible progress",
    )
    _require_equal(
        proof.get("observation_method"),
        "controller_opened_status_window_visual_decoder",
        "progress observation method",
    )

    before = _progress(historical)
    after = _progress(current)
    if expected["kind"] == "preserve_existing_progress":
        _require_equal(after, before, "preserved commander progress")
        return

    predicate = expected["historical_predicate"]
    _require_equal(before[0], predicate["class_id"], "historical recovery class")
    level_rule = predicate["level"]
    if level_rule["operator"] == "equal":
        _require_equal(before[1], level_rule["value"], "historical recovery level")
    elif before[1] < level_rule["value"]:
        raise ValueError("historical Fighter did not naturally reach LV11+")
    _require_equal(
        after,
        (
            expected["expected_selected_class_id"],
            expected["expected_selected_level"],
            expected["expected_selected_experience"],
        ),
        "one-time legacy recovery result",
    )


def verify_evidence(plan: Mapping[str, object], evidence: Mapping[str, object]) -> dict[str, object]:
    """Strictly validate a completed controller-only 51-case evidence set."""

    _require_equal(evidence.get("schema_version"), SCHEMA_VERSION, "evidence schema")
    _require_equal(evidence.get("kind"), EVIDENCE_KIND, "evidence kind")
    _require_equal(evidence.get("run_id"), plan["run_id"], "evidence run_id")
    _require_equal(evidence.get("plan_sha256"), plan["plan_sha256"], "evidence plan hash")
    _require_equal(evidence.get("status"), "pass", "evidence status")
    rows = evidence.get("cases")
    if not isinstance(rows, list):
        raise ValueError("evidence cases are missing")
    planned_cases = plan["cases"]
    if not isinstance(planned_cases, list):
        raise ValueError("plan cases are malformed")
    expected_by_id = {case["case_id"]: case for case in planned_cases}
    if len(expected_by_id) != EXPECTED_CASE_COUNT:
        raise ValueError("plan does not contain 51 unique cases")
    observed_ids = [row.get("case_id") for row in rows if isinstance(row, Mapping)]
    _require_equal(len(rows), EXPECTED_CASE_COUNT, "evidence case count")
    _require_equal(set(observed_ids), set(expected_by_id), "evidence case IDs")
    if len(set(observed_ids)) != len(observed_ids):
        raise ValueError("evidence contains duplicate case IDs")

    verified: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("evidence case row is malformed")
        case = expected_by_id[str(row["case_id"])]
        _require_equal(row.get("status"), "pass", "case status")
        _require_equal(row.get("release"), case["release"], "case release")
        _require_equal(row.get("profile"), case["profile"], "case profile")
        _require_equal(
            row.get("character"), case["character"]["key"], "case character"
        )
        _require_equal(
            row.get("route_contract_sha256"),
            case["route_contract"]["contract_sha256"],
            "route contract SHA-256",
        )
        _require_equal(
            row.get("historical_provenance_sha256"),
            case["historical_target"]["provenance_sha256"],
            "historical provenance SHA-256",
        )
        _require_equal(
            row.get("final_provenance_sha256"),
            case["final_target"]["provenance_sha256"],
            "final provenance SHA-256",
        )

        counts = row.get("mechanism_counts")
        if not isinstance(counts, Mapping):
            raise ValueError("mechanism counts are missing")
        required_zero = (
            "emulator_state_inputs",
            "external_save_inputs",
            "manual_slot_mutations",
            "direct_ram_writes",
            "direct_sram_writes",
            "marker_injections",
            "scenario_selector_entries",
        )
        for key in required_zero:
            _require_equal(counts.get(key), 0, f"{key} count")
        expected_historical_saves = 2 if case["predecessor"] is not None else 1
        _require_equal(
            counts.get("historical_stock_in_game_saves"),
            expected_historical_saves,
            "historical stock-save count",
        )
        _require_equal(counts.get("current_stock_in_game_saves"), 1, "current stock-save count")
        _require_equal(counts.get("current_title_loads"), 2, "current title LOAD count")

        _verify_processes(row, case)
        checkpoints = row.get("sram_checkpoints")
        if not isinstance(checkpoints, Mapping):
            raise ValueError("SRAM checkpoints are missing")
        historical = _decode_checkpoint(
            checkpoints.get("historical_after_exit", {}),
            Commander(**case["character"]),
            "historical_after_exit",
        )
        current = _decode_checkpoint(
            checkpoints.get("current_after_resave_exit", {}),
            Commander(**case["character"]),
            "current_after_resave_exit",
        )
        _require_equal(
            row.get("current_first_load_input_sha256"),
            historical["sha256"],
            "first current LOAD input",
        )
        _require_equal(
            row.get("current_second_load_input_sha256"),
            current["sha256"],
            "second current LOAD input",
        )
        _verify_behavior(row, case, historical, current)

        visual = row.get("visual_artifacts")
        if not isinstance(visual, list):
            raise ValueError("visual artifacts are missing")
        phases = [item.get("phase") for item in visual if isinstance(item, Mapping)]
        _require_equal(phases, case["required_visual_artifact_phases"], "visual phases")
        for item in visual:
            _verify_artifact(item, f"{case['case_id']} {item['phase']}")
        verified.append(
            {
                "case_id": case["case_id"],
                "status": "pass",
                "historical_sram_sha256": historical["sha256"],
                "current_sram_sha256": current["sha256"],
                "behavior": case["expected_behavior"]["kind"],
            }
        )

    report: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "kind": REPORT_KIND,
        "verifier_id": VERIFIER_ID,
        "run_id": plan["run_id"],
        "status": "pass",
        "release_acceptance_eligible": True,
        "historical_target_count": EXPECTED_TARGET_COUNT,
        "case_count": EXPECTED_CASE_COUNT,
        "plan_sha256": plan["plan_sha256"],
        "checks": {
            "all_public_v131_v136_targets_hash_locked": True,
            "all_saves_originated_in_stock_game_ui": True,
            "all_historical_sram_exactly_8kib_after_process_exit": True,
            "all_current_entries_used_fresh_process_title_load": True,
            "damaged_v132_v133_fighter_lineage_originated_in_v131": True,
            "no_external_state_or_save_input": True,
            "no_direct_memory_or_save_mutation": True,
            "no_duplicate_join_exp_grant": True,
        },
        "cases": verified,
    }
    report["report_sha256"] = canonical_sha256(report)
    return report


def _write_json_report(path: Path, payload: Mapping[str, object]) -> None:
    if path.suffix.lower() != ".json":
        raise ValueError("this command writes JSON reports only")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan", help="verify artifacts and emit 51-case plan")
    plan_parser.add_argument("--run-id", required=True)
    plan_parser.add_argument("--artifact-root", type=Path, required=True)
    plan_parser.add_argument("--output", type=Path)

    verify_parser = subparsers.add_parser("verify", help="verify completed runtime evidence")
    verify_parser.add_argument("--run-id", required=True)
    verify_parser.add_argument("--artifact-root", type=Path, required=True)
    verify_parser.add_argument("--evidence", type=Path, required=True)
    verify_parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def _emit(payload: Mapping[str, object], output: Path | None) -> None:
    if output is None:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _write_json_report(output, payload)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    plan = build_plan(args.run_id, args.artifact_root.resolve())
    if args.command == "plan":
        _emit(plan, args.output)
        return 0
    evidence = _read_json(args.evidence)
    report = verify_evidence(plan, evidence)
    _emit(report, args.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error

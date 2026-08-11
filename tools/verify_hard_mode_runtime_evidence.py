#!/usr/bin/env python3
"""Verify retained emulator evidence for the Standard Hard runtime loader."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_GST = ROOT / "captures/analysis/0718_hard_s01_turn1_command.gst"
SCENARIO_TEN_GST = (
    ROOT / "captures/analysis/0718_hard_s10_early_seed_turn1.gst"
)
SCENARIO_SIXTEEN_GST = (
    ROOT / "captures/analysis/0718_hard_s16_turn1_command.gst"
)
SCENARIO_TWENTY_FIVE_GST = (
    ROOT / "captures/analysis/0718_hard_s25_turn1_banner.gst"
)
SCENARIO_TWENTY_SEVEN_GST = (
    ROOT / "captures/analysis/0718_hard_s27_turn1_command.gst"
)
RUNTIME_EXCEPTIONS = (
    ROOT / "localization/hard_mode_runtime_exceptions.json"
)
APPLIED_PLAN = ROOT / "localization/hard_mode_plan.json"

GST_WORK_RAM_FILE_OFFSET = 0x2478
RUNTIME_GROUP_BASE = 0x603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_MEMBER_SIZE = 0x0C
RUNTIME_LEVEL_OFFSET = 0x2E
RUNTIME_COMMANDER_AT_OFFSET = 0x3A
RUNTIME_COMMANDER_DF_OFFSET = 0x3B
RUNTIME_SOLDIER_AT_OFFSET = 0x46
RUNTIME_SOLDIER_DF_OFFSET = 0x47

SCENARIO_ONE_PLAYER_GROUPS = 2
SCENARIO_ONE_EXPECTED_GST_SHA256 = (
    "a9be34a13f38616617ce806f6b63821d1c15433b44e4e9e5d1ef1394b09a9256"
)
SCENARIO_TEN_EXPECTED_GST_SHA256 = (
    "8bc9b52b8218ca6f144ef7736472d99cc1b062f961bef001aafcd96a0a50e094"
)
SCENARIO_SIXTEEN_PLAYER_GROUPS = 8
SCENARIO_SIXTEEN_EXPECTED_GST_SHA256 = (
    "29e409e300b0c4d333c037fe966fbbb69f4ec203e5902a9a0492d15cc0793ccf"
)
SCENARIO_TWENTY_FIVE_PLAYER_GROUPS = 9
SCENARIO_TWENTY_FIVE_EXPECTED_GST_SHA256 = (
    "a895583ab3d3b94789354c7f690c87a3b5f3dec7f1ff14530245441e73a0c8e2"
)
SCENARIO_TWENTY_SEVEN_PLAYER_GROUPS = 10
SCENARIO_TWENTY_SEVEN_EXPECTED_GST_SHA256 = (
    "7e0088f23ae05ab1ec8386a2e28b9044ad8673f25096efcb254f6d7fb91af6cc"
)


@dataclass(frozen=True)
class ExpectedRuntimeGroup:
    fixed_record_index: int
    fixed_record_offset: int
    name: str
    class_id: int
    name_id: int
    level: int
    commander_at: int
    commander_df: int
    soldier_at: int
    soldier_df: int
    mercenaries: tuple[int, ...]
    hard_target: bool

    @property
    def runtime_group_index(self) -> int:
        return SCENARIO_ONE_PLAYER_GROUPS + self.fixed_record_index


@dataclass(frozen=True)
class RuntimeGroup:
    class_id: int
    name_id: int
    level: int
    commander_at: int
    commander_df: int
    soldier_at: int
    soldier_df: int
    mercenaries: tuple[int, ...]


SCENARIO_ONE_GROUPS = (
    ExpectedRuntimeGroup(
        fixed_record_index=8,
        fixed_record_offset=0x1802D8,
        name="발드",
        class_id=0x2E,
        name_id=0x12,
        level=4,
        commander_at=23,
        commander_df=19,
        soldier_at=3,
        soldier_df=1,
        mercenaries=(0x72,) * 6,
        hard_target=True,
    ),
    ExpectedRuntimeGroup(
        fixed_record_index=9,
        fixed_record_offset=0x1802FC,
        name="레온",
        class_id=0x45,
        name_id=0x0D,
        level=4,
        commander_at=40,
        commander_df=31,
        soldier_at=11,
        soldier_df=8,
        mercenaries=(0x7B, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF),
        hard_target=False,
    ),
    ExpectedRuntimeGroup(
        fixed_record_index=10,
        fixed_record_offset=0x180320,
        name="레아드",
        class_id=0x37,
        name_id=0x11,
        level=6,
        commander_at=33,
        commander_df=25,
        soldier_at=6,
        soldier_df=4,
        mercenaries=(0x7A, 0x7A, 0xFF, 0xFF, 0xFF, 0xFF),
        hard_target=False,
    ),
    ExpectedRuntimeGroup(
        fixed_record_index=11,
        fixed_record_offset=0x180344,
        name="제국지휘관",
        class_id=0x2D,
        name_id=0x2A,
        level=1,
        commander_at=21,
        commander_df=19,
        soldier_at=1,
        soldier_df=3,
        mercenaries=(0x72,) * 6,
        hard_target=True,
    ),
)


def read_runtime_group(gst: bytes, group_index: int) -> RuntimeGroup:
    if group_index < 0:
        raise ValueError("runtime group index must be non-negative")
    start = (
        GST_WORK_RAM_FILE_OFFSET
        + RUNTIME_GROUP_BASE
        + group_index * RUNTIME_GROUP_SIZE
    )
    end = start + RUNTIME_GROUP_SIZE
    if len(gst) < end:
        raise ValueError(
            f"GST is too short to contain runtime group {group_index}"
        )
    record = gst[start:end]
    return RuntimeGroup(
        class_id=record[0],
        name_id=record[1],
        level=record[RUNTIME_LEVEL_OFFSET],
        commander_at=record[RUNTIME_COMMANDER_AT_OFFSET],
        commander_df=record[RUNTIME_COMMANDER_DF_OFFSET],
        soldier_at=record[RUNTIME_SOLDIER_AT_OFFSET],
        soldier_df=record[RUNTIME_SOLDIER_DF_OFFSET],
        mercenaries=tuple(
            record[member_index * RUNTIME_MEMBER_SIZE]
            for member_index in range(1, 7)
        ),
    )


def expected_runtime_group(expected: ExpectedRuntimeGroup) -> RuntimeGroup:
    return RuntimeGroup(
        class_id=expected.class_id,
        name_id=expected.name_id,
        level=expected.level,
        commander_at=expected.commander_at,
        commander_df=expected.commander_df,
        soldier_at=expected.soldier_at,
        soldier_df=expected.soldier_df,
        mercenaries=expected.mercenaries,
    )


def load_runtime_exceptions(
    path: Path = RUNTIME_EXCEPTIONS,
) -> dict[tuple[int, int], dict]:
    model = json.loads(path.read_text(encoding="utf-8"))
    if model.get("schema_version") != 1:
        raise ValueError("unsupported hard-mode runtime exception schema")
    result = {}
    for row in model.get("exceptions", []):
        key = (int(row["scenario"]), int(row["fixed_record_index"]))
        if key in result:
            raise ValueError(f"duplicate hard-mode runtime exception: {key}")
        result[key] = row
    return result


def load_applied_plan(path: Path = APPLIED_PLAN) -> dict:
    """Load the reviewed plan that was actually used to build Hard ROMs.

    Runtime replay must stay usable after the private/ignored v1.0.0 ROM
    used to derive the plan is removed from a checkout. Rebuilding the plan
    here made valid emulator evidence depend on that old local ROM.
    """
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("schema_version") != 1:
        raise ValueError("unsupported hard-mode plan schema")
    scenarios = plan.get("scenarios", [])
    if [int(row["number"]) for row in scenarios] != list(range(1, 32)):
        raise ValueError("hard-mode plan must contain scenarios 1..31")
    if (
        plan.get("status") != "approved_balance_plan"
        or plan.get("approval", {}).get("status") != "approved"
    ):
        raise ValueError("hard-mode plan is not the approved balance plan")
    return plan


def runtime_exception_for(
    scenario_number: int,
    fixed_record_index: int,
) -> dict | None:
    return load_runtime_exceptions().get(
        (scenario_number, fixed_record_index)
    )


def verify_scenario_one(gst: bytes) -> tuple[RuntimeGroup, ...]:
    actual_groups = []
    for expected in SCENARIO_ONE_GROUPS:
        actual = read_runtime_group(gst, expected.runtime_group_index)
        wanted = expected_runtime_group(expected)
        if actual != wanted:
            raise ValueError(
                f"Scenario 1 {expected.name} runtime group "
                f"{expected.runtime_group_index} differs: "
                f"expected {wanted!r}, found {actual!r}"
            )
        actual_groups.append(actual)
    return tuple(actual_groups)


def verify_evidence(path: Path = DEFAULT_GST) -> tuple[RuntimeGroup, ...]:
    gst = path.read_bytes()
    digest = hashlib.sha256(gst).hexdigest()
    if path.resolve() == DEFAULT_GST.resolve():
        if digest != SCENARIO_ONE_EXPECTED_GST_SHA256:
            raise ValueError(
                "retained Scenario 1 GST hash changed: "
                f"{digest} != {SCENARIO_ONE_EXPECTED_GST_SHA256}"
            )
    return verify_scenario_one(gst)


def verify_planned_scenario(
    gst: bytes,
    scenario_number: int,
    player_group_count: int,
) -> tuple[RuntimeGroup, ...]:
    plan = load_applied_plan()
    scenario = next(
        row for row in plan["scenarios"]
        if int(row["number"]) == scenario_number
    )
    actual_groups = []
    for record in scenario["records"]:
        fixed_record_index = int(record["index"])
        runtime_group = player_group_count + fixed_record_index
        actual = read_runtime_group(gst, runtime_group)
        commander = record["commander"]
        soldier = record["enemy_soldier_correction"]
        expected = {
            "class_id": int(str(record["class_id"]), 16),
            "name_id": runtime_name_id(
                scenario_number,
                fixed_record_index,
                int(str(record["name_id"]), 16),
            ),
            "commander_at": int(commander["at"]["planned"]),
            "commander_df": int(commander["df"]["planned"]),
            "soldier_at": int(soldier["at"]["planned"]),
            "soldier_df": int(soldier["df"]["planned"]),
            "mercenaries": tuple(record["mercenaries"]["planned"]),
        }
        actual_projection = {
            "class_id": actual.class_id,
            "name_id": actual.name_id,
            "commander_at": actual.commander_at,
            "commander_df": actual.commander_df,
            "soldier_at": actual.soldier_at,
            "soldier_df": actual.soldier_df,
            "mercenaries": actual.mercenaries,
        }
        exception = runtime_exception_for(
            scenario_number,
            fixed_record_index,
        )
        if exception is not None:
            if (
                str(record["offset"])
                != str(exception["fixed_record_offset"])
                or str(record["name_id"]) != str(exception["name_id"])
                or str(record["class_id"]) != str(exception["class_id"])
            ):
                raise ValueError(
                    f"Scenario {scenario_number} runtime exception no longer "
                    f"matches fixed record {fixed_record_index}"
                )
            for field in exception["runtime_overridden_fields"]:
                expected.pop(field)
                actual_projection.pop(field)
        if actual_projection != expected:
            raise ValueError(
                f"Scenario {scenario_number} {record['name_korean']} "
                f"runtime group {runtime_group} differs: "
                f"expected {expected!r}, found {actual_projection!r}"
            )
        actual_groups.append(actual)
    return tuple(actual_groups)


def runtime_name_id(
    scenario_number: int,
    fixed_record_index: int,
    planned_name_id: int,
) -> int:
    """Apply reviewed shared-gameplay identity fixes over balance metadata."""

    # The approved Hard plan intentionally describes Japanese-source balance
    # records.  v1.3.5 corrects Scenario 31 record 8's duplicate Demon Lord
    # ID 0x65 to the stock death handler's ID 0x66 in every edition.  Keep the
    # balance plan immutable and overlay that non-balance production fix only
    # when checking loaded runtime groups.
    if (
        scenario_number == 31
        and fixed_record_index == 8
        and planned_name_id == 0x65
    ):
        return 0x66
    return planned_name_id


def verify_retained_planned_scenario(
    scenario_number: int,
    path: Path,
    retained_path: Path,
    expected_sha256: str,
    player_group_count: int,
) -> tuple[RuntimeGroup, ...]:
    gst = path.read_bytes()
    digest = hashlib.sha256(gst).hexdigest()
    if path.resolve() == retained_path.resolve():
        if digest != expected_sha256:
            raise ValueError(
                f"retained Scenario {scenario_number} GST hash changed: "
                f"{digest} != {expected_sha256}"
            )
    return verify_planned_scenario(
        gst,
        scenario_number=scenario_number,
        player_group_count=player_group_count,
    )


def verify_scenario_sixteen(
    path: Path = SCENARIO_SIXTEEN_GST,
) -> tuple[RuntimeGroup, ...]:
    return verify_retained_planned_scenario(
        16,
        path,
        SCENARIO_SIXTEEN_GST,
        SCENARIO_SIXTEEN_EXPECTED_GST_SHA256,
        SCENARIO_SIXTEEN_PLAYER_GROUPS,
    )


def verify_scenario_twenty_five(
    path: Path = SCENARIO_TWENTY_FIVE_GST,
) -> tuple[RuntimeGroup, ...]:
    return verify_retained_planned_scenario(
        25,
        path,
        SCENARIO_TWENTY_FIVE_GST,
        SCENARIO_TWENTY_FIVE_EXPECTED_GST_SHA256,
        SCENARIO_TWENTY_FIVE_PLAYER_GROUPS,
    )


def verify_scenario_twenty_seven(
    path: Path = SCENARIO_TWENTY_SEVEN_GST,
) -> tuple[RuntimeGroup, ...]:
    return verify_retained_planned_scenario(
        27,
        path,
        SCENARIO_TWENTY_SEVEN_GST,
        SCENARIO_TWENTY_SEVEN_EXPECTED_GST_SHA256,
        SCENARIO_TWENTY_SEVEN_PLAYER_GROUPS,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the Standard Hard Scenario 1 runtime AT/DF, soldier "
            "corrections, mercenaries, and excluded scripted commanders"
        )
    )
    parser.add_argument(
        "--scenario",
        type=int,
        choices=(1, 16, 25, 27),
        help="verify only one retained scenario; default verifies all",
    )
    parser.add_argument(
        "--gst",
        type=Path,
        help="override the retained GST for --scenario",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.gst is not None and args.scenario is None:
        raise ValueError("--gst requires --scenario")
    if args.scenario in (None, 1):
        groups = verify_evidence(args.gst or DEFAULT_GST)
        for expected, actual in zip(SCENARIO_ONE_GROUPS, groups):
            target = "hard target" if expected.hard_target else "excluded"
            print(
                f"S1 group {expected.runtime_group_index:02d} "
                f"{expected.name} ({target}): "
                f"AT/DF {actual.commander_at}/{actual.commander_df}, "
                f"soldier {actual.soldier_at}/{actual.soldier_df}, "
                "mercs "
                + " ".join(f"{value:02X}" for value in actual.mercenaries)
            )
    planned_evidence = (
        (16, SCENARIO_SIXTEEN_GST, SCENARIO_SIXTEEN_PLAYER_GROUPS,
         verify_scenario_sixteen),
        (25, SCENARIO_TWENTY_FIVE_GST, SCENARIO_TWENTY_FIVE_PLAYER_GROUPS,
         verify_scenario_twenty_five),
        (27, SCENARIO_TWENTY_SEVEN_GST, SCENARIO_TWENTY_SEVEN_PLAYER_GROUPS,
         verify_scenario_twenty_seven),
    )
    for scenario_number, retained_path, player_groups, verifier in planned_evidence:
        if args.scenario not in (None, scenario_number):
            continue
        groups = verifier(
            args.gst or retained_path
        )
        scenario = next(
            row for row in load_applied_plan()["scenarios"]
            if int(row["number"]) == scenario_number
        )
        record_indexes = [int(record["index"]) for record in scenario["records"]]
        first_group = player_groups + min(record_indexes)
        last_group = player_groups + max(record_indexes)
        print(
            f"S{scenario_number} groups {first_group}..{last_group}: "
            f"{len(groups)} hard targets match planned commander AT/DF, "
            "soldier corrections, and mercenaries"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

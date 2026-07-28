#!/usr/bin/env python3
"""Lock hard-mode balance writes behind an explicit user approval record."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from tools import hard_mode_baseline


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APPROVAL = ROOT / "localization/hard_mode_approval.json"
EXPECTED_CONFIRMATION = "표준 하드로 해줘"

REQUIRED_DECISIONS = (
    "scenario_band_target_difficulty",
    "enemy_commander_at_df_formula_and_caps",
    "stronger_mercenary_start_and_replacement_ratio",
    "late_summon_unit_start_and_ratio",
    "boss_reinforcement_branch_ending_exceptions",
)

DECISION_APPROVAL_VALUES = {
    "scenario_band_target_difficulty": (
        "standard_hard_runestone_v1_endgame_curve"
    ),
    "enemy_commander_at_df_formula_and_caps": (
        "standard_hard_runestone_v1_main_story_formula"
    ),
    "stronger_mercenary_start_and_replacement_ratio": (
        "eligible_occupied_slots_up_to_quota_runtime_guarded"
    ),
    "late_summon_unit_start_and_ratio": (
        "scenario_26_27_curated_runtime_guarded_with_fallback"
    ),
    "boss_reinforcement_branch_ending_exceptions": (
        "standard_hard_runestone_v1_exceptions_and_secret_mapping"
    ),
}

SECRET_SCENARIO_POLICY = {
    "28_X1": {
        "main_story_band_equivalent": "scenarios_11_15",
        "reason": "X1 복귀 시점의 본편 난이도에 맞춤",
    },
    "29_X2": {
        "main_story_band_equivalent": "scenarios_16_20",
        "reason": "X2 복귀 시점의 본편 난이도에 맞춤",
    },
    "30_X3": {
        "main_story_band_equivalent": "scenarios_21_24",
        "reason": "X3 복귀 시점의 본편 난이도에 맞춤",
        "exception": "미나 1·2단계는 하나의 보스로 보고 보정 중복 금지",
    },
    "31_X4": {
        "main_story_band_equivalent": "scenario_27",
        "reason": "최종 비밀 시나리오이므로 본편 최종장 수준으로 조정",
        "exception": (
            "베른하르트 0x183902의 원본 AT87/DF61은 본편 상한보다 "
            "높으므로 자동 공식·상한을 적용하지 않고 원본 유지"
        ),
        "summon_rule": (
            "직접 공격·AI·이벤트 진단을 통과한 편성만 사용하고 "
            "실패하면 일반 상위 용병으로 대체"
        ),
    },
}


def _pair_rows(pairs: tuple[tuple[int, int], ...]) -> list[dict[str, str]]:
    return [
        {"source_class_id": f"{source:02X}", "target_class_id": f"{target:02X}"}
        for source, target in pairs
    ]


def approval_subject() -> dict[str, Any]:
    """Return every balance decision covered by the one-line approval."""
    return {
        "schema_version": 1,
        "proposal": hard_mode_baseline.RECOMMENDED_DISCUSSION_PROPOSAL,
        "mercenary_policy": {
            "quota_interpretation": "up_to_quota_on_eligible_occupied_slots",
            "empty_slots_remain_empty": True,
            "conservative_pairs": _pair_rows(
                hard_mode_baseline.CONSERVATIVE_MERCENARY_UPGRADE_PAIRS
            ),
            "conditional_role_aware_pairs": _pair_rows(
                hard_mode_baseline.CONDITIONAL_ROLE_AWARE_MERCENARY_UPGRADE_PAIRS
            ),
            "conditional_pair_gate": (
                "per-scenario terrain, movement, attack, AI, and event checks"
            ),
            "unsafe_candidate_fallback": "keep_original_mercenary",
        },
        "summon_policy": {
            "candidate_class_ids": [
                f"{class_id:02X}"
                for class_id in hard_mode_baseline.SUMMON_CLASS_IDS
            ],
            "excluded_class_ids": ["94"],
            "fixed_unit_gate": (
                "direct attack, ordinary AI, and event path must pass before use"
            ),
            "unsafe_candidate_fallback": (
                "use a conventional upper mercenary or keep the original"
            ),
        },
        "secret_scenario_policy": SECRET_SCENARIO_POLICY,
        "required_decision_values": DECISION_APPROVAL_VALUES,
        "normal_release_invariant": {
            "size": hard_mode_baseline.NORMAL_SIZE,
            "header_checksum": hard_mode_baseline.NORMAL_CHECKSUM,
            "sha256": hard_mode_baseline.NORMAL_SHA256,
            "immutable": True,
        },
    }


def subject_sha256() -> str:
    payload = json.dumps(
        approval_subject(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def pending_manifest() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "pending_user_approval",
        "proposal_id": hard_mode_baseline.RECOMMENDED_DISCUSSION_PROPOSAL[
            "id"
        ],
        "proposal_sha256": subject_sha256(),
        "expected_confirmation": EXPECTED_CONFIRMATION,
        "preliminary_user_selection": {
            "difficulty_target": "standard_hard",
        },
        "approval": {
            "confirmation": None,
            "approved_at": None,
            "decisions": {decision: None for decision in REQUIRED_DECISIONS},
        },
        "build_gate": {
            "may_build_hard_mode_rom": False,
            "may_apply_balance_values": False,
        },
    }


def approved_manifest(
    confirmation: str,
    *,
    approved_at: str | None = None,
) -> dict[str, Any]:
    if confirmation != EXPECTED_CONFIRMATION:
        raise ValueError(
            f"confirmation must be exactly {EXPECTED_CONFIRMATION!r}"
        )
    model = pending_manifest()
    model["status"] = "approved"
    model["approval"] = {
        "confirmation": confirmation,
        "approved_at": approved_at or datetime.now(timezone.utc).isoformat(),
        "decisions": dict(DECISION_APPROVAL_VALUES),
    }
    model["build_gate"] = {
        "may_build_hard_mode_rom": True,
        "may_apply_balance_values": True,
    }
    return model


def validate_manifest(model: dict[str, Any]) -> None:
    expected = pending_manifest()
    for key in (
        "schema_version",
        "proposal_id",
        "proposal_sha256",
        "expected_confirmation",
        "preliminary_user_selection",
    ):
        if model.get(key) != expected[key]:
            raise ValueError(f"hard-mode approval field is stale: {key}")

    status = model.get("status")
    if status == "pending_user_approval":
        if model != expected:
            raise ValueError("pending approval manifest contains unauthorized values")
        return
    if status != "approved":
        raise ValueError(f"invalid hard-mode approval status: {status!r}")

    approval = model.get("approval")
    if not isinstance(approval, dict):
        raise ValueError("approved manifest has no approval object")
    if approval.get("confirmation") != EXPECTED_CONFIRMATION:
        raise ValueError("approved manifest has no exact user confirmation")
    if not approval.get("approved_at"):
        raise ValueError("approved manifest has no approval timestamp")
    if approval.get("decisions") != DECISION_APPROVAL_VALUES:
        raise ValueError("approved manifest does not approve all five decisions")
    if model.get("build_gate") != {
        "may_build_hard_mode_rom": True,
        "may_apply_balance_values": True,
    }:
        raise ValueError("approved manifest does not open both build gates")


def load_manifest(path: Path = DEFAULT_APPROVAL) -> dict[str, Any]:
    model = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(model)
    return model


def require_approved(path: Path = DEFAULT_APPROVAL) -> dict[str, Any]:
    model = load_manifest(path)
    if model["status"] != "approved":
        raise PermissionError(
            f"hard-mode balance is not approved; reply {EXPECTED_CONFIRMATION!r}"
        )
    return model


def write_manifest(path: Path, model: dict[str, Any]) -> None:
    validate_manifest(model)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(model, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate or record the explicit hard-mode balance approval"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_APPROVAL)
    parser.add_argument("--write-pending", action="store_true")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--confirmation")
    parser.add_argument("--require-approved", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    actions = sum((
        args.write_pending,
        args.approve,
        args.require_approved,
    ))
    if actions > 1:
        raise SystemExit("choose only one approval action")

    if args.write_pending:
        if args.manifest.exists():
            current = json.loads(args.manifest.read_text(encoding="utf-8"))
            if current.get("status") == "approved":
                raise SystemExit("refusing to overwrite an approved manifest")
        write_manifest(args.manifest, pending_manifest())
    elif args.approve:
        if not args.confirmation:
            raise SystemExit("--approve requires --confirmation")
        try:
            model = approved_manifest(args.confirmation)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        write_manifest(args.manifest, model)
    elif args.require_approved:
        try:
            require_approved(args.manifest)
        except PermissionError as exc:
            raise SystemExit(str(exc)) from exc
    else:
        load_manifest(args.manifest)

    model = load_manifest(args.manifest)
    print(
        f"hard-mode approval: {model['status']} "
        f"proposal={model['proposal_id']} "
        f"sha256={model['proposal_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

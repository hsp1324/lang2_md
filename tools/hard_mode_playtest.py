#!/usr/bin/env python3
"""Track full-scenario playtests against an exact Standard Hard ROM build."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUILD = ROOT / "localization/hard_mode_build.json"
DEFAULT_PLAN = ROOT / "localization/hard_mode_plan.json"
DEFAULT_RUNTIME = (
    ROOT / "localization/hard_mode_current_candidate_runtime.json"
)
DEFAULT_FIRST_TURN = (
    ROOT / "localization/hard_mode_current_candidate_first_turn.json"
)
DEFAULT_COSMETIC_DELTA = (
    ROOT / "localization/ai_class_release_delta.json"
)
DEFAULT_CANDIDATE_DELTA = (
    ROOT / "localization/hard_mode_candidate_delta.json"
)
DEFAULT_CLASS_SPOT_CHECK = (
    ROOT / "localization/ai_class_runtime_spot_check.json"
)
DEFAULT_RESULTS = ROOT / "localization/hard_mode_playtest.json"
DEFAULT_MARKDOWN = ROOT / "docs/hard_mode_playtest.md"

SCENARIO_COUNT = 31
RESULTS = ("in_progress", "cleared", "blocked")
DIFFICULTIES = ("too_easy", "easy", "target", "hard", "too_hard")
RESULT_LABELS = {
    "pending": "미검수",
    "in_progress": "진행 중",
    "cleared": "클리어",
    "blocked": "진행 불가",
    "stale": "이전 후보 결과",
}
DIFFICULTY_LABELS = {
    "too_easy": "너무 쉬움",
    "easy": "쉬움",
    "target": "적정",
    "hard": "어려움",
    "too_hard": "너무 어려움",
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def scenario_display(number: int) -> str:
    if 1 <= number <= 27:
        return f"시나리오 {number}"
    if 28 <= number <= 31:
        return f"시나리오 X{number - 27}"
    raise ValueError(f"scenario must be between 1 and {SCENARIO_COUNT}")


def current_identity(
    build_path: Path = DEFAULT_BUILD,
    plan_path: Path = DEFAULT_PLAN,
    runtime_path: Path = DEFAULT_RUNTIME,
    first_turn_path: Path = DEFAULT_FIRST_TURN,
    cosmetic_delta_path: Path = DEFAULT_COSMETIC_DELTA,
    candidate_delta_path: Path = DEFAULT_CANDIDATE_DELTA,
    class_spot_check_path: Path = DEFAULT_CLASS_SPOT_CHECK,
) -> dict[str, Any]:
    build = load_json(build_path)
    rom_path = ROOT / build["release"]["output"]
    payload = rom_path.read_bytes()
    digest = sha256_bytes(payload)
    expected = build["hard"]
    if digest != expected["sha256"]:
        raise ValueError(
            f"hard candidate SHA-256 changed: {digest} != "
            f"{expected['sha256']}"
        )
    if len(payload) != int(expected["size"]):
        raise ValueError("hard candidate size changed")
    checksum = payload[0x18E:0x190].hex().upper()
    if checksum != expected["header_checksum"]:
        raise ValueError("hard candidate header checksum changed")

    runtime = load_json(runtime_path)
    first_turn = load_json(first_turn_path)
    cosmetic_delta = load_json(cosmetic_delta_path)
    candidate_delta = load_json(candidate_delta_path)
    class_spot_check = load_json(class_spot_check_path)
    runtime_source = runtime["hard_rom"]["sha256"]
    first_turn_source = first_turn["hard_rom"]["sha256"]
    if runtime_source != first_turn_source:
        raise ValueError(
            "hard runtime and first-turn evidence use different ROMs"
        )
    if runtime_source != digest:
        raise ValueError(
            "hard runtime and first-turn evidence do not match the current "
            "candidate"
        )
    if (
        candidate_delta["before"]["sha256"]
        != cosmetic_delta["after"]["sha256"]
    ):
        raise ValueError(
            "post-release candidate delta does not follow cosmetic delta"
        )
    delta = cosmetic_delta["delta"]
    if (
        cosmetic_delta["status"] != "verified_cosmetic_only_delta"
        or delta["categories"]["outside_owned_ranges"] != 0
        or delta["balance_event_ai_changed_bytes"] != 0
    ):
        raise ValueError(
            "hard runtime evidence cannot cross an unverified ROM delta"
        )
    candidate_change = candidate_delta["delta"]
    if (
        candidate_delta["status"] != "verified_ui_sprite_only_delta"
        or candidate_delta["after"]["sha256"] != digest
        or candidate_change["outside_owned_ranges"] != 0
        or candidate_change["balance_event_ai_changed_bytes"] != 0
    ):
        raise ValueError(
            "hard runtime evidence cannot cross the post-release candidate "
            "delta"
        )
    if (
        class_spot_check["status"] != "passed"
        or class_spot_check["rom"]["sha256"]
        != candidate_delta["before"]["sha256"]
        or len(class_spot_check["checks"]) != 6
        or any(
            row["result"] != "passed"
            for row in class_spot_check["checks"]
        )
    ):
        raise ValueError("current hard class-sprite spot checks are incomplete")
    runtime_verified = sorted(
        int(row["number"])
        for row in runtime["scenarios"]
        if row["status"] == "runtime_loader_smoke_verified"
    )
    first_turn_verified = sorted(
        int(row["number"])
        for row in first_turn["scenarios"]
        if row["status"] == "first_turn_runtime_verified"
    )
    required = list(range(1, SCENARIO_COUNT + 1))
    if runtime_verified != required:
        raise ValueError("hard runtime smoke coverage is incomplete")
    if first_turn_verified != required:
        raise ValueError("hard first-turn coverage is incomplete")

    return {
        "release_id": build["release"]["release_id"],
        "profile_id": build["profile_id"],
        "rom_path": str(rom_path.relative_to(ROOT)),
        "size": len(payload),
        "header_checksum": checksum,
        "sha256": digest,
        "plan_sha256": sha256_path(plan_path),
        "runtime_manifest_sha256": sha256_path(runtime_path),
        "first_turn_manifest_sha256": sha256_path(first_turn_path),
        "runtime_verified_scenarios": runtime_verified,
        "first_turn_verified_scenarios": first_turn_verified,
        "verification_lineage": {
            "runtime_source_sha256": runtime_source,
            "first_turn_source_sha256": first_turn_source,
            "cosmetic_delta_manifest": str(
                cosmetic_delta_path.relative_to(ROOT)
            ),
            "cosmetic_delta_manifest_sha256": sha256_path(
                cosmetic_delta_path
            ),
            "cosmetic_delta_status": cosmetic_delta["status"],
            "post_release_candidate_delta_manifest": str(
                candidate_delta_path.relative_to(ROOT)
            ),
            "post_release_candidate_delta_manifest_sha256": sha256_path(
                candidate_delta_path
            ),
            "post_release_candidate_delta_status": candidate_delta["status"],
            "current_class_spot_check_manifest": str(
                class_spot_check_path.relative_to(ROOT)
            ),
            "current_class_spot_check_manifest_sha256": sha256_path(
                class_spot_check_path
            ),
            "current_class_spot_checks_passed": 6,
        },
    }


def initial_manifest(identity: dict[str, Any] | None = None) -> dict[str, Any]:
    identity = identity or current_identity()
    manifest = {
        "schema_version": 1,
        "status": "awaiting_player_clear_verification",
        "hard_release": deepcopy(identity),
        "completion_policy": {
            "required_scenarios": list(range(1, SCENARIO_COUNT + 1)),
            "accepted_result": "cleared",
            "difficulty_rating_required": True,
            "hash_locked_evidence_required": True,
            "candidate_sha256_must_match": True,
            "scope": (
                "complete each scenario on the unmodified Standard Hard "
                "candidate, including its normal victory transition"
            ),
        },
        "scenarios": [
            {
                "number": number,
                "display": scenario_display(number),
                "attempts": [],
            }
            for number in range(1, SCENARIO_COUNT + 1)
        ],
        "coverage": {},
    }
    return refresh(manifest)


def latest_attempt(row: dict[str, Any]) -> dict[str, Any] | None:
    attempts = row.get("attempts", [])
    return attempts[-1] if attempts else None


def effective_result(
    row: dict[str, Any],
    candidate_sha256: str,
) -> str:
    attempt = latest_attempt(row)
    if attempt is None:
        return "pending"
    if attempt["candidate_sha256"] != candidate_sha256:
        return "stale"
    return str(attempt["result"])


def coverage(
    scenarios: list[dict[str, Any]],
    candidate_sha256: str,
) -> dict[str, Any]:
    cleared = []
    in_progress = []
    blocked = []
    stale = []
    pending = []
    for row in scenarios:
        number = int(row["number"])
        result = effective_result(row, candidate_sha256)
        {
            "cleared": cleared,
            "in_progress": in_progress,
            "blocked": blocked,
            "stale": stale,
            "pending": pending,
        }[result].append(number)
    return {
        "cleared_count": len(cleared),
        "required_count": SCENARIO_COUNT,
        "cleared_scenarios": cleared,
        "in_progress_scenarios": in_progress,
        "blocked_scenarios": blocked,
        "stale_scenarios": stale,
        "pending_scenarios": pending,
        "complete": len(cleared) == SCENARIO_COUNT,
    }


def refresh(manifest: dict[str, Any]) -> dict[str, Any]:
    digest = manifest["hard_release"]["sha256"]
    manifest["scenarios"] = sorted(
        manifest["scenarios"],
        key=lambda row: int(row["number"]),
    )
    manifest["coverage"] = coverage(manifest["scenarios"], digest)
    manifest["status"] = (
        "all_scenarios_player_cleared"
        if manifest["coverage"]["complete"]
        else "awaiting_player_clear_verification"
    )
    return manifest


def validate_manifest(
    manifest: dict[str, Any],
    identity: dict[str, Any] | None = None,
) -> None:
    identity = identity or current_identity()
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported hard playtest schema")
    if manifest.get("hard_release") != identity:
        raise ValueError(
            "hard playtest candidate identity is stale; use "
            "--rebase-candidate after reviewing the new ROM"
        )
    rows = manifest.get("scenarios")
    if not isinstance(rows, list):
        raise ValueError("hard playtest scenarios must be a list")
    numbers = [int(row["number"]) for row in rows]
    if numbers != list(range(1, SCENARIO_COUNT + 1)):
        raise ValueError("hard playtest must contain scenarios 1 through 31")
    for row in rows:
        if row.get("display") != scenario_display(int(row["number"])):
            raise ValueError("hard playtest scenario display is stale")
        for attempt in row.get("attempts", []):
            if attempt.get("result") not in RESULTS:
                raise ValueError("invalid hard playtest result")
            difficulty = attempt.get("difficulty")
            if difficulty is not None and difficulty not in DIFFICULTIES:
                raise ValueError("invalid hard playtest difficulty")
            if attempt["result"] == "cleared" and difficulty is None:
                raise ValueError("cleared playtests require a difficulty rating")
            if attempt["result"] == "cleared" and not attempt.get("evidence"):
                raise ValueError("cleared playtests require hash-locked evidence")
            turns = attempt.get("clear_turns")
            if turns is not None and (not isinstance(turns, int) or turns < 1):
                raise ValueError("clear turns must be a positive integer")
            retries = attempt.get("retry_count")
            if retries is not None and (
                not isinstance(retries, int) or retries < 0
            ):
                raise ValueError("retry count must be non-negative")
            for evidence in attempt.get("evidence", []):
                path = ROOT / evidence["path"]
                if not path.is_file():
                    raise ValueError(f"missing playtest evidence: {path}")
                if sha256_path(path) != evidence["sha256"]:
                    raise ValueError(f"changed playtest evidence: {path}")
    expected = coverage(rows, identity["sha256"])
    if manifest.get("coverage") != expected:
        raise ValueError("hard playtest coverage summary is stale")
    expected_status = (
        "all_scenarios_player_cleared"
        if expected["complete"]
        else "awaiting_player_clear_verification"
    )
    if manifest.get("status") != expected_status:
        raise ValueError("hard playtest status is stale")


def _evidence_record(path_text: str) -> dict[str, str]:
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("playtest evidence must be inside the repository") from exc
    if not path.is_file():
        raise ValueError(f"playtest evidence does not exist: {path}")
    return {
        "path": str(relative),
        "sha256": sha256_path(path),
    }


def record_attempt(
    manifest: dict[str, Any],
    scenario: int,
    result: str,
    difficulty: str | None = None,
    clear_turns: int | None = None,
    retry_count: int | None = None,
    notes: str = "",
    issues: list[str] | None = None,
    evidence_paths: list[str] | None = None,
    player: str = "hsp1324",
    recorded_at: str | None = None,
) -> dict[str, Any]:
    scenario_display(scenario)
    if result not in RESULTS:
        raise ValueError(f"result must be one of {', '.join(RESULTS)}")
    if difficulty is not None and difficulty not in DIFFICULTIES:
        raise ValueError(
            f"difficulty must be one of {', '.join(DIFFICULTIES)}"
        )
    if result == "cleared" and difficulty is None:
        raise ValueError("cleared playtests require --difficulty")
    if result == "cleared" and not evidence_paths:
        raise ValueError("cleared playtests require --evidence")
    if clear_turns is not None and clear_turns < 1:
        raise ValueError("--turns must be positive")
    if retry_count is not None and retry_count < 0:
        raise ValueError("--retries must be non-negative")

    candidate = manifest["hard_release"]["sha256"]
    row = next(
        row for row in manifest["scenarios"]
        if int(row["number"]) == scenario
    )
    row["attempts"].append({
        "candidate_sha256": candidate,
        "result": result,
        "difficulty": difficulty,
        "clear_turns": clear_turns,
        "retry_count": retry_count,
        "player": player,
        "recorded_at": recorded_at or datetime.now(timezone.utc).isoformat(),
        "notes": notes.strip(),
        "issues": list(issues or []),
        "evidence": [
            _evidence_record(path) for path in (evidence_paths or [])
        ],
    })
    return refresh(manifest)


def rebase_candidate(
    manifest: dict[str, Any],
    identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest["hard_release"] = deepcopy(identity or current_identity())
    return refresh(manifest)


def _cell(value: object) -> str:
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(manifest: dict[str, Any]) -> str:
    identity = manifest["hard_release"]
    summary = manifest["coverage"]
    lines = [
        "# 표준 하드 실제 플레이 검수",
        "",
        "> 자동 로딩·첫 턴 검증과 별개로, 동일 후보 ROM에서 각 장을",
        "> 실제로 승리하고 다음 장 또는 정상 종료까지 진행한 결과를 기록한다.",
        "",
        "## 후보",
        "",
        f"- 릴리스 ID: `{identity['release_id']}`",
        f"- ROM: `{identity['rom_path']}`",
        f"- MD 체크섬: `{identity['header_checksum']}`",
        f"- SHA-256: `{identity['sha256']}`",
        (
            "- 자동 런타임 적재: 31/31 "
            f"(증거 ROM `{identity['verification_lineage']['runtime_source_sha256']}`)"
        ),
        (
            "- 자동 첫 턴 진행: 31/31 "
            f"(증거 ROM `{identity['verification_lineage']['first_turn_source_sha256']}`)"
        ),
        (
            "- 승격 클래스 전이: "
            f"`{identity['verification_lineage']['cosmetic_delta_status']}`"
        ),
        (
            "- 최신 UI/스프라이트 전이: "
            f"`{identity['verification_lineage']['post_release_candidate_delta_status']}`"
        ),
        (
            "- 승격 클래스 실기 표본(직전 후보): "
            f"{identity['verification_lineage']['current_class_spot_checks_passed']}/6"
        ),
        "",
        "## 완료 조건",
        "",
        "- 수정하지 않은 동일 후보 ROM으로 31개 장을 각각 클리어한다.",
        "- 승리 뒤 결과·저장·다음 장 또는 정상 종료까지 확인한다.",
        "- 각 클리어에는 체감 난이도와 화면·저장 증거를 반드시 기록한다.",
        "- 후보 SHA-256이 바뀌면 이전 결과는 자동으로 완료 수에서 제외한다.",
        "- 31/31 클리어 전에는 최종 릴리스로 판정하지 않는다.",
        "",
        "## 진행률",
        "",
        f"- 실제 클리어: {summary['cleared_count']}/{summary['required_count']}",
        f"- 진행 중: {_cell(summary['in_progress_scenarios'])}",
        f"- 진행 불가: {_cell(summary['blocked_scenarios'])}",
        f"- 이전 후보 결과: {_cell(summary['stale_scenarios'])}",
        f"- 미검수: {_cell(summary['pending_scenarios'])}",
        "",
        "## 장별 결과",
        "",
        "| 장 | 상태 | 난이도 | 턴 | 재시도 | 기록자 | 문제 | 메모 |",
        "|---:|---|---|---:|---:|---|---|---|",
    ]
    candidate = identity["sha256"]
    for row in manifest["scenarios"]:
        result = effective_result(row, candidate)
        attempt = latest_attempt(row)
        if attempt is None:
            difficulty = turns = retries = player = issues = notes = None
        else:
            difficulty = DIFFICULTY_LABELS.get(
                attempt.get("difficulty"),
                attempt.get("difficulty"),
            )
            turns = attempt.get("clear_turns")
            retries = attempt.get("retry_count")
            player = attempt.get("player")
            issues = ", ".join(attempt.get("issues", []))
            notes = attempt.get("notes")
        lines.append(
            "| "
            + " | ".join([
                _cell(row["display"]),
                _cell(RESULT_LABELS[result]),
                _cell(difficulty),
                _cell(turns),
                _cell(retries),
                _cell(player),
                _cell(issues),
                _cell(notes),
            ])
            + " |"
        )
    lines.extend([
        "",
        "## 기록 명령",
        "",
        "```bash",
        "python3 tools/hard_mode_playtest.py --scenario 1 --result cleared \\",
        "  --difficulty target --turns 12 --retries 1 \\",
        '  --notes "발드전 난이도 적정" \\',
        "  --evidence captures/playtest/hard_s01_next_scenario.png",
        "```",
        "",
        "문제가 있으면 `--result blocked --difficulty too_hard`와",
        "`--issue ISSUE-ID`, `--evidence 저장경로`를 함께 사용한다.",
        "실제 기록은 Codex가 사용자 보고를 확인한 뒤 대신 입력해도 된다.",
        "",
    ])
    return "\n".join(lines)


def write_outputs(
    manifest: dict[str, Any],
    results_path: Path = DEFAULT_RESULTS,
    markdown_path: Path = DEFAULT_MARKDOWN,
) -> None:
    results_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(manifest), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track full-scenario Standard Hard playtest results"
    )
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--rebase-candidate", action="store_true")
    parser.add_argument("--scenario", type=int)
    parser.add_argument("--result", choices=RESULTS)
    parser.add_argument("--difficulty", choices=DIFFICULTIES)
    parser.add_argument("--turns", type=int)
    parser.add_argument("--retries", type=int)
    parser.add_argument("--notes", default="")
    parser.add_argument("--issue", action="append", default=[])
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--player", default="hsp1324")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    identity = current_identity()
    if args.initialize:
        if args.results.exists() and not args.force:
            raise SystemExit(f"playtest manifest already exists: {args.results}")
        manifest = initial_manifest(identity)
        write_outputs(manifest, args.results, args.markdown)
    else:
        if not args.results.is_file():
            raise SystemExit(
                f"missing playtest manifest; run with --initialize: "
                f"{args.results}"
            )
        manifest = load_json(args.results)
        if args.rebase_candidate:
            manifest = rebase_candidate(manifest, identity)
        else:
            validate_manifest(manifest, identity)
        if args.scenario is not None or args.result is not None:
            if args.scenario is None or args.result is None:
                raise SystemExit("--scenario and --result must be used together")
            manifest = record_attempt(
                manifest,
                args.scenario,
                args.result,
                difficulty=args.difficulty,
                clear_turns=args.turns,
                retry_count=args.retries,
                notes=args.notes,
                issues=args.issue,
                evidence_paths=args.evidence,
                player=args.player,
            )
        if args.rebase_candidate or args.scenario is not None:
            write_outputs(manifest, args.results, args.markdown)

    validate_manifest(manifest, identity)
    if args.check:
        expected = render_markdown(manifest)
        if args.markdown.read_text(encoding="utf-8") != expected:
            raise SystemExit(f"stale hard playtest document: {args.markdown}")
    summary = manifest["coverage"]
    print(
        f"hard playtest {summary['cleared_count']}/"
        f"{summary['required_count']} scenarios cleared"
    )
    if args.require_complete and not summary["complete"]:
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)

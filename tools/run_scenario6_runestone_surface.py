#!/usr/bin/env python3
# ruff: noqa: E402
"""Prove Scenario 6's reachable well Rune Stone on isolated Xvfb.

The runner hash-locks one production candidate, derives the minimal deployment
probe in memory, and performs the ordinary Elwin move ``(6,4) -> (7,4)``.  It
keeps three independent runtime facts: the localized item dialogue, the moved
and acted commander state, and the exact ``(0x1A, 0xFF)`` inventory insertion
after the dialogue is dismissed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_scenario6_runestone_probe_rom as probe_builder
from tools import run_blastem_sequence as blastem
from tools import run_pike_acted_surface_probe as battle
from tools import run_preparation_surface_matrix as preparation
from tools import run_preparation_surface_parallel as preparation_parallel


PROFILES = ("pure", "normal", "hard")
SCENARIO_NUMBER = 6
ELWIN_COMMANDER_ID = 1
RUNESTONE_ITEM_ID = 0x1A
EXPECTED_START = (6, 4)
EXPECTED_DESTINATION = (7, 4)
DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/scenario6_runestone_surface"
DEFAULT_RUNTIME_ROOT = ROOT / "captures/runtime"
DEFAULT_DISPLAY = ":176"


def sha256_bytes(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def inventory_records(gst_path: Path) -> list[tuple[int, int]]:
    record = preparation.manual_slot_record_from_gst(gst_path)
    start = blastem.MANUAL_SLOT_ITEM_INVENTORY_OFFSET
    size = blastem.MANUAL_SLOT_ITEM_INVENTORY_RECORD_SIZE
    end = start + blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT * size
    inventory = record[start:end]
    if len(inventory) != blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT * size:
        raise ValueError("manual-slot record is missing the item inventory")
    return [
        (inventory[offset], inventory[offset + 1])
        for offset in range(0, len(inventory), size)
    ]


def runestone_acquisition_report(
    before: list[tuple[int, int]],
    after: list[tuple[int, int]],
) -> dict[str, object]:
    if len(before) != blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT:
        raise ValueError("before inventory must contain exactly 40 records")
    if len(after) != blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT:
        raise ValueError("after inventory must contain exactly 40 records")
    changes = [
        {
            "slot": index,
            "before": list(old),
            "after": list(new),
        }
        for index, (old, new) in enumerate(zip(before, after))
        if old != new
    ]
    expected = (RUNESTONE_ITEM_ID, blastem.MANUAL_SLOT_ITEM_UNEQUIPPED_OWNER)
    passed = (
        len(changes) == 1
        and tuple(changes[0]["before"]) == (0xFF, 0xFF)
        and tuple(changes[0]["after"]) == expected
        and sum(item == expected for item in after)
        == sum(item == expected for item in before) + 1
    )
    return {
        "status": "pass" if passed else "fail",
        "expected_inserted_record": list(expected),
        "runestone_count_before": sum(item == expected for item in before),
        "runestone_count_after": sum(item == expected for item in after),
        "changed_record_count": len(changes),
        "changes": changes,
    }


def probe_delta_report(
    candidate: bytes,
    probe: bytes,
) -> dict[str, object]:
    if len(candidate) != len(probe):
        raise ValueError("candidate and Scenario 6 probe sizes differ")
    changed = [
        index
        for index, (old, new) in enumerate(zip(candidate, probe))
        if old != new
    ]
    checksum_offsets = {0x18E, 0x18F}
    payload_changes = [index for index in changed if index not in checksum_offsets]
    expected_payload_changes = [
        probe_builder.FIRST_PLAYER_DEPLOYMENT + 1,
        probe_builder.FIRST_PLAYER_DEPLOYMENT + 3,
    ]
    passed = (
        payload_changes == expected_payload_changes
        and set(changed).issubset(checksum_offsets | set(expected_payload_changes))
    )
    return {
        "status": "pass" if passed else "fail",
        "changed_offsets": [f"0x{offset:X}" for offset in changed],
        "payload_changed_offsets": [
            f"0x{offset:X}" for offset in payload_changes
        ],
        "expected_payload_changed_offsets": [
            f"0x{offset:X}" for offset in expected_payload_changes
        ],
    }


def commander_state(gst_path: Path) -> dict[str, object]:
    member = battle.commander_group(gst_path, ELWIN_COMMANDER_ID)["members"][0]
    return {
        "class_id": int(member["class_id"]),
        "commander_id": int(member["commander_id"]),
        "acted_flag": int(member["acted_flag"]),
        "hp": int(member["hp"]),
        "x": int(member["x"]),
        "y": int(member["y"]),
        "record": str(member["record"]),
    }


def image_report(path: Path) -> dict[str, object]:
    return {"path": relative(path), "sha256": sha256(path)}


def state_report(path: Path) -> dict[str, object]:
    return {"path": relative(path), "sha256": sha256(path)}


def run_surface(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.profile / args.run_id
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    seed = state_report(args.seed_gst)

    source = args.source_rom.read_bytes()
    candidate, candidate_origin = probe_builder.load_hash_locked_candidate(
        args.candidate_rom,
        args.expected_candidate_sha256,
    )
    probe = bytes(probe_builder.build_probe(candidate, source))
    probe_delta = probe_delta_report(candidate, probe)
    if probe_delta["status"] != "pass":
        raise ValueError(f"Scenario 6 probe is not minimal: {probe_delta}")
    probe_path = output / "scenario6-runestone-probe.md"
    probe_path.write_bytes(probe)

    runtime_name = f"s6-runestone-{args.profile}-{args.run_id}"
    if Path(runtime_name).name != runtime_name:
        raise ValueError("--run-id must produce one safe runtime directory name")
    runtime_home = args.runtime_root / runtime_name
    recorder = preparation.RuntimeRecorder(output, args.display, runtime_home)
    xvfb = preparation_parallel.start_xvfb(
        args.xvfb,
        args.xvfb_library_path,
        args.display,
    )
    started = time.monotonic()
    try:
        identity = preparation.launch_to_preparation(
            recorder,
            probe_path,
            args.seed_gst,
            SCENARIO_NUMBER,
            runtime_name,
            output,
        )
        prep_capture = recorder.capture("preparation/root.png")
        battle.enter_battle_command(recorder, probe_path, output)
        command_capture = recorder.capture("battle/active_command.png")
        before_gst = recorder.save_gst("states/before_move.gst")
        before_commander = commander_state(before_gst)
        before_inventory = inventory_records(before_gst)
        if (
            (before_commander["x"], before_commander["y"])
            != EXPECTED_START
            or before_commander["acted_flag"] != 0
        ):
            raise RuntimeError(
                "Scenario 6 probe did not start with active Elwin at "
                f"{EXPECTED_START}: {before_commander}"
            )

        # detect-command leaves Elwin's command window open on Move. Confirm
        # Move, target the reachable right approach, confirm the destination,
        # then confirm Standby so the stock hidden-item dispatcher runs.
        recorder.send(["c"], delay=0.8)
        recorder.send(["right"], delay=0.6)
        target_capture = recorder.capture("battle/move_target_7_4.png")
        recorder.send(["c"], delay=0.9)
        moved_capture = recorder.capture("battle/after_move_before_standby.png")
        recorder.send(["c"], delay=1.4)
        dialogue_capture = recorder.capture("battle/runestone_found.png")
        if not blastem.battle_dialogue_visible(dialogue_capture):
            raise RuntimeError(
                "Scenario 6 move did not render the Rune Stone dialogue panel"
            )
        dialogue_gst = recorder.save_gst("states/runestone_dialogue.gst")
        dialogue_commander = commander_state(dialogue_gst)
        if (
            (dialogue_commander["x"], dialogue_commander["y"])
            != EXPECTED_DESTINATION
            or dialogue_commander["acted_flag"] != 1
        ):
            raise RuntimeError(
                "Rune Stone dialogue did not follow an acted move to "
                f"{EXPECTED_DESTINATION}: {dialogue_commander}"
            )

        # The item opcode follows the dialogue opcode in the stock handler.
        # Keep the dialogue GST, dismiss it, then prove the serialized item
        # table gained exactly one unequipped Rune Stone and nothing else.
        recorder.send(["c"], delay=1.3)
        acquired_capture = recorder.capture("battle/after_item_acquisition.png")
        acquired_gst = recorder.save_gst("states/after_item_acquisition.gst")
        acquired_commander = commander_state(acquired_gst)
        after_inventory = inventory_records(acquired_gst)
        acquisition = runestone_acquisition_report(
            before_inventory,
            after_inventory,
        )
        if acquisition["status"] != "pass":
            raise RuntimeError(
                "Scenario 6 Rune Stone inventory insertion failed: "
                f"{acquisition}"
            )
        if (
            (acquired_commander["x"], acquired_commander["y"])
            != EXPECTED_DESTINATION
            or acquired_commander["acted_flag"] != 1
        ):
            raise RuntimeError(
                "Elwin state changed unexpectedly after item acquisition: "
                f"{acquired_commander}"
            )

        report = {
            "schema_version": 1,
            "status": "pass",
            "run_id": args.run_id,
            "profile": args.profile,
            "scenario": SCENARIO_NUMBER,
            "virtual_display": args.display,
            "candidate": {
                "path": relative(args.candidate_rom),
                "origin": candidate_origin,
                "sha256": sha256_bytes(candidate),
                "md_checksum": candidate[0x18E:0x190].hex().upper(),
            },
            "seed": seed,
            "probe": {
                "path": relative(probe_path),
                "sha256": sha256_bytes(probe),
                "md_checksum": probe[0x18E:0x190].hex().upper(),
                "delta_from_candidate": probe_delta,
            },
            "scenario_identity": identity,
            "movement": {
                "expected_start": list(EXPECTED_START),
                "expected_destination": list(EXPECTED_DESTINATION),
                "before": before_commander,
                "dialogue": dialogue_commander,
                "after_acquisition": acquired_commander,
            },
            "inventory_acquisition": acquisition,
            "evidence": {
                "preparation": image_report(prep_capture),
                "active_command": image_report(command_capture),
                "move_target": image_report(target_capture),
                "after_move_before_standby": image_report(moved_capture),
                "runestone_dialogue": image_report(dialogue_capture),
                "after_item_acquisition": image_report(acquired_capture),
                "before_move_gst": state_report(before_gst),
                "runestone_dialogue_gst": state_report(dialogue_gst),
                "after_item_acquisition_gst": state_report(acquired_gst),
            },
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
        (output / "evidence.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return report
    except Exception as exc:
        failure_gst = None
        try:
            saved = recorder.save_gst("states/failure.gst")
            failure_gst = state_report(saved)
        except Exception:
            pass
        failure = {
            "schema_version": 1,
            "status": "failed_attempt",
            "run_id": args.run_id,
            "profile": args.profile,
            "scenario": SCENARIO_NUMBER,
            "virtual_display": args.display,
            "candidate": {
                "path": relative(args.candidate_rom),
                "sha256": sha256_bytes(candidate),
            },
            "seed": seed,
            "probe": {
                "path": relative(probe_path),
                "sha256": sha256_bytes(probe),
                "delta_from_candidate": probe_delta,
            },
            "error_type": type(exc).__name__,
            "error": str(exc),
            "failure_gst": failure_gst,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
        (output / "failure.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raise
    finally:
        preparation.terminate_blastem_processes(display=args.display)
        preparation_parallel.stop_process(xvfb)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--candidate-rom", type=Path, required=True)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument(
        "--source-rom", type=Path, default=probe_builder.DEFAULT_SOURCE
    )
    parser.add_argument(
        "--seed-gst", type=Path, default=preparation.DEFAULT_SEED_GST
    )
    parser.add_argument("--display", default=DEFAULT_DISPLAY)
    parser.add_argument(
        "--xvfb", type=Path, default=preparation_parallel.DEFAULT_XVFB
    )
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=preparation_parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=preparation.validate_run_id, required=True)
    args = parser.parse_args()
    try:
        preparation_parallel.display_number(args.display)
    except ValueError as exc:
        parser.error(str(exc))
    for name in (
        "candidate_rom",
        "source_rom",
        "seed_gst",
        "xvfb",
        "xvfb_library_path",
        "output_root",
        "runtime_root",
    ):
        setattr(args, name, getattr(args, name).resolve())
    for label, path in (
        ("candidate ROM", args.candidate_rom),
        ("Japanese source ROM", args.source_rom),
        ("seed GST", args.seed_gst),
        ("Xvfb executable", args.xvfb),
    ):
        if not path.is_file():
            parser.error(f"{label} does not exist: {path}")
    if not args.xvfb_library_path.is_dir():
        parser.error(
            f"Xvfb library directory does not exist: {args.xvfb_library_path}"
        )
    report = run_surface(args)
    print(
        f"pass: {args.profile} Scenario 6 moved Elwin "
        f"{EXPECTED_START} -> {EXPECTED_DESTINATION} and added Rune Stone 0x1A"
    )
    print(
        args.output_root
        / args.profile
        / args.run_id
        / "evidence.json"
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

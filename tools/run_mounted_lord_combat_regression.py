#!/usr/bin/env python3
"""Run isolated-Xvfb map, status, and side-view mounted-lord regressions.

Each run first derives and re-verifies a byte-locked Scenario 1 diagnostic ROM
from the supplied exact production ROM.  The live checks then prove that the
selected Hawk/Croco Lord survives into work RAM, uses its reviewed map sprite
on Plane A, renders a status panel with the expected stats and zero EXP, and
loads the commander-specific side-view resource while a real attack animates.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
from typing import Iterable

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import build_mounted_lord_combat_probe_rom as probe_builder
from tools import capture_class_change_application as class_capture
from tools import run_blastem_sequence as blastem_sequence
from tools import run_preparation_surface_matrix as matrix
from tools import run_preparation_surface_parallel as parallel
from tools.jp_compressed_resource_inventory import decoded_payload
from tools.run_pike_acted_surface_probe import work_ram
from tools.verify_preparation_surface_evidence import load_gst, plane_tile_hits


RUN_SEQUENCE = ROOT / "tools/run_blastem_sequence.py"
DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/mounted_lord_combat_regression"
DEFAULT_DISPLAY = ":780"
COMBAT_VRAM_DESTINATION = 0x7000
RUNTIME_RECORD = 0x603C
RUNTIME_RECORD_SIZE = 0x60
RUNTIME_CLASS_OFFSET = 0x00
RUNTIME_COMMANDER_OFFSET = 0x01
RUNTIME_ACTED_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
RUNTIME_Y_OFFSET = 0x07
RUNTIME_LEVEL_OFFSET = 0x2E
RUNTIME_EXPERIENCE_OFFSET = 0x2F
RUNTIME_AT_OFFSET = 0x3A
RUNTIME_DF_OFFSET = 0x3B
RUNTIME_CLASS_STATS_OFFSET = 0x44
EXPECTED_RUNTIME_AT = 23
EXPECTED_RUNTIME_DF = 18
STATUS_COMMAND_PANEL = (31, 43, 97, 165)
STATUS_DETAIL_PANEL = (98, 44, 280, 194)
STATUS_BOTTOM_BAR = (0, 208, 320, 233)
BATTLE_UPPER_SURFACE = (0, 0, 320, 160)
BATTLE_ATTACKER_SURFACE = (0, 20, 160, 155)
BATTLE_UI_SURFACE = (0, 160, 320, 233)
DARK_BLUE = (0, 0, 119)


@dataclass(frozen=True)
class RunConfig:
    input_rom: Path
    input_sha256: str
    source_rom: Path
    source_sha256: str
    case: probe_builder.MountedLordCase
    display: str
    output: Path
    run_id: str
    xvfb: Path
    xvfb_library_path: Path
    initial_delay: float = 12.0
    confirmation_delay: float = 0.9
    max_confirmations: int = 80
    max_candidate_advances: int = 8
    attack_samples: int = 18
    attack_interval: float = 0.25


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256(payload: bytes | bytearray) -> str:
    return hashlib.sha256(payload).hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def rgb_ratio(
    image: Image.Image,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int],
) -> float:
    crop = image.crop(box)
    pixels = list(crop.getdata())
    return pixels.count(color) / len(pixels)


def image_model(path: Path) -> dict[str, object]:
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    return {
        "path": relative(path),
        "sha256": sha256_path(path),
        "dimensions": [image.width, image.height],
    }


def runtime_state_report(
    gst: Path,
    case: probe_builder.MountedLordCase,
) -> dict[str, object]:
    ram = work_ram(gst)
    record = ram[RUNTIME_RECORD : RUNTIME_RECORD + RUNTIME_RECORD_SIZE]
    if len(record) != RUNTIME_RECORD_SIZE:
        raise ValueError("GST runtime commander record is truncated")
    class_stats = bytes(
        record[
            RUNTIME_CLASS_STATS_OFFSET :
            RUNTIME_CLASS_STATS_OFFSET + len(case.expected_runtime_stats)
        ]
    )
    values = {
        "class_id": record[RUNTIME_CLASS_OFFSET],
        "commander_id": record[RUNTIME_COMMANDER_OFFSET],
        "acted_flag": record[RUNTIME_ACTED_OFFSET],
        "hp": record[RUNTIME_HP_OFFSET],
        "x": record[RUNTIME_X_OFFSET],
        "y": record[RUNTIME_Y_OFFSET],
        "level": record[RUNTIME_LEVEL_OFFSET],
        "experience": record[RUNTIME_EXPERIENCE_OFFSET],
        "at": record[RUNTIME_AT_OFFSET],
        "df": record[RUNTIME_DF_OFFSET],
        "class_stats": class_stats.hex().upper(),
        "move": class_stats[0],
        "a_plus": class_stats[2],
        "d_plus": class_stats[3],
    }
    checks = {
        "class_is_selected_mounted_lord": values["class_id"] == case.class_id,
        "commander_identity_preserved": (
            values["commander_id"] == case.commander_id
        ),
        "alive_and_visible": (
            values["hp"] > 0
            and values["x"] not in (0, 0xFF)
            and values["y"] not in (0, 0xFF)
        ),
        "level_reset_to_one": values["level"] == 1,
        "experience_reset_to_zero": values["experience"] == 0,
        "class_stats_match_mounted_source": (
            class_stats == case.expected_runtime_stats
        ),
        "display_at_matches": values["at"] == EXPECTED_RUNTIME_AT,
        "display_df_matches": values["df"] == EXPECTED_RUNTIME_DF,
    }
    return {
        "path": relative(gst),
        "sha256": sha256_path(gst),
        "record_range": "0x603C..0x609B",
        "record_hex": record.hex().upper(),
        "values": {
            **values,
            "class_id": f"0x{values['class_id']:02X}",
        },
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def complete_plane_a_occurrences(
    state: object,
    tile: int,
) -> tuple[int, list[dict[str, object]]]:
    rows = []
    counts = []
    for current in range(tile, tile + 4):
        hits = plane_tile_hits(state, current)
        plane_a = sum(hit["plane"] == "plane_a" for hit in hits)
        counts.append(plane_a)
        rows.append(
            {
                "tile": f"0x{current:04X}",
                "plane_a_hits": plane_a,
                "hits": hits,
            }
        )
    return min(counts), rows


def map_sprite_runtime_report(
    rom: bytes,
    gst: Path,
    case: probe_builder.MountedLordCase,
) -> dict[str, object]:
    state = load_gst(gst)
    sprite_id = probe_builder.map_sprite_id(
        rom,
        case.commander_id,
        case.class_id,
    )
    wrong_sprite_id = probe_builder.map_sprite_id(
        rom,
        case.commander_id,
        case.wrong_stats_class_id,
    )
    frames = probe_builder.map_sprite_frames(rom, sprite_id)
    wrong_frames = probe_builder.map_sprite_frames(rom, wrong_sprite_id)
    frame_rows = []
    visible_hashes: set[str] = set()
    for frame_index, expected in enumerate(frames):
        matches = []
        for offset in range(0, len(state.vram) - len(expected) + 1, 32):
            if state.vram[offset : offset + len(expected)] != expected:
                continue
            complete, references = complete_plane_a_occurrences(
                state,
                offset // 32,
            )
            if complete:
                visible_hashes.add(sha256(expected))
            matches.append(
                {
                    "vram_range": (
                        f"0x{offset:04X}..0x{offset + len(expected) - 1:04X}"
                    ),
                    "tile_range": (
                        f"0x{offset // 32:04X}..0x{offset // 32 + 3:04X}"
                    ),
                    "complete_plane_a_occurrences": complete,
                    "plane_references": references,
                }
            )
        frame_rows.append(
            {
                "frame": frame_index,
                "expected_sha256": sha256(expected),
                "wrong_class_sha256": sha256(wrong_frames[frame_index]),
                "differs_from_wrong_class": expected != wrong_frames[frame_index],
                "vram_matches": matches,
                "visible_vram_match": any(
                    row["complete_plane_a_occurrences"] > 0 for row in matches
                ),
            }
        )
    checks = {
        "mapped_to_reviewed_mounted_sprite": sprite_id != wrong_sprite_id,
        "frames_differ_from_wrong_class": all(
            row["differs_from_wrong_class"] for row in frame_rows
        ),
        "rom_payload_loaded_into_vram": all(
            row["vram_matches"] for row in frame_rows
        ),
        "actual_plane_a_unit_uses_verified_payload": bool(visible_hashes),
    }
    return {
        "sprite_id": f"0x{sprite_id:04X}",
        "wrong_class_id": f"0x{case.wrong_stats_class_id:02X}",
        "wrong_sprite_id": f"0x{wrong_sprite_id:04X}",
        "frames": frame_rows,
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def status_surface_report(
    capture: Path,
    runtime: dict[str, object],
    case: probe_builder.MountedLordCase,
) -> dict[str, object]:
    with Image.open(capture) as opened:
        image = opened.convert("RGB")
    if image.size != (320, 240):
        raise ValueError(f"unexpected status capture dimensions: {image.size}")
    command_blue = rgb_ratio(image, STATUS_COMMAND_PANEL, DARK_BLUE)
    detail_blue = rgb_ratio(image, STATUS_DETAIL_PANEL, DARK_BLUE)
    bottom_blue = rgb_ratio(image, STATUS_BOTTOM_BAR, DARK_BLUE)
    values = runtime["values"]
    checks = {
        "command_panel_visible": command_blue >= 0.45,
        "status_detail_panel_visible": detail_blue >= 0.30,
        "bottom_status_and_exp_bar_visible": bottom_blue >= 0.30,
        "runtime_status_is_exact": runtime["status"] == "pass",
        "class_name_source_is_selected_class": (
            values["class_id"] == f"0x{case.class_id:02X}"
        ),
        "exp_bar_source_is_zero": values["experience"] == 0,
    }
    return {
        **image_model(capture),
        "dark_blue_ratios": {
            "command_panel": round(command_blue, 6),
            "detail_panel": round(detail_blue, 6),
            "bottom_status_and_exp_bar": round(bottom_blue, 6),
        },
        "expected_visible_values": {
            "commander": case.commander_name,
            "class": case.class_name,
            "level": 1,
            "experience": 0,
            "at": EXPECTED_RUNTIME_AT,
            "df": EXPECTED_RUNTIME_DF,
            "move": case.expected_runtime_stats[0],
            "a_plus": case.expected_runtime_stats[2],
            "d_plus": case.expected_runtime_stats[3],
        },
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def battle_surface_report(capture: Path) -> dict[str, object]:
    with Image.open(capture) as opened:
        image = opened.convert("RGB")
    if image.size != (320, 240):
        raise ValueError(f"unexpected battle capture dimensions: {image.size}")
    upper_blue = rgb_ratio(image, BATTLE_UPPER_SURFACE, DARK_BLUE)
    ui_blue = rgb_ratio(image, BATTLE_UI_SURFACE, DARK_BLUE)
    attacker = image.crop(BATTLE_ATTACKER_SURFACE)
    attacker_hash = sha256(attacker.tobytes())
    # The stock side-view scene has a dark-blue combat HUD in the lower third
    # but not the full dark-blue status overlay in the upper playfield.
    visible = ui_blue >= 0.34 and upper_blue < 0.15
    return {
        **image_model(capture),
        "battle_ui_dark_blue_ratio": round(ui_blue, 6),
        "upper_dark_blue_ratio": round(upper_blue, 6),
        "attacker_crop_sha256": attacker_hash,
        "battle_surface_visible": visible,
    }


def commander_combat_resource(
    rom: bytes,
    case: probe_builder.MountedLordCase,
) -> tuple[int, int, bytes]:
    records = probe_builder.commander_combat_records(
        rom,
        case.commander_id,
    )
    _, record = records[case.class_id]
    raw_id = int.from_bytes(record[2:4], "big")
    index = raw_id & 0x7FFF
    pointer = (
        builder.be32(
            rom,
            builder.BYTE_UI_FONT_RESOURCE_TABLE + index * 4,
        )
        & 0x00FFFFFF
    )
    payload = decoded_payload(rom, pointer)
    if payload is None:
        raise ValueError(
            f"combat resource {index} uses an unsupported compression type"
        )
    return raw_id, pointer, payload


def decoded_resource(rom: bytes, raw_id: int) -> tuple[int, bytes]:
    index = raw_id & 0x7FFF
    pointer = (
        builder.be32(
            rom,
            builder.BYTE_UI_FONT_RESOURCE_TABLE + index * 4,
        )
        & 0x00FFFFFF
    )
    payload = decoded_payload(rom, pointer)
    if payload is None:
        raise ValueError(f"resource {index} cannot be decoded")
    return pointer, payload


def combat_vram_report(
    rom: bytes,
    vram: bytes,
    case: probe_builder.MountedLordCase,
) -> dict[str, object]:
    if len(vram) != 0x10000:
        raise ValueError(f"VRAM must be 64 KiB, got 0x{len(vram):X}")
    raw_id, pointer, expected = commander_combat_resource(rom, case)
    if raw_id != case.expected_commander_resource_id:
        raise ValueError(
            f"{case.class_name} commander combat resource changed: "
            f"0x{raw_id:04X}"
        )
    generic = probe_builder.generic_combat_record(rom, case.class_id)
    generic_raw_id = int.from_bytes(generic[0:2], "big")
    forbidden_ids = (
        case.forbidden_generic_resource_id,
        generic_raw_id,
    )
    forbidden = []
    for forbidden_id in dict.fromkeys(forbidden_ids):
        fallback_pointer, fallback_payload = decoded_resource(rom, forbidden_id)
        forbidden.append(
            {
                "raw_resource_id": f"0x{forbidden_id:04X}",
                "resource_index": forbidden_id & 0x7FFF,
                "rom_pointer": f"0x{fallback_pointer:06X}",
                "payload_sha256": sha256(fallback_payload),
                "loaded_at_combat_destination": (
                    vram[
                        COMBAT_VRAM_DESTINATION :
                        COMBAT_VRAM_DESTINATION + len(fallback_payload)
                    ]
                    == fallback_payload
                ),
            }
        )
    destination = vram[
        COMBAT_VRAM_DESTINATION :
        COMBAT_VRAM_DESTINATION + len(expected)
    ]
    exact_matches = []
    start = 0
    while True:
        match = vram.find(expected, start)
        if match < 0:
            break
        exact_matches.append(f"0x{match:04X}")
        start = match + 1
    checks = {
        "commander_override_resource_selected": raw_id
        == case.expected_commander_resource_id,
        "expected_payload_at_battle_destination": destination == expected,
        "expected_payload_present_in_vram": bool(exact_matches),
        "sister_vampire_or_generic_fallback_absent": not any(
            row["loaded_at_combat_destination"] for row in forbidden
        ),
    }
    return {
        "raw_resource_id": f"0x{raw_id:04X}",
        "resource_index": raw_id & 0x7FFF,
        "rom_pointer": f"0x{pointer:06X}",
        "decoded_size": len(expected),
        "decoded_sha256": sha256(expected),
        "destination": (
            f"0x{COMBAT_VRAM_DESTINATION:04X}.."
            f"0x{COMBAT_VRAM_DESTINATION + len(expected) - 1:04X}"
        ),
        "destination_sha256": sha256(destination),
        "exact_vram_matches": exact_matches,
        "forbidden_fallbacks": forbidden,
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def combat_gst_report(
    rom: bytes,
    gst: Path,
    case: probe_builder.MountedLordCase,
) -> dict[str, object]:
    state = load_gst(gst)
    resource = combat_vram_report(rom, state.vram, case)
    return {
        "path": relative(gst),
        "sha256": sha256_path(gst),
        "resource": resource,
        "status": resource["status"],
    }


def attack_animation_report(
    samples: Iterable[dict[str, object]],
    combat_states: Iterable[dict[str, object]],
) -> dict[str, object]:
    sample_rows = list(samples)
    state_rows = list(combat_states)
    battle_rows = [row for row in sample_rows if row["battle_surface_visible"]]
    crop_hashes = {str(row["attacker_crop_sha256"]) for row in battle_rows}
    passing_states = [row for row in state_rows if row["status"] == "pass"]
    checks = {
        "multiple_live_battle_frames_captured": len(battle_rows) >= 2,
        "side_view_attacker_region_animated": len(crop_hashes) >= 2,
        "commander_specific_combat_payload_observed": bool(passing_states),
    }
    return {
        "sample_count": len(sample_rows),
        "battle_frame_count": len(battle_rows),
        "unique_attacker_crop_count": len(crop_hashes),
        "attacker_crop_sha256": sorted(crop_hashes),
        "combat_state_count": len(state_rows),
        "passing_combat_state_count": len(passing_states),
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def build_exact_probe(config: RunConfig) -> tuple[Path, Path, dict[str, object]]:
    input_rom, source = read_locked_inputs(config)
    probe = bytearray(input_rom)
    _, manifest = probe_builder.patch_probe(probe, source, config.case)
    probe_builder.verify_probe(
        input_rom,
        bytes(probe),
        source,
        config.case,
        manifest,
    )
    probe_path = config.output / "diagnostic/probe.md"
    manifest_path = config.output / "diagnostic/delta.json"
    probe_path.parent.mkdir(parents=True, exist_ok=True)
    probe_path.write_bytes(probe)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    # Check the on-disk artifacts rather than trusting the just-written buffer.
    verify_exact_probe_artifacts(config, probe_path, manifest_path)
    return probe_path, manifest_path, manifest


def locked_file_bytes(path: Path, expected_sha256: str, label: str) -> bytes:
    payload = path.read_bytes()
    actual = sha256(payload)
    if actual != expected_sha256:
        raise ValueError(
            f"{label} SHA-256 changed after matrix preflight: "
            f"expected {expected_sha256}, got {actual}"
        )
    return payload


def read_locked_inputs(config: RunConfig) -> tuple[bytes, bytes]:
    return (
        locked_file_bytes(
            config.input_rom,
            config.input_sha256,
            "production input ROM",
        ),
        locked_file_bytes(
            config.source_rom,
            config.source_sha256,
            "Japanese source ROM",
        ),
    )


def verify_exact_probe_artifacts(
    config: RunConfig,
    probe_path: Path,
    manifest_path: Path,
) -> tuple[bytes, bytes]:
    input_rom, source = read_locked_inputs(config)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["input_rom"]["sha256"] != config.input_sha256:
        raise ValueError("diagnostic manifest input SHA-256 is not locked")
    if manifest["source_rom"]["sha256"] != config.source_sha256:
        raise ValueError("diagnostic manifest source SHA-256 is not locked")
    probe_builder.verify_probe(
        input_rom,
        probe_path.read_bytes(),
        source,
        config.case,
        manifest,
    )
    return input_rom, source


def require_idle_emulator() -> None:
    existing_pids = blastem_sequence.running_blastem_pids()
    if existing_pids:
        raise RuntimeError(
            "BlastEm is already running; mounted-lord regression requires "
            "an otherwise idle emulator environment (PID "
            + ", ".join(str(pid) for pid in existing_pids)
            + ")"
        )


def isolated_runtime_home(
    case: probe_builder.MountedLordCase,
    run_id: str,
) -> Path:
    runtime_name = f"mounted-{case.key}-{matrix.validate_run_id(run_id)}"
    return ROOT / "captures/runtime" / runtime_name


def advance_to_candidate_surface(
    recorder: matrix.RuntimeRecorder,
    max_advances: int,
) -> Path:
    for advance in range(max_advances + 1):
        capture = recorder.capture(
            f"class_change/candidate_advance_{advance:02d}.png"
        )
        if class_capture.class_change_candidate_surface_visible(capture):
            selected = recorder.output / "class_change/candidate_first.png"
            selected.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(capture, selected)
            return selected
        if advance < max_advances:
            recorder.send(["c"], delay=1.1)
    raise RuntimeError("class-change candidate surface did not appear")


def launch_to_class_change(
    recorder: matrix.RuntimeRecorder,
    config: RunConfig,
    probe_path: Path,
    runtime_name: str,
) -> None:
    recorder.run_command(
        [
            sys.executable,
            str(RUN_SEQUENCE),
            "first-turn-dialogue",
            "--rom",
            str(probe_path),
            "--runtime-name",
            runtime_name,
            "--runtime-root",
            str(recorder.runtime_home.parent),
            "--send-event",
            "--initial-delay",
            str(config.initial_delay),
            "--confirmation-delay",
            str(config.confirmation_delay),
            "--max-confirmations",
            str(config.max_confirmations),
            "--virtual-display",
            config.display,
        ]
    )


def run_probe(config: RunConfig) -> dict[str, object]:
    runtime_home = isolated_runtime_home(config.case, config.run_id)
    runtime_name = runtime_home.name
    if config.output.exists():
        raise FileExistsError(f"output already exists: {config.output}")
    if runtime_home.exists():
        raise FileExistsError(
            "isolated runtime home already exists; use a new --run-id: "
            f"{runtime_home}"
        )
    require_idle_emulator()
    config.output.mkdir(parents=True)
    probe_path, manifest_path, manifest = build_exact_probe(config)
    recorder = matrix.RuntimeRecorder(
        config.output,
        config.display,
        runtime_home,
    )
    xvfb = parallel.start_xvfb(
        config.xvfb,
        config.xvfb_library_path,
        config.display,
    )
    started = time.monotonic()
    try:
        # This is deliberately the final filesystem read before launching the
        # emulator: the production/source hashes, derivative bytes, and every
        # declared changed byte must still match the preflight snapshot.
        rom, _ = verify_exact_probe_artifacts(
            config,
            probe_path,
            manifest_path,
        )
        launch_to_class_change(
            recorder,
            config,
            probe_path,
            runtime_name,
        )
        trigger = recorder.capture("class_change/trigger.png")
        candidate_first = advance_to_candidate_surface(
            recorder,
            config.max_candidate_advances,
        )
        recorder.send(["down"], delay=1.0)
        candidate_selected = recorder.capture(
            "class_change/candidate_mounted_lord.png"
        )
        recorder.send(["c"], delay=5.0)
        applied_map = recorder.capture("map/applied.png")
        map_gst = recorder.save_gst("states/applied_map.gst")

        map_runtime = runtime_state_report(map_gst, config.case)
        map_sprite = map_sprite_runtime_report(rom, map_gst, config.case)

        recorder.send(["c"], delay=1.5)
        status_capture = recorder.capture("status/detail.png")
        status_gst = recorder.save_gst("states/status.gst")
        status_runtime = runtime_state_report(status_gst, config.case)
        status_surface = status_surface_report(
            status_capture,
            status_runtime,
            config.case,
        )

        # The command panel opens on Move.  Select Attack, target the Bald
        # staged immediately above the automatically deployed commander, and
        # let the real side-view battle progress without frame stepping.
        recorder.send(["down"], delay=0.8)
        recorder.send(["c"], delay=0.8)
        recorder.send(["up"], delay=0.8)
        recorder.send(["c"], delay=1.8)

        samples: list[dict[str, object]] = []
        combat_states: list[dict[str, object]] = []
        for sample_index in range(config.attack_samples):
            capture = recorder.capture(
                f"battle/attack_{sample_index:02d}.png"
            )
            surface = battle_surface_report(capture)
            samples.append(surface)
            if surface["battle_surface_visible"] and len(combat_states) < 3:
                gst = recorder.save_gst(
                    f"states/battle_{len(combat_states):02d}.gst"
                )
                combat_states.append(
                    combat_gst_report(rom, gst, config.case)
                )
            if sample_index + 1 < config.attack_samples:
                time.sleep(config.attack_interval)

        animation = attack_animation_report(samples, combat_states)
        passed = (
            map_runtime["status"] == "pass"
            and map_sprite["status"] == "pass"
            and status_runtime["status"] == "pass"
            and status_surface["status"] == "pass"
            and animation["status"] == "pass"
        )
        result = {
            "schema_version": 1,
            "status": "pass" if passed else "fail",
            "case": config.case.key,
            "profile_input": {
                "path": relative(config.input_rom),
                "sha256": config.input_sha256,
                "md_checksum": f"{builder.be16(rom, 0x18E):04X}",
            },
            "source_rom": {
                "path": relative(config.source_rom),
                "sha256": config.source_sha256,
            },
            "diagnostic": {
                "rom": relative(probe_path),
                "rom_sha256": sha256_path(probe_path),
                "manifest": relative(manifest_path),
                "manifest_sha256": sha256_path(manifest_path),
                "changed_byte_count": manifest["scope"]["changed_byte_count"],
                "exact_derivative_verified_before_launch": True,
            },
            "runtime_isolation": {
                "runtime_home": relative(runtime_home),
                "required_absent_before_launch": True,
                "existing_blastem_pids_before_launch": [],
                "reuse_runtime_state": False,
            },
            "class_change": {
                "trigger": image_model(trigger),
                "candidate_first": image_model(candidate_first),
                "candidate_mounted_lord": image_model(candidate_selected),
                "selected_candidate_index": 2,
                "selected_class_id": f"0x{config.case.class_id:02X}",
            },
            "map": {
                "capture": image_model(applied_map),
                "runtime": map_runtime,
                "sprite": map_sprite,
            },
            "status_detail_and_exp": {
                "runtime": status_runtime,
                "surface": status_surface,
            },
            "side_view_attack": {
                "animation": animation,
                "samples": samples,
                "combat_states": combat_states,
            },
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
        (config.output / "evidence.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result
    finally:
        matrix.terminate_blastem_processes(display=config.display)
        parallel.stop_process(xvfb)


def common_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--source-rom",
        type=Path,
        default=probe_builder.DEFAULT_SOURCE_ROM,
    )
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--initial-delay", type=float, default=12.0)
    parser.add_argument("--confirmation-delay", type=float, default=0.9)
    parser.add_argument("--max-confirmations", type=int, default=80)
    parser.add_argument("--max-candidate-advances", type=int, default=8)
    parser.add_argument("--attack-samples", type=int, default=18)
    parser.add_argument("--attack-interval", type=float, default=0.25)


def make_config(
    args: argparse.Namespace,
    *,
    input_rom: Path,
    input_sha256: str,
    source_sha256: str,
    case: probe_builder.MountedLordCase,
    display: str,
    output: Path,
    run_id: str,
) -> RunConfig:
    return RunConfig(
        input_rom=input_rom.resolve(),
        input_sha256=input_sha256,
        source_rom=args.source_rom.resolve(),
        source_sha256=source_sha256,
        case=case,
        display=display,
        output=output.resolve(),
        run_id=run_id,
        xvfb=args.xvfb.resolve(),
        xvfb_library_path=args.xvfb_library_path.resolve(),
        initial_delay=args.initial_delay,
        confirmation_delay=args.confirmation_delay,
        max_confirmations=args.max_confirmations,
        max_candidate_advances=args.max_candidate_advances,
        attack_samples=args.attack_samples,
        attack_interval=args.attack_interval,
    )


def require_inputs(paths: Iterable[tuple[str, Path]]) -> None:
    for label, path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")


def run_matrix(args: argparse.Namespace) -> dict[str, object]:
    root = (args.output_root / args.run_id).resolve()
    if root.exists():
        raise FileExistsError(f"output already exists: {root}")
    profiles = {
        "pure": args.pure_rom.resolve(),
        "normal": args.normal_rom.resolve(),
        "hard": args.hard_rom.resolve(),
    }
    require_inputs(
        [(f"{profile} ROM", path) for profile, path in profiles.items()]
        + [("source ROM", args.source_rom.resolve())]
    )
    require_idle_emulator()
    profile_hashes = {
        profile: sha256_path(path) for profile, path in profiles.items()
    }
    if len(set(profile_hashes.values())) != len(profile_hashes):
        raise ValueError("pure, normal, and hard ROM inputs must be distinct")
    source_sha256 = sha256_path(args.source_rom.resolve())
    jobs = [
        (profile, case)
        for profile in ("pure", "normal", "hard")
        for case in probe_builder.CASES.values()
    ]
    stale_runtime_homes = []
    for profile, case in jobs:
        job_id = f"{args.run_id}-{profile}-{case.key}"
        runtime_home = isolated_runtime_home(case, job_id)
        if runtime_home.exists():
            stale_runtime_homes.append(runtime_home)
    if stale_runtime_homes:
        raise FileExistsError(
            "isolated runtime homes already exist; use a new --run-id: "
            + ", ".join(str(path) for path in stale_runtime_homes)
        )
    root.mkdir(parents=True)
    results = []
    for job_index, (profile, case) in enumerate(jobs):
        display = f":{args.display_base + job_index}"
        job_id = f"{args.run_id}-{profile}-{case.key}"
        config = make_config(
            args,
            input_rom=profiles[profile],
            input_sha256=profile_hashes[profile],
            source_sha256=source_sha256,
            case=case,
            display=display,
            output=root / profile / case.key,
            run_id=job_id,
        )
        try:
            evidence = run_probe(config)
            evidence_path = config.output / "evidence.json"
            results.append(
                {
                    "profile": profile,
                    "case": case.key,
                    "display": display,
                    "status": evidence["status"],
                    "evidence": relative(evidence_path),
                    "evidence_sha256": sha256_path(evidence_path),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "profile": profile,
                    "case": case.key,
                    "display": display,
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    passed = all(row["status"] == "pass" for row in results)
    summary = {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "execution": "strictly_sequential_isolated_xvfb",
        "job_count": len(results),
        "pass_count": sum(row["status"] == "pass" for row in results),
        "profiles": {
            profile: {
                "path": relative(path),
                "sha256": profile_hashes[profile],
            }
            for profile, path in profiles.items()
        },
        "jobs": results,
    }
    (root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    one = subparsers.add_parser("one", help="run one exact-ROM commander case")
    common_parser(one)
    one.add_argument("--input-rom", type=Path, required=True)
    one.add_argument(
        "--case",
        type=probe_builder.parse_case,
        required=True,
    )
    one.add_argument("--display", default=DEFAULT_DISPLAY)

    all_profiles = subparsers.add_parser(
        "matrix",
        help="run pure/normal/hard x Keith/Lester sequentially",
    )
    common_parser(all_profiles)
    all_profiles.add_argument("--pure-rom", type=Path, required=True)
    all_profiles.add_argument("--normal-rom", type=Path, required=True)
    all_profiles.add_argument("--hard-rom", type=Path, required=True)
    all_profiles.add_argument("--display-base", type=int, default=780)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.initial_delay < 0:
        raise ValueError("--initial-delay must be non-negative")
    if args.confirmation_delay < 0:
        raise ValueError("--confirmation-delay must be non-negative")
    if args.max_confirmations < 1:
        raise ValueError("--max-confirmations must be positive")
    if args.max_candidate_advances < 1:
        raise ValueError("--max-candidate-advances must be positive")
    if args.attack_samples < 4:
        raise ValueError("--attack-samples must be at least four")
    if args.attack_interval < 0:
        raise ValueError("--attack-interval must be non-negative")
    if args.command == "one":
        parallel.display_number(args.display)
    else:
        job_count = len(probe_builder.CASES) * 3
        if not (
            parallel.MIN_ISOLATED_DISPLAY_NUMBER
            <= args.display_base
            <= 999 - job_count
        ):
            raise ValueError(
                "--display-base must reserve only high-numbered isolated "
                "Xvfb displays and leave room for every job"
            )


def main() -> int:
    args = parse_args()
    validate_args(args)
    if args.command == "matrix":
        summary = run_matrix(args)
        print(
            f"{summary['status']}: {summary['pass_count']}/"
            f"{summary['job_count']} mounted-lord combat jobs"
        )
        return 0 if summary["status"] == "pass" else 1

    require_inputs(
        [
            ("input ROM", args.input_rom.resolve()),
            ("source ROM", args.source_rom.resolve()),
        ]
    )
    input_sha256 = sha256_path(args.input_rom.resolve())
    source_sha256 = sha256_path(args.source_rom.resolve())
    output = (args.output_root / args.run_id).resolve()
    config = make_config(
        args,
        input_rom=args.input_rom,
        input_sha256=input_sha256,
        source_sha256=source_sha256,
        case=args.case,
        display=args.display,
        output=output,
        run_id=args.run_id,
    )
    result = run_probe(config)
    print(
        f"{result['status']}: {args.case.commander_name} "
        f"{args.case.class_name} map/status/side-view combat"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from PIL import Image, ImageDraw

from tools import run_late_enemy_battle_surface_matrix as late
from tools import run_sequential_campaign_revalidation as campaign


ROOT = Path(__file__).resolve().parents[1]


class LateEnemyBattleSurfaceMatrixTests(unittest.TestCase):
    def test_target_matrix_covers_every_late_chapter_once(self):
        self.assertEqual(tuple(sorted(late.TARGETS)), late.SCENARIOS)
        self.assertEqual(
            {target.scenario for target in late.TARGETS.values()},
            set(late.SCENARIOS),
        )
        self.assertTrue(
            all(target.mercenary_index > 0 for target in late.TARGETS.values())
        )

    def test_targets_are_visible_named_release_records_with_mercenaries(self):
        rom = (
            ROOT
            / "roms/builds/Langrisser II (Korean Hard v1.3.7).md"
        ).read_bytes()
        reference = (
            ROOT / "roms/original/Langrisser II (Japan).md"
        ).read_bytes()
        for scenario, target in late.TARGETS.items():
            with self.subTest(scenario=scenario):
                model = late.source_target_model(rom, reference, target)
                self.assertEqual(model["side_id"], 0x04)
                self.assertNotEqual(model["name_korean"], "")
                self.assertNotEqual(model["class_korean"], "")
                self.assertNotEqual(model["mercenary_class_id"], 0xFF)
                self.assertNotEqual(model["mercenary_class_korean"], "")
                self.assertEqual(model["mercenary_x"], model["x"] - 1)
                self.assertEqual(model["mercenary_y"], model["y"])

    def test_runtime_target_requires_all_identity_layout_fields(self):
        source = {
            "name_id": 0x11,
            "class_id": 0x43,
            "side_id": 0x04,
            "level": 10,
            "x": 23,
            "y": 7,
            "mercenary_index": 1,
            "mercenary_class_id": 0x7B,
            "mercenary_x": 22,
            "mercenary_y": 7,
            "name_korean": "레아드",
            "class_korean": "실버나이트",
            "mercenary_class_korean": "로얄호스",
        }
        members = [
            {
                "member_index": index,
                "class_id": 0xFF,
                "identity_id": 0,
                "acted_flag": 0,
                "hp": 0,
                "x": 0,
                "y": 0,
                "record_hex": "00" * 12,
            }
            for index in range(8)
        ]
        members[0].update(
            class_id=0x43,
            identity_id=0x11,
            hp=10,
            x=23,
            y=7,
        )
        members[1].update(class_id=0x7B, hp=10, x=22, y=7)
        group = {
            "group_index": 13,
            "side_id": 0x04,
            "level": 10,
            "record_hex": "11" * 0x60,
            "members": members,
        }
        self.assertEqual(late.runtime_target_report(group, source)["status"], "pass")
        members[1]["class_id"] = 0x7A
        failed = late.runtime_target_report(group, source)
        self.assertEqual(failed["status"], "fail")
        self.assertFalse(failed["checks"]["mercenary_class_exact"])

    def test_runtime_group_reads_side_level_and_all_members(self):
        payload = bytearray(0x2478 + 0x10000)
        group_index = 13
        start = 0x2478 + late.RUNTIME_GROUP_BASE + (
            group_index * late.RUNTIME_GROUP_SIZE
        )
        payload[start] = 0x43
        payload[start + 1] = 0x11
        payload[start + 3] = 10
        payload[start + 6] = 23
        payload[start + 7] = 7
        payload[start + late.RUNTIME_SIDE_OFFSET] = 0x04
        payload[start + late.RUNTIME_LEVEL_OFFSET] = 10
        member = start + late.RUNTIME_MEMBER_SIZE
        payload[member] = 0x7B
        payload[member + 3] = 10
        payload[member + 6] = 22
        payload[member + 7] = 7
        with self.subTest("temporary GST"):
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as directory:
                path = Path(directory) / "state.gst"
                path.write_bytes(payload)
                result = late.runtime_group(path, group_index)
        self.assertEqual(result["side_id"], 0x04)
        self.assertEqual(result["level"], 10)
        self.assertEqual(result["members"][0]["identity_id"], 0x11)
        self.assertEqual(result["members"][1]["class_id"], 0x7B)
        self.assertEqual(
            (result["members"][1]["x"], result["members"][1]["y"]),
            (22, 7),
        )

    def test_map_sprite_report_links_exact_rom_frames_to_plane_a(self):
        class_id = 0x43
        sprite_id = 1
        rom = bytearray(0x60000)
        table = late.builder.GENERIC_CLASS_SPRITE_TABLE + class_id * 2
        rom[table:table + 2] = sprite_id.to_bytes(2, "big")
        frame_payloads = []
        for frame, base in enumerate(late.builder.MAP_SPRITE_FRAME_BASES):
            payload = bytes((index + frame * 17) & 0xFF for index in range(0x80))
            start = base + sprite_id * 0x80
            rom[start:start + 0x80] = payload
            frame_payloads.append(payload)
        vram = bytearray(0x10000)
        starts = (0x1000, 0x2000)
        for start, payload in zip(starts, frame_payloads, strict=True):
            vram[start:start + 0x80] = payload

        linked_tiles = {
            tile
            for start in starts
            for tile in range(start // 32, start // 32 + 4)
        }
        with mock.patch.object(
            late,
            "load_gst",
            return_value=SimpleNamespace(vram=bytes(vram)),
        ), mock.patch.object(
            late,
            "plane_tile_hits",
            side_effect=lambda _state, tile: (
                [{"plane": "plane_a", "x": 1, "y": 1}]
                if tile in linked_tiles
                else []
            ),
        ):
            report = late.map_sprite_report(bytes(rom), Path("ignored.gst"), class_id)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["sprite_id"], "0x0001")
        self.assertTrue(
            report["checks"][
                "both_animation_frames_loaded_from_exact_rom_source"
            ]
        )
        self.assertTrue(
            report["checks"][
                "hovered_map_unit_uses_one_exact_frame_on_plane_a"
            ]
        )

    def test_status_surface_requires_full_detail_and_exact_cursor(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            path = Path(directory) / "status.png"
            image = Image.new("RGB", (320, 240), (0, 0, 0))
            draw = ImageDraw.Draw(image)
            for box in (
                late.STATUS_DETAIL_PANEL,
                late.STATUS_BOTTOM_BAR,
                late.ENEMY_UNIT_MESSAGE_PANEL,
            ):
                draw.rectangle(box, fill=late.DARK_BLUE)
            image.save(path)
            report = late.status_surface_report(
                path,
                cursor=(23, 7),
                expected_coordinate=(23, 7),
                expected_name="레아드",
                expected_class="실버나이트",
                group_unchanged=True,
                role="commander",
            )
            mismatch = late.status_surface_report(
                path,
                cursor=(22, 7),
                expected_coordinate=(23, 7),
                expected_name="레아드",
                expected_class="실버나이트",
                group_unchanged=True,
                role="commander",
            )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(mismatch["status"], "fail")
        self.assertFalse(
            mismatch["checks"]["cursor_still_selects_exact_runtime_member"]
        )

    def test_campaign_contract_rejects_arbitrary_seed_path_or_hash(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            rom = root / "release.md"
            rom.write_bytes(b"release")
            seed = root / "seed.gst"
            seed.write_bytes(b"seed")
            other = root / "other.gst"
            other.write_bytes(b"seed")
            summary = root / "summary.json"
            state = {
                "path": str(seed),
                "gst_sha256": hashlib.sha256(b"seed").hexdigest(),
                "record_sha256": "a" * 64,
                "scenario": 23,
            }
            summary.write_text(
                json.dumps(
                    {
                        "status": "pass",
                        "continuous_save_chain": True,
                        "route_order": list(campaign.FULL_ROUTE_ORDER),
                        "run_id": "fresh-02",
                        "results": [
                            {
                                "profile": "normal",
                                "status": "pass",
                                "release_rom": {
                                    "path": str(rom),
                                    "sha256": hashlib.sha256(b"release").hexdigest(),
                                },
                                "results": [
                                    {
                                        "scenario": 23,
                                        "status": "pass",
                                        "route_index": 23,
                                        "input_state": state,
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            snapshot = {
                "scenario": 23,
                "gst_sha256": state["gst_sha256"],
                "record_sha256": state["record_sha256"],
            }
            with mock.patch.object(campaign, "state_snapshot", return_value=snapshot):
                accepted = late.campaign_input_contract(
                    summary,
                    profile="normal",
                    scenario=23,
                    seed_gst=seed,
                    rom_path=rom,
                )
                with self.assertRaisesRegex(ValueError, "exact input GST"):
                    late.campaign_input_contract(
                        summary,
                        profile="normal",
                        scenario=23,
                        seed_gst=other,
                        rom_path=rom,
                    )
            self.assertEqual(accepted["status"], "pass")

    def test_preflight_lineage_is_never_release_eligible(self):
        args = argparse.Namespace(
            seed_gst=Path("preflight.gst"),
            preflight_only=True,
            campaign_summary=None,
            profile="normal",
            scenario=23,
            rom=Path("release.md"),
        )
        with mock.patch.object(
            campaign,
            "state_snapshot",
            return_value={"scenario": 1, "gst_sha256": "a" * 64},
        ):
            lineage = late.seed_lineage(args)
        self.assertFalse(lineage["final_acceptance_eligible"])
        self.assertEqual(lineage["mode"], "harness_preflight_only")

    def test_natural_combat_advances_to_second_enemy_phase(self):
        args = argparse.Namespace(
            scenario=23,
            display=":1010",
            max_turn_checks=400,
            turn_delay=0.1,
            emulator_speed=4,
            natural_combat_turns=2,
        )
        recorder = SimpleNamespace(environment={}, send=mock.Mock())
        empty = {
            "detector_capture_count": 20,
            "combat_episode_count": 0,
            "combat_frame_count": 0,
            "combat_frames": [],
            "accepted_combat_capture": None,
        }
        observed = {
            "detector_capture_count": 20,
            "combat_episode_count": 1,
            "combat_frame_count": 2,
            "combat_frames": [
                {"capture": {"path": "frame-a.png"}},
                {"capture": {"path": "frame-b.png"}},
            ],
            "accepted_combat_capture": {"path": "accepted.png"},
        }
        retained_calls = iter((empty, observed))
        surface_calls = iter(("a" * 64, "b" * 64))
        with mock.patch.object(
            late.first_turn,
            "select_turn_end",
            return_value={"final_cursor_row": 4},
        ), mock.patch.object(
            late.first_turn,
            "run_detector",
            return_value=("turn_command", 0),
        ), mock.patch.object(
            late.movement,
            "retained_turn_combat_report",
            side_effect=lambda *_args: next(retained_calls),
        ), mock.patch.object(
            late.mounted,
            "battle_surface_report",
            side_effect=lambda _path: {
                "battle_surface_visible": True,
                "attacker_crop_sha256": next(surface_calls),
            },
        ):
            report = late.natural_combat_report(
                recorder,
                args=args,
                output=Path("ignored"),
            )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["turns_attempted"], 2)
        self.assertEqual(report["accepted_turn_attempt"], 2)
        self.assertEqual(report["turns"][0]["motion_status"], "not_observed")
        self.assertEqual(report["turns"][1]["motion_status"], "pass")
        self.assertEqual(recorder.send.call_count, 2)


if __name__ == "__main__":
    unittest.main()

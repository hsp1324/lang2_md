import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools import run_gray_acted_surface_matrix as gray
from tools import run_gray_acted_surface_parallel as gray_parallel


ROOT = Path(__file__).resolve().parents[1]
HARD_RELEASE_ROM = (
    ROOT / "roms/builds/Langrisser II (Korean Hard v1.3.7).md"
)
PURE_RELEASE_ROM = (
    ROOT / "roms/builds/Langrisser II (Korean Original v1.3.7).md"
)


class GrayActedSurfaceMatrixTests(unittest.TestCase):
    def test_parallel_refuses_an_already_listening_xvfb_display(self) -> None:
        connection = mock.Mock()
        with mock.patch.object(
            gray_parallel.socket,
            "create_connection",
            return_value=connection,
        ):
            with self.assertRaisesRegex(RuntimeError, "occupied.*:852"):
                gray_parallel.require_displays_available([":852"])
        connection.close.assert_called_once_with()

    def test_campaign_bound_worker_uses_exact_scenario_seed_without_override(
        self,
    ) -> None:
        seed = gray.matrix.DEFAULT_SEED_GST.resolve()
        args = argparse.Namespace(
            profile="pure",
            rom=PURE_RELEASE_ROM.resolve(),
            seed_gst=seed,
            output_root=ROOT / "tmp/gray-worker-unit",
            runtime_root=ROOT / "tmp/gray-worker-runtime-unit",
            run_id="unit-campaign-bound",
            directions=["down", "right"],
            commander_id=1,
            commander_class=1,
            commander_level=1,
            commander_experience=0,
            scenario_seeds={
                8: {
                    "path": str(seed),
                    "sha256": gray.sha256(seed),
                    "record_sha256": "1" * 64,
                    "route_index": 7,
                    "source": "continuous_campaign_input",
                }
            },
        )
        command, origin, selected_seed, campaign_bound = (
            gray_parallel.worker_command(args, 8, ":852")
        )
        self.assertTrue(campaign_bound)
        self.assertEqual(selected_seed, seed)
        self.assertEqual(origin, args.scenario_seeds[8])
        self.assertIn("--preserve-seed-roster", command)
        self.assertEqual(command[command.index("--seed-gst") + 1], str(seed))
        self.assertEqual(command[command.index("--scenario") + 1], "8")

    def test_direction_parser_preserves_retry_order(self) -> None:
        self.assertEqual(
            gray.parse_directions("down,right,left,up"),
            ["down", "right", "left", "up"],
        )
        with self.assertRaises(argparse.ArgumentTypeError):
            gray.parse_directions("down,down")
        with self.assertRaises(argparse.ArgumentTypeError):
            gray.parse_directions("diagonal")

    def test_scenario_12_experiment_proves_real_move_and_stock_gray_payload(self) -> None:
        root = (
            ROOT
            / "captures/run/gray_acted_surface_experiment/normal/s12/path02"
        )
        if not (root / "states/acted_gray.gst").is_file():
            self.skipTest("historical experiment capture is not part of the release tree")
        after = gray.runtime_group_zero(root / "states/acted_gray.gst")
        state = gray.load_gst(root / "states/acted_gray.gst")
        _, _, expected = gray.expected_gray_payload()
        payload = state.vram[
            gray.GRAY_VRAM_START : gray.GRAY_VRAM_START + gray.GRAY_VRAM_BYTES
        ]
        self.assertEqual(after["acted_flag"], 1)
        self.assertEqual((after["x"], after["y"]), (15, 24))
        self.assertEqual(payload, expected)

    def test_parallel_plan_is_machine_readable(self) -> None:
        output = subprocess.check_output(
            [
                sys.executable,
                str(ROOT / "tools/run_gray_acted_surface_parallel.py"),
                "plan",
                "--profile", "normal",
                "--rom", str(ROOT / "roms/builds/Langrisser II (Korean Normal v1.3.7).md"),
                "--scenarios", "12-14",
                "--workers", "2",
                "--display-base", "150",
                "--run-id", "unit-plan",
                "--commander-id", "5",
                "--commander-class", "0x14",
                "--commander-level", "10",
                "--commander-experience", "7",
            ],
            cwd=ROOT,
            text=True,
        )
        plan = json.loads(output)
        self.assertEqual(plan["scenarios"], [12, 13, 14])
        self.assertEqual(plan["displays"], [":150", ":151"])
        self.assertEqual(plan["directions"], ["down", "right", "left", "up"])
        self.assertEqual(plan["selection_policy"], gray.SELECTION_POLICY)
        self.assertEqual(plan["seed_policy"], "shared_manual_diagnostic_seed")
        self.assertIsNone(plan["campaign_summary"])
        self.assertEqual(plan["commander_id"], 5)
        self.assertEqual(plan["commander_class_id"], "0x14")

    def test_live_stock_pointer_selects_scenario_eight_group_six(self) -> None:
        rom = PURE_RELEASE_ROM.read_bytes()
        payload = bytearray(gray.matrix.GST_WORK_RAM_FILE_OFFSET + 0x10000)
        ram = gray.matrix.GST_WORK_RAM_FILE_OFFSET
        group_index = 6
        group = (
            ram
            + gray.matrix.RUNTIME_GROUP_BASE
            + group_index * gray.matrix.RUNTIME_GROUP_SIZE
        )
        payload[group:group + 8] = bytes.fromhex("04 07 00 0A 06 00 06 12")
        expected_pointer = (
            gray.RUNTIME_GROUP_ABSOLUTE_BASE
            + group_index * gray.matrix.RUNTIME_GROUP_SIZE
        )
        payload[ram + gray.SELECTED_GROUP_INDEX_ADDRESS] = group_index
        payload[ram + gray.SELECTED_MEMBER_INDEX_ADDRESS] = 0
        payload[
            ram + gray.SELECTED_GROUP_POINTER_ADDRESS:
            ram + gray.SELECTED_GROUP_POINTER_ADDRESS + 4
        ] = expected_pointer.to_bytes(4, "big")
        payload[
            ram + gray.SELECTED_MEMBER_POINTER_ADDRESS:
            ram + gray.SELECTED_MEMBER_POINTER_ADDRESS + 4
        ] = expected_pointer.to_bytes(4, "big")
        payload[ram + gray.CURSOR_X_ADDRESS] = 6
        payload[ram + gray.CURSOR_Y_ADDRESS] = 18
        with tempfile.TemporaryDirectory() as directory:
            gst = Path(directory) / "selected.gst"
            gst.write_bytes(payload)
            selected = gray.selected_player_commander(gst, rom, 8)
        self.assertEqual(selected["policy"], gray.SELECTION_POLICY)
        self.assertEqual(selected["player_group_count"], 7)
        self.assertEqual(selected["group_index"], 6)
        self.assertEqual(selected["commander_id"], 7)
        self.assertEqual(selected["class_id"], 0x04)
        self.assertEqual(selected["cursor"], [6, 18])

    def test_live_stock_pointer_rejects_a_cursor_identity_mismatch(self) -> None:
        rom = PURE_RELEASE_ROM.read_bytes()
        payload = bytearray(gray.matrix.GST_WORK_RAM_FILE_OFFSET + 0x10000)
        ram = gray.matrix.GST_WORK_RAM_FILE_OFFSET
        group = ram + gray.matrix.RUNTIME_GROUP_BASE
        payload[group:group + 8] = bytes.fromhex("01 01 00 0A 00 00 0B 11")
        pointer = gray.RUNTIME_GROUP_ABSOLUTE_BASE
        payload[ram + gray.SELECTED_GROUP_INDEX_ADDRESS] = 0
        payload[ram + gray.SELECTED_MEMBER_INDEX_ADDRESS] = 0
        payload[
            ram + gray.SELECTED_GROUP_POINTER_ADDRESS:
            ram + gray.SELECTED_GROUP_POINTER_ADDRESS + 4
        ] = pointer.to_bytes(4, "big")
        payload[
            ram + gray.SELECTED_MEMBER_POINTER_ADDRESS:
            ram + gray.SELECTED_MEMBER_POINTER_ADDRESS + 4
        ] = pointer.to_bytes(4, "big")
        payload[ram + gray.CURSOR_X_ADDRESS] = 10
        payload[ram + gray.CURSOR_Y_ADDRESS] = 17
        with tempfile.TemporaryDirectory() as directory:
            gst = Path(directory) / "wrong-cursor.gst"
            gst.write_bytes(payload)
            with self.assertRaisesRegex(RuntimeError, "cursor does not match"):
                gray.selected_player_commander(gst, rom, 1)

    def test_campaign_seed_policy_never_builds_a_manual_roster_override(self) -> None:
        self.assertIsNone(
            gray.manual_slot_arguments(
                preserve_seed_roster=True,
                commander_id=1,
                commander_class=1,
                commander_level=1,
                commander_experience=0,
            )
        )
        self.assertEqual(
            gray.manual_slot_arguments(
                preserve_seed_roster=False,
                commander_id=7,
                commander_class=0x04,
                commander_level=5,
                commander_experience=3,
            ),
            [
                "--manual-slot-commander-id", "7",
                "--manual-slot-level", "5",
                "--manual-slot-experience", "3",
                "--manual-slot-class", "0x04",
            ],
        )

    def test_fixed_event_coverage_is_structural_and_ui_claims_stay_bounded(self) -> None:
        rom = PURE_RELEASE_ROM.read_bytes()
        model = gray.matrix.read_scenario(
            rom,
            gray.matrix.DEFAULT_REFERENCE_ROM.read_bytes(),
            8,
        )
        fixed = {
            "status": "pass",
            "mismatch_count": 0,
            "checked_fields": [
                "class_id",
                "name_id",
                "side_id",
                "level",
                "x",
                "y",
                "mercenaries",
            ],
            "records": [
                {
                    "fixed_record_index": index,
                    "protected_mismatches": {},
                }
                for index in range(model["record_count"])
            ],
        }
        coverage = gray.fixed_record_runtime_coverage(
            scenario_identity={"fixed_record_layout": fixed},
            rom_data=rom,
            scenario=8,
        )
        self.assertEqual(coverage["status"], "pass")
        self.assertEqual(
            coverage["runtime_records_checked"], model["record_count"]
        )
        self.assertEqual(
            sum(coverage["side_record_counts"].values()),
            model["record_count"],
        )
        claims = coverage["ui_surface_claims"]
        self.assertTrue(claims["selected_allied_real_move_and_gray_sprite"])
        self.assertTrue(claims["all_fixed_and_event_record_identity_fields"])
        self.assertFalse(claims["every_side_bottom_status_opened"])
        self.assertFalse(claims["every_side_detail_popup_opened"])
        self.assertFalse(claims["every_side_combat_animation_opened"])

    def test_fixed_event_coverage_rejects_missing_runtime_record(self) -> None:
        rom = PURE_RELEASE_ROM.read_bytes()
        model = gray.matrix.read_scenario(
            rom,
            gray.matrix.DEFAULT_REFERENCE_ROM.read_bytes(),
            8,
        )
        fixed = {
            "status": "pass",
            "mismatch_count": 0,
            "checked_fields": [
                "class_id",
                "name_id",
                "side_id",
                "level",
                "x",
                "y",
                "mercenaries",
            ],
            "records": [
                {
                    "fixed_record_index": index,
                    "protected_mismatches": {},
                }
                for index in range(model["record_count"] - 1)
            ],
        }
        with self.assertRaisesRegex(RuntimeError, "coverage count differs"):
            gray.fixed_record_runtime_coverage(
                scenario_identity={"fixed_record_layout": fixed},
                rom_data=rom,
                scenario=8,
            )

    def test_all_deployed_allied_records_bind_to_imported_save_roster(self) -> None:
        rom = PURE_RELEASE_ROM.read_bytes()
        seed = gray.matrix.DEFAULT_SEED_GST.resolve()
        roster = {
            row["commander_id"]: row
            for row in gray.matrix.manual_slot_roster(seed)
        }
        commander_ids = gray.matrix.player_commander_ids(rom, 8)
        payload = bytearray(gray.matrix.GST_WORK_RAM_FILE_OFFSET + 0x10000)
        for group_index, commander_id in enumerate(commander_ids):
            start = (
                gray.matrix.GST_WORK_RAM_FILE_OFFSET
                + gray.matrix.RUNTIME_GROUP_BASE
                + group_index * gray.matrix.RUNTIME_GROUP_SIZE
            )
            payload[start] = roster[commander_id]["class_id"]
            payload[start + 1] = commander_id
            payload[start + 2] = 0
            payload[start + 3] = 10
            payload[start + 6] = 4 + group_index
            payload[start + 7] = 12
            payload[start + gray.matrix.RUNTIME_LEVEL_OFFSET] = roster[commander_id][
                "level"
            ]
            for member_index in range(1, 7):
                payload[
                    start + member_index * gray.matrix.RUNTIME_MEMBER_SIZE
                ] = 0xFF
        with tempfile.TemporaryDirectory() as directory:
            gst = Path(directory) / "players.gst"
            gst.write_bytes(payload)
            coverage = gray.player_runtime_coverage(
                gst=gst,
                seed_gst=seed,
                rom_data=rom,
                scenario=8,
                manual_override=None,
            )
        self.assertEqual(coverage["status"], "pass")
        self.assertEqual(coverage["commander_ids"], commander_ids)
        self.assertEqual(
            coverage["player_runtime_groups_checked"], len(commander_ids)
        )
        self.assertTrue(coverage["all_player_runtime_identities_asserted"])

    def test_campaign_bound_summary_verifier_preserves_bounded_ui_claims(
        self,
    ) -> None:
        ui_claims = {
            "selected_allied_real_move_and_gray_sprite": True,
            "all_fixed_and_event_record_identity_fields": True,
            "every_side_bottom_status_opened": False,
            "every_side_detail_popup_opened": False,
            "every_side_combat_animation_opened": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = root / "campaign.json"
            campaign.write_text("{}\n", encoding="utf-8")
            seed = root / "s08.gst"
            seed.write_bytes(b"campaign-s08")
            seed_lineage = {
                "path": str(seed),
                "sha256": gray.sha256(seed),
                "record_sha256": "2" * 64,
                "route_index": 7,
                "source": "continuous_campaign_input",
            }
            fixed = {
                "status": "pass",
                "runtime_structural_identity_asserted": True,
                "reference_rom_sha256": gray.REFERENCE_ROM_SHA256,
                "runtime_records_checked": 4,
                "ui_surface_claims": ui_claims,
            }
            summary = {
                "status": "pass",
                "profile": "pure",
                "run_id": "unit-bound-summary",
                "rom": {"sha256": "3" * 64},
                "campaign_bound": True,
                "seed_policy": "exact_continuous_campaign_inputs",
                "campaign": {
                    "path": str(campaign),
                    "sha256": gray.sha256(campaign),
                },
                "campaign_unchanged": True,
                "scenario_seeds": {"8": seed_lineage},
                "scenario_seeds_unchanged": True,
                "scenarios": [8],
                "source_runtime_coverage": {
                    "status": "pass",
                    "scenario_rows_checked": 1,
                    "fixed_and_event_runtime_records_checked": 4,
                    "deployed_allied_runtime_records_checked": 3,
                    "selected_allied_real_moves_checked": 1,
                    "all_deployed_allied_runtime_identities_asserted": True,
                    "ui_surface_claims": ui_claims,
                    "scope_note": "structural only",
                },
                "results": [
                    {
                        "scenario": 8,
                        "status": "pass",
                        "returncode": 0,
                        "selection_policy": gray.SELECTION_POLICY,
                        "seed_policy": "preserve_exact_campaign_roster",
                        "seed_source": seed_lineage,
                        "selected_commander": {
                            "commander_id": 7,
                            "class_id": 4,
                        },
                        "fixed_record_runtime_coverage": fixed,
                        "player_runtime_coverage": {
                            "status": "pass",
                            "player_runtime_groups_checked": 3,
                            "all_player_runtime_identities_asserted": True,
                        },
                    }
                ],
            }
            report = gray_parallel.verify_summary_contract(
                summary,
                expected_profile="pure",
                expected_run_id="unit-bound-summary",
                expected_rom_sha256="3" * 64,
            )
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["scenarios_checked"], 1)
            self.assertEqual(report["fixed_and_event_runtime_records_checked"], 4)
            self.assertEqual(report["deployed_allied_runtime_records_checked"], 3)
            self.assertFalse(
                report["ui_surface_claims"]["every_side_combat_animation_opened"]
            )

            overstated = json.loads(json.dumps(summary))
            overstated["source_runtime_coverage"]["ui_surface_claims"][
                "every_side_combat_animation_opened"
            ] = True
            with self.assertRaisesRegex(ValueError, "coverage contract changed"):
                gray_parallel.verify_summary_contract(
                    overstated,
                    expected_profile="pure",
                    expected_run_id="unit-bound-summary",
                    expected_rom_sha256="3" * 64,
                )

    def test_original_keith_lord_gray_payload_uses_live_stock_sprite(self) -> None:
        data = PURE_RELEASE_ROM.read_bytes()
        source_record, sprite_id, payload, source_kind = (
            gray.expected_commander_gray_payload(data, 7, 0x04)
        )
        self.assertEqual(source_kind, "stock")
        self.assertEqual(sprite_id, 0x004E)
        self.assertEqual(
            source_record,
            gray.builder.commander_sprite_record_offset(
                data,
                7,
                0x04,
            ),
        )
        self.assertEqual(len(payload), gray.GRAY_VRAM_BYTES)

    def test_normal_keith_lord_gray_payload_uses_expanded_custom_sprite(self) -> None:
        data = (
            ROOT / "roms/builds/Langrisser II (Korean Normal v1.3.7).md"
        ).read_bytes()
        mask_offset, sprite_id, payload, source_kind = (
            gray.expected_commander_gray_payload(data, 7, 0x04)
        )
        release_record = gray.builder.commander_sprite_record_offset(
            data, 7, 0x04
        )
        self.assertEqual(
            gray.builder.be16(data, release_record + 1),
            sprite_id,
        )
        self.assertEqual(source_kind, "custom")
        self.assertEqual(sprite_id, 0x5808)
        first_custom_id = min(
            gray.builder.custom_map_sprite_gray_source_map(
                gray.builder.IN_ROM.read_bytes()
            )
        )
        self.assertEqual(
            mask_offset,
            gray.builder.MAP_SPRITE_GRAY_CUSTOM_MASK_TABLE
            + (sprite_id - first_custom_id)
            * gray.builder.MAP_SPRITE_GRAY_SOURCE_MASK_BYTES,
        )
        self.assertEqual(len(payload), gray.GRAY_VRAM_BYTES)

    def test_custom_archmage_gray_payload_comes_from_release_rom_mask(self) -> None:
        data = HARD_RELEASE_ROM.read_bytes()
        mask_offset, sprite_id, payload, source_kind = (
            gray.expected_commander_gray_payload(data, 1, 0x14)
        )
        self.assertEqual(source_kind, "custom")
        self.assertEqual(len(payload), gray.GRAY_VRAM_BYTES)
        self.assertTrue(any(payload))
        source_mask = data[
            mask_offset:
            mask_offset + gray.builder.MAP_SPRITE_GRAY_SOURCE_MASK_BYTES
        ]
        self.assertEqual(payload, gray.expand_gray_source_mask(source_mask))
        self.assertIn(
            (1, 0x14, sprite_id),
            gray.builder.AI_CLASS_MAP_SPRITE_SPECS,
        )


if __name__ == "__main__":
    unittest.main()

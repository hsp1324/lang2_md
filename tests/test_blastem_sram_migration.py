from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from tools.run_blastem_sequence import (
    JP_DEFAULT_HERO_NAME,
    JP_DEFAULT_HERO_DIALOGUE_NAME,
    GST_WORK_RAM_FILE_OFFSET,
    KO_DEFAULT_HERO_NAME,
    MANUAL_SLOT_CHECKSUM_OFFSET,
    MANUAL_SLOT_COMMANDER_CLASS_OFFSET,
    MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET,
    MANUAL_SLOT_COMMANDER_LEVEL_OFFSET,
    MANUAL_SLOT_COMMANDER_RECORD_SIZE,
    MANUAL_SLOT_COMMANDER_ROSTER_OFFSET,
    MANUAL_SLOT_HERO_DIALOGUE_NAME_OFFSET,
    MANUAL_SLOT_HERO_NAME_OFFSET,
    MANUAL_SLOT_WORK_RAM_SEGMENTS,
    SEQUENCES,
    SRAM_FORMAT_MARKER,
    SRAM_FORMAT_MARKER_OFFSET,
    SRAM_VALID_FLAGS_OFFSET,
    manual_slot_checksum,
    manual_slot_scenario_number,
    migrate_scenario_select_default_name,
    patch_manual_slot_commander_progress,
    recover_manual_slot_from_gst,
    running_blastem_pids,
    scenario_select_entry_keys,
    scenario_select_keys,
    terminate_blastem_processes,
)


class BlastEmSramMigrationTests(unittest.TestCase):
    KO_DIALOGUE_NAME = bytes.fromhex("70 01 70 02 FF FF FF FF FF FF")

    def make_sram(self) -> tuple[bytearray, int]:
        data = bytearray(0x2000)
        base = 0x194E
        start = base + MANUAL_SLOT_HERO_NAME_OFFSET
        data[start : start + len(JP_DEFAULT_HERO_NAME)] = JP_DEFAULT_HERO_NAME
        dialogue_start = base + MANUAL_SLOT_HERO_DIALOGUE_NAME_OFFSET
        data[
            dialogue_start : dialogue_start + len(JP_DEFAULT_HERO_DIALOGUE_NAME)
        ] = JP_DEFAULT_HERO_DIALOGUE_NAME
        checksum = manual_slot_checksum(data, base)
        offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
        data[offset : offset + 2] = checksum.to_bytes(2, "big")
        return data, base

    def test_migrates_exact_japanese_default_and_updates_checksum(self):
        data, base = self.make_sram()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(data)
            self.assertEqual(
                migrate_scenario_select_default_name(path, self.KO_DIALOGUE_NAME),
                1,
            )
            migrated = path.read_bytes()

        start = base + MANUAL_SLOT_HERO_NAME_OFFSET
        self.assertEqual(
            migrated[start : start + len(KO_DEFAULT_HERO_NAME)],
            KO_DEFAULT_HERO_NAME,
        )
        dialogue_start = base + MANUAL_SLOT_HERO_DIALOGUE_NAME_OFFSET
        self.assertEqual(
            migrated[dialogue_start : dialogue_start + len(self.KO_DIALOGUE_NAME)],
            self.KO_DIALOGUE_NAME,
        )
        offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
        self.assertEqual(
            int.from_bytes(migrated[offset : offset + 2], "big"),
            manual_slot_checksum(migrated, base),
        )

    def test_rejects_invalid_slot_before_writing(self):
        data, _ = self.make_sram()
        data[0x1950] ^= 1
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "invalid checksum"):
                migrate_scenario_select_default_name(path, self.KO_DIALOGUE_NAME)
            self.assertEqual(path.read_bytes(), data)

    def test_finishes_partially_migrated_default_name(self):
        data, base = self.make_sram()
        start = base + MANUAL_SLOT_HERO_NAME_OFFSET
        data[start : start + len(KO_DEFAULT_HERO_NAME)] = KO_DEFAULT_HERO_NAME
        offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
        data[offset : offset + 2] = manual_slot_checksum(data, base).to_bytes(2, "big")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(data)
            self.assertEqual(
                migrate_scenario_select_default_name(path, self.KO_DIALOGUE_NAME),
                1,
            )
            migrated = path.read_bytes()

        dialogue_start = base + MANUAL_SLOT_HERO_DIALOGUE_NAME_OFFSET
        self.assertEqual(
            migrated[dialogue_start : dialogue_start + len(self.KO_DIALOGUE_NAME)],
            self.KO_DIALOGUE_NAME,
        )
        self.assertEqual(
            int.from_bytes(migrated[offset : offset + 2], "big"),
            manual_slot_checksum(migrated, base),
        )

    def test_leaves_custom_dialogue_name_untouched(self):
        data, _ = self.make_sram()
        dialogue_start = 0x194E + MANUAL_SLOT_HERO_DIALOGUE_NAME_OFFSET
        data[dialogue_start : dialogue_start + 10] = bytes.fromhex(
            "70 03 70 04 FF FF FF FF FF FF"
        )
        checksum_offset = 0x194E + MANUAL_SLOT_CHECKSUM_OFFSET
        data[checksum_offset : checksum_offset + 2] = manual_slot_checksum(
            data, 0x194E
        ).to_bytes(2, "big")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(data)
            self.assertEqual(
                migrate_scenario_select_default_name(path, self.KO_DIALOGUE_NAME),
                0,
            )
            self.assertEqual(path.read_bytes(), data)

    def test_recovers_manual_slot_from_gst_work_ram(self):
        record = bytearray(0x1A6)
        record[:2] = (2).to_bytes(2, "big")
        name_start = MANUAL_SLOT_HERO_NAME_OFFSET
        record[name_start : name_start + len(KO_DEFAULT_HERO_NAME)] = (
            KO_DEFAULT_HERO_NAME
        )
        gst_size = max(
            GST_WORK_RAM_FILE_OFFSET + address + size
            for address, size in MANUAL_SLOT_WORK_RAM_SEGMENTS
        )
        gst = bytearray(gst_size)
        record_offset = 0
        for address, size in MANUAL_SLOT_WORK_RAM_SEGMENTS:
            start = GST_WORK_RAM_FILE_OFFSET + address
            gst[start : start + size] = record[record_offset : record_offset + size]
            record_offset += size

        with TemporaryDirectory() as directory:
            gst_path = Path(directory) / "scenario2.gst"
            sram_path = Path(directory) / "save.sram"
            gst_path.write_bytes(gst)
            self.assertIsNone(recover_manual_slot_from_gst(gst_path, sram_path))
            recovered = sram_path.read_bytes()

        base = 0x194E
        self.assertEqual(recovered[base : base + len(record)], record)
        checksum_offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
        self.assertEqual(
            int.from_bytes(recovered[checksum_offset : checksum_offset + 2], "big"),
            manual_slot_checksum(recovered, base),
        )
        self.assertEqual(
            int.from_bytes(
                recovered[SRAM_VALID_FLAGS_OFFSET : SRAM_VALID_FLAGS_OFFSET + 2],
                "big",
            ),
            0x0002,
        )
        self.assertEqual(
            int.from_bytes(
                recovered[
                    SRAM_FORMAT_MARKER_OFFSET : SRAM_FORMAT_MARKER_OFFSET + 2
                ],
                "big",
            ),
            SRAM_FORMAT_MARKER,
        )

    def test_recovery_rejects_unknown_existing_sram_format(self):
        record = bytearray(0x1A6)
        record[:2] = (2).to_bytes(2, "big")
        name_start = MANUAL_SLOT_HERO_NAME_OFFSET
        record[name_start : name_start + len(KO_DEFAULT_HERO_NAME)] = (
            KO_DEFAULT_HERO_NAME
        )
        gst = bytearray(
            max(
                GST_WORK_RAM_FILE_OFFSET + address + size
                for address, size in MANUAL_SLOT_WORK_RAM_SEGMENTS
            )
        )
        record_offset = 0
        for address, size in MANUAL_SLOT_WORK_RAM_SEGMENTS:
            start = GST_WORK_RAM_FILE_OFFSET + address
            gst[start : start + size] = record[record_offset : record_offset + size]
            record_offset += size

        with TemporaryDirectory() as directory:
            gst_path = Path(directory) / "scenario2.gst"
            sram_path = Path(directory) / "save.sram"
            gst_path.write_bytes(gst)
            sram = bytearray(0x2000)
            sram[
                SRAM_FORMAT_MARKER_OFFSET : SRAM_FORMAT_MARKER_OFFSET + 2
            ] = (0x1234).to_bytes(2, "big")
            sram_path.write_bytes(sram)
            with self.assertRaisesRegex(ValueError, "unexpected format marker"):
                recover_manual_slot_from_gst(gst_path, sram_path)
            self.assertEqual(sram_path.read_bytes(), sram)

    def test_recovery_rejects_record_without_hero_terminator(self):
        first_address, first_size = MANUAL_SLOT_WORK_RAM_SEGMENTS[0]
        record_start = GST_WORK_RAM_FILE_OFFSET + first_address
        gst = bytearray(
            max(
                GST_WORK_RAM_FILE_OFFSET + address + size
                for address, size in MANUAL_SLOT_WORK_RAM_SEGMENTS
            )
        )
        name_start = record_start + MANUAL_SLOT_HERO_NAME_OFFSET
        gst[name_start : name_start + len(JP_DEFAULT_HERO_NAME)] = b"ABCDEF"
        with TemporaryDirectory() as directory:
            gst_path = Path(directory) / "invalid.gst"
            gst_path.write_bytes(gst)
            with self.assertRaisesRegex(ValueError, "no hero-name terminator"):
                recover_manual_slot_from_gst(
                    gst_path, Path(directory) / "save.sram"
                )

    def test_patches_valid_commander_progress_and_updates_checksum(self):
        data, base = self.make_sram()
        data[base : base + 2] = (2).to_bytes(2, "big")
        record = base + MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
        data[record + MANUAL_SLOT_COMMANDER_CLASS_OFFSET] = 1
        data[record + MANUAL_SLOT_COMMANDER_LEVEL_OFFSET] = 1
        data[record + MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET] = 0
        data[
            SRAM_FORMAT_MARKER_OFFSET : SRAM_FORMAT_MARKER_OFFSET + 2
        ] = SRAM_FORMAT_MARKER.to_bytes(2, "big")
        data[SRAM_VALID_FLAGS_OFFSET : SRAM_VALID_FLAGS_OFFSET + 2] = (
            2
        ).to_bytes(2, "big")
        checksum_offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
        data[checksum_offset : checksum_offset + 2] = manual_slot_checksum(
            data, base
        ).to_bytes(2, "big")

        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(data)
            old = patch_manual_slot_commander_progress(
                path, 1, 9, 16, expected_class=1
            )
            patched = path.read_bytes()

        self.assertEqual(old, (1, 1, 0))
        self.assertEqual(
            patched[record + MANUAL_SLOT_COMMANDER_LEVEL_OFFSET], 9
        )
        self.assertEqual(
            patched[record + MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET], 16
        )
        self.assertEqual(
            int.from_bytes(patched[checksum_offset : checksum_offset + 2], "big"),
            manual_slot_checksum(patched, base),
        )
        changed = {
            index for index, (before, after) in enumerate(zip(data, patched))
            if before != after
        }
        self.assertEqual(
            changed,
            {
                record + MANUAL_SLOT_COMMANDER_LEVEL_OFFSET,
                record + MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET,
                checksum_offset,
                checksum_offset + 1,
            },
        )

    def test_commander_progress_uses_24_byte_roster_records(self):
        self.assertEqual(MANUAL_SLOT_COMMANDER_RECORD_SIZE, 0x18)

    def test_commander_progress_rejects_invalid_source_class(self):
        data, base = self.make_sram()
        data[base : base + 2] = (2).to_bytes(2, "big")
        data[
            SRAM_FORMAT_MARKER_OFFSET : SRAM_FORMAT_MARKER_OFFSET + 2
        ] = SRAM_FORMAT_MARKER.to_bytes(2, "big")
        data[SRAM_VALID_FLAGS_OFFSET : SRAM_VALID_FLAGS_OFFSET + 2] = (
            2
        ).to_bytes(2, "big")
        checksum_offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
        data[checksum_offset : checksum_offset + 2] = manual_slot_checksum(
            data, base
        ).to_bytes(2, "big")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "class changed"):
                patch_manual_slot_commander_progress(
                    path, 1, 9, 16, expected_class=1
                )
            self.assertEqual(path.read_bytes(), data)


class BlastEmScenarioSelectTests(unittest.TestCase):
    def test_load_screen_waits_for_transition_before_selector_input(self):
        self.assertEqual(SEQUENCES["load-screen"][-1], "c:4.0")

    def test_launch_only_sends_no_game_input(self):
        self.assertEqual(SEQUENCES["launch-only"], [])

    def test_selector_cheat_uses_short_verified_key_intervals(self):
        keys = scenario_select_entry_keys()
        cheat_start = keys.index("left@0.12:0.05")
        self.assertEqual(
            keys[cheat_start : cheat_start + 4],
            [
                "left@0.12:0.05",
                "right@0.12:0.05",
                "start@0.12:0.05",
                "c@0.12:2.0",
            ],
        )
        self.assertEqual(keys[-1], "c@0.12:2.0")

    def test_selector_entry_stops_before_movement_or_confirmation(self):
        keys = scenario_select_entry_keys()
        self.assertNotIn("down:0.08", keys)
        self.assertNotIn("up:0.08", keys)
        self.assertNotEqual(keys[-1], "c:4.0")

    def test_selector_target_adds_movement_and_confirmation(self):
        keys = scenario_select_keys(27)
        self.assertEqual(keys.count("down:0.08"), 26)
        self.assertEqual(keys[-1], "c:4.0")

    def test_selector_movement_is_relative_to_saved_scenario(self):
        self.assertNotIn("down:0.08", scenario_select_keys(2, 2))
        self.assertNotIn("up:0.08", scenario_select_keys(2, 2))
        self.assertEqual(scenario_select_keys(1, 2).count("up:0.08"), 1)
        self.assertEqual(scenario_select_keys(4, 2).count("down:0.08"), 2)

    def test_reads_valid_manual_slot_scenario_number(self):
        data = bytearray(0x2000)
        data[
            SRAM_FORMAT_MARKER_OFFSET : SRAM_FORMAT_MARKER_OFFSET + 2
        ] = SRAM_FORMAT_MARKER.to_bytes(2, "big")
        base = 0x194E
        data[base : base + 2] = (2).to_bytes(2, "big")
        checksum_offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
        data[checksum_offset : checksum_offset + 2] = manual_slot_checksum(
            data, base
        ).to_bytes(2, "big")
        data[SRAM_VALID_FLAGS_OFFSET : SRAM_VALID_FLAGS_OFFSET + 2] = (
            2
        ).to_bytes(2, "big")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(data)
            self.assertEqual(manual_slot_scenario_number(path), 2)

    def test_rejects_manual_slot_without_sram_format_marker(self):
        data = bytearray(0x2000)
        base = 0x194E
        data[base : base + 2] = (2).to_bytes(2, "big")
        checksum_offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
        data[checksum_offset : checksum_offset + 2] = manual_slot_checksum(
            data, base
        ).to_bytes(2, "big")
        data[SRAM_VALID_FLAGS_OFFSET : SRAM_VALID_FLAGS_OFFSET + 2] = (
            2
        ).to_bytes(2, "big")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "invalid format marker"):
                manual_slot_scenario_number(path)

    def test_selector_rejects_out_of_range_scenario(self):
        for scenario_number in (0, 32):
            with self.assertRaisesRegex(ValueError, "1..31"):
                scenario_select_keys(scenario_number)


class BlastEmProcessTests(unittest.TestCase):
    def write_process(self, root: Path, pid: int, name: str, state: str) -> None:
        process = root / str(pid)
        process.mkdir()
        (process / "comm").write_text(name + "\n", encoding="ascii")
        (process / "stat").write_text(
            f"{pid} ({name}) {state} 1 2 3\n", encoding="ascii"
        )

    def test_running_pids_ignore_zombies_and_other_processes(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_process(root, 30, "blastem", "S")
            self.write_process(root, 20, "blastem", "Z")
            self.write_process(root, 10, "python3", "R")
            self.assertEqual(running_blastem_pids(root), [30])

    @mock.patch("tools.run_blastem_sequence.time.sleep")
    @mock.patch("tools.run_blastem_sequence.os.kill")
    @mock.patch("tools.run_blastem_sequence.running_blastem_pids")
    def test_termination_escalates_survivor_to_sigkill(
        self, running: mock.Mock, kill: mock.Mock, sleep: mock.Mock
    ) -> None:
        running.side_effect = [[42], [42], [42], [42], [], []]
        with mock.patch(
            "tools.run_blastem_sequence.time.monotonic",
            side_effect=[0.0, 0.1, 3.0, 3.0, 3.1],
        ):
            terminate_blastem_processes(timeout=2.0)
        self.assertEqual(
            kill.call_args_list,
            [mock.call(42, 15), mock.call(42, 9)],
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import argparse
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from tools import build_fresh_s1_runtime_seed as seed


class FreshScenarioOneRuntimeSeedTests(unittest.TestCase):
    def snapshot(self) -> dict[str, object]:
        return {
            "scenario": 1,
            "commanders": [
                {
                    "commander_id": commander_id,
                    "class_id": values["class_id"],
                    "level": values["level"],
                    "experience": values["experience"],
                }
                for commander_id, values in seed.EXPECTED_ROSTER.items()
            ],
        }

    def test_roster_lock_requires_scenario_one_and_exact_progress(self) -> None:
        rows = seed.locked_roster(self.snapshot())
        self.assertEqual(set(rows), {7, 9, 10})
        self.assertEqual(rows[9]["class_id"], 0x07)
        self.assertEqual(rows[9]["experience"], 15)

        wrong_scenario = self.snapshot()
        wrong_scenario["scenario"] = 2
        with self.assertRaisesRegex(ValueError, "not 1"):
            seed.locked_roster(wrong_scenario)

        wrong_progress = self.snapshot()
        wrong_progress["commanders"][0]["level"] = 11
        with self.assertRaisesRegex(ValueError, "commander 7 level"):
            seed.locked_roster(wrong_progress)

    def test_roster_lock_rejects_missing_and_duplicate_rows(self) -> None:
        missing = self.snapshot()
        missing["commanders"].pop()
        with self.assertRaisesRegex(ValueError, "missing commander IDs 10"):
            seed.locked_roster(missing)

        duplicate = self.snapshot()
        duplicate["commanders"].append(dict(duplicate["commanders"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate commander 7"):
            seed.locked_roster(duplicate)

    def test_new_game_detector_requires_gold_menu_panel(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plain_path = Path(directory) / "plain.png"
            menu_path = Path(directory) / "menu.png"
            plain = Image.new("RGB", (320, 240), (0, 0, 100))
            menu = plain.copy()
            left, top, right, bottom = seed.NEW_GAME_PANEL_BOX
            for x in range(left, right):
                for y in (*range(top, top + 3), *range(bottom - 3, bottom)):
                    menu.putpixel((x, y), (210, 160, 20))
            for y in range(top, bottom):
                for x in (*range(left, left + 3), *range(right - 3, right)):
                    menu.putpixel((x, y), (210, 160, 20))
            for x in range(130, 180):
                menu.putpixel((x, 170), (255, 255, 255))
                menu.putpixel((x, 175), (255, 255, 255))
            plain.save(plain_path)
            menu.save(menu_path)
            self.assertFalse(seed.new_game_menu_visible(plain_path))
            self.assertTrue(seed.new_game_menu_visible(menu_path))

    def test_new_game_detector_rejects_wrong_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "small.png"
            Image.new("RGB", (160, 120)).save(path)
            self.assertFalse(seed.new_game_menu_visible(path))

    def test_clean_targets_must_not_preexist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            runtime = root / "runtime"
            seed.validate_clean_targets(output, runtime)
            output.mkdir()
            with self.assertRaisesRegex(FileExistsError, "absent output/runtime"):
                seed.validate_clean_targets(output, runtime)

    def test_sha_parser_and_expected_hash_guard(self) -> None:
        self.assertEqual(seed.valid_sha256("A" * 64), "a" * 64)
        with self.assertRaises(argparse.ArgumentTypeError):
            seed.valid_sha256("xyz")
        with tempfile.TemporaryDirectory() as directory:
            rom = Path(directory) / "candidate.md"
            rom.write_bytes(b"candidate")
            actual = seed.verify_rom_hash(rom, None)
            self.assertEqual(len(actual), 64)
            with self.assertRaisesRegex(ValueError, "expected"):
                seed.verify_rom_hash(rom, "0" * 64)

    def test_plan_records_clean_runtime_and_required_evidence(self) -> None:
        plan = seed.build_plan(
            profile="normal",
            rom=Path("candidate.md"),
            rom_sha256="1" * 64,
            output=Path("output/normal/run"),
            runtime_home=Path("runtime/fresh-s1-normal-run"),
            display=":795",
            run_id="run",
        )
        self.assertEqual(plan["rom"]["sha256"], "1" * 64)
        self.assertIsNone(plan["isolation"]["manual_sram_seed"])
        self.assertIsNone(plan["isolation"]["manual_gst_seed"])
        self.assertIn("title", plan["required_evidence"])
        self.assertIn("new_game_menu", plan["required_evidence"])
        self.assertIn("scenario_1_gst", plan["required_evidence"])
        self.assertEqual(plan["expected_roster"][9]["class_id"], 0x07)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from tools.run_blastem_sequence import (
    battle_command_menu_visible,
    game_over_visible,
    preparation_screen_visible,
)


class BlastemCommandDetectorTests(unittest.TestCase):
    def test_rejects_solid_blue_water_map(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "water.png"
            frame = Image.new("RGB", (320, 240), (0, 0, 0))
            frame.paste((0, 0, 146), (15, 25, 95, 110))
            frame.paste((0, 0, 119), (0, 195, 320, 235))
            frame.save(path)
            self.assertFalse(battle_command_menu_visible(path))

    def test_accepts_framed_dark_command_panel(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "command.png"
            frame = Image.new("RGB", (320, 240), (0, 0, 0))
            # The detector only needs the stable panel proportions, not a
            # screenshot fixture tied to one scenario or emulator scale.
            frame.paste((0, 0, 119), (15, 25, 65, 105))
            frame.paste((255, 255, 255), (20, 35, 30, 65))
            frame.paste((119, 87, 87), (65, 25, 95, 105))
            frame.paste((180, 130, 20), (95, 42, 101, 145))
            frame.paste((0, 0, 119), (0, 195, 154, 235))
            frame.save(path)
            self.assertTrue(battle_command_menu_visible(path))

    def test_rejects_preparation_panel_with_too_much_solid_blue(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "preparation.png"
            frame = Image.new("RGB", (320, 240), (0, 0, 0))
            frame.paste((0, 0, 119), (15, 25, 65, 105))
            frame.paste((119, 87, 87), (65, 25, 95, 105))
            frame.paste((0, 0, 119), (0, 195, 167, 235))
            frame.save(path)
            self.assertFalse(battle_command_menu_visible(path))

    def test_rejects_map_roofs_and_unit_selection_highlight(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "map-selection.png"
            frame = Image.new("RGB", (320, 240), (0, 0, 0))
            frame.paste((0, 70, 150), (15, 25, 45, 105))
            frame.paste((0, 0, 119), (60, 25, 95, 105))
            frame.paste((0, 0, 119), (0, 195, 154, 235))
            frame.save(path)
            self.assertFalse(battle_command_menu_visible(path))

    def test_accepts_sparse_four_row_panel_at_960_by_720(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "command-960.png"
            frame = Image.new("RGB", (320, 240), (0, 128, 0))
            # Match the shifted, slightly wider four-row panel observed in the
            # Scenario 9 960x720 run. Its text occupies only about four percent
            # of the old command-interior crop.
            frame.paste((0, 0, 119), (40, 42, 100, 145))
            frame.paste((180, 130, 20), (100, 42, 105, 145))
            frame.paste((255, 255, 255), (43, 52, 50, 74))
            frame.paste((0, 0, 119), (0, 195, 152, 235))
            frame = frame.resize((960, 720), Image.Resampling.NEAREST)
            frame.save(path)
            self.assertTrue(battle_command_menu_visible(path))

    def test_rejects_wide_result_panel_after_relaxed_text_threshold(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "result-960.png"
            frame = Image.new("RGB", (320, 240), (0, 0, 119))
            frame.paste((255, 255, 255), (40, 52, 48, 74))
            frame.paste((0, 0, 119), (0, 195, 152, 235))
            frame = frame.resize((960, 720), Image.Resampling.NEAREST)
            frame.save(path)
            self.assertFalse(battle_command_menu_visible(path))


class BlastemPreparationDetectorTests(unittest.TestCase):
    @staticmethod
    def make_preparation_shape(path: Path) -> Image.Image:
        frame = Image.new("RGB", (320, 240), (0, 0, 0))
        frame.paste((0, 0, 119), (10, 32, 142, 136))
        frame.paste((0, 0, 119), (145, 115, 318, 214))
        frame.paste((0, 0, 119), (10, 214, 142, 239))
        frame.paste((180, 130, 20), (141, 32, 147, 215))
        frame.save(path)
        return frame

    def test_accepts_preparation_panel_shape(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "preparation.png"
            self.make_preparation_shape(path)
            self.assertTrue(preparation_screen_visible(path))

    def test_rejects_briefing_without_money_panel(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "briefing.png"
            frame = self.make_preparation_shape(path)
            frame.paste((0, 0, 0), (10, 214, 142, 239))
            frame.save(path)
            self.assertFalse(preparation_screen_visible(path))

    def test_rejects_battle_panel_without_gold_divider(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "battle.png"
            frame = self.make_preparation_shape(path)
            frame.paste((0, 0, 119), (141, 32, 147, 215))
            frame.save(path)
            self.assertFalse(preparation_screen_visible(path))


class BlastemGameOverDetectorTests(unittest.TestCase):
    def test_accepts_centered_game_over_panel(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "game-over.png"
            frame = Image.new("RGB", (320, 240), (0, 0, 0))
            frame.paste((0, 0, 119), (24, 97, 294, 170))
            frame.paste((255, 255, 255), (100, 124, 220, 139))
            frame.save(path)
            self.assertTrue(game_over_visible(path))

    def test_rejects_top_aligned_dialogue(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "dialogue.png"
            frame = Image.new("RGB", (320, 240), (0, 0, 0))
            frame.paste((0, 0, 119), (24, 97, 294, 170))
            frame.paste((255, 255, 255), (36, 104, 180, 116))
            frame.save(path)
            self.assertFalse(game_over_visible(path))

if __name__ == "__main__":
    unittest.main()

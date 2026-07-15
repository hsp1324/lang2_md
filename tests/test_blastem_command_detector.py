from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from tools.run_blastem_sequence import battle_command_menu_visible


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
            frame.paste((119, 87, 87), (65, 25, 95, 105))
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


if __name__ == "__main__":
    unittest.main()

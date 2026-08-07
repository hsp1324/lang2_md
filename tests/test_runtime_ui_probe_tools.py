from pathlib import Path
import tempfile
import unittest

from PIL import Image

from scripts import build_korean_jp_probe as builder
from tools import capture_magic_application as magic
from tools import run_invalid_move_marker_probe as invalid
from tools import run_start_menu_roundtrip_probe as start_menu


class RuntimeUiProbeToolTests(unittest.TestCase):
    def test_prebuilt_magic_probe_is_copied_without_mutation(self) -> None:
        data = bytearray(0x400)
        data[0x18E:0x190] = bytes.fromhex("98 BA")
        probe, checksum = magic.prepare_probe(
            bytes(data), None, prebuilt=True, stock_magic=True
        )
        self.assertEqual(probe, data)
        self.assertEqual(checksum, 0x98BA)

    def test_start_menu_crop_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.png"
            first = root / "first.png"
            second = root / "second.png"
            Image.new("RGB", (320, 240), (12, 34, 56)).save(source)
            start_menu.crop(source, first)
            start_menu.crop(source, second)
            with Image.open(first) as cropped:
                self.assertEqual(cropped.size, (130, 130))
            self.assertEqual(start_menu.sha256(first), start_menu.sha256(second))

    def test_invalid_marker_owns_eight_tiles_outside_dynamic_glyph_pool(self) -> None:
        marker = set(builder.BATTLE_INVALID_TARGET_CURSOR_TILES)
        dynamic = set(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS)
        self.assertEqual(len(marker), 8)
        self.assertTrue(dynamic.isdisjoint(marker))
        self.assertEqual(
            {route[0] for route in invalid.ROUTES},
            {"up", "down", "left", "right"},
        )
        self.assertTrue(all(len(route) == 16 for route in invalid.ROUTES))


if __name__ == "__main__":
    unittest.main()

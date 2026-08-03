from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.analyze_preparation_vram_ownership import (
    load_gst,
    sprite_referenced_tiles,
)


ROOT = Path(__file__).resolve().parents[1]
MAGIC_TARGET_GST = (
    ROOT
    / "captures/analysis/b104_overlay_probe2_s12/fireball_target_enemy.gst"
)


class BattleOverlayVramOwnershipTests(unittest.TestCase):
    def test_magic_target_cursor_does_not_share_battle_glyph_tiles(self) -> None:
        state = load_gst(MAGIC_TARGET_GST)
        target_cursor = set(range(0x07CE, 0x07D2))
        self.assertTrue(target_cursor <= sprite_referenced_tiles(state))
        self.assertTrue(
            set(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS).isdisjoint(target_cursor)
        )

    def test_preparation_keeps_its_independent_proven_destinations(self) -> None:
        self.assertEqual(
            builder.BYTE_UI_PREP_DYNAMIC_MAP_TILE_IDS[4],
            0x07D0,
        )
        self.assertEqual(
            builder.BYTE_UI_PREP_DYNAMIC_MAP_TILE_IDS[6],
            0x07D1,
        )


if __name__ == "__main__":
    unittest.main()

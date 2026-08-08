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

    def test_class_change_exit_restores_every_shared_battle_overlay_tile(self) -> None:
        source = (ROOT / "roms/original/Langrisser II (Japan).md").read_bytes()
        production = (ROOT / "roms/builds/Langrisser II (Korean).md").read_bytes()
        payload = builder.battle_overlay_source_payload(source)
        self.assertEqual(len(payload), 0x04E0)
        restored_tiles = set()
        for tile_id, source_offset, tile_count in builder.BATTLE_OVERLAY_SOURCE_SEGMENTS:
            self.assertNotEqual(
                payload[source_offset : source_offset + tile_count * 32],
                b"\x00" * (tile_count * 32),
            )
            restored_tiles.update(range(tile_id, tile_id + tile_count))
        self.assertEqual(
            restored_tiles,
            set(builder.BATTLE_TARGET_CURSOR_TILES)
            | set(builder.BATTLE_INVALID_TARGET_CURSOR_TILES)
            | set(builder.BATTLE_MAGIC_CONFIRM_CURSOR_TILES),
        )
        self.assertTrue(
            restored_tiles
            & set(builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS),
            "the regression requires preparation glyphs to share overlay VRAM",
        )

        routine = builder.build_battle_overlay_restore_routine()
        self.assertTrue(routine.startswith(bytes.fromhex("48 E7 FF FE")))
        self.assertTrue(routine.endswith(bytes.fromhex("4C DF 7F FF 4E 75")))
        expected_raw = b"".join(
            payload[source_offset : source_offset + tile_count * 32]
            for _tile_id, source_offset, tile_count
            in builder.BATTLE_OVERLAY_SOURCE_SEGMENTS
        )
        self.assertEqual(
            production[
                builder.BATTLE_OVERLAY_RAW_DATA :
                builder.BATTLE_OVERLAY_RAW_DATA + len(expected_raw)
            ],
            expected_raw,
        )
        self.assertEqual(
            production[
                builder.BATTLE_OVERLAY_RESTORE_ROUTINE :
                builder.BATTLE_OVERLAY_RESTORE_ROUTINE + len(routine)
            ],
            routine,
        )
        wrapper = builder.build_join_class_choice_level_wrapper()
        self.assertIn(
            bytes.fromhex("4E B9")
            + builder.BATTLE_OVERLAY_RESTORE_ROUTINE.to_bytes(4, "big"),
            wrapper,
        )


if __name__ == "__main__":
    unittest.main()

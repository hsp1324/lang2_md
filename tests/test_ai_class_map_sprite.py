import json
import unittest

from PIL import Image

from scripts import build_korean_jp_probe as builder


class AiClassMapSpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original = bytearray(builder.IN_ROM.read_bytes())
        cls.expanded = bytearray(cls.original)
        builder.expand_rom(cls.expanded)
        cls.patched = bytearray(cls.expanded)
        builder.patch_ai_class_map_sprites(cls.patched)
        cls.manifest = json.loads(
            (
                builder.AI_CLASS_MAP_SPRITE_ASSET_ROOT
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )

    def test_reviewed_target_inventory_is_stable(self) -> None:
        self.assertEqual(len(builder.AI_CLASS_MAP_SPRITE_SPECS), 40)
        self.assertEqual(
            len(
                {
                    custom_sprite_id
                    for _, _, custom_sprite_id in (
                        builder.AI_CLASS_MAP_SPRITE_SPECS
                    )
                }
            ),
            40,
        )
        self.assertEqual(
            {
                class_id
                for _, class_id, _ in builder.AI_CLASS_MAP_SPRITE_SPECS
            },
            {0x04, 0x0B, 0x11, 0x13, 0x14, 0x16},
        )

    def test_every_promoted_asset_is_reviewed_as_redesigned(self) -> None:
        for commander_id, class_id, _ in (
            builder.AI_CLASS_MAP_SPRITE_SPECS
        ):
            row = self.manifest["commanders"][str(commander_id)][
                "classes"
            ][str(class_id)]
            self.assertTrue(row["redesigned"])
            self.assertFalse(row["pending_redesign"])
            self.assertEqual(
                row["file"],
                f"{commander_id}/{class_id:02X}.png",
            )

    def test_only_target_commander_class_records_change(self) -> None:
        target = {
            (commander_id, class_id): custom_sprite_id
            for commander_id, class_id, custom_sprite_id in (
                builder.AI_CLASS_MAP_SPRITE_SPECS
            )
        }
        for commander_id in range(1, 11):
            pointer = builder.be32(
                self.original,
                builder.COMMANDER_SPRITE_POINTER_TABLE
                + (commander_id - 1) * 4,
            )
            while self.original[pointer] != 0xFF:
                class_id = self.original[pointer]
                before = builder.be16(self.original, pointer + 1)
                after = builder.be16(self.patched, pointer + 1)
                expected = target.get((commander_id, class_id), before)
                self.assertEqual(
                    after,
                    expected,
                    (commander_id, class_id),
                )
                pointer += 3

    def test_both_frames_match_the_quantized_accepted_asset(self) -> None:
        for commander_id, class_id, custom_sprite_id in (
            builder.AI_CLASS_MAP_SPRITE_SPECS
        ):
            asset = (
                builder.AI_CLASS_MAP_SPRITE_ASSET_ROOT
                / str(commander_id)
                / f"{class_id:02X}.png"
            )
            expected = builder.encode_ai_class_map_sprite(
                Image.open(asset)
            )
            self.assertTrue(any(expected))
            for frame_base in builder.MAP_SPRITE_FRAME_BASES:
                offset = (
                    frame_base
                    + custom_sprite_id * builder.MAP_SPRITE_BYTES
                )
                self.assertEqual(
                    bytes(
                        self.patched[
                            offset : offset + builder.MAP_SPRITE_BYTES
                        ]
                    ),
                    expected,
                )

    def test_promoted_frames_use_blank_isolated_expansion_slots(self) -> None:
        existing = set(builder.BALD_CUSTOM_FRAME_OFFSETS)
        existing.update(builder.LOREN_CUSTOM_FRAME_OFFSETS)
        existing.update(builder.SHAMAN_CUSTOM_FRAME_OFFSETS)
        for offsets in builder.SHAMAN_COMMANDER_CUSTOM_FRAME_OFFSETS.values():
            existing.update(offsets)
        for spec in builder.PAIRED_NPC_MAP_SPRITES.values():
            custom_sprite_id = int(spec["custom_sprite_id"])
            existing.update(
                frame_base
                + custom_sprite_id * builder.MAP_SPRITE_BYTES
                for frame_base in builder.MAP_SPRITE_FRAME_BASES
            )

        promoted = set()
        for _, _, custom_sprite_id in builder.AI_CLASS_MAP_SPRITE_SPECS:
            for frame_base in builder.MAP_SPRITE_FRAME_BASES:
                offset = (
                    frame_base
                    + custom_sprite_id * builder.MAP_SPRITE_BYTES
                )
                promoted.add(offset)
                self.assertLessEqual(
                    offset + builder.MAP_SPRITE_BYTES,
                    0x300000,
                )
                self.assertTrue(
                    all(
                        value == 0xFF
                        for value in self.expanded[
                            offset : offset + builder.MAP_SPRITE_BYTES
                        ]
                    )
                )
        self.assertEqual(len(promoted), 80)
        self.assertTrue(promoted.isdisjoint(existing))

    def test_patch_rejects_occupied_destination(self) -> None:
        data = bytearray(self.original)
        builder.expand_rom(data)
        _, _, custom_sprite_id = builder.AI_CLASS_MAP_SPRITE_SPECS[0]
        target = (
            builder.MAP_SPRITE_FRAME_BASES[0]
            + custom_sprite_id * builder.MAP_SPRITE_BYTES
        )
        data[target] = 0
        with self.assertRaisesRegex(ValueError, "is not blank"):
            builder.patch_ai_class_map_sprites(data)


if __name__ == "__main__":
    unittest.main()

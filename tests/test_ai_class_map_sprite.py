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
        # The production build repurposes Keith/Lester's obsolete Fighter
        # map records for the new Hawk Lord and Croco Lord classes before it
        # attaches the reviewed commander-specific sprite set.
        builder.patch_join_class_choice_class_data(
            cls.patched,
            cls.original,
        )
        cls.class_data_patched = bytearray(cls.patched)
        builder.patch_ai_class_map_sprites(cls.patched)
        cls.manifest = json.loads(
            (
                builder.AI_CLASS_MAP_SPRITE_ASSET_ROOT
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )

    def test_reviewed_target_inventory_is_stable(self) -> None:
        reviewed = {
            (int(commander_id), int(class_id))
            for commander_id, commander in self.manifest[
                "commanders"
            ].items()
            for class_id, row in commander["classes"].items()
            if row["redesigned"] and not row["pending_redesign"]
        }
        promoted = {
            (commander_id, class_id)
            for commander_id, class_id, _ in (
                builder.AI_CLASS_MAP_SPRITE_SPECS
            )
        }
        self.assertEqual(len(builder.AI_CLASS_MAP_SPRITE_SPECS), 131)
        self.assertEqual(promoted, reviewed)
        self.assertEqual(
            len(
                {
                    custom_sprite_id
                    for _, _, custom_sprite_id in (
                        builder.AI_CLASS_MAP_SPRITE_SPECS
                    )
                }
            ),
            131,
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
        repurposed = {
            (7, 0x01): builder.JOIN_CLASS_CHOICE_HAWK_LORD,
            (9, 0x01): builder.JOIN_CLASS_CHOICE_CROCO_LORD,
        }
        repurposed_design = {
            (7, 0x01): 0x0F,
            (9, 0x01): 0x10,
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
                after_class_id = self.patched[pointer]
                after = builder.be16(self.patched, pointer + 1)
                expected_class_id = repurposed.get(
                    (commander_id, class_id),
                    class_id,
                )
                expected = target.get(
                    (commander_id, expected_class_id),
                    before,
                )
                design_class_id = repurposed_design.get(
                    (commander_id, class_id)
                )
                if design_class_id is not None:
                    design_record = builder.commander_sprite_record_offset(
                        self.class_data_patched,
                        commander_id,
                        design_class_id,
                    )
                    expected = builder.be16(
                        self.class_data_patched,
                        design_record + 1,
                    )
                self.assertEqual(
                    after_class_id,
                    expected_class_id,
                    (commander_id, class_id),
                )
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
            source_image = Image.open(asset)
            expected = builder.encode_ai_class_map_sprite(
                source_image,
                palette_index_overrides=(
                    builder.ai_class_map_palette_index_overrides(
                        source_image
                    )
                ),
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
                    builder.MAP_SPRITE_GRAY_CUSTOM_MASK_TABLE,
                )
                self.assertTrue(
                    all(
                        value == 0xFF
                        for value in self.expanded[
                            offset : offset + builder.MAP_SPRITE_BYTES
                        ]
                    )
                )
        self.assertEqual(
            len(promoted),
            len(builder.AI_CLASS_MAP_SPRITE_SPECS)
            * len(builder.MAP_SPRITE_FRAME_BASES),
        )
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

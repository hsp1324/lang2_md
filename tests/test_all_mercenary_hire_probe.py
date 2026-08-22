import unittest
from scripts import build_korean_jp_probe as builder
from tools import run_all_mercenary_hire_probe as probe


class AllMercenaryHireProbeTests(unittest.TestCase):
    def test_full_mask_covers_all_six_hire_pages(self) -> None:
        pages = probe.expected_pages()
        self.assertEqual(len(pages), 6)
        self.assertEqual(sum(len(page) for page in pages), 16)
        self.assertEqual(
            [[row["korean"] for row in page] for page in pages],
            [
                ["파이크", "팔랑크스", "솔저"],
                ["글래디에이터", "아머솔저", "호스맨"],
                ["헤비호스맨", "드라군", "엘프"],
                ["발리스타", "몽크", "가드맨"],
                ["머맨", "그리폰", "엔젤"],
                ["시민"],
            ],
        )

    def test_collision_class_exercises_slot_five_character(self) -> None:
        self.assertEqual(probe.DEFAULT_CLASS_ID, 0x4D)
        self.assertIn("가", probe.matrix.KOREAN_CLASS_LABELS[probe.DEFAULT_CLASS_ID])

    def test_royal_guard_does_not_overwrite_gladiator_or_angel(self) -> None:
        slots = {
            char: slot
            for slot, group in enumerate(builder.BYTE_UI_PREP_DYNAMIC_SLOT_GROUPS)
            for char in group
        }
        self.assertNotEqual(slots["가"], slots["디"])
        self.assertNotEqual(slots["가"], slots["엔"])
        self.assertEqual(
            probe.matrix.KOREAN_CLASS_LABELS[0x65],
            "글래디에이터",
        )

    def test_dynamic_glyph_payload_inventory_is_nonempty(self) -> None:
        data = bytearray(
            b"\xFF" * builder.BYTE_UI_DYNAMIC_GLYPH_TABLE_LIMIT
        )
        first = bytes(range(32))
        second = bytes(reversed(range(32)))
        start = builder.BYTE_UI_DYNAMIC_GLYPH_TABLE
        data[start:start + 32] = first
        data[start + 32:start + 64] = second
        self.assertEqual(
            probe.dynamic_glyph_payloads(bytes(data)),
            {first, second},
        )

    def test_preparation_scratch_tiles_avoid_the_whole_icon_cache(self) -> None:
        occupied = set(
            range(
                probe.MERCENARY_ICON_TILE_FIRST,
                probe.MERCENARY_ICON_TILE_LAST + 1,
            )
        )
        self.assertTrue(
            set(builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS).isdisjoint(occupied)
        )

    def test_elf_final_syllable_uses_a_preparation_scratch_tile(self) -> None:
        self.assertIn("프", builder.BYTE_UI_PREP_DYNAMIC_CHARS)
        self.assertIn("프", builder.BYTE_UI_PREP_DYNAMIC_SLOT_GROUPS[24])
        self.assertEqual(builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS[24], 0x07EB)


if __name__ == "__main__":
    unittest.main()

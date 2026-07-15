from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tests.test_ending_dialogue import name_controls, record_words


ROOT = Path(__file__).resolve().parents[1]


class EpilogueDialogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = (ROOT / builder.IN_ROM).read_bytes()
        cls.korean = (ROOT / builder.OUT_ROM).read_bytes()
        cls.rows = builder.load_epilogue_dialogue_translations(
            ROOT / builder.EPILOGUE_DIALOGUE_TRANSLATIONS
        )
        cls.inventory = builder.load_epilogue_record_inventory(
            ROOT / builder.EPILOGUE_RECORD_INVENTORY
        )
        cls.inventory_by_address = {
            int(row["address_int"]): row for row in cls.inventory
        }

    def test_all_character_and_world_outcomes_are_complete(self):
        self.assertEqual(len(self.rows), 90)
        self.assertEqual(
            {int(row["english_record"]) for row in self.rows},
            set(range(1934, 1943))
            | set(range(1910, 1919))
            | set(range(1901, 1910))
            | set(range(1943, 1952))
            | set(range(1961, 1970))
            | set(range(1952, 1961))
            | set(range(1978, 1987))
            | set(range(1925, 1934))
            | set(range(1919, 1925))
            | set(range(1970, 1978))
            | set(range(1987, 1991)),
        )

    def test_controls_page_breaks_relocated_pointers_and_glyphs(self):
        relocated_addresses = []
        expected_relocated = builder.EPILOGUE_RELOC_BASE
        for row in self.rows:
            start = int(row["address_int"])
            inventory = self.inventory_by_address[start]
            pointer_reference = int(inventory["pointer_reference_int"])
            self.assertEqual(builder.be32(self.japanese, pointer_reference), start)
            relocated = builder.be32(self.korean, pointer_reference)
            relocated_addresses.append(relocated)
            self.assertEqual(relocated, expected_relocated)
            self.assertGreaterEqual(relocated, builder.EPILOGUE_RELOC_BASE)
            self.assertLess(relocated, builder.EPILOGUE_RELOC_LIMIT)
            original = record_words(self.japanese, start)
            translated = record_words(self.korean, relocated)
            expected_relocated += len(translated) * 2
            self.assertEqual(name_controls(translated), name_controls(original))
            self.assertEqual(translated.count(0xFFFD), original.count(0xFFFD))
            index = 0
            while index < len(translated):
                word = translated[index]
                if word == 0xFFF7:
                    index += 2
                    continue
                if word in (0xFFFD, 0xFFFE, 0xFFFF, builder.SPACE_GLYPH):
                    index += 1
                    continue
                self.assertGreaterEqual(word, 0x7000, f"0x{start:06X}: 0x{word:04X}")
                index += 1
        self.assertEqual(relocated_addresses, sorted(relocated_addresses))
        self.assertEqual(len(relocated_addresses), len(set(relocated_addresses)))
        self.assertLessEqual(expected_relocated, builder.EPILOGUE_RELOC_LIMIT)

    def test_relocation_rejects_changed_pointer_or_occupied_target(self):
        rows = self.rows[:1]
        inventory = self.inventory[:1]
        glyphs = builder.collect_chars(
            builder.ending_dialogue_visible_text(str(rows[0]["text"]))
        )
        data = bytearray(self.japanese)
        builder.expand_rom(data)
        glyph_by_char = {char: 0x7000 + index for index, char in enumerate(glyphs)}

        pointer_reference = int(inventory[0]["pointer_reference_int"])
        changed_pointer = bytearray(data)
        builder.put32(changed_pointer, pointer_reference, 0)
        with self.assertRaisesRegex(ValueError, "changed before relocation"):
            builder.patch_relocated_epilogue_dialogue_records(
                changed_pointer, self.japanese, glyph_by_char, rows, inventory
            )

        occupied = bytearray(data)
        occupied[builder.EPILOGUE_RELOC_BASE] = 0
        with self.assertRaisesRegex(ValueError, "target is not empty"):
            builder.patch_relocated_epilogue_dialogue_records(
                occupied, self.japanese, glyph_by_char, rows, inventory
            )

    def test_authored_lines_fit_the_dialogue_window(self):
        for row in self.rows:
            text = str(row["text"])
            self.assertNotIn(
                "}일행",
                text,
                f"{row['address']} joins a dynamic name directly to 일행",
            )
            for page_number, page in enumerate(text.split("\f"), 1):
                lines = page.splitlines()
                self.assertLessEqual(
                    len(lines),
                    3,
                    f"{row['address']} page {page_number} has too many lines",
                )
                for line in lines:
                    visible = builder.EVENT_NAME_CONTROL_RE.sub("이름", line)
                    self.assertLessEqual(
                        len(visible), 24, f"{row['address']}: {visible!r}"
                    )


if __name__ == "__main__":
    unittest.main()

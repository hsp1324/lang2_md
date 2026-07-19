from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_ending_dialogue_probe_rom as probe_builder


ROOT = Path(__file__).resolve().parents[1]


class EndingDialogueProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.production = (ROOT / builder.OUT_ROM).read_bytes()
        cls.rows = builder.load_ending_dialogue_translations()

    def patched(self) -> tuple[bytearray, int, list[dict[str, object]]]:
        data = bytearray(self.production)
        _, pages, manifest = probe_builder.patch_probe(
            data, self.source, self.rows
        )
        return data, pages, manifest

    def test_combined_stream_matches_all_relocated_records(self):
        data, pages, manifest = self.patched()
        self.assertEqual(len(manifest), 23)
        self.assertEqual(pages, sum(row["page_count"] for row in manifest))
        self.assertEqual(
            [row["start_page"] for row in manifest],
            [
                sum(item["page_count"] for item in manifest[:index])
                for index in range(len(manifest))
            ],
        )

        for index, (row, item) in enumerate(zip(self.rows, manifest)):
            relocated = builder.be32(
                self.production, int(row["pointer_reference_int"])
            )
            original = probe_builder.read_record(
                self.production,
                relocated,
                builder.ENDING_DIALOGUE_RELOC_LIMIT,
            )
            stream_start = (
                probe_builder.ALL_DIALOGUE_STREAM_BASE
                + int(item["stream_word_offset"]) * 2
            )
            combined = [
                builder.be16(data, stream_start + word_index * 2)
                for word_index in range(int(item["stream_word_count"]))
            ]
            expected = original[:-1] + [
                0xFFFF if index == len(manifest) - 1 else 0xFFFD
            ]
            self.assertEqual(combined, expected)

    def test_probe_changes_only_pointers_stream_and_checksum(self):
        data, _, manifest = self.patched()
        stream_words = sum(int(row["stream_word_count"]) for row in manifest)
        allowed = {0x18E, 0x18F}
        allowed.update(
            range(
                probe_builder.ALL_DIALOGUE_STREAM_BASE,
                probe_builder.ALL_DIALOGUE_STREAM_BASE + stream_words * 2,
            )
        )
        for row in self.rows:
            pointer_reference = int(row["pointer_reference_int"])
            allowed.update(range(pointer_reference, pointer_reference + 4))
            self.assertEqual(
                builder.be32(data, pointer_reference),
                probe_builder.ALL_DIALOGUE_STREAM_BASE,
            )
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, allowed)

    def test_probe_checksum_is_valid(self):
        data, _, _ = self.patched()
        expected = sum(
            builder.be16(data, offset) for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(builder.be16(data, 0x18E), expected)

    def test_nonempty_stream_reservation_is_rejected(self):
        data = bytearray(self.production)
        data[probe_builder.ALL_DIALOGUE_STREAM_BASE] = 0
        with self.assertRaisesRegex(ValueError, "reservation is not empty"):
            probe_builder.patch_probe(data, self.source, self.rows)


if __name__ == "__main__":
    unittest.main()

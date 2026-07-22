from pathlib import Path
import unittest

from tools import build_title_save_probe_rom as probe_builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class TitleSaveProbeBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()
        cls.production = KO_ROM.read_bytes()

    def test_probe_changes_only_two_entry_operands_and_checksum(self):
        probe = bytearray(self.production)
        checksum = probe_builder.patch_probe(probe, self.source)
        replacement = probe_builder.TITLE_SAVE_ENTRY.to_bytes(4, "big")
        for offset in probe_builder.TITLE_LOAD_ENTRY_OPERANDS:
            self.assertEqual(probe[offset : offset + 4], replacement)
        self.assertEqual(probe[0x18E:0x190], checksum.to_bytes(2, "big"))

        allowed = set(range(0x18E, 0x190))
        for offset in probe_builder.TITLE_LOAD_ENTRY_OPERANDS:
            allowed.update(range(offset, offset + 4))
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.production, probe))
            if before != after
        }
        self.assertLessEqual(changed, allowed)
        operand_changes = {
            index
            for offset in probe_builder.TITLE_LOAD_ENTRY_OPERANDS
            for index in range(offset, offset + 4)
            if self.production[index] != probe[index]
        }
        self.assertTrue(operand_changes)
        self.assertTrue(operand_changes.issubset(changed))

    def test_probe_rejects_unexpected_input_operand(self):
        probe = bytearray(self.production)
        offset = probe_builder.TITLE_LOAD_ENTRY_OPERANDS[0]
        probe[offset] ^= 0xFF
        with self.assertRaisesRegex(ValueError, "input title LOAD operand changed"):
            probe_builder.patch_probe(probe, self.source)


if __name__ == "__main__":
    unittest.main()

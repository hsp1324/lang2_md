from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_game_genie_probe_rom as probe_builder
from tools.game_genie import decode_genesis_game_genie


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / builder.IN_ROM
KO_ROM = ROOT / builder.OUT_ROM


class GameGenieProbeRomTests(unittest.TestCase):
    def test_decoder_matches_published_sonic_example(self):
        patch = decode_genesis_game_genie("SCRA-BJX0")
        self.assertEqual(patch.address, 0x009C76)
        self.assertEqual(patch.value, 0x5478)

    def test_langrisser_ui_probe_codes_decode_stably(self):
        expected = {
            "AJKA-EA7E": (0x0212A4, 0x6002),
            "AJMT-EA7A": (0x0217A0, 0x6002),
            "RGJA-Y6X2": (0x0A9078, 0x4E71),
            "RGJA-Y6ZG": (0x0A90A6, 0x4E71),
            "AMMT-AA7E": (0x00D7A4, 0x6002),
            "R18T-A6X4": (0x00FD7A, 0x4E75),
            "AKEA-CA6N": (0x01488C, 0x6002),
        }
        for code, (address, value) in expected.items():
            with self.subTest(code=code):
                patch = decode_genesis_game_genie(code)
                self.assertEqual((patch.address, patch.value), (address, value))

    def test_probe_validates_source_words_and_updates_checksum(self):
        source = JP_ROM.read_bytes()
        probe = bytearray(KO_ROM.read_bytes())
        patches = [
            decode_genesis_game_genie(code)
            for code in ("AJKA-EA7E", "RGJA-Y6X2")
        ]
        checksum = probe_builder.apply_patches(probe, source, patches)
        for patch in patches:
            self.assertEqual(
                probe[patch.address : patch.address + 2],
                patch.value.to_bytes(2, "big"),
            )
        self.assertEqual(int.from_bytes(probe[0x18E:0x190], "big"), checksum)

    def test_probe_rejects_localization_code_drift(self):
        source = JP_ROM.read_bytes()
        probe = bytearray(KO_ROM.read_bytes())
        patch = decode_genesis_game_genie("AJKA-EA7E")
        probe[patch.address] ^= 1
        with self.assertRaisesRegex(ValueError, "differs from Japanese source"):
            probe_builder.apply_patches(probe, source, [patch])

    def test_decoder_rejects_bad_codes(self):
        for code in ("AJKA-EA7", "AJKA_EA7E", "AJKA-EA7I"):
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    decode_genesis_game_genie(code)


if __name__ == "__main__":
    unittest.main()

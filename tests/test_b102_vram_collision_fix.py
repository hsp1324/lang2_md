import hashlib
import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/b102_vram_collision_fix.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class B102VramCollisionFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL.read_text(encoding="utf-8"))
        cls.source = (ROOT / cls.model["source_rom"]["path"]).read_bytes()
        cls.output = (ROOT / cls.model["output_rom"]["path"]).read_bytes()

    def test_release_hash_header_and_checksum_are_exact(self) -> None:
        self.assertEqual(sha256(self.source), self.model["source_rom"]["sha256"])
        self.assertEqual(sha256(self.output), self.model["output_rom"]["sha256"])
        self.assertEqual(
            self.output[0x150:0x180].decode("ascii").rstrip(),
            self.model["output_rom"]["header_title"],
        )
        checksum = sum(
            int.from_bytes(self.output[offset : offset + 2], "big")
            for offset in range(0x200, len(self.output), 2)
        ) & 0xFFFF
        self.assertEqual(checksum, int(self.model["output_rom"]["md_checksum"], 16))
        self.assertEqual(self.output[0x18E:0x190], checksum.to_bytes(2, "big"))

    def test_only_declared_release_bytes_changed(self) -> None:
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.source, self.output))
            if before != after
        }
        allowed = (
            {0x171}
            | set(range(0x18E, 0x190))
            | set(range(builder.BYTE_UI_DYNAMIC_VDP_COMMAND_TABLE + 2 * 4,
                        builder.BYTE_UI_DYNAMIC_VDP_COMMAND_TABLE + 4 * 4))
            | set(range(builder.BYTE_UI_DYNAMIC_VDP_COMMAND_TABLE + 8 * 4,
                        builder.BYTE_UI_DYNAMIC_VDP_COMMAND_TABLE + 10 * 4))
            | set(range(builder.BYTE_UI_DYNAMIC_TILE_ID_TABLE + 2 * 2,
                        builder.BYTE_UI_DYNAMIC_TILE_ID_TABLE + 4 * 2))
            | set(range(builder.BYTE_UI_DYNAMIC_TILE_ID_TABLE + 8 * 2,
                        builder.BYTE_UI_DYNAMIC_TILE_ID_TABLE + 10 * 2))
        )
        self.assertEqual(len(changed), self.model["delta"]["changed_byte_count"])
        self.assertTrue(changed <= allowed)

    def test_builder_uses_the_released_four_slot_relocation(self) -> None:
        slots = self.model["collision"]["map_slots"]
        replacements = [
            int(value, 16) for value in self.model["collision"]["replacement_tiles"]
        ]
        self.assertEqual(
            [builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS[slot] for slot in slots],
            replacements,
        )
        for slot, tile in zip(slots, replacements):
            self.assertEqual(
                builder.be16(
                    self.output,
                    builder.BYTE_UI_DYNAMIC_TILE_ID_TABLE + slot * 2,
                ),
                tile,
            )


if __name__ == "__main__":
    unittest.main()

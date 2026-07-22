from pathlib import Path
import unittest

from tools import build_discard_prompt_probe_rom as probe_builder
from tools import build_item_shop_probe_rom as shop_probe


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class DiscardPromptProbeBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()
        cls.production = KO_ROM.read_bytes()

    def test_probe_changes_only_declared_diagnostic_fields(self):
        probe = bytearray(self.production)
        checksum = probe_builder.patch_probe(probe, self.source)
        self.assertEqual(checksum, int.from_bytes(probe[0x18E:0x190], "big"))
        hook = bytes.fromhex("4E F9") + probe_builder.PROBE_ROUTINE.to_bytes(4, "big")
        self.assertEqual(
            probe[
                probe_builder.SHOP_FULL_HOOK :
                probe_builder.SHOP_FULL_HOOK + len(hook)
            ],
            hook,
        )
        self.assertEqual(
            probe_builder.builder.be32(
                probe, probe_builder.NOTICE_DISMISS_CALLBACK_POINTER
            ),
            probe_builder.PROBE_CLEAR_CALLBACK,
        )
        self.assertEqual(
            probe[
                probe_builder.PROBE_ROUTINE :
                probe_builder.PROBE_ROUTINE + len(probe_builder.PROBE_ROUTINE_BYTES)
            ],
            probe_builder.PROBE_ROUTINE_BYTES,
        )
        self.assertEqual(
            probe[
                probe_builder.PROBE_INIT_CALLBACK :
                probe_builder.PROBE_INIT_CALLBACK
                + len(probe_builder.PROBE_INIT_CALLBACK_BYTES)
            ],
            probe_builder.PROBE_INIT_CALLBACK_BYTES,
        )
        self.assertEqual(
            probe[
                probe_builder.PROBE_ARM_CALLBACK :
                probe_builder.PROBE_ARM_CALLBACK
                + len(probe_builder.PROBE_ARM_CALLBACK_BYTES)
            ],
            probe_builder.PROBE_ARM_CALLBACK_BYTES,
        )
        self.assertEqual(
            probe[
                probe_builder.PROBE_CLEAR_CALLBACK :
                probe_builder.PROBE_CLEAR_CALLBACK
                + len(probe_builder.PROBE_CLEAR_CALLBACK_BYTES)
            ],
            probe_builder.PROBE_CLEAR_CALLBACK_BYTES,
        )
        self.assertEqual(
            probe[
                probe_builder.PROBE_PLANE_CLEAR_ROUTINE :
                probe_builder.PROBE_PLANE_CLEAR_ROUTINE
                + len(probe_builder.PROBE_PLANE_CLEAR_ROUTINE_BYTES)
            ],
            probe_builder.PROBE_PLANE_CLEAR_ROUTINE_BYTES,
        )
        self.assertEqual(
            probe[
                probe_builder.PROBE_INPUT_CALLBACK :
                probe_builder.PROBE_INPUT_CALLBACK
                + len(probe_builder.PROBE_INPUT_CALLBACK_BYTES)
            ],
            probe_builder.PROBE_INPUT_CALLBACK_BYTES,
        )
        allowed = {
            0x18E,
            0x18F,
            *range(
                shop_probe.SHOP_LIST_SELECTOR_OFFSET,
                shop_probe.SHOP_LIST_SELECTOR_OFFSET + len(shop_probe.SHOP_LIST_SELECTOR_PATCH),
            ),
            *range(shop_probe.ITEM_PRICE_TABLE, shop_probe.ITEM_PRICE_TABLE_END),
            *range(
                probe_builder.SHOP_FULL_HOOK,
                probe_builder.SHOP_FULL_HOOK + len(probe_builder.SHOP_FULL_HOOK_SOURCE),
            ),
            *range(
                probe_builder.NOTICE_DISMISS_CALLBACK_POINTER,
                probe_builder.NOTICE_DISMISS_CALLBACK_POINTER + 4,
            ),
            *range(
                probe_builder.PROBE_ROUTINE,
                probe_builder.PROBE_ROUTINE + len(probe_builder.PROBE_ROUTINE_BYTES),
            ),
            *range(
                probe_builder.PROBE_INIT_CALLBACK,
                probe_builder.PROBE_INIT_CALLBACK
                + len(probe_builder.PROBE_INIT_CALLBACK_BYTES),
            ),
            *range(
                probe_builder.PROBE_ARM_CALLBACK,
                probe_builder.PROBE_ARM_CALLBACK
                + len(probe_builder.PROBE_ARM_CALLBACK_BYTES),
            ),
            *range(
                probe_builder.PROBE_CLEAR_CALLBACK,
                probe_builder.PROBE_CLEAR_CALLBACK
                + len(probe_builder.PROBE_CLEAR_CALLBACK_BYTES),
            ),
            *range(
                probe_builder.PROBE_PLANE_CLEAR_ROUTINE,
                probe_builder.PROBE_PLANE_CLEAR_ROUTINE
                + len(probe_builder.PROBE_PLANE_CLEAR_ROUTINE_BYTES),
            ),
            *range(
                probe_builder.PROBE_INPUT_CALLBACK,
                probe_builder.PROBE_INPUT_CALLBACK
                + len(probe_builder.PROBE_INPUT_CALLBACK_BYTES),
            ),
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.production, probe))
            if before != after
        }
        self.assertLessEqual(changed, allowed)

    def test_source_and_probe_mutations_are_rejected(self):
        source = bytearray(self.source)
        source[probe_builder.SHOP_FULL_HOOK] ^= 1
        with self.assertRaisesRegex(ValueError, "Japanese full-inventory"):
            probe_builder.patch_probe(bytearray(self.production), bytes(source))

        probe = bytearray(self.production)
        probe[probe_builder.PROBE_ROUTINE] = 0
        with self.assertRaisesRegex(ValueError, "routine area"):
            probe_builder.patch_probe(probe, self.source)

    def test_probe_callback_branches_land_on_instruction_boundaries(self):
        def branch_target(routine: int, payload: bytes, opcode_offset: int) -> int:
            displacement = int.from_bytes(
                payload[opcode_offset + 2 : opcode_offset + 4],
                "big",
                signed=True,
            )
            return routine + opcode_offset + 2 + displacement

        self.assertEqual(
            branch_target(
                probe_builder.PROBE_INIT_CALLBACK,
                probe_builder.PROBE_INIT_CALLBACK_BYTES,
                12,
            ),
            probe_builder.PROBE_INIT_CALLBACK + 0x30,
        )
        self.assertEqual(
            branch_target(
                probe_builder.PROBE_INPUT_CALLBACK,
                probe_builder.PROBE_INPUT_CALLBACK_BYTES,
                4,
            ),
            probe_builder.PROBE_INPUT_CALLBACK + 0x0C,
        )
        self.assertEqual(
            branch_target(
                probe_builder.PROBE_INPUT_CALLBACK,
                probe_builder.PROBE_INPUT_CALLBACK_BYTES,
                16,
            ),
            probe_builder.PROBE_INPUT_CALLBACK + 0x1A,
        )


if __name__ == "__main__":
    unittest.main()

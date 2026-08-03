from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario12_hidden_event_probe_rom as probe_builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class Scenario12HiddenEventProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()
        cls.input = KO_ROM.read_bytes()
        cls.probes = {}
        for event in probe_builder.PROBE_ELWIN_DEPLOYMENTS:
            probe = bytearray(cls.input)
            probe_builder.patch_probe(probe, cls.source, event=event)
            cls.probes[event] = probe

    def test_stock_hidden_tiles_point_to_distinct_dialogue_pages(self):
        self.assertEqual(
            probe_builder.be32(self.source, probe_builder.MUSCLE_DIALOGUE_POINTER),
            probe_builder.MUSCLE_DIALOGUE,
        )
        self.assertEqual(
            probe_builder.be32(self.source, probe_builder.CARBUNKLE_DIALOGUE_POINTER),
            probe_builder.CARBUNKLE_DIALOGUE,
        )
        self.assertNotEqual(
            probe_builder.MUSCLE_DIALOGUE,
            probe_builder.CARBUNKLE_DIALOGUE,
        )

    def test_probe_changes_only_elwin_deployment_and_checksum(self):
        for event, probe in self.probes.items():
            changed = {
                index
                for index, (before, after) in enumerate(zip(self.input, probe))
                if before != after
            }
            allowed = {
                *range(
                    probe_builder.FIRST_PLAYER_DEPLOYMENT,
                    probe_builder.FIRST_PLAYER_DEPLOYMENT + 4,
                ),
                0x18E,
                0x18F,
            }
            self.assertLessEqual(changed, allowed)
            self.assertEqual(
                probe[
                    probe_builder.FIRST_PLAYER_DEPLOYMENT:
                    probe_builder.FIRST_PLAYER_DEPLOYMENT + 4
                ],
                probe_builder.PROBE_ELWIN_DEPLOYMENTS[event],
            )

    def test_probe_preserves_hidden_event_triggers_and_handlers(self):
        for probe in self.probes.values():
            self.assertEqual(
                probe[
                    probe_builder.TRIGGER_TABLE_START:
                    probe_builder.TRIGGER_TABLE_END
                ],
                self.source[
                    probe_builder.TRIGGER_TABLE_START:
                    probe_builder.TRIGGER_TABLE_END
                ],
            )
            self.assertEqual(
                probe[
                    probe_builder.MUSCLE_HANDLER:
                    probe_builder.CARBUNKLE_DIALOGUE_POINTER + 4
                ],
                self.source[
                    probe_builder.MUSCLE_HANDLER:
                    probe_builder.CARBUNKLE_DIALOGUE_POINTER + 4
                ],
            )
            self.assertEqual(
                sum(
                    int.from_bytes(probe[offset:offset + 2], "big")
                    for offset in range(0x200, len(probe) - 1, 2)
                ) & 0xFFFF,
                int.from_bytes(probe[0x18E:0x190], "big"),
            )

    def test_optional_carbunkle_guard_override_only_retargets_the_branch(self):
        probe = bytearray(self.input)
        probe_builder.patch_probe(
            probe,
            self.source,
            event="carbunkle",
            force_carbunkle_event=True,
        )
        self.assertEqual(
            probe_builder.be32(
                self.source,
                probe_builder.CARBUNKLE_GUARD_BRANCH_POINTER,
            ),
            probe_builder.CARBUNKLE_GUARD_SOURCE_TARGET,
        )
        self.assertEqual(
            probe_builder.be32(
                probe,
                probe_builder.CARBUNKLE_GUARD_BRANCH_POINTER,
            ),
            probe_builder.CARBUNKLE_GUARD_FORCED_TARGET,
        )
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.input, probe))
            if before != after
        }
        allowed = {
            *range(
                probe_builder.FIRST_PLAYER_DEPLOYMENT,
                probe_builder.FIRST_PLAYER_DEPLOYMENT + 4,
            ),
            *range(
                probe_builder.CARBUNKLE_GUARD_BRANCH_POINTER,
                probe_builder.CARBUNKLE_GUARD_BRANCH_POINTER + 4,
            ),
            0x18E,
            0x18F,
        }
        self.assertLessEqual(changed, allowed)

    def test_carbunkle_guard_override_rejects_muscle_probe(self):
        with self.assertRaisesRegex(ValueError, "Carbunkle-only"):
            probe_builder.patch_probe(
                bytearray(self.input),
                self.source,
                event="muscle",
                force_carbunkle_event=True,
            )

    def test_unknown_event_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported hidden event"):
            probe_builder.patch_probe(
                bytearray(self.input), self.source, event="unknown"
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from scripts import build_korean_jp_probe as builder


class Scenario18ResidentLossPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = builder.IN_ROM.read_bytes()

    def expanded_source(self) -> bytearray:
        data = bytearray(self.source)
        builder.expand_rom(data)
        return data

    def test_relocates_complete_source_list_and_preserves_dialogue(self):
        data = self.expanded_source()
        start = builder.SCENARIO18_DISPLACED_DIALOGUE_START
        end = builder.SCENARIO18_DISPLACED_DIALOGUE_END
        data[start : start + 4] = bytes.fromhex("02 0A 19 01")
        displaced = bytes(data[start:end])

        builder.patch_scenario18_resident_loss(data, self.source)

        self.assertEqual(
            builder.be32(data, builder.SCENARIO18_DEFEAT_TRIGGER_POINTER),
            builder.SCENARIO18_RELOCATED_TRIGGER_LIST,
        )
        self.assertEqual(
            builder.be32(data, builder.SCENARIO18_DISPLACED_DIALOGUE_POINTER),
            builder.SCENARIO18_RELOCATED_DIALOGUE,
        )
        relocated_end = builder.SCENARIO18_RELOCATED_DIALOGUE + len(displaced)
        self.assertEqual(
            data[builder.SCENARIO18_RELOCATED_DIALOGUE:relocated_end],
            displaced,
        )

        source_triggers = self.source[
            builder.SCENARIO18_DEFEAT_TRIGGER_LIST:
            builder.SCENARIO18_DEFEAT_TRIGGER_LIST_END
        ]
        relocated = builder.SCENARIO18_RELOCATED_TRIGGER_LIST
        self.assertEqual(
            data[relocated : relocated + len(source_triggers) - 2],
            source_triggers[:-2],
        )
        aggregate = bytes(
            (
                builder.SCENARIO18_RESIDENT_LOSS_EVENT_ID,
                0x04,
                *builder.SCENARIO18_RESIDENT_LOSS_NAMES,
                0,
            )
        ) + builder.SCENARIO18_RESIDENT_LOSS_HANDLER.to_bytes(4, "big")
        aggregate_start = relocated + len(source_triggers) - 2
        self.assertEqual(
            data[aggregate_start : aggregate_start + len(aggregate)],
            aggregate,
        )
        self.assertEqual(
            data[
                aggregate_start + len(aggregate):
                aggregate_start + len(aggregate) + 2
            ],
            b"\xFF\xFF",
        )

    def test_rejects_nonblank_expansion_destination(self):
        data = self.expanded_source()
        data[builder.SCENARIO18_RELOCATED_DIALOGUE] = 0
        with self.assertRaisesRegex(ValueError, "region is not blank"):
            builder.patch_scenario18_resident_loss(data, self.source)

    def test_rejects_changed_source_list(self):
        data = self.expanded_source()
        source = bytearray(self.source)
        source[builder.SCENARIO18_DEFEAT_TRIGGER_LIST] ^= 1
        with self.assertRaisesRegex(ValueError, "source defeat-trigger"):
            builder.patch_scenario18_resident_loss(data, bytes(source))


if __name__ == "__main__":
    unittest.main()

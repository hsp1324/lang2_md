import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario31_clear_probe_rom as scenario31_probe
from tools.scenario_data import KOREAN_NAME_BY_ID


class Scenario31DemonLordIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = builder.IN_ROM.read_bytes()

    def patched(self) -> bytearray:
        data = bytearray(self.source)
        builder.expand_rom(data)
        builder.patch_scenario31_demon_lord_identity(data, self.source)
        return data

    def test_source_duplicate_cannot_reach_the_stock_id_66_trigger(self) -> None:
        offset = builder.SCENARIO31_DEMON_LORD_NAME_OFFSET
        self.assertEqual(
            self.source[offset],
            builder.SCENARIO31_DEMON_LORD_SOURCE_NAME_ID,
        )
        trigger = builder.SCENARIO31_DEMON_LORD_EVENT_TRIGGER
        expected = builder.SCENARIO31_DEMON_LORD_EVENT_TRIGGER_BYTES
        self.assertEqual(self.source[trigger : trigger + len(expected)], expected)
        self.assertEqual(expected[2], builder.SCENARIO31_DEMON_LORD_EVENT_NAME_ID)
        self.assertNotEqual(self.source[offset], expected[2])

    def test_patch_changes_only_the_intended_fixed_record_name_id(self) -> None:
        data = self.patched()
        source_expanded = bytearray(self.source)
        builder.expand_rom(source_expanded)
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(source_expanded, data))
            if before != after
        }
        self.assertEqual(changed, {builder.SCENARIO31_DEMON_LORD_NAME_OFFSET})
        self.assertEqual(
            data[builder.SCENARIO31_DEMON_LORD_NAME_OFFSET],
            builder.SCENARIO31_DEMON_LORD_EVENT_NAME_ID,
        )

    def test_corrected_id_keeps_the_same_visible_demon_lord_label(self) -> None:
        self.assertEqual(
            KOREAN_NAME_BY_ID[builder.SCENARIO31_DEMON_LORD_SOURCE_NAME_ID],
            "데몬로드",
        )
        self.assertEqual(
            KOREAN_NAME_BY_ID[builder.SCENARIO31_DEMON_LORD_EVENT_NAME_ID],
            "데몬로드",
        )

    def test_corrected_probe_needs_no_runtime_name_rewrite(self) -> None:
        data = self.patched()
        scenario31_probe.patch_probe(
            data,
            self.source,
            branch_target=8,
            protect_protagonist=True,
        )
        target = (
            scenario31_probe.RUNTIME_GROUP_BASE
            + (
                scenario31_probe.FIRST_FIXED_RUNTIME_GROUP + 8
            )
            * scenario31_probe.RUNTIME_GROUP_SIZE
        )
        runtime_name_write = (
            bytes.fromhex("13 FC 00 66")
            + (target + scenario31_probe.RUNTIME_NAME_OFFSET).to_bytes(4, "big")
        )
        wrapper = data[
            scenario31_probe.BRANCH_HP_WRAPPER :
            scenario31_probe.BRANCH_HP_WRAPPER + 96
        ]
        self.assertNotIn(runtime_name_write, wrapper)
        self.assertIn(
            bytes.fromhex("00 39 00 80")
            + (
                target + scenario31_probe.RUNTIME_DEFEATED_FLAG_OFFSET
            ).to_bytes(4, "big"),
            wrapper,
        )

    def test_rejects_changed_input_or_event_handler(self) -> None:
        changed_name = bytearray(self.source)
        builder.expand_rom(changed_name)
        changed_name[builder.SCENARIO31_DEMON_LORD_NAME_OFFSET] = 0x66
        with self.assertRaisesRegex(ValueError, "input Scenario 31"):
            builder.patch_scenario31_demon_lord_identity(
                changed_name,
                self.source,
            )

        changed_trigger = bytearray(self.source)
        builder.expand_rom(changed_trigger)
        changed_trigger[builder.SCENARIO31_DEMON_LORD_EVENT_TRIGGER] ^= 1
        with self.assertRaisesRegex(ValueError, "input Scenario 31"):
            builder.patch_scenario31_demon_lord_identity(
                changed_trigger,
                self.source,
            )


if __name__ == "__main__":
    unittest.main()

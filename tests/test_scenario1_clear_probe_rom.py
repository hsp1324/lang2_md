from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario1_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario1ClearProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def patched(self, *, protagonist_death: bool = False) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            protagonist_death=protagonist_death,
        )
        return data

    def test_probe_only_changes_verified_bald_fields_and_checksum(self):
        data = self.patched()
        base = probe_builder.BALD_RECORD_OFFSET
        expected_changes = {
            base + FIELD_OFFSETS["at"],
            base + FIELD_OFFSETS["df"],
            base + FIELD_OFFSETS["x"],
            base + FIELD_OFFSETS["y"],
            *(base + FIELD_OFFSETS["mercenaries"] + index for index in range(6)),
            0x18E,
            0x18F,
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)
        self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
        self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
        self.assertEqual(
            data[base + FIELD_OFFSETS["x"]], probe_builder.PROBE_BALD_X
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["y"]], probe_builder.PROBE_BALD_Y
        )
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(data[mercenary_offset : mercenary_offset + 6], b"\xFF" * 6)

    def test_probe_rejects_changed_scenario_layout(self):
        data = bytearray(self.built)
        data[probe_builder.BALD_RECORD_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Bald record differs"):
            probe_builder.patch_probe(data, self.source)

    def test_probe_updates_megadrive_checksum(self):
        data = self.patched()
        expected = sum(
            builder.be16(data, offset) for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(builder.be16(data, 0x18E), expected)

    def test_protagonist_death_event_is_source_locked(self):
        for data in (self.source, self.built):
            self.assertEqual(
                data[
                    probe_builder.PROTAGONIST_DEATH_TRIGGER :
                    probe_builder.PROTAGONIST_DEATH_TRIGGER
                    + len(probe_builder.PROTAGONIST_DEATH_TRIGGER_BYTES)
                ],
                probe_builder.PROTAGONIST_DEATH_TRIGGER_BYTES,
            )
            self.assertEqual(
                data[
                    probe_builder.PROTAGONIST_DEATH_HANDLER :
                    probe_builder.PROTAGONIST_DEATH_HANDLER
                    + len(probe_builder.PROTAGONIST_DEATH_HANDLER_BYTES)
                ],
                probe_builder.PROTAGONIST_DEATH_HANDLER_BYTES,
            )
        self.assertEqual(
            int.from_bytes(
                probe_builder.PROTAGONIST_DEATH_HANDLER_BYTES[4:8],
                "big",
            ),
            probe_builder.PROTAGONIST_DEATH_TEXT,
        )

    def test_protagonist_death_preserves_every_scenario_record(self):
        data = self.patched(protagonist_death=True)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        start = layout.records_offset
        end = start + layout.record_count * FIXED_RECORD_SIZE
        self.assertEqual(data[start:end], self.source[start:end])
        self.assertEqual(
            data[
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET :
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
                + probe_builder.PLAYER_DEPLOYMENT_COUNT * 4
            ],
            self.source[
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET :
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
                + probe_builder.PLAYER_DEPLOYMENT_COUNT * 4
            ],
        )

    def test_protagonist_death_changes_only_wrapper_and_checksum(self):
        data = self.patched(protagonist_death=True)
        wrapper = probe_builder.protagonist_death_wrapper_code()
        allowed = {
            0x18E,
            0x18F,
            *range(
                probe_builder.START_MENU_ENTRY_OPERAND,
                probe_builder.START_MENU_ENTRY_OPERAND + 4,
            ),
            *range(
                probe_builder.RUNTIME_WRAPPER,
                probe_builder.RUNTIME_WRAPPER + len(wrapper),
            ),
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, allowed)
        self.assertEqual(
            data[
                probe_builder.START_MENU_ENTRY_OPERAND :
                probe_builder.START_MENU_ENTRY_OPERAND + 4
            ],
            probe_builder.RUNTIME_WRAPPER.to_bytes(4, "big"),
        )

    def test_protagonist_death_wrapper_targets_only_player_group_zero(self):
        code = probe_builder.protagonist_death_wrapper_code()
        self.assertIn(
            (
                probe_builder.RUNTIME_GROUP_BASE
                + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
            ).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 00")
            + (
                probe_builder.RUNTIME_GROUP_BASE
                + probe_builder.RUNTIME_HP_OFFSET
            ).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 FF")
            + (
                probe_builder.RUNTIME_GROUP_BASE
                + probe_builder.RUNTIME_X_OFFSET
            ).to_bytes(4, "big"),
            code,
        )
        first_fixed_group = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.PLAYER_DEPLOYMENT_COUNT * 0x60
        )
        self.assertNotIn(
            (
                first_fixed_group + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
            ).to_bytes(4, "big"),
            code,
        )
        self.assertEqual(
            code[-6:],
            bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_protagonist_death_checksum_is_current(self):
        data = self.patched(protagonist_death=True)
        expected = sum(
            builder.be16(data, offset) for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(builder.be16(data, 0x18E), expected)
        self.assertEqual(expected, 0xD87E)


if __name__ == "__main__":
    unittest.main()

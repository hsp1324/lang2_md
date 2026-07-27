from pathlib import Path
import hashlib
import unittest
from unittest import mock

from tools import build_fixed_enemy_summon_probe_rom as probe_builder
from tools import hard_mode_baseline
from tools import verify_fixed_enemy_summon_probe_evidence as evidence_verifier
from tools.scenario_data import FIELD_OFFSETS, scenario_layout


ROOT = Path(__file__).resolve().parents[1]
NORMAL_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


def md_checksum(data: bytes) -> int:
    return sum(
        int.from_bytes(data[offset : offset + 2], "big")
        for offset in range(0x200, len(data), 2)
    ) & 0xFFFF


class FixedEnemySummonProbeBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.normal = NORMAL_ROM.read_bytes()

    def test_probe_changes_only_two_soldiers_and_checksum(self):
        probe, report = probe_builder.patch_probe(self.normal)
        layout = scenario_layout(self.normal, probe_builder.PROBE_SCENARIO)
        record = (
            layout.records_offset
            + probe_builder.PROBE_RECORD_INDEX * 0x24
        )
        mercenary_offset = record + FIELD_OFFSETS["mercenaries"]
        target_offsets = {
            mercenary_offset + slot for slot in probe_builder.PROBE_SLOTS
        }
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.normal, probe))
            if before != after
        }

        self.assertEqual(record, probe_builder.PROBE_RECORD_OFFSET)
        self.assertEqual(
            probe[mercenary_offset : mercenary_offset + 6],
            bytes((0x89, 0x89, 0x89, 0x89, 0x8F, 0x8F)),
        )
        self.assertTrue(target_offsets.issubset(changed))
        self.assertLessEqual(
            changed,
            target_offsets | set(probe_builder.CHECKSUM_OFFSETS),
        )
        self.assertEqual(
            int.from_bytes(probe[0x18E:0x190], "big"),
            md_checksum(probe),
        )
        self.assertEqual(
            report["target_offsets"],
            [f"0x{offset:06X}" for offset in sorted(target_offsets)],
        )
        self.assertEqual(
            report["status"],
            "diagnostic_only_not_for_distribution",
        )

    def test_probe_keeps_normal_release_immutable(self):
        _, report = probe_builder.patch_probe(self.normal)
        current = NORMAL_ROM.read_bytes()
        self.assertEqual(current, self.normal)
        self.assertEqual(
            hashlib.sha256(current).hexdigest(),
            hard_mode_baseline.NORMAL_SHA256,
        )
        self.assertNotEqual(
            report["output_sha256"],
            hard_mode_baseline.NORMAL_SHA256,
        )

    def test_probe_rejects_non_release_source(self):
        damaged = bytearray(self.normal)
        damaged[0x200000] ^= 0x01
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            probe_builder.patch_probe(bytes(damaged))

    def test_probe_rejects_changed_target_layout(self):
        damaged = bytearray(self.normal)
        mercenary_offset = (
            probe_builder.PROBE_RECORD_OFFSET
            + FIELD_OFFSETS["mercenaries"]
        )
        damaged[mercenary_offset] ^= 0x01
        damaged_bytes = bytes(damaged)
        with mock.patch.object(
            hard_mode_baseline,
            "NORMAL_SHA256",
            hashlib.sha256(damaged_bytes).hexdigest(),
        ):
            with self.assertRaisesRegex(ValueError, "mercenary layout"):
                probe_builder.patch_probe(damaged_bytes)

    def test_retained_runtime_evidence_has_two_fixed_white_dragons(self):
        gst = evidence_verifier.DEFAULT_GST.read_bytes()
        group = evidence_verifier.read_runtime_group(gst)
        evidence_verifier.verify_runtime_group(group)
        self.assertEqual(
            [
                (member.class_id, member.x, member.y)
                for member in group.members[5:7]
            ],
            [(0x8F, 14, 9), (0x8F, 16, 7)],
        )

    def test_runtime_evidence_rejects_a_changed_summon_slot(self):
        gst = bytearray(evidence_verifier.DEFAULT_GST.read_bytes())
        member_offset = (
            evidence_verifier.GST_WORK_RAM_FILE_OFFSET
            + evidence_verifier.RUNTIME_RECORD_BASE
            + evidence_verifier.TARGET_RUNTIME_GROUP
            * evidence_verifier.RUNTIME_RECORD_SIZE
            + 5 * evidence_verifier.MEMBER_RECORD_SIZE
        )
        gst[member_offset] = 0x87
        group = evidence_verifier.read_runtime_group(bytes(gst))
        with self.assertRaisesRegex(ValueError, "runtime members"):
            evidence_verifier.verify_runtime_group(group)


if __name__ == "__main__":
    unittest.main()

import hashlib
import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import scenario_data


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "localization/scenario6_runestone_runtime.json"


class Scenario6RunestoneRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.roms = {
            row["role"]: ROOT / row["path"]
            for row in cls.manifest["roms"]
        }

    def test_manifest_rom_identities(self):
        for row in self.manifest["roms"]:
            data = (ROOT / row["path"]).read_bytes()
            self.assertEqual(data[0x18E:0x190].hex().upper(), row["md_checksum"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])

    def test_runestone_event_keeps_handler_and_expands_only_x_end(self):
        trigger = bytes.fromhex(
            self.manifest["secret_item"]["event_trigger_source_bytes"]
        )
        patched_trigger = bytes.fromhex(
            self.manifest["secret_item"]["event_trigger_patched_bytes"]
        )
        handler = bytes.fromhex(
            self.manifest["secret_item"]["handler_bytes"]
        )
        source = self.roms["japanese_reference"].read_bytes()
        candidate = self.roms["v1.3.2_normal_candidate"].read_bytes()
        probe = self.roms["v1.3.2_accessibility_probe"].read_bytes()
        self.assertEqual(source[0x18D768:0x18D778], trigger)
        self.assertEqual(candidate[0x18D768:0x18D778], patched_trigger)
        self.assertEqual(probe[0x18D768:0x18D778], patched_trigger)
        for data in (candidate, probe):
            self.assertEqual(data[0x18D8D8:0x18D8F0], handler)
        changed = {
            index
            for index, (before, after) in enumerate(zip(trigger, patched_trigger))
            if before != after
        }
        self.assertEqual(changed, {8})
        self.assertEqual(patched_trigger[8], 0x07)
        self.assertEqual(
            builder.SCENARIO6_RUNESTONE_TRIGGER_ACCESSIBLE,
            patched_trigger,
        )

    def test_npc_coordinates_are_source_locked(self):
        reference = self.roms["japanese_reference"].read_bytes()
        expected = [
            (row["coordinate"][0], row["coordinate"][1])
            for row in self.manifest["source_locked_npc_records"]
        ]
        for role in ("v1.3.2_normal_candidate", "v1.3.2_accessibility_probe"):
            data = self.roms[role].read_bytes()
            layout = scenario_data.scenario_layout(data, 6)
            positions = []
            for index in range(4):
                offset = layout.records_offset + index * scenario_data.FIXED_RECORD_SIZE
                positions.append((
                    data[offset + scenario_data.FIELD_OFFSETS["x"]],
                    data[offset + scenario_data.FIELD_OFFSETS["y"]],
                ))
                reference_offset = (
                    scenario_data.scenario_layout(reference, 6).records_offset
                    + index * scenario_data.FIXED_RECORD_SIZE
                )
                self.assertEqual(
                    data[offset:offset + scenario_data.FIXED_RECORD_SIZE],
                    reference[
                        reference_offset:
                        reference_offset + scenario_data.FIXED_RECORD_SIZE
                    ],
                )
            self.assertEqual(positions, expected)

    def test_runtime_evidence_hashes(self):
        cheat = self.manifest["all_factions_cheat"]
        for path_key, hash_key in (
            ("capture", "capture_sha256"),
            ("gst", "gst_sha256"),
        ):
            data = (ROOT / cheat[path_key]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), cheat[hash_key])
        self.assertEqual(cheat["hard_candidate_result"], "pass")
        accessibility = self.manifest["v1.3.2_accessibility"]
        for path_key, hash_key in (
            ("capture", "capture_sha256"),
            ("gst", "gst_sha256"),
        ):
            data = (ROOT / accessibility[path_key]).read_bytes()
            self.assertEqual(
                hashlib.sha256(data).hexdigest(),
                accessibility[hash_key],
            )
        self.assertEqual(accessibility["visual_result"], "룬스톤을 찾았다!")


if __name__ == "__main__":
    unittest.main()

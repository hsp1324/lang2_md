import hashlib
import json
from pathlib import Path
import unittest

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

    def test_runestone_event_is_source_locked(self):
        trigger = bytes.fromhex(
            self.manifest["secret_item"]["event_trigger_bytes"]
        )
        handler = bytes.fromhex(
            self.manifest["secret_item"]["handler_bytes"]
        )
        for rom in self.roms.values():
            data = rom.read_bytes()
            self.assertEqual(data[0x18D768:0x18D778], trigger)
            self.assertEqual(data[0x18D8D8:0x18D8F0], handler)

    def test_npc_coordinates_are_source_locked(self):
        reference = self.roms["japanese_reference"].read_bytes()
        expected = [
            (row["coordinate"][0], row["coordinate"][1])
            for row in self.manifest["source_locked_npc_records"]
        ]
        for rom in self.roms.values():
            data = rom.read_bytes()
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


if __name__ == "__main__":
    unittest.main()

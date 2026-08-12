import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario6_runestone_probe_rom as probe_builder
from tools import scenario_data
from tools.rom_update import bps_apply


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "localization/scenario6_runestone_runtime.json"


class Scenario6RunestoneManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_tracks_current_release_without_deleted_evidence(self):
        self.assertEqual(self.manifest["schema"], 3)
        self.assertEqual(self.manifest["release"], "v1.3.6")
        self.assertEqual(
            self.manifest["status"],
            "v1.3.6_reproducible_probe_ready",
        )
        serialized = json.dumps(self.manifest, ensure_ascii=False)
        self.assertNotIn("v1.3.2", serialized)
        self.assertNotIn("v132_", serialized)
        self.assertNotIn("captures/", serialized)
        self.assertNotIn("quicksave.gst", serialized)
        self.assertNotIn('Langrisser II (Korean).md', serialized)

    def test_probe_recipe_uses_versioned_input_and_tmp_output(self):
        probe = self.manifest["probe"]
        self.assertEqual(probe["input_profile"], "normal")
        self.assertFalse(probe["generated_artifact_tracked"])
        self.assertEqual(
            probe_builder.DEFAULT_INPUT,
            ROOT / "roms/builds/Langrisser II (Korean Normal v1.3.6).md",
        )
        self.assertEqual(
            probe_builder.DEFAULT_OUTPUT,
            ROOT / probe["default_output"],
        )
        self.assertEqual(
            probe_builder.DEFAULT_PATCH,
            ROOT / probe["fallback_patch"],
        )
        self.assertTrue((ROOT / probe["builder"]).is_file())


class Scenario6RunestoneRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        source_path = ROOT / cls.manifest["source"]["path"]
        if not source_path.is_file():
            raise unittest.SkipTest("local Japanese verification ROM is absent")
        cls.source = source_path.read_bytes()
        cls.release_manifest = json.loads(
            (ROOT / cls.manifest["release_manifest"]).read_text(
                encoding="utf-8"
            )
        )
        cls.release_rows = {
            row["id"]: row for row in cls.release_manifest["targets"]
        }
        cls.profile_rows = {
            row["id"]: row for row in cls.manifest["release_profiles"]
        }
        cls.targets = {}
        for profile_id, row in cls.profile_rows.items():
            patch = (ROOT / row["patch"]).read_bytes()
            cls.targets[profile_id] = bps_apply(patch, cls.source)
        cls.probe = bytes(
            probe_builder.build_probe(cls.targets["normal"], cls.source)
        )

    def test_v136_bps_profiles_reproduce_locked_rom_identities(self):
        source_row = self.manifest["source"]
        self.assertEqual(
            hashlib.sha256(self.source).hexdigest(),
            source_row["sha256"],
        )
        self.assertEqual(
            self.source[0x18E:0x190].hex().upper(),
            source_row["md_checksum"],
        )
        self.assertEqual(self.release_manifest["release"], "v1.3.6")
        self.assertEqual(
            set(self.profile_rows),
            {"pure", "normal", "hard"},
        )
        for profile_id, row in self.profile_rows.items():
            release_row = self.release_rows[profile_id]
            patch = (ROOT / row["patch"]).read_bytes()
            output = self.targets[profile_id]
            with self.subTest(profile=profile_id):
                self.assertEqual(
                    Path(row["patch"]).name,
                    release_row["patch_filename"],
                )
                self.assertEqual(
                    hashlib.sha256(patch).hexdigest(),
                    row["patch_sha256"],
                )
                self.assertEqual(
                    row["patch_sha256"],
                    release_row["patch_sha256"],
                )
                self.assertEqual(
                    hashlib.sha256(output).hexdigest(),
                    row["output_sha256"],
                )
                self.assertEqual(
                    row["output_sha256"],
                    release_row["output_sha256"],
                )
                self.assertEqual(
                    output[0x18E:0x190].hex().upper(),
                    row["md_checksum"],
                )

    def test_trigger_changes_only_x_end_while_handler_stays_source_locked(self):
        item = self.manifest["secret_item"]
        source_trigger = bytes.fromhex(item["event_trigger_source_bytes"])
        release_trigger = bytes.fromhex(item["event_trigger_release_bytes"])
        handler = bytes.fromhex(item["handler_bytes"])
        trigger_start = builder.SCENARIO6_RUNESTONE_TRIGGER
        trigger_end = trigger_start + len(source_trigger)
        handler_start = 0x18D8D8
        handler_end = handler_start + len(handler)

        self.assertEqual(self.source[trigger_start:trigger_end], source_trigger)
        self.assertEqual(self.source[handler_start:handler_end], handler)
        self.assertEqual(
            hashlib.sha256(source_trigger).hexdigest(),
            item["event_trigger_source_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(release_trigger).hexdigest(),
            item["event_trigger_release_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(handler).hexdigest(),
            item["handler_sha256"],
        )
        for profile_id, data in {**self.targets, "probe": self.probe}.items():
            with self.subTest(profile=profile_id):
                self.assertEqual(data[trigger_start:trigger_end], release_trigger)
                self.assertEqual(data[handler_start:handler_end], handler)

        changed = {
            index
            for index, (before, after) in enumerate(
                zip(source_trigger, release_trigger)
            )
            if before != after
        }
        delta = item["intentional_trigger_delta"]
        self.assertEqual(changed, {delta["relative_offset"]})
        self.assertEqual(source_trigger[delta["relative_offset"]], delta["source"])
        self.assertEqual(release_trigger[delta["relative_offset"]], delta["release"])
        self.assertEqual(
            builder.SCENARIO6_RUNESTONE_TRIGGER_ACCESSIBLE,
            release_trigger,
        )

    def test_npc_records_are_source_locked_in_every_release_and_probe(self):
        reference_layout = scenario_data.scenario_layout(self.source, 6)
        expected_positions = [
            tuple(row["coordinate"])
            for row in self.manifest["source_locked_npc_records"]
        ]
        for profile_id, data in {**self.targets, "probe": self.probe}.items():
            layout = scenario_data.scenario_layout(data, 6)
            positions = []
            for index in range(4):
                offset = (
                    layout.records_offset
                    + index * scenario_data.FIXED_RECORD_SIZE
                )
                reference_offset = (
                    reference_layout.records_offset
                    + index * scenario_data.FIXED_RECORD_SIZE
                )
                positions.append(
                    (
                        data[offset + scenario_data.FIELD_OFFSETS["x"]],
                        data[offset + scenario_data.FIELD_OFFSETS["y"]],
                    )
                )
                with self.subTest(profile=profile_id, record=index):
                    self.assertEqual(
                        data[offset:offset + scenario_data.FIXED_RECORD_SIZE],
                        self.source[
                            reference_offset:
                            reference_offset + scenario_data.FIXED_RECORD_SIZE
                        ],
                    )
            self.assertEqual(positions, expected_positions)

    def test_current_normal_probe_is_reproducible_and_minimal(self):
        probe_row = self.manifest["probe"]
        normal = self.targets["normal"]
        self.assertEqual(
            self.probe[0x18E:0x190].hex().upper(),
            probe_row["md_checksum"],
        )
        self.assertEqual(
            hashlib.sha256(self.probe).hexdigest(),
            probe_row["sha256"],
        )
        deployment = probe_row["probe_only_deployment_change"]
        offset = int(deployment["rom_offset"], 16)
        end = offset + len(probe_builder.SOURCE_FIRST_PLAYER_COORDINATE)
        self.assertEqual(
            normal[offset:end],
            probe_builder.SOURCE_FIRST_PLAYER_COORDINATE,
        )
        self.assertEqual(
            self.probe[offset:end],
            probe_builder.PROBE_FIRST_PLAYER_COORDINATE,
        )
        changed = {
            index
            for index, (before, after) in enumerate(zip(normal, self.probe))
            if before != after
        }
        allowed = {0x18E, 0x18F, *range(offset, end)}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(deployment["from"], [4, 26])
        self.assertEqual(deployment["to"], [6, 4])
        self.assertEqual(probe_row["ordinary_move"]["to"], [7, 4])
        self.assertEqual(
            probe_row["expected_visual_result"],
            self.manifest["secret_item"]["dialogue"],
        )

    def test_probe_builder_accepts_every_hash_locked_release_profile(self):
        offset = probe_builder.FIRST_PLAYER_DEPLOYMENT
        end = offset + len(probe_builder.PROBE_FIRST_PLAYER_COORDINATE)
        for profile, candidate in self.targets.items():
            with self.subTest(profile=profile):
                probe = bytes(
                    probe_builder.build_probe(candidate, self.source)
                )
                self.assertEqual(
                    probe[offset:end],
                    probe_builder.PROBE_FIRST_PLAYER_COORDINATE,
                )
                changed = {
                    index
                    for index, values in enumerate(zip(candidate, probe))
                    if values[0] != values[1]
                }
                self.assertLessEqual(
                    changed,
                    {0x18E, 0x18F, *range(offset, end)},
                )

    def test_probe_builder_rejects_npc_or_item_handler_corruption(self):
        layout = scenario_data.scenario_layout(self.targets["normal"], 6)
        npc = layout.records_offset
        changed_npc = bytearray(self.targets["normal"])
        changed_npc[npc + scenario_data.FIELD_OFFSETS["name_id"]] ^= 1
        with self.assertRaisesRegex(ValueError, "NPC record 0 changed"):
            probe_builder.build_probe(bytes(changed_npc), self.source)

        changed_handler = bytearray(self.targets["normal"])
        changed_handler[probe_builder.RUNESTONE_HANDLER] ^= 1
        with self.assertRaisesRegex(ValueError, "Rune Stone handler changed"):
            probe_builder.build_probe(bytes(changed_handler), self.source)

    def test_explicit_candidate_loader_requires_the_declared_sha256(self):
        candidate = self.targets["pure"]
        digest = hashlib.sha256(candidate).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "candidate.md"
            path.write_bytes(candidate)
            loaded, origin = probe_builder.load_hash_locked_candidate(
                path,
                digest,
            )
            self.assertEqual(loaded, candidate)
            self.assertEqual(origin, str(path))
            with self.assertRaisesRegex(ValueError, "identity changed"):
                probe_builder.load_hash_locked_candidate(path, "0" * 64)
            with self.assertRaisesRegex(ValueError, "64 hex digits"):
                probe_builder.load_hash_locked_candidate(path, "not-a-hash")

    def test_builder_can_reconstruct_normal_without_a_build_rom(self):
        missing_input = ROOT / "tmp/nonexistent-v1.3.6-normal-build.md"
        self.assertFalse(missing_input.exists())
        reconstructed, origin = probe_builder.load_normal_release(
            missing_input,
            probe_builder.DEFAULT_PATCH,
            self.source,
        )
        self.assertEqual(reconstructed, self.targets["normal"])
        self.assertIn("normal-v1.3.6.bps", origin)


if __name__ == "__main__":
    unittest.main()

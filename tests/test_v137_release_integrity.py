import hashlib
import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario6_runestone_probe_rom as scenario6_runestone
from tools.build_hard_mode_rom import (
    load_applied_plan,
    verify_applied_hard_mode,
)
from tools.build_v138_release_patches import (
    MANIFEST_PATH,
    SOURCE_PATH,
    TARGETS,
    build,
)
from tools.rom_update import bps_apply, md_sram_descriptor
from tools.rom_version import get_profile
from tools.scenario_data import FIXED_RECORD_SIZE, scenario_layout
from patcher import langrisser_ii_korean_patcher as patcher


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_MANIFEST = ROOT / "patches/v1.3.7.json"


class V138ReleaseIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE_PATH.is_file():
            raise unittest.SkipTest("local Japanese verification ROM is absent")
        cls.source = SOURCE_PATH.read_bytes()
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.previous_manifest = json.loads(
            PREVIOUS_MANIFEST.read_text(encoding="utf-8")
        )
        cls.targets = cls._apply_manifest(cls.manifest)
        cls.previous_targets = cls._apply_manifest(cls.previous_manifest)

    @classmethod
    def _apply_manifest(cls, manifest):
        return {
            row["id"]: bps_apply(
                (ROOT / "patches" / row["patch_filename"]).read_bytes(),
                cls.source,
            )
            for row in manifest["targets"]
        }

    def test_manifest_and_bps_assets_are_reproducible(self):
        generated = build(check=True)
        self.assertEqual(generated, self.manifest)
        self.assertEqual(self.manifest["release"], "v1.3.8")
        self.assertEqual(
            {row["id"] for row in self.manifest["targets"]},
            {"pure", "normal", "hard"},
        )
        target_specs = {row["id"]: row for row in TARGETS}
        for row in self.manifest["targets"]:
            payload = self.targets[row["id"]]
            with self.subTest(profile=row["id"]):
                self.assertEqual(len(payload), row["output_size"])
                self.assertEqual(
                    hashlib.sha256(payload).hexdigest(),
                    row["output_sha256"],
                )
                self.assertEqual(
                    row["output_sha256"],
                    target_specs[row["id"]]["sha256"],
                )
                self.assertEqual(
                    payload,
                    Path(target_specs[row["id"]]["rom_path"]).read_bytes(),
                )
                self.assertEqual(
                    md_sram_descriptor(payload),
                    bytes.fromhex("5241F8200040000100403FFF"),
                )

    def test_profile_lineage_and_hard_balance_version_are_explicit(self):
        expected = {
            "pure": ("ko-original-1.3.8", None, "ko-original-1.3.7"),
            "normal": ("ko-normal-1.3.8", None, "ko-normal-1.3.7"),
            "hard": ("ko-hard-1.3.8", "1.3.8", "ko-hard-1.3.7"),
        }
        for profile_name, values in expected.items():
            profile = get_profile(profile_name)
            with self.subTest(profile=profile_name):
                self.assertEqual(profile["release_id"], values[0])
                self.assertEqual(profile["translation_version"], "1.3.8")
                self.assertEqual(profile["balance_version"], values[1])
                self.assertEqual(profile["base_release"], values[2])

    def test_v137_delta_keeps_only_reviewed_v138_regions(self):
        version_offsets = {
            "pure": {0x016F, 0x018E, 0x2B7EEA},
            "normal": {0x016A, 0x018E, 0x018F, 0x2B7EEA},
            "hard": {0x016A, 0x0171, 0x018E, 0x018F, 0x2B8A12, 0x2B8A32},
        }
        loren_sprite_bytes = {
            offset
            for offset in range(0x310000, 0x316000)
            if self.previous_targets["normal"][offset]
            != self.targets["normal"][offset]
        }
        self.assertEqual(len(loren_sprite_bytes), 75)

        for profile_name, current in self.targets.items():
            previous = self.previous_targets[profile_name]
            changed = {
                offset
                for offset, (before, after) in enumerate(zip(previous, current))
                if before != after
            }
            expected_changed = set(version_offsets[profile_name])
            if profile_name in {"normal", "hard"}:
                expected_changed |= loren_sprite_bytes

            with self.subTest(profile=profile_name):
                self.assertEqual(
                    len(changed),
                    {"pure": 3, "normal": 79, "hard": 81}[
                        profile_name
                    ],
                )
                self.assertEqual(changed, expected_changed)

    def test_hard_output_retains_the_approved_balance_layer(self):
        verify_applied_hard_mode(self.targets["hard"])

    def test_all_340_fixed_records_retain_reviewed_structural_identity(self):
        """Lock the exact final ROMs, not only the v1.3.7 inheritance chain."""

        changed_identity = builder.SCENARIO31_DEMON_LORD_NAME_OFFSET
        hard_plan = load_applied_plan()
        hard_record_offsets = {
            int(str(record["offset"]), 16)
            for scenario in hard_plan["scenarios"]
            for record in scenario["records"]
        }
        self.assertEqual(len(hard_record_offsets), 300)
        npc_protection_offsets = {
            int(str(record["offset"]), 16)
            for scenario in hard_plan["npc_survival_protection"]["scenarios"]
            for record in scenario["records"]
        }
        self.assertEqual(len(npc_protection_offsets), 19)
        reviewed_hard_record_offsets = (
            hard_record_offsets | npc_protection_offsets
        )

        total_records = 0
        hard_changed_records = set()
        for scenario in range(1, 32):
            source_layout = scenario_layout(self.source, scenario)
            total_records += source_layout.record_count
            for profile, payload in self.targets.items():
                with self.subTest(profile=profile, scenario=scenario):
                    self.assertEqual(
                        scenario_layout(payload, scenario),
                        source_layout,
                    )
            for index in range(source_layout.record_count):
                start = source_layout.records_offset + index * FIXED_RECORD_SIZE
                end = start + FIXED_RECORD_SIZE
                expected = bytearray(self.source[start:end])
                if start <= changed_identity < end:
                    expected[changed_identity - start] = (
                        builder.SCENARIO31_DEMON_LORD_EVENT_NAME_ID
                    )

                for profile in ("pure", "normal"):
                    with self.subTest(
                        profile=profile,
                        scenario=scenario,
                        record=index,
                    ):
                        self.assertEqual(self.targets[profile][start:end], expected)

                hard = self.targets["hard"][start:end]
                changed_relative = {
                    offset
                    for offset, (before, after) in enumerate(zip(expected, hard))
                    if before != after
                }
                if changed_relative:
                    hard_changed_records.add(start)
                with self.subTest(
                    profile="hard",
                    scenario=scenario,
                    record=index,
                ):
                    self.assertLessEqual(
                        changed_relative,
                        {
                            0x12,  # approved commander AT
                            0x13,  # approved commander DF
                            0x1D,  # approved soldier-correction tag
                            *range(0x1E, 0x24),  # approved mercenary slots
                        },
                    )

        self.assertEqual(total_records, 340)
        self.assertEqual(hard_changed_records, reviewed_hard_record_offsets)

    def test_scenario6_well_fix_and_npcs_are_exact_in_final_roms(self):
        trigger = builder.SCENARIO6_RUNESTONE_TRIGGER
        source_trigger = builder.SCENARIO6_RUNESTONE_TRIGGER_SOURCE
        release_trigger = builder.SCENARIO6_RUNESTONE_TRIGGER_ACCESSIBLE
        trigger_end = trigger + len(source_trigger)
        self.assertEqual(self.source[trigger:trigger_end], source_trigger)
        self.assertEqual(
            {
                offset
                for offset, (before, after) in enumerate(
                    zip(source_trigger, release_trigger)
                )
                if before != after
            },
            {8},
        )
        self.assertEqual(source_trigger[8], 5)
        self.assertEqual(release_trigger[8], 7)

        handler = scenario6_runestone.RUNESTONE_HANDLER
        handler_end = handler + len(scenario6_runestone.RUNESTONE_HANDLER_BYTES)
        source_layout = scenario_layout(self.source, 6)
        for profile, payload in self.targets.items():
            with self.subTest(profile=profile, part="trigger"):
                self.assertEqual(payload[trigger:trigger_end], release_trigger)
            with self.subTest(profile=profile, part="handler"):
                self.assertEqual(
                    payload[handler:handler_end],
                    self.source[handler:handler_end],
                )
                self.assertEqual(
                    payload[handler:handler_end],
                    scenario6_runestone.RUNESTONE_HANDLER_BYTES,
                )
            for index in scenario6_runestone.SOURCE_LOCKED_NPC_RECORDS:
                start = source_layout.records_offset + index * FIXED_RECORD_SIZE
                record_end = start + FIXED_RECORD_SIZE
                with self.subTest(profile=profile, npc_record=index):
                    if profile in {"pure", "normal"}:
                        self.assertEqual(
                            payload[start:record_end],
                            self.source[start:record_end],
                        )
                    else:
                        changed = {
                            relative
                            for relative, (before, after) in enumerate(zip(
                                self.source[start:record_end],
                                payload[start:record_end],
                            ))
                            if before != after
                        }
                        self.assertEqual(
                            changed,
                            {0x13, 0x1D} if index in {1, 2, 3} else set(),
                        )

    def test_patcher_and_platform_workflows_package_only_v138_assets(self):
        self.assertEqual(patcher.PATCHER_RELEASE, "v1.3.8")
        self.assertEqual(patcher.MANIFEST_FILENAME, "v1.3.8.json")
        for relative_path in (
            ".github/workflows/build-v1.3-patcher.yml",
            ".github/workflows/build-v1.3-patcher-platforms.yml",
        ):
            workflow = (ROOT / relative_path).read_text(encoding="utf-8")
            with self.subTest(workflow=relative_path):
                self.assertIn("patches/v1.3.8.json", workflow)
                self.assertIn("patches/original-v1.3.8.bps", workflow)
                self.assertIn("patches/normal-v1.3.8.bps", workflow)
                self.assertIn("patches/hard-v1.3.8.bps", workflow)

    def test_public_readme_links_published_v138_assets(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("/releases/download/v1.3.8/", readme)

    def test_validation_records_targeted_scenario2_color_check(self):
        validation = (ROOT / "docs/v1.3.8_validation.md").read_text(
            encoding="utf-8"
        )
        for topic in ("시나리오 2", "(219, 0, 0)", "(109, 0, 0)"):
            with self.subTest(topic=topic):
                self.assertIn(topic, validation)


if __name__ == "__main__":
    unittest.main()

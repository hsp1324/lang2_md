import hashlib
import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.build_hard_mode_rom import verify_applied_hard_mode
from tools.class_change_data import read_class_change_chain
from tools.rom_update import bps_apply, md_sram_descriptor
from tools.scenario_data import FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
MANIFEST = ROOT / "patches/v1.3.5.json"


class V135ReleaseIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE_ROM.is_file():
            raise unittest.SkipTest("local Japanese verification ROM is absent")
        cls.source = SOURCE_ROM.read_bytes()
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.targets = {}
        for row in cls.manifest["targets"]:
            patch = (ROOT / "patches" / row["patch_filename"]).read_bytes()
            cls.targets[row["id"]] = bps_apply(patch, cls.source)

    def test_manifest_hashes_and_save_layout_match_all_three_outputs(self):
        self.assertEqual(self.manifest["release"], "v1.3.5")
        release_descriptor = bytes.fromhex("5241F8200040000100403FFF")
        for row in self.manifest["targets"]:
            payload = self.targets[row["id"]]
            with self.subTest(profile=row["id"]):
                self.assertEqual(len(payload), row["output_size"])
                self.assertEqual(
                    hashlib.sha256(payload).hexdigest(),
                    row["output_sha256"],
                )
                self.assertEqual(md_sram_descriptor(payload), release_descriptor)

    def test_pure_and_normal_fixed_records_preserve_all_source_fields(self):
        changed_identity = builder.SCENARIO31_DEMON_LORD_NAME_OFFSET
        total_records = 0
        for scenario in range(1, 32):
            layout = scenario_layout(self.source, scenario)
            total_records += layout.record_count
            for index in range(layout.record_count):
                start = layout.records_offset + index * FIXED_RECORD_SIZE
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
                        self.assertEqual(
                            self.targets[profile][start:end],
                            expected,
                        )
        self.assertEqual(total_records, 340)

    def test_hard_balance_layer_and_shared_scenario31_fix_are_present(self):
        verify_applied_hard_mode(self.targets["hard"])
        for profile, payload in self.targets.items():
            with self.subTest(profile=profile):
                self.assertEqual(
                    payload[builder.SCENARIO31_DEMON_LORD_NAME_OFFSET],
                    builder.SCENARIO31_DEMON_LORD_EVENT_NAME_ID,
                )
                trigger = builder.SCENARIO31_DEMON_LORD_EVENT_TRIGGER
                self.assertEqual(
                    payload[
                        trigger : trigger
                        + len(builder.SCENARIO31_DEMON_LORD_EVENT_TRIGGER_BYTES)
                    ],
                    builder.SCENARIO31_DEMON_LORD_EVENT_TRIGGER_BYTES,
                )

    def test_runestone_first_choices_and_join_only_rows_coexist(self):
        expected = {
            7: ((0x01, (0x04, 0x06, 0x08)), 0x2B),
            9: ((0x01, (0x05, 0x07, 0x0A)), 0x2C),
            10: ((0x03, (0x08, 0x09, 0x04)), None),
        }
        for profile, payload in self.targets.items():
            for commander_id, (first, custom_class) in expected.items():
                chain = read_class_change_chain(payload, commander_id)
                with self.subTest(
                    profile=profile,
                    commander_id=commander_id,
                ):
                    self.assertEqual(
                        (chain[0].current_class, chain[0].candidates),
                        first,
                    )
                    if custom_class is not None:
                        self.assertIn(
                            custom_class,
                            {row.current_class for row in chain},
                        )

    def test_scenario6_well_runestone_trigger_is_shared(self):
        start = builder.SCENARIO6_RUNESTONE_TRIGGER
        end = start + len(builder.SCENARIO6_RUNESTONE_TRIGGER_ACCESSIBLE)
        for profile, payload in self.targets.items():
            with self.subTest(profile=profile):
                self.assertEqual(
                    payload[start:end],
                    builder.SCENARIO6_RUNESTONE_TRIGGER_ACCESSIBLE,
                )


if __name__ == "__main__":
    unittest.main()

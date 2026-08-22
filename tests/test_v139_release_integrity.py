import hashlib
import json
from pathlib import Path
import unittest

from tools.build_hard_mode_rom import verify_applied_hard_mode
from tools.build_v139_release_patches import MANIFEST_PATH, SOURCE_PATH
from tools.rom_update import bps_apply, md_sram_descriptor


ROOT = Path(__file__).resolve().parents[1]


class V139ReleaseIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE_PATH.is_file():
            raise unittest.SkipTest("local Japanese verification ROM is absent")
        cls.source = SOURCE_PATH.read_bytes()
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_bps_and_release_roms_are_reproducible(self):
        self.assertEqual(self.manifest["release"], "v1.3.9")
        for row in self.manifest["targets"]:
            with self.subTest(profile=row["id"]):
                target = bps_apply(
                    (ROOT / "patches" / row["patch_filename"]).read_bytes(),
                    self.source,
                )
                self.assertEqual(len(target), 4_194_304)
                self.assertEqual(
                    hashlib.sha256(target).hexdigest(), row["output_sha256"]
                )
                self.assertEqual(
                    md_sram_descriptor(target),
                    bytes.fromhex("5241F8200040000100403FFF"),
                )
        hard = bps_apply(
            (ROOT / "patches/hard-v1.3.9.bps").read_bytes(), self.source
        )
        verify_applied_hard_mode(hard)

    def test_archived_manifest_keeps_the_v139_identity(self):
        self.assertEqual(self.manifest["release"], "v1.3.9")
        self.assertEqual(
            {row["output_filename"] for row in self.manifest["targets"]},
            {
                "Langrisser II (Korean Original v1.3.9).md",
                "Langrisser II (Korean Normal v1.3.9).md",
                "Langrisser II (Korean Hard v1.3.9).md",
            },
        )

import hashlib
import json
from pathlib import Path
import unittest

from patcher import langrisser_ii_korean_patcher as patcher
from tools.build_hard_mode_rom import verify_applied_hard_mode
from tools.build_v139_release_patches import MANIFEST_PATH, SOURCE_PATH, TARGETS, build
from tools.rom_update import bps_apply, md_sram_descriptor
from tools.rom_version import get_profile


ROOT = Path(__file__).resolve().parents[1]


class V139ReleaseIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE_PATH.is_file():
            raise unittest.SkipTest("local Japanese verification ROM is absent")
        cls.source = SOURCE_PATH.read_bytes()
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_bps_and_release_roms_are_reproducible(self):
        self.assertEqual(build(check=True), self.manifest)
        self.assertEqual(self.manifest["release"], "v1.3.9")
        specs = {str(spec["id"]): spec for spec in TARGETS}
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
                self.assertEqual(target, Path(specs[row["id"]]["rom_path"]).read_bytes())
                self.assertEqual(
                    md_sram_descriptor(target),
                    bytes.fromhex("5241F8200040000100403FFF"),
                )
        hard = bps_apply(
            (ROOT / "patches/hard-v1.3.9.bps").read_bytes(), self.source
        )
        verify_applied_hard_mode(hard)

    def test_profiles_and_patcher_name_the_same_release(self):
        expected = {
            "pure": ("ko-original-1.3.9", None, "ko-original-1.3.8"),
            "normal": ("ko-normal-1.3.9", None, "ko-normal-1.3.8"),
            "hard": ("ko-hard-1.3.9", "1.3.9", "ko-hard-1.3.8"),
        }
        for profile_name, values in expected.items():
            profile = get_profile(profile_name)
            with self.subTest(profile=profile_name):
                self.assertEqual(profile["release_id"], values[0])
                self.assertEqual(profile["translation_version"], "1.3.9")
                self.assertEqual(profile["balance_version"], values[1])
                self.assertEqual(profile["base_release"], values[2])
        self.assertEqual(patcher.PATCHER_RELEASE, "v1.3.9")
        self.assertEqual(patcher.MANIFEST_FILENAME, "v1.3.9.json")

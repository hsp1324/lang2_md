from pathlib import Path
import json
import tempfile
import unittest

from tools import rom_version


ROOT = Path(__file__).resolve().parents[1]


class RomVersionTests(unittest.TestCase):
    def test_pure_profile_is_translation_only_release(self):
        profile = rom_version.get_profile("pure")
        self.assertEqual(profile["status"], "released")
        self.assertEqual(profile["release_id"], "ko-original-1.3.7")
        self.assertEqual(profile["translation_version"], "1.3.7")
        self.assertIsNone(profile["balance_version"])
        self.assertEqual(profile["title_text"], "번역:1.3.7")
        self.assertEqual(
            profile["rom_filename"],
            "Langrisser II (Korean Original v1.3.7).md",
        )
        self.assertEqual(
            profile["header_title"],
            "LANGRISSER II KOREAN PURE T1.3.7 BY HSP1324",
        )
        self.assertEqual(profile["base_release"], "ko-original-1.3.6")
        self.assertEqual(profile["save_format"], "lang2-ko-sram-v1")

    def test_normal_profile_is_latest_release(self):
        profile = rom_version.get_profile("normal")
        self.assertEqual(profile["status"], "released")
        self.assertEqual(profile["release_id"], "ko-normal-1.3.7")
        self.assertEqual(profile["translation_version"], "1.3.7")
        self.assertIsNone(profile["balance_version"])
        self.assertEqual(profile["title_text"], "번역:1.3.7")
        self.assertEqual(
            profile["rom_filename"],
            "Langrisser II (Korean Normal v1.3.7).md",
        )
        self.assertEqual(
            profile["header_title"],
            "LANGRISSER II KOREAN T1.3.7 BY HSP1324",
        )
        self.assertEqual(profile["creator"], "hsp1324")
        self.assertEqual(profile["base_release"], "ko-normal-1.3.6")
        self.assertEqual(profile["save_format"], "lang2-ko-sram-v1")

    def test_hard_profile_is_the_standard_hard_release(self):
        hard = rom_version.get_profile("hard")
        self.assertEqual(hard["status"], "released")
        self.assertEqual(
            hard["release_id"],
            "ko-hard-1.3.7",
        )
        self.assertEqual(hard["translation_version"], "1.3.7")
        self.assertEqual(hard["balance_version"], "1.3.7")
        self.assertEqual(
            hard["title_text"],
            "번역/밸런스:1.3.7/1.3.7",
        )
        self.assertEqual(
            hard["rom_filename"],
            "Langrisser II (Korean Hard v1.3.7).md",
        )
        self.assertEqual(
            hard["header_title"],
            "LANGRISSER II KOREAN T1.3.7 B1.3.7 BY HSP1324",
        )
        self.assertEqual(hard["base_release"], "ko-hard-1.3.6")

    def test_released_hard_profile_uses_dual_version_title(self):
        registry = rom_version.load_registry()
        registry["profiles"]["hard"].update(
            {
                "status": "released",
                "release_id": "ko-hard-1.0.0",
                "balance_version": "1.0.0",
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "versions.json"
            path.write_text(
                json.dumps(registry, ensure_ascii=False),
                encoding="utf-8",
            )
            profile = rom_version.get_profile("hard", path)
        self.assertEqual(
            profile["title_text"],
            "번역/밸런스:1.3.7/1.0.0",
        )
        self.assertEqual(
            profile["rom_filename"],
            "Langrisser II (Korean Hard T1.3.7 B1.0.0).md",
        )
        self.assertEqual(
            profile["header_title"],
            "LANGRISSER II KOREAN T1.3.7 B1.0.0 BY HSP1324",
        )

    def test_invalid_or_overlong_version_is_rejected(self):
        registry = rom_version.load_registry()
        registry["profiles"]["normal"]["translation_version"] = "1.0"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "versions.json"
            path.write_text(
                json.dumps(registry, ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "MAJOR.MINOR.PATCH"):
                rom_version.load_registry(path)

        registry["profiles"]["normal"]["translation_version"] = (
            "123456789.123456789.123456789"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "versions.json"
            path.write_text(
                json.dumps(registry, ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "exceeds"):
                rom_version.load_registry(path)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest

from tools import v137_release_identity as identity


ROOT = Path(__file__).resolve().parents[1]


class V137ReleaseIdentityTests(unittest.TestCase):
    def test_all_code_uses_one_exact_sha_update_point(self):
        for digest in identity.INVALIDATED_RELEASE_SHA256:
            locations = []
            for root in (ROOT / "tools", ROOT / "tests", ROOT / "patcher"):
                for path in root.rglob("*.py"):
                    if digest in path.read_text(encoding="utf-8"):
                        locations.append(path.relative_to(ROOT).as_posix())
            self.assertEqual(locations, ["tools/v137_release_identity.py"])

    def test_pending_identity_is_impossible_to_use_as_final(self):
        current = set(identity.RELEASE_ROM_SHA256.values())
        if identity.RELEASE_IDENTITY_FINALIZED:
            self.assertFalse(current & identity.INVALIDATED_RELEASE_SHA256)
            identity.require_final_release_identity(
                dict(identity.RELEASE_ROM_SHA256)
            )
        else:
            self.assertTrue(current <= identity.INVALIDATED_RELEASE_SHA256)
            with self.assertRaisesRegex(ValueError, "invalidated pending"):
                identity.require_final_release_identity()

    def test_all_derived_identity_records_are_listed_for_final_refresh(self):
        self.assertEqual(
            set(identity.DERIVED_IDENTITY_FILES),
            {
                "patches/v1.3.7.json",
                "localization/hard_mode_build.json",
                "localization/hard_mode_update_releases.json",
                "docs/player_patch_distribution.md",
                "docs/release_notes_v1.3.7.md",
                "docs/v1.3.7_validation.md",
            },
        )
        self.assertTrue(
            all((ROOT / path).is_file() for path in identity.DERIVED_IDENTITY_FILES)
        )


if __name__ == "__main__":
    unittest.main()

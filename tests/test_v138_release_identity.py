from pathlib import Path
import unittest

from tools import v138_release_identity as identity


ROOT = Path(__file__).resolve().parents[1]


class V138ReleaseIdentityTests(unittest.TestCase):
    def test_final_identity_is_complete_and_materialized(self):
        self.assertTrue(identity.RELEASE_IDENTITY_FINALIZED)
        self.assertEqual(set(identity.RELEASE_ROM_SHA256), {"pure", "normal", "hard"})
        identity.require_final_release_identity(dict(identity.RELEASE_ROM_SHA256))
        self.assertTrue(
            all((ROOT / relative).is_file() for relative in identity.DERIVED_IDENTITY_FILES)
        )

    def test_current_hashes_do_not_overlap_invalidated_hashes(self):
        self.assertFalse(
            set(identity.RELEASE_ROM_SHA256.values())
            & identity.INVALIDATED_RELEASE_SHA256
        )


if __name__ == "__main__":
    unittest.main()

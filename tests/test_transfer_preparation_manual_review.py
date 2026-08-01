import unittest

from tools import transfer_preparation_manual_review as transfer


class TransferPreparationManualReviewTests(unittest.TestCase):
    def test_surface_key_ignores_run_specific_prefix(self) -> None:
        self.assertEqual(
            transfer.surface_key(
                "captures/run/preparation_surface_matrix/normal/s12/"
                "pike-safe-full01/pre/allied/commander_01_root.png"
            ),
            "allied/commander_01_root.png",
        )

    def test_pair_hashes_bind_both_pre_and_post(self) -> None:
        evidence = {
            "capture_pairs": [{
                "surface": "allied/test.png",
                "pre_sha256": "pre",
                "post_sha256": "post",
            }]
        }
        self.assertEqual(
            transfer.pair_hashes(evidence),
            {"allied/test.png": ("pre", "post")},
        )

    def test_duplicate_source_surface_is_rejected(self) -> None:
        manifest = {
            "groups": [{
                "sheets": [
                    {"sources": [{"path": "a/pre/allied/x.png", "sha256": "1"}]},
                    {"sources": [{"path": "b/pre/allied/x.png", "sha256": "1"}]},
                ]
            }]
        }
        with self.assertRaisesRegex(ValueError, "duplicate review source"):
            transfer.source_hashes(manifest)


if __name__ == "__main__":
    unittest.main()

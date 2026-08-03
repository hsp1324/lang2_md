import argparse
import copy
from pathlib import Path
import unittest

from tools import record_preparation_manual_review as review


class PreparationManualReviewTests(unittest.TestCase):
    def test_preparation_evidence_requires_every_pair_to_match(self) -> None:
        evidence = {
            "status": "captured_exact_unreviewed",
            "expected_pair_count": 2,
            "capture_pairs": [
                {"byte_identical": True},
                {"byte_identical": True},
            ],
        }
        self.assertEqual(review.verify_preparation_evidence(evidence), 2)
        broken = copy.deepcopy(evidence)
        broken["capture_pairs"][1]["byte_identical"] = False
        with self.assertRaisesRegex(ValueError, "non-identical"):
            review.verify_preparation_evidence(broken)

    def test_identity_rejects_a_different_scenario(self) -> None:
        document = {"profile": "normal", "scenario": 11, "run_id": "probe"}
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            review.verify_identity(document, "normal", 12, "probe", "test")

    def test_runtime_identity_rejects_the_wrong_run(self) -> None:
        evidence = Path(__file__)
        report = {
            "status": "pass",
            "profiles": {
                "normal": {
                    "scenarios": [{
                        "scenario": 3,
                        "run_id": "wrong-run",
                        "status": "pass",
                        "evidence": str(evidence.resolve().relative_to(review.ROOT)),
                        "evidence_sha256": review.sha256(evidence),
                        "identity": {"identified_scenario": 3},
                    }],
                },
            },
        }
        with self.assertRaisesRegex(ValueError, "run mismatch"):
            review.verify_scenario_identity_report(
                report,
                profile="normal",
                scenario=3,
                run_id="correct-run",
                preparation_path=evidence,
            )


if __name__ == "__main__":
    unittest.main()

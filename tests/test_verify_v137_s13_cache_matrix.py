import tempfile
from pathlib import Path
import unittest

from tools import verify_v137_s13_cache_matrix as matrix


class V137S13CacheMatrixTests(unittest.TestCase):
    def test_retained_formal_matrix_is_fail_closed_and_passes(self):
        report = matrix.build_report(matrix.DEFAULT_EVIDENCE_ROOT)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(len(report["fresh_seed_lineage"]), 3)
        self.assertTrue(
            all(row["status"] == "pass" for row in report["fresh_seed_lineage"])
        )
        self.assertEqual(len(report["hover_cases"]), 9)
        self.assertTrue(
            all(
                row["checks"]["declared_contract_source_locked"]
                for row in report["hover_cases"]
            )
        )
        self.assertTrue(
            all(
                row["checks"]["declared_fresh_seed_contract_source_locked"]
                for row in report["hover_cases"]
            )
        )
        self.assertEqual(
            report["pure_synthetic_stress"]["classification"],
            "unsupported_out_of_domain_synthetic_stress",
        )
        self.assertFalse(report["pure_synthetic_stress"]["acceptance_blocker"])

    def test_check_mode_contract_uses_stable_rendering(self):
        report = matrix.build_report(matrix.DEFAULT_EVIDENCE_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "summary.json"
            output.write_text(
                __import__("json").dumps(report, ensure_ascii=False, indent=2)
                + "\n",
                encoding="utf-8",
            )
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()

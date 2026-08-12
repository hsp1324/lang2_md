import json
from pathlib import Path
import tempfile
import unittest

from tools import verify_ede6_discard_evidence as verifier


class Ede6DiscardEvidenceTests(unittest.TestCase):
    def test_current_frozen_discard_bundle_recomputes_exactly(self):
        report = verifier.build_report()
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertTrue(report["checks"])
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(
            report["release_sha256"],
            "2d475a96f5f5ee26352bef6c3c392a77"
            "aafa283a2c0f260a6d1cb8603b3610ac",
        )
        self.assertEqual(report["rebuilt_probe_sha256"], verifier.EXPECTED_PROBE_SHA256)
        self.assertEqual(report["changed_byte_count"], 288)
        self.assertEqual(report["changed_payload_byte_count"], 286)

    def test_expanded_mutation_scope_is_rejected(self):
        payload = json.loads(verifier.DEFAULT_EVIDENCE.read_text(encoding="utf-8"))
        payload["diagnostic_probe"]["declared_mutation_scope"][0]["start"] = "0x000000"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            report = verifier.build_report(path)
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["checks"]["declared_mutation_ranges_are_exact"])


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

from tools import verify_v134_release_regression as verifier


ROOT = Path(__file__).resolve().parents[1]


class V134ReleaseRegressionTests(unittest.TestCase):
    def test_manifest_declares_isolated_reviewed_runtime(self) -> None:
        import json

        manifest = json.loads(verifier.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["release"], "v1.3.4")
        self.assertEqual(manifest["status"], "reviewed_pass")
        self.assertEqual(manifest["method"]["display"], "isolated Xvfb")
        self.assertFalse(manifest["method"]["physical_desktop_used"])
        self.assertEqual(
            [row["character"] for row in manifest["join_class_choice"]],
            ["Keith", "Lester", "Jessica"],
        )

    def test_local_runtime_evidence_when_available(self) -> None:
        manifest = __import__("json").loads(
            verifier.DEFAULT_MANIFEST.read_text(encoding="utf-8")
        )
        local_paths = [
            ROOT / state["path"]
            for case in manifest["join_class_choice"]
            for state in case["states"]
        ]
        if not all(path.is_file() for path in local_paths):
            self.skipTest("ignored local BlastEm GST evidence is not present")
        result = verifier.verify_manifest()
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["join_cases"], 3)


if __name__ == "__main__":
    unittest.main()

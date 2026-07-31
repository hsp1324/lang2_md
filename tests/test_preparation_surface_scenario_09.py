import hashlib
import json
from pathlib import Path
import unittest

from tools.verify_preparation_surface_evidence import runtime_group_zero


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/preparation_surface_scenario_09.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PreparationSurfaceScenario09Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL.read_text(encoding="utf-8"))

    def test_review_and_both_profiles_are_complete(self) -> None:
        self.assertEqual(self.model["status"], "scenario_9_complete_pass")
        review = json.loads(
            (ROOT / self.model["review"]["path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(review["status"], "reviewed_pass")
        self.assertEqual(
            review["class_change"]["status"], "not_applicable_in_this_seed"
        )
        self.assertEqual(set(self.model["profiles"]), {"normal", "hard"})

    def test_capture_pairs_and_runtime_order_are_exact(self) -> None:
        for profile, row in self.model["profiles"].items():
            with self.subTest(profile=profile):
                run = ROOT / row["run"]
                plan_path = run / "plan.json"
                evidence_path = run / "evidence.json"
                self.assertEqual(sha256(plan_path), row["plan_sha256"])
                self.assertEqual(sha256(evidence_path), row["evidence_sha256"])

                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                ids = [
                    record["commander_id"]
                    for record in plan["allied_commanders"]["seed_records"]
                ]
                self.assertEqual(ids, row["commander_ids_in_runtime_order"])
                self.assertEqual(plan["allied_commanders"]["roster_page_count"], 2)
                self.assertEqual(plan["fixed_records"]["visible_count"], 13)
                self.assertEqual(evidence["expected_pair_count"], 32)
                self.assertEqual(evidence["actual_pair_count"], 32)
                self.assertEqual(len(evidence["capture_pairs"]), 32)
                self.assertTrue(
                    all(pair["byte_identical"] for pair in evidence["capture_pairs"])
                )
                for pair in evidence["capture_pairs"]:
                    pre = run / "pre" / pair["surface"]
                    post = run / "post" / pair["surface"]
                    self.assertEqual(sha256(pre), pair["pre_sha256"])
                    self.assertEqual(sha256(post), pair["post_sha256"])

    def test_gray_and_result_evidence_are_hash_locked(self) -> None:
        for profile, row in self.model["profiles"].items():
            with self.subTest(profile=profile):
                battle = row["battle"]
                for key in (
                    "gray_active",
                    "gray_acted",
                    "gray_gst",
                    "result",
                    "result_gst",
                ):
                    artifact = battle[key]
                    self.assertEqual(
                        sha256(ROOT / artifact["path"]), artifact["sha256"]
                    )
                runtime = runtime_group_zero(ROOT / battle["gray_gst"]["path"])
                self.assertEqual(runtime["acted_flag"], 1)
                self.assertEqual(runtime["commander_id"], 1)
                self.assertEqual(runtime["class_id"], 1)


if __name__ == "__main__":
    unittest.main()

import copy
import json
from pathlib import Path
import unittest

from tools import verify_v134_all_scenario_replay as verifier


ROOT = Path(__file__).resolve().parents[1]


class V134AllScenarioReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(
            verifier.DEFAULT_MANIFEST.read_text(encoding="utf-8")
        )

    def test_manifest_contract_covers_all_profiles_and_scenarios(self) -> None:
        verifier.validate_contract(self.manifest)
        self.assertEqual(
            self.manifest["coverage_assertions"],
            {
                "first_turn_profile_scenario_pairs": 93,
                "preparation_profile_scenario_pairs": 62,
                "gray_acted_profile_scenario_pairs": 62,
                "late_result_profile_scenario_pairs": 8,
                "fresh_result_and_ending_profile_scenario_pairs": 50,
                "carried_result_profile_scenario_pairs": 12,
                "all_result_profile_scenario_pairs": 62,
            },
        )

    def test_contract_rejects_missing_scenario(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["scenarios"].pop()
        with self.assertRaisesRegex(ValueError, "Scenarios 1..31"):
            verifier.validate_contract(changed)

    def test_local_hash_bound_evidence_when_present(self) -> None:
        first_source = (
            ROOT
            / self.manifest["first_turn_replay"]["profiles"][0][
                "source_summaries"
            ][0]["path"]
        )
        if not first_source.is_file():
            self.skipTest("ignored local all-scenario evidence is unavailable")
        result = verifier.verify_manifest()
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["verified_files"], 92)


if __name__ == "__main__":
    unittest.main()

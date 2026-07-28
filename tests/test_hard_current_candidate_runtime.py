import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "localization/hard_mode_current_candidate_runtime.json"
CANDIDATE_DELTA = ROOT / "localization/hard_mode_candidate_delta.json"


class HardCurrentCandidateRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.delta = json.loads(CANDIDATE_DELTA.read_text(encoding="utf-8"))

    def test_manifest_is_tied_to_current_candidate(self) -> None:
        self.assertEqual(
            self.model["hard_rom"]["sha256"],
            self.delta["after"]["sha256"],
        )
        self.assertEqual(
            self.model["hard_rom"]["path"],
            "roms/builds/Langrisser II (Korean Hard T1.0.0 B1.0.0).md",
        )

    def test_scenario_four_runtime_targets_are_verified(self) -> None:
        self.assertEqual(
            [row["number"] for row in self.model["scenarios"]],
            [4, 5],
        )
        row = self.model["scenarios"][0]
        self.assertEqual(row["number"], 4)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 3)
        self.assertEqual(row["target_record_count"], 6)
        self.assertEqual(row["strict_runtime_target_record_count"], 6)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [8, 13])
        self.assertEqual(
            row["gst_sha256"],
            "ade2fee468a2318556faf02e80caf38ce6e001695eea896ec8be0d62ff59bc6d",
        )
        self.assertEqual(
            row["capture_sha256"],
            "e31cfa84e6b198278e496d04ac78e7560efbfa997b211b825b5057fe158cf167",
        )

    def test_scenario_five_runtime_targets_are_verified(self) -> None:
        row = self.model["scenarios"][1]
        self.assertEqual(row["number"], 5)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 5)
        self.assertEqual(row["target_record_count"], 9)
        self.assertEqual(row["strict_runtime_target_record_count"], 9)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [5, 13])
        self.assertEqual(
            row["gst_sha256"],
            "7140fb55513bcefddb142c262ddd66e374b706252dfa05860965e1c54b1e54f9",
        )
        self.assertEqual(
            row["capture_sha256"],
            "478c87c02baaee079332a91a6d96471d7135730a3344a1c4bc52263dc6e4d211",
        )


if __name__ == "__main__":
    unittest.main()

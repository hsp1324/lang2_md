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
            [4, 5, 6, 7, 8, 9, 10],
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

    def test_scenario_six_runtime_targets_and_mercenaries_are_verified(
        self,
    ) -> None:
        row = self.model["scenarios"][2]
        self.assertEqual(row["number"], 6)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 5)
        self.assertEqual(row["target_record_count"], 9)
        self.assertEqual(row["strict_runtime_target_record_count"], 9)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [9, 17])
        self.assertEqual(
            row["gst_sha256"],
            "2ab66de2b9b9787e0cf4388736c6eb69fbb5dc291bc935dd24acf1396010fe2b",
        )
        self.assertEqual(
            row["capture_sha256"],
            "1d438f5e41d5997465125c099f03fc722b4c577a85cb77faa4ab37059efb5727",
        )

    def test_scenario_seven_runtime_targets_are_verified(self) -> None:
        row = self.model["scenarios"][3]
        self.assertEqual(row["number"], 7)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 6)
        self.assertEqual(row["target_record_count"], 8)
        self.assertEqual(row["strict_runtime_target_record_count"], 8)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [10, 17])
        self.assertEqual(
            row["gst_sha256"],
            "6c18eb4612cbb8e6cf5a22ff822f563e20d6c94b596bc237b58d4967f3914953",
        )
        self.assertEqual(
            row["capture_sha256"],
            "9ee44eda91beffcebe1cdd5873cad9fab21940e0f3433964a4ba3973278e99a8",
        )

    def test_scenario_eight_runtime_targets_are_verified(self) -> None:
        row = self.model["scenarios"][4]
        self.assertEqual(row["number"], 8)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 7)
        self.assertEqual(row["target_record_count"], 11)
        self.assertEqual(row["strict_runtime_target_record_count"], 11)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [7, 17])
        self.assertEqual(
            row["gst_sha256"],
            "bfbb3a73e8e38fd39f0907b5715b14a57bfad4f8c4664d5c4251fabf713f4f84",
        )
        self.assertEqual(
            row["capture_sha256"],
            "7c981e2d66fe76044785096648a063828dd45550931c476067912fef0d81d520",
        )

    def test_scenario_nine_runtime_targets_are_verified(self) -> None:
        row = self.model["scenarios"][5]
        self.assertEqual(row["number"], 9)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 7)
        self.assertEqual(row["target_record_count"], 10)
        self.assertEqual(row["strict_runtime_target_record_count"], 10)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [10, 19])
        self.assertEqual(
            row["gst_sha256"],
            "6d5f549efa7e2db62b4fba1c3dacb1e51d2fb9d79ecd8b97bddcdaf7ea1162e8",
        )
        self.assertEqual(
            row["capture_sha256"],
            "6f212d876d38ba43fa15b999f1509d36dd53bf68f92a2809909e3b57df1aac25",
        )

    def test_scenario_ten_runtime_targets_and_exception_are_verified(
        self,
    ) -> None:
        row = self.model["scenarios"][6]
        self.assertEqual(row["number"], 10)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 5)
        self.assertEqual(row["target_record_count"], 13)
        self.assertEqual(row["strict_runtime_target_record_count"], 12)
        self.assertEqual(row["runtime_exception_record_count"], 1)
        self.assertEqual(row["runtime_exception_indexes"], [1])
        self.assertEqual(row["runtime_group_range"], [5, 17])
        self.assertEqual(
            row["gst_sha256"],
            "e9ef42fa1a0a8abea32869eb46abdc9f0108cc76b32150c25b03c0ef90b35251",
        )
        self.assertEqual(
            row["capture_sha256"],
            "86cc44c73fa1a2c78dc974c897c93e266b915f32a9be35e73e16753b045bf2e5",
        )


if __name__ == "__main__":
    unittest.main()

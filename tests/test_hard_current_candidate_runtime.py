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
        cls.rows_by_number = {
            row["number"]: row for row in cls.model["scenarios"]
        }

    def test_manifest_is_tied_to_current_candidate(self) -> None:
        self.assertEqual(
            self.model["hard_rom"]["sha256"],
            self.delta["after"]["sha256"],
        )
        self.assertEqual(
            self.model["hard_rom"]["path"],
            "roms/builds/Langrisser II (Korean Hard T1.0.0 B1.0.0).md",
        )
        self.assertEqual(self.model["coverage"]["missing_scenarios"], [])
        self.assertEqual(
            self.model["coverage"]["verified_scenarios"],
            list(range(1, 32)),
        )

    def test_scenario_two_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[2]
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 3)
        self.assertEqual(row["target_record_count"], 6)
        self.assertEqual(row["strict_runtime_target_record_count"], 6)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [7, 12])
        self.assertEqual(
            row["gst_sha256"],
            "1e68a91b3f6c8de0963eafcf53fc43054ace358df3a7182f6c0a09546550f0b6",
        )
        self.assertEqual(
            row["capture_sha256"],
            "27cee3780f99e620239ac0519fb9275f7ec7595118105c2543f4aea894c96d8e",
        )

    def test_scenario_one_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[1]
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 2)
        self.assertEqual(row["target_record_count"], 2)
        self.assertEqual(row["strict_runtime_target_record_count"], 2)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [10, 13])
        self.assertEqual(
            row["gst_sha256"],
            "6e7203a44957612658dbf75efcfd5011d70a496b318eb221f5dc2bcd5deb9d19",
        )
        self.assertEqual(
            row["capture_sha256"],
            "81fc89d0e8184fc12334fb62413decc6b87c85a0f0303cd003603fe4d38aa816",
        )

    def test_scenario_three_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[3]
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 3)
        self.assertEqual(row["target_record_count"], 8)
        self.assertEqual(row["strict_runtime_target_record_count"], 8)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [5, 12])
        self.assertEqual(
            row["gst_sha256"],
            "376bdfecd69a43449fc8e506c027a12c82a14b970681b73f5af7311f985373e5",
        )
        self.assertEqual(
            row["capture_sha256"],
            "571845032021813e8c4c2263f229bacb5b48e267b66fddd1e2c6a0bee90969dc",
        )

    def test_scenario_four_runtime_targets_are_verified(self) -> None:
        self.assertEqual(
            [row["number"] for row in self.model["scenarios"]],
            list(range(1, 32)),
        )
        row = self.rows_by_number[4]
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
        row = self.rows_by_number[5]
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
        row = self.rows_by_number[6]
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
        row = self.rows_by_number[7]
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
        row = self.rows_by_number[8]
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
        row = self.rows_by_number[9]
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
        row = self.rows_by_number[10]
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

    def test_scenario_eleven_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[11]
        self.assertEqual(row["number"], 11)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 6)
        self.assertEqual(row["target_record_count"], 10)
        self.assertEqual(row["strict_runtime_target_record_count"], 10)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [7, 16])
        self.assertEqual(
            row["gst_sha256"],
            "fb1a1e2aba3924dd54022ea9f524165f91fc8aeafc28003eac99615ec3408d59",
        )
        self.assertEqual(
            row["capture_sha256"],
            "ba9122e02154f398351f5aac38a7a44ead59634f6e25736c4cdad7a13c0af87b",
        )

    def test_scenario_twelve_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[12]
        self.assertEqual(row["number"], 12)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 7)
        self.assertEqual(row["target_record_count"], 11)
        self.assertEqual(row["strict_runtime_target_record_count"], 11)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [7, 17])
        self.assertEqual(
            row["gst_sha256"],
            "f99778e7c8f7222ea36935dd1d6359d3aa76abedee7d7c00e3e088eabab6a179",
        )
        self.assertEqual(
            row["capture_sha256"],
            "727457ec46644d3be022b07ce64a29e41089f366269543765b63d5ae7e7afc95",
        )

    def test_scenario_thirteen_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[13]
        self.assertEqual(row["number"], 13)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 7)
        self.assertEqual(row["target_record_count"], 13)
        self.assertEqual(row["strict_runtime_target_record_count"], 13)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [7, 19])
        self.assertEqual(
            row["gst_sha256"],
            "455333e1bf26129811f4788022c1585d64642eebaaa65af5b8bf2488a97ec358",
        )
        self.assertEqual(
            row["capture_sha256"],
            "4f12c7b3e18d81c02ca97d2dd91e259d9180fc7ad253a8691361768ddef0c3ed",
        )

    def test_scenario_fourteen_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[14]
        self.assertEqual(row["number"], 14)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 7)
        self.assertEqual(row["target_record_count"], 11)
        self.assertEqual(row["strict_runtime_target_record_count"], 11)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [7, 17])
        self.assertEqual(
            row["gst_sha256"],
            "a39b7c75faf91aaac0cfbb5c86f346771e8a0773bdb9bfdcc1091e66410b3cd3",
        )
        self.assertEqual(
            row["capture_sha256"],
            "4b06192a8fe118cab25f7c350066eb14f249e68e65f277234a3a50ae7d552ab5",
        )

    def test_scenario_fifteen_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[15]
        self.assertEqual(row["number"], 15)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 7)
        self.assertEqual(row["target_record_count"], 11)
        self.assertEqual(row["strict_runtime_target_record_count"], 11)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [8, 18])
        self.assertEqual(
            row["gst_sha256"],
            "473bc3241798ded1b58790a3fbf6ad99e634e74cf720d743a49f3105b96b8414",
        )
        self.assertEqual(
            row["capture_sha256"],
            "f5ba877a879dd2ac2e1f16333b03ec9c7b9618486a47d0bea8b2a604c161d7b6",
        )

    def test_scenario_sixteen_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[16]
        self.assertEqual(row["number"], 16)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 8)
        self.assertEqual(row["target_record_count"], 10)
        self.assertEqual(row["strict_runtime_target_record_count"], 10)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [8, 17])
        self.assertEqual(
            row["gst_sha256"],
            "69303b039e3bccee6fb7c2215d085ca1bcd68559d4069497632135f0947a6e0e",
        )
        self.assertEqual(
            row["capture_sha256"],
            "7ed88fe78f07dd08725245bf14616c09583869339344858ee0aa62a7907bd637",
        )

    def test_scenario_seventeen_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[17]
        self.assertEqual(row["number"], 17)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 8)
        self.assertEqual(row["target_record_count"], 11)
        self.assertEqual(row["strict_runtime_target_record_count"], 11)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [8, 18])
        self.assertEqual(
            row["gst_sha256"],
            "37d7313a7dcd64dfc5e774c16dae378f6b8915353cd474cf0c2df04c843c5ef1",
        )
        self.assertEqual(
            row["capture_sha256"],
            "f619bcfd81b8bf979b152dda99690d7ce589b3f25c9eec3e84d729f918729c73",
        )

    def test_scenario_eighteen_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[18]
        self.assertEqual(row["number"], 18)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 8)
        self.assertEqual(row["target_record_count"], 9)
        self.assertEqual(row["strict_runtime_target_record_count"], 9)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [10, 18])
        self.assertEqual(
            row["gst_sha256"],
            "ddf9bbfc783db8e8b70fec66071b9fe4a2ac9869a71f449d1f3ede4a383324da",
        )
        self.assertEqual(
            row["capture_sha256"],
            "12d6fbf153b691607ea598db75bd33ca3bcfac06cb916ebd7ad41dbd565d2010",
        )

    def test_scenario_nineteen_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[19]
        self.assertEqual(row["number"], 19)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 8)
        self.assertEqual(row["target_record_count"], 10)
        self.assertEqual(row["strict_runtime_target_record_count"], 10)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [8, 17])
        self.assertEqual(
            row["gst_sha256"],
            "23a6b67050d9eae1eaa0e809fce8e606bbc6048ecb797bd3ff49f2975a9e0856",
        )
        self.assertEqual(
            row["capture_sha256"],
            "c83db18ea9ec67c0180c4c3e0c6d159772fc6576658ab10b339224819a023f5b",
        )

    def test_scenario_twenty_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[20]
        self.assertEqual(row["number"], 20)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 8)
        self.assertEqual(row["target_record_count"], 10)
        self.assertEqual(row["strict_runtime_target_record_count"], 10)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [8, 17])
        self.assertEqual(
            row["gst_sha256"],
            "9f96045d379559189afd68d4ce9e0e1e2b52fa7549cc2eb13b8e396e48da293a",
        )
        self.assertEqual(
            row["capture_sha256"],
            "5959b7b1ae4e779831b5a62c231947b24a64fac7f0955571e76de7fdf9c91e94",
        )

    def test_scenario_twenty_one_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[21]
        self.assertEqual(row["number"], 21)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 8)
        self.assertEqual(row["target_record_count"], 11)
        self.assertEqual(row["strict_runtime_target_record_count"], 11)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [8, 18])
        self.assertEqual(
            row["gst_sha256"],
            "2afa5e5af0f8a292b6b191224ef434d922c65ae2ae2c871ffeb4bee691f7835b",
        )
        self.assertEqual(
            row["capture_sha256"],
            "e5ed6bc01163d858cf2fdf68778325b1144ed21ed62083d66a674d23c46ba9b0",
        )

    def test_scenario_twenty_two_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[22]
        self.assertEqual(row["number"], 22)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 8)
        self.assertEqual(row["target_record_count"], 11)
        self.assertEqual(row["strict_runtime_target_record_count"], 11)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [9, 19])
        self.assertEqual(
            row["gst_sha256"],
            "9d82473dd3688afb481f15f79aaf2a13796071820005af1b7a3ef5349a796f42",
        )
        self.assertEqual(
            row["capture_sha256"],
            "b91224ec06cdad8fde57f4c2f5648dae0f014cd781f7a53d113cdbbf75a2b0b7",
        )

    def test_scenario_twenty_three_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[23]
        self.assertEqual(row["number"], 23)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 9)
        self.assertEqual(row["target_record_count"], 11)
        self.assertEqual(row["strict_runtime_target_record_count"], 11)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [9, 19])
        self.assertEqual(
            row["gst_sha256"],
            "6293d7771d05a4353587416dbb852ac78a62a0f63b74f1e65c11ac09dba0cac9",
        )
        self.assertEqual(
            row["capture_sha256"],
            "63ad46b5fd2367202b839b658bfac17461d800d4924735a4618040a2aef0ea6e",
        )

    def test_scenario_twenty_four_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[24]
        self.assertEqual(row["number"], 24)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 9)
        self.assertEqual(row["target_record_count"], 10)
        self.assertEqual(row["strict_runtime_target_record_count"], 10)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [10, 19])
        self.assertEqual(
            row["gst_sha256"],
            "a97a1dd47001196286a0cbb5a81f0737e531557fb2bd5c2746f2a6259f9d2275",
        )
        self.assertEqual(
            row["capture_sha256"],
            "dafe7a7803b99835318d1083104c89bd9b17a44e35537fa154adca46768d2b55",
        )

    def test_scenario_twenty_five_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[25]
        self.assertEqual(row["number"], 25)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 9)
        self.assertEqual(row["target_record_count"], 11)
        self.assertEqual(row["strict_runtime_target_record_count"], 11)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [10, 20])
        self.assertEqual(
            row["gst_sha256"],
            "8d3069aafe00cda087e8a8cf5cf658cf585372626960a7cf31dde091208ff4bf",
        )
        self.assertEqual(
            row["capture_sha256"],
            "67e422c5130e928b29181b3beea4feeea0e76580868a2d080fd4dd44c42b6e1d",
        )

    def test_scenario_twenty_six_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[26]
        self.assertEqual(row["number"], 26)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 10)
        self.assertEqual(row["target_record_count"], 10)
        self.assertEqual(row["strict_runtime_target_record_count"], 10)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [10, 19])
        self.assertEqual(
            row["gst_sha256"],
            "9ea6b57152d86852b1c181e58f76fa89ae03c080213a41ba7d05301eb40913b1",
        )
        self.assertEqual(
            row["capture_sha256"],
            "9ea0547d73645a719bc4f3748d3dd93c54ca80e40fa73aedeed008882c5572d1",
        )

    def test_scenario_twenty_seven_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[27]
        self.assertEqual(row["number"], 27)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 10)
        self.assertEqual(row["target_record_count"], 10)
        self.assertEqual(row["strict_runtime_target_record_count"], 10)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [10, 19])
        self.assertEqual(
            row["gst_sha256"],
            "c044cad7c04e312e49bf6b80dca39530028c09cf527286730b27248d06fa526a",
        )
        self.assertEqual(
            row["capture_sha256"],
            "fc48ccc1ca9297456a60a31b5162bacc651e244eab9b247408de794d922f410f",
        )

    def test_scenario_twenty_eight_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[28]
        self.assertEqual(row["number"], 28)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 7)
        self.assertEqual(row["target_record_count"], 9)
        self.assertEqual(row["strict_runtime_target_record_count"], 9)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [7, 15])
        self.assertEqual(
            row["gst_sha256"],
            "c7ece6f4f9dbf8369de697327856be066f5e12ecf2aed0be9e103a29189e79fe",
        )
        self.assertEqual(
            row["capture_sha256"],
            "40eaef200abbbccf1cc68e89c1fbf16f483565ec20754b5023b4f654de8c7736",
        )

    def test_scenario_twenty_nine_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[29]
        self.assertEqual(row["number"], 29)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 8)
        self.assertEqual(row["target_record_count"], 9)
        self.assertEqual(row["strict_runtime_target_record_count"], 9)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [8, 16])
        self.assertEqual(
            row["gst_sha256"],
            "1d92e3ee04d144f0972895c51033ecdcc3f82ac6d4c6a0752986ee51512f79df",
        )
        self.assertEqual(
            row["capture_sha256"],
            "e128a3e66a314438cb117d565fb33e7503f42c4002f654a021087da9133edde5",
        )

    def test_scenario_thirty_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[30]
        self.assertEqual(row["number"], 30)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 9)
        self.assertEqual(row["target_record_count"], 11)
        self.assertEqual(row["strict_runtime_target_record_count"], 11)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [9, 19])
        self.assertEqual(
            row["gst_sha256"],
            "a0e5398ae5dd83b4a6330eb08007db139ff4e164082391784263f6d2fdf8f5c0",
        )
        self.assertEqual(
            row["capture_sha256"],
            "c693e9e4cdaf505da3b76f215ca722cee337f17bf90c497c0ac0c890cfa1cb32",
        )

    def test_scenario_thirty_one_runtime_targets_are_verified(self) -> None:
        row = self.rows_by_number[31]
        self.assertEqual(row["number"], 31)
        self.assertEqual(row["status"], "runtime_loader_smoke_verified")
        self.assertEqual(row["player_group_count"], 10)
        self.assertEqual(row["target_record_count"], 9)
        self.assertEqual(row["strict_runtime_target_record_count"], 9)
        self.assertEqual(row["runtime_exception_record_count"], 0)
        self.assertEqual(row["runtime_group_range"], [10, 18])
        self.assertEqual(
            row["gst_sha256"],
            "d5cfc1a88903f8e58c4830d3ccbce730499a0efb68848094b8343fd01dcbc2c1",
        )
        self.assertEqual(
            row["capture_sha256"],
            "d84b360c6c80b8080884fb08b37fde355e809899ffd33e226b6c021a512e978a",
        )


if __name__ == "__main__":
    unittest.main()

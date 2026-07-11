from pathlib import Path
import unittest

from tools.jp_direct_string_inventory import inventory, scan_candidates


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class JapaneseDirectStringInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.result = inventory(cls.japanese, KO_ROM.read_bytes())

    def test_candidate_baseline(self):
        self.assertEqual(len(scan_candidates(self.japanese)), 783)
        self.assertEqual(self.result["candidate_count"], 783)

    def test_known_magic_string_is_declared(self):
        row = next(row for row in self.result["candidates"] if row["address"] == "0x082BFE")
        self.assertEqual(row["ownership"], "declared_direct_patch")
        self.assertEqual(row["target_korean"], "마법화살")
        self.assertTrue(row["modified"])

    def test_unclassified_candidates_remain_unreviewed(self):
        counts = self.result["ownership_counts"]
        self.assertGreater(counts["unclassified_candidate"], 0)
        self.assertTrue(
            all(
                not row["reviewed"]
                for row in self.result["candidates"]
                if row["ownership"] == "unclassified_candidate"
            )
        )


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest

from tools import run_shop_necklace_probe as probe


ROOT = Path(__file__).resolve().parents[1]


class ShopNecklaceProbeTests(unittest.TestCase):
    def test_probe_covers_the_reported_adjacent_rows(self) -> None:
        self.assertEqual(probe.ITEM_IDS, (27, 28))
        self.assertEqual(
            [probe.ITEM_LABELS[item_id] for item_id in probe.ITEM_IDS],
            ["크로스", "넥클리스"],
        )

    def test_accepted_runtime_captures_are_hash_locked(self) -> None:
        self.assertEqual(
            [probe.sha256(probe.ACCEPTED[item_id]) for item_id in probe.ITEM_IDS],
            [
                "a2d886f9b9519513966b7ef7f4c0a93391cae54c48a4796fe02b11bd1119bb87",
                "ddfe81f821aabb7200b2045b1ce3e978e67fad1b702403a0e9875d73168dbfea",
            ],
        )

    def test_capture_paths_are_deterministic(self) -> None:
        prefix = ROOT / "tmp/shop/item"
        self.assertEqual(
            probe.capture_path(prefix, 28),
            ROOT / "tmp/shop/item_id28.png",
        )


if __name__ == "__main__":
    unittest.main()

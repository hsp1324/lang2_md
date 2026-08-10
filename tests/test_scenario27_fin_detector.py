from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import run_scenario27_ending_surface as runner


class Scenario27FinDetectorTests(unittest.TestCase):
    def test_bound_covers_v134_extended_epilogue_roster(self) -> None:
        self.assertGreaterEqual(runner.DEFAULT_MAX_ENDING_FRAMES, 5200)

    def test_detector_uses_locked_hash_without_historical_capture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary) / "new-fin.png"
            capture.write_bytes(b"fresh runtime capture")

            with mock.patch.object(
                runner.shared,
                "sha256",
                return_value=runner.FIN_SHA256,
            ):
                self.assertTrue(runner.fin_visible(capture))

            with mock.patch.object(
                runner.shared,
                "sha256",
                return_value="0" * 64,
            ):
                self.assertFalse(runner.fin_visible(capture))

    def test_missing_capture_is_not_fin(self) -> None:
        self.assertFalse(runner.fin_visible(Path("missing-fin.png")))


if __name__ == "__main__":
    unittest.main()

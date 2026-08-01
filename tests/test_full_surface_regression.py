from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FullSurfaceRegressionTests(unittest.TestCase):
    def test_plan_covers_all_profiles_and_all_runtime_surfaces(self) -> None:
        output = subprocess.check_output(
            [
                sys.executable,
                str(ROOT / "tools/run_full_surface_regression.py"),
                "plan",
                "--normal-rom", str(ROOT / "tmp/current-battle-glyph-cache-normal.md"),
                "--hard-rom", str(ROOT / "tmp/current-battle-glyph-cache-hard.md"),
                "--scenarios", "1-31",
                "--workers", "6",
                "--display-base", "300",
                "--run-id", "full-plan-test",
            ],
            cwd=ROOT,
            text=True,
        )
        for marker in (
            '"preparation"',
            '"gray_acted"',
            '"all_mercenary"',
            '"pike_acted"',
            '"monk_acted"',
            '"shop_necklace_serial"',
            '"battle_cache_verify"',
            '"preparation_glyph_conflict_verify"',
            '"preparation_identity_verify"',
            '"maximum_simultaneous_emulators": 12',
        ):
            self.assertIn(marker, output)
        self.assertIn('"scenarios": [\n    1,', output)
        self.assertIn('    31\n  ]', output)
        self.assertIn('"--mercenary-class",\n        "0x6C"', output)
        self.assertIn('"--hired-count",\n        "1"', output)
        self.assertIn('monk-probe-normal.md', output)


if __name__ == "__main__":
    unittest.main()

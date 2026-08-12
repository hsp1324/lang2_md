import json
from pathlib import Path
import unittest

from tools.release_delta_inventory import (
    CANDIDATE_SHA256,
    DEFAULT_CANDIDATE,
    PUBLIC_CANDIDATE,
    PUBLIC_CANDIDATE_CHECKSUM,
    PUBLIC_CANDIDATE_SHA256,
    PUBLIC_MANIFEST,
    PUBLIC_RELEASE,
    analyze_delta,
    markdown_report,
    sha256,
)
from tools.capture_class_change_application import runtime_progress


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_JSON = ROOT / "localization/release_delta_5ed9_to_99fd.json"
INVENTORY_MARKDOWN = ROOT / "docs/release_delta_5ed9_to_99fd.md"


class ReleaseDeltaInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))

    def test_classifier_accounts_for_every_changed_byte(self) -> None:
        baseline = bytes(16)
        candidate = bytearray(baseline)
        candidate[1:3] = b"\x01\x02"
        candidate[10] = 3
        result = analyze_delta(
            baseline,
            bytes(candidate),
            [
                {"owner": "first", "start": 0, "end": 4},
                {"owner": "second", "start": 8, "end": 12},
            ],
        )
        self.assertEqual(result["changed_byte_count"], 3)
        self.assertEqual(result["unclassified_changed_byte_count"], 0)
        self.assertEqual(
            {
                row["owner"]: row["changed_byte_count"]
                for row in result["owners"]
            },
            {"first": 2, "second": 1},
        )

        candidate = bytearray(candidate)
        candidate[15] = 4
        result = analyze_delta(
            baseline,
            bytes(candidate),
            [{"owner": "known", "start": 0, "end": 12}],
        )
        self.assertEqual(result["unclassified_changed_byte_count"], 1)

    def test_checked_release_delta_is_complete(self) -> None:
        delta = self.result["delta"]
        self.assertTrue(self.result["complete"])
        self.assertEqual(delta["changed_byte_count"], 2244)
        self.assertEqual(delta["unchanged_byte_count"], 4192060)
        self.assertEqual(delta["unclassified_changed_byte_count"], 0)
        self.assertFalse(
            self.result["scope"]["scenario_event_or_ui_code_changed"]
        )
        self.assertFalse(
            self.result["scope"]["normal_game_balance_changed"]
        )

    def test_owner_counts_are_locked(self) -> None:
        self.assertEqual(
            {
                row["owner"]: row["changed_byte_count"]
                for row in self.result["delta"]["owners"]
            },
            {
                "bald_custom_sprite": 0,
                "header_checksum": 2,
                "loren_custom_sprite": 94,
                "shaman_commander_sprites": 1788,
                "shaman_generic_sprite": 256,
                "shaman_sprite_pointers": 16,
                "villain_montage_records": 88,
            },
        )

    def test_historical_candidate_and_public_release_are_not_conflated(self) -> None:
        self.assertNotEqual(DEFAULT_CANDIDATE, PUBLIC_CANDIDATE)
        self.assertIn("ko-99fd", DEFAULT_CANDIDATE.name)
        self.assertEqual(
            self.result["candidate"]["sha256"],
            CANDIDATE_SHA256,
        )
        public = PUBLIC_CANDIDATE.read_bytes()
        self.assertEqual(PUBLIC_RELEASE, "v1.3.6")
        self.assertEqual(sha256(public), PUBLIC_CANDIDATE_SHA256)
        self.assertEqual(
            public[0x18E:0x190].hex().upper(),
            PUBLIC_CANDIDATE_CHECKSUM,
        )
        manifest = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
        normal = next(
            row for row in manifest["targets"] if row["id"] == "normal"
        )
        self.assertEqual(manifest["release"], PUBLIC_RELEASE)
        self.assertEqual(normal["output_sha256"], PUBLIC_CANDIDATE_SHA256)

    def test_live_evidence_is_retained_and_hash_locked(self) -> None:
        self.assertEqual(len(self.result["live_evidence"]), 10)
        owners = {row["owner"] for row in self.result["live_evidence"]}
        self.assertEqual(
            owners,
            {
                "loren_custom_sprite",
                "shaman_commander_sprites",
                "shaman_generic_sprite",
                "shaman_sprite_pointers",
                "villain_montage_records",
            },
        )
        for row in self.result["live_evidence"]:
            path = ROOT / row["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(sha256(path.read_bytes()), row["sha256"])

    def test_shaman_gst_contains_the_verified_application_result(self) -> None:
        gst = (
            ROOT / "captures/analysis/99fd_release_shaman.gst"
        ).read_bytes()
        self.assertEqual(runtime_progress(gst, 0), (0x0A, 1, 1, 0))

    def test_generated_markdown_is_current(self) -> None:
        self.assertEqual(
            INVENTORY_MARKDOWN.read_text(encoding="utf-8"),
            markdown_report(self.result),
        )


if __name__ == "__main__":
    unittest.main()

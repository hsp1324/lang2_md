from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from tools import build_preparation_review_contact_sheets as sheets
from tools import record_v137_preparation_visual_review as review


class V137PreparationVisualReviewTests(unittest.TestCase):
    def make_case(self, root: Path) -> tuple[Path, Path, argparse.Namespace]:
        capture_root = root / "captures"
        review_root = root / "reviews"
        case_root = capture_root / "pure/s01/unit-run"
        pre = case_root / "pre"
        for relative in (
            "root.png",
            "allied/commander_01_root.png",
            "arrangement/menu.png",
            "arrangement/returned_menu.png",
            "fixed/map_entry.png",
            "fixed/record_00.png",
        ):
            path = pre / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (320, 240), "navy").save(path)
        for name in (
            "menu.png",
            "item_list.png",
            "returned_unfocused.png",
            "returned_focused.png",
        ):
            path = case_root / "shop" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (320, 240), "navy").save(path)
        evidence = {
            "status": "captured_exact_unreviewed",
            "profile": "pure",
            "scenario": 1,
            "run_id": "unit-run",
            "expected_pair_count": 1,
            "actual_pair_count": 1,
            "capture_pairs": [{"byte_identical": True}],
            "scenario_identity": {
                "status": "pass",
                "requested_scenario": 1,
                "identified_scenario": 1,
            },
        }
        (case_root / "evidence.json").write_text(
            json.dumps(evidence), encoding="utf-8"
        )
        seed = root / "fresh.gst"
        seed.write_bytes(b"fresh")
        candidate = root / "pure.md"
        candidate.write_bytes(b"candidate")
        plan = {
            "scenario": 1,
            "rom": {
                "path": str(candidate),
                "sha256": sheets.sha256(candidate),
            },
            "seed_gst": {
                "path": str(seed),
                "sha256": sheets.sha256(seed),
            },
        }
        (case_root / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        build_args = argparse.Namespace(
            capture_root=capture_root,
            output_root=review_root,
            profile="pure",
            scenario=1,
            run_id="unit-run",
            overwrite=False,
        )
        sheets.build_manifest(build_args)
        record_args = argparse.Namespace(
            review_root=review_root,
            capture_root=capture_root,
            profile="pure",
            scenario=1,
            run_id="unit-run",
            approve=list(review.REQUIREMENT_IDS),
            reviewer="unit-reviewer",
            reviewed_at="2026-08-11T12:00:00+09:00",
            note=["all surfaces inspected"],
        )
        return capture_root, review_root, record_args

    def test_review_requires_and_records_every_visual_item(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, review_root, args = self.make_case(Path(temporary))
            manifest = review.record_review(args)
            decision = manifest["review_decision"]
            self.assertEqual(manifest["status"], "manual_review_pass")
            self.assertEqual(
                decision["approved_requirement_ids"],
                list(review.REQUIREMENT_IDS),
            )
            self.assertEqual(decision["reviewed_source_count"], 10)
            stored = review.load_json(
                review_root / "pure/s01/unit-run/manifest.json"
            )
            self.assertEqual(stored["review_decision"]["reviewer"], "unit-reviewer")

    def test_review_rejects_missing_item_or_changed_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            capture_root, review_root, args = self.make_case(Path(temporary))
            args.approve = list(review.REQUIREMENT_IDS[:-1])
            with self.assertRaisesRegex(ValueError, "every requirement"):
                review.record_review(args)
            source = capture_root / "pure/s01/unit-run/pre/root.png"
            source.write_bytes(b"changed")
            manifest = review.load_json(
                review_root / "pure/s01/unit-run/manifest.json"
            )
            with self.assertRaisesRegex(ValueError, "review source changed"):
                review.verify_manifest_files(
                    manifest,
                    pre_root=capture_root / "pure/s01/unit-run/pre",
                )

    def test_review_rejects_a_sheet_not_composed_from_bound_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            capture_root, review_root, _ = self.make_case(Path(temporary))
            manifest_path = review_root / "pure/s01/unit-run/manifest.json"
            manifest = review.load_json(manifest_path)
            sheet_path = review.resolve_report_path(
                manifest["groups"][0]["sheets"][0]["path"]
            )
            Image.new("RGB", (640, 520), "red").save(sheet_path)
            manifest["groups"][0]["sheets"][0]["sha256"] = sheets.sha256(
                sheet_path
            )
            with self.assertRaisesRegex(ValueError, "pixels differ"):
                review.verify_manifest_files(
                    manifest,
                    pre_root=capture_root / "pure/s01/unit-run/pre",
                )


if __name__ == "__main__":
    unittest.main()

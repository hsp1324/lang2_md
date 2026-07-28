import json
from pathlib import Path
import tempfile
import unittest

from tools import hard_mode_playtest as playtest


class HardModePlaytestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = playtest.current_identity()

    def test_initial_manifest_requires_all_31_scenarios(self):
        manifest = playtest.initial_manifest(self.identity)
        self.assertEqual(
            [row["number"] for row in manifest["scenarios"]],
            list(range(1, 32)),
        )
        self.assertEqual(manifest["coverage"]["cleared_count"], 0)
        self.assertFalse(manifest["coverage"]["complete"])
        self.assertEqual(
            manifest["hard_release"]["sha256"],
            "142580f8ff9021f011ae5da186c7685f9ed7f7bd01d1ebdb9959148f9691cd27",
        )
        self.assertEqual(
            manifest["hard_release"]["rom_path"],
            "roms/builds/Langrisser II (Korean Hard T1.0.0 B1.0.0).md",
        )
        lineage = manifest["hard_release"]["verification_lineage"]
        self.assertEqual(
            lineage["runtime_source_sha256"],
            "18f1203c32e66f660b84897cebe372c89e3c7d7787690abc5b62a84f470554ac",
        )
        self.assertEqual(
            lineage["cosmetic_delta_status"],
            "verified_cosmetic_only_delta",
        )
        self.assertEqual(
            lineage["post_release_candidate_delta_status"],
            "verified_ui_sprite_only_delta",
        )
        self.assertEqual(lineage["current_class_spot_checks_passed"], 6)

    def test_cleared_attempt_requires_rating_and_evidence(self):
        manifest = playtest.initial_manifest(self.identity)
        with self.assertRaisesRegex(ValueError, "require --difficulty"):
            playtest.record_attempt(manifest, 1, "cleared")
        with self.assertRaisesRegex(ValueError, "require --evidence"):
            playtest.record_attempt(
                manifest,
                1,
                "cleared",
                difficulty="target",
            )
        with tempfile.NamedTemporaryFile(
            dir=playtest.ROOT,
            suffix=".png",
        ) as evidence:
            Path(evidence.name).write_bytes(b"next scenario")
            playtest.record_attempt(
                manifest,
                1,
                "cleared",
                difficulty="target",
                clear_turns=12,
                retry_count=1,
                notes="balanced",
                evidence_paths=[evidence.name],
                recorded_at="2026-07-28T00:00:00+00:00",
            )
            self.assertEqual(manifest["coverage"]["cleared_scenarios"], [1])
            self.assertEqual(
                playtest.effective_result(
                    manifest["scenarios"][0],
                    self.identity["sha256"],
                ),
                "cleared",
            )

    def test_changed_candidate_marks_old_result_stale(self):
        manifest = playtest.initial_manifest(self.identity)
        with tempfile.NamedTemporaryFile(
            dir=playtest.ROOT,
            suffix=".png",
        ) as evidence:
            Path(evidence.name).write_bytes(b"next scenario")
            playtest.record_attempt(
                manifest,
                1,
                "cleared",
                difficulty="hard",
                evidence_paths=[evidence.name],
                recorded_at="2026-07-28T00:00:00+00:00",
            )
            changed = dict(self.identity)
            changed["sha256"] = "0" * 64
            playtest.rebase_candidate(manifest, changed)
            self.assertEqual(manifest["coverage"]["cleared_count"], 0)
            self.assertEqual(manifest["coverage"]["stale_scenarios"], [1])

    def test_evidence_is_hash_locked(self):
        manifest = playtest.initial_manifest(self.identity)
        with tempfile.NamedTemporaryFile(
            dir=playtest.ROOT,
            suffix=".png",
        ) as evidence:
            Path(evidence.name).write_bytes(b"capture")
            playtest.record_attempt(
                manifest,
                1,
                "blocked",
                difficulty="too_hard",
                evidence_paths=[evidence.name],
                recorded_at="2026-07-28T00:00:00+00:00",
            )
            playtest.validate_manifest(manifest, self.identity)
            Path(evidence.name).write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "changed playtest evidence"):
                playtest.validate_manifest(manifest, self.identity)

    def test_checked_in_manifest_and_document_are_current(self):
        manifest = json.loads(
            playtest.DEFAULT_RESULTS.read_text(encoding="utf-8")
        )
        playtest.validate_manifest(manifest, self.identity)
        self.assertEqual(
            playtest.DEFAULT_MARKDOWN.read_text(encoding="utf-8"),
            playtest.render_markdown(manifest),
        )


if __name__ == "__main__":
    unittest.main()

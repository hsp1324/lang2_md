import json
from pathlib import Path
import tempfile
import unittest

from tools import hard_mode_playtest as playtest


class HardModePlaytestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build = playtest.load_json(playtest.DEFAULT_BUILD)
        build_sha256 = build["hard"]["sha256"]
        runtime_sha256 = playtest.load_json(
            playtest.DEFAULT_RUNTIME
        )["hard_rom"]["sha256"]
        first_turn_sha256 = playtest.load_json(
            playtest.DEFAULT_FIRST_TURN
        )["hard_rom"]["sha256"]
        if {runtime_sha256, first_turn_sha256} != {build_sha256}:
            raise unittest.SkipTest(
                "retained legacy hard-mode playtest manifests do not match "
                "the current candidate; current v1.3.7 runtime acceptance "
                "is performed by the v1.3.7 final gate"
            )
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
            "227e7a25818860ebd674d62bda3ca748901aaa45f0919c3eb1ae4340157742bd",
        )
        self.assertEqual(
            manifest["hard_release"]["rom_path"],
            "roms/builds/Langrisser II (Korean Hard T1.0.0 B1.0.0).md",
        )
        lineage = manifest["hard_release"]["verification_lineage"]
        self.assertEqual(
            lineage["runtime_source_sha256"],
            "227e7a25818860ebd674d62bda3ca748901aaa45f0919c3eb1ae4340157742bd",
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
        readiness = manifest["hard_release"]["implementation_readiness"]
        self.assertTrue(readiness["complete"])
        self.assertEqual(
            readiness["pending_features"],
            [],
        )
        features = {
            feature["id"]: feature
            for feature in readiness["features"]
        }
        self.assertTrue(
            features["scenario_curve_and_commander_stats"]["applied"]
        )
        self.assertTrue(features["enemy_soldier_corrections"]["applied"])
        self.assertEqual(
            features["stronger_mercenary_replacements"][
                "applied_slot_count"
            ],
            304,
        )
        self.assertTrue(
            features["late_summon_unit_replacements"]["applied"]
        )
        self.assertEqual(
            features["late_summon_unit_replacements"][
                "applied_slot_count"
            ],
            2,
        )
        self.assertTrue(manifest["coverage"]["implementation_complete"])
        self.assertFalse(manifest["coverage"]["complete"])

    def test_all_clears_complete_when_every_approved_feature_is_applied(self):
        manifest = playtest.initial_manifest(self.identity)
        digest = self.identity["sha256"]
        for row in manifest["scenarios"]:
            row["attempts"].append({
                "candidate_sha256": digest,
                "result": "cleared",
                "difficulty": "target",
                "evidence": [{"path": "unused", "sha256": "unused"}],
            })
        playtest.refresh(manifest)
        self.assertTrue(manifest["coverage"]["scenario_clear_complete"])
        self.assertTrue(manifest["coverage"]["implementation_complete"])
        self.assertTrue(manifest["coverage"]["complete"])
        self.assertEqual(
            manifest["status"],
            "complete",
        )

    def test_implementation_audit_rejects_a_missing_approval_decision(self):
        build = playtest.load_json(playtest.DEFAULT_BUILD)
        plan = playtest.load_json(playtest.DEFAULT_PLAN)
        approval = playtest.load_json(playtest.DEFAULT_APPROVAL)
        approval["approval"]["decisions"][
            "late_summon_unit_start_and_ratio"
        ] = None
        with self.assertRaisesRegex(ValueError, "missing decisions"):
            playtest.implementation_readiness(build, plan, approval)

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

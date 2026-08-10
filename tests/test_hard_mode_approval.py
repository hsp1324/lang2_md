from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest

from tools import hard_mode_approval
from tools import hard_mode_baseline


ROOT = Path(__file__).resolve().parents[1]
NORMAL_ROM = ROOT / "roms/releases/Langrisser II (Korean v1.0.0).md"
APPROVAL = ROOT / "localization/hard_mode_approval.json"


class HardModeApprovalTests(unittest.TestCase):
    def test_checked_in_manifest_records_the_user_standard_hard_approval(self):
        model = hard_mode_approval.load_manifest(APPROVAL)
        self.assertEqual(model["status"], "approved")
        self.assertEqual(
            model["approval"]["confirmation"],
            "표준 하드로 해줘",
        )
        self.assertTrue(model["build_gate"]["may_build_hard_mode_rom"])
        self.assertTrue(model["build_gate"]["may_apply_balance_values"])

    def test_checked_in_manifest_authorizes_the_builder(self):
        self.assertEqual(
            hard_mode_approval.require_approved(APPROVAL)["status"],
            "approved",
        )

    def test_stale_pending_manifest_can_be_refreshed(self):
        stale = hard_mode_approval.pending_manifest()
        stale["proposal_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approval.json"
            path.write_text(
                json.dumps(stale, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.hard_mode_approval",
                    "--manifest",
                    str(path),
                    "--write-pending",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                hard_mode_approval.load_manifest(path),
                hard_mode_approval.pending_manifest(),
            )

    def test_wrong_confirmation_cannot_create_approval(self):
        with self.assertRaisesRegex(ValueError, "confirmation must be exactly"):
            hard_mode_approval.approved_manifest("승인")

    def test_exact_confirmation_approves_all_five_decisions(self):
        model = hard_mode_approval.approved_manifest(
            "표준 하드로 해줘",
            approved_at="2026-07-28T00:00:00+00:00",
        )
        hard_mode_approval.validate_manifest(model)
        self.assertEqual(model["status"], "approved")
        self.assertEqual(
            model["approval"]["decisions"],
            hard_mode_approval.DECISION_APPROVAL_VALUES,
        )
        self.assertEqual(
            set(model["approval"]["decisions"]),
            set(hard_mode_approval.REQUIRED_DECISIONS),
        )
        self.assertTrue(model["build_gate"]["may_build_hard_mode_rom"])
        self.assertTrue(model["build_gate"]["may_apply_balance_values"])

    def test_approved_manifest_is_loadable_by_future_builders(self):
        model = hard_mode_approval.approved_manifest(
            "표준 하드로 해줘",
            approved_at="2026-07-28T00:00:00+00:00",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approval.json"
            hard_mode_approval.write_manifest(path, model)
            self.assertEqual(
                hard_mode_approval.require_approved(path),
                model,
            )

    def test_proposal_hash_covers_values_pairs_exceptions_and_normal_release(self):
        subject = hard_mode_approval.approval_subject()
        self.assertEqual(
            subject["proposal"]["id"],
            "standard_hard_runestone_v1",
        )
        self.assertEqual(
            len(subject["mercenary_policy"]["conservative_pairs"]),
            len(hard_mode_baseline.CONSERVATIVE_MERCENARY_UPGRADE_PAIRS),
        )
        self.assertEqual(
            len(subject["mercenary_policy"]["conditional_role_aware_pairs"]),
            len(
                hard_mode_baseline
                .CONDITIONAL_ROLE_AWARE_MERCENARY_UPGRADE_PAIRS
            ),
        )
        self.assertEqual(
            sorted(subject["secret_scenario_policy"]),
            ["28_X1", "29_X2", "30_X3", "31_X4"],
        )
        self.assertEqual(
            subject["normal_release_invariant"]["sha256"],
            hard_mode_baseline.NORMAL_SHA256,
        )
        self.assertEqual(
            hard_mode_approval.subject_sha256(),
            hashlib.sha256(
                json.dumps(
                    subject,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
        )

    def test_gate_work_does_not_change_the_normal_release(self):
        if not NORMAL_ROM.is_file():
            self.skipTest("ignored v1.0.0 normal reference ROM is absent")
        self.assertEqual(
            hashlib.sha256(NORMAL_ROM.read_bytes()).hexdigest(),
            hard_mode_baseline.NORMAL_SHA256,
        )


if __name__ == "__main__":
    unittest.main()

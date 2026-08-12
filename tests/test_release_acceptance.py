import json
from pathlib import Path
import tempfile
import unittest

from tools import release_acceptance


ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "roms/builds/Langrisser II (Korean Normal v1.3.6).md"


class ReleaseAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = release_acceptance.build_inventory(ROM)

    def test_all_goal_requirements_pass(self):
        self.assertTrue(self.inventory["complete"])
        self.assertEqual(
            [row["id"] for row in self.inventory["requirements"]],
            list(range(1, 9)),
        )
        failures = [
            (row["id"], check["label"])
            for row in self.inventory["requirements"]
            for check in row["checks"]
            if not check["passed"]
        ]
        self.assertEqual(failures, [])

    def test_checked_reports_match_public_release(self):
        self.assertEqual(
            json.loads(
                release_acceptance.JSON_OUTPUT.read_text(encoding="utf-8")
            ),
            json.loads(json.dumps(self.inventory, ensure_ascii=False)),
        )
        self.assertEqual(
            release_acceptance.MARKDOWN_OUTPUT.read_text(encoding="utf-8"),
            release_acceptance.render_markdown(self.inventory),
        )

    def test_release_identity_is_locked(self):
        release = self.inventory["release"]
        self.assertEqual(release["size"], 0x400000)
        self.assertEqual(release["header_checksum"], "1F84")
        self.assertEqual(
            release["sha256"],
            "b74359800a697eea5e85d7942ac712b74360bbd8b43ff2082b88d009e94a370a",
        )

    def test_verification_lineage_is_not_relabelled(self):
        lineage = self.inventory["verification_lineage"]
        self.assertEqual(lineage["runtime_matrix_checksum"], "1AB2")
        self.assertEqual(
            lineage["last_full_game_baseline_checksum"],
            "54C2",
        )
        self.assertEqual(lineage["candidate_checksum"], "1F84")
        self.assertEqual(lineage["candidate_delta_changed_bytes"], 725)
        self.assertEqual(
            lineage["candidate_delta_unclassified_bytes"],
            0,
        )

    def test_editor_noop_roundtrip_preserves_release(self):
        production = ROM.read_bytes()
        reference = (
            ROOT / "roms/original/Langrisser II (Japan).md"
        ).read_bytes()
        self.assertEqual(
            release_acceptance.editor_noop_roundtrip(
                production,
                reference,
            ),
            production,
        )

    def test_hard_mode_is_required_but_not_started(self):
        hard_mode = self.inventory["hard_mode_follow_up"]
        self.assertTrue(hard_mode["required"])
        self.assertEqual(
            hard_mode["status"],
            "balance_discussion_required",
        )
        self.assertTrue(hard_mode["normal_release_must_remain_unchanged"])
        self.assertFalse(hard_mode["implementation_started"])

    def test_wrong_rom_cannot_pass(self):
        damaged = bytearray(ROM.read_bytes())
        damaged[0x200000] ^= 0x01
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "damaged.md"
            path.write_bytes(damaged)
            inventory = release_acceptance.build_inventory(path)
        self.assertFalse(inventory["complete"])
        release_checks = inventory["requirements"][-1]["checks"]
        self.assertFalse(
            next(
                row for row in release_checks if row["label"] == "SHA-256"
            )["passed"]
        )

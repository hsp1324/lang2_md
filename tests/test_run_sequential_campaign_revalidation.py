from __future__ import annotations

import argparse
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import run_blastem_sequence as sequence
from tools import run_sequential_campaign_revalidation as campaign


ROOT = Path(__file__).resolve().parents[1]


class SequentialCampaignRevalidationTests(unittest.TestCase):
    def test_xvfb_supervisor_restarts_only_a_dead_display(self) -> None:
        args = argparse.Namespace(
            xvfb=Path("/tmp/fake-xvfb"),
            xvfb_library_path=Path("/tmp/fake-library"),
        )
        alive = mock.Mock()
        alive.poll.return_value = None
        replacement = mock.Mock()
        replacement.poll.return_value = None
        supervisor = campaign.XvfbSupervisor(args, ":777", alive)

        with (
            mock.patch.object(campaign.parallel, "stop_process") as stop,
            mock.patch.object(
                campaign.parallel,
                "start_xvfb",
                return_value=replacement,
            ) as start,
        ):
            self.assertFalse(supervisor.ensure_alive())
            stop.assert_not_called()
            start.assert_not_called()

            alive.poll.return_value = 1
            self.assertTrue(supervisor.ensure_alive())
            stop.assert_called_once_with(alive)
            start.assert_called_once_with(
                args.xvfb,
                args.xvfb_library_path,
                ":777",
            )

        self.assertIs(supervisor.process, replacement)
        self.assertEqual(supervisor.restarts, 1)

    def test_route_covers_every_scenario_once_in_campaign_order(self) -> None:
        self.assertEqual(len(campaign.FULL_ROUTE_ORDER), 31)
        self.assertEqual(set(campaign.FULL_ROUTE_ORDER), set(range(1, 32)))
        self.assertEqual(campaign.FULL_ROUTE_ORDER[:12], tuple(range(1, 13)))
        self.assertEqual(campaign.FULL_ROUTE_ORDER[12], 28)
        self.assertEqual(campaign.FULL_ROUTE_ORDER[-2:], (31, 27))

    def test_secret_scenarios_return_to_the_stock_main_route(self) -> None:
        self.assertEqual(
            {scenario: campaign.NEXT_SCENARIO[scenario] for scenario in (28, 29, 30, 31)},
            {28: 13, 29: 20, 30: 23, 31: 27},
        )
        for index, scenario in enumerate(campaign.FULL_ROUTE_ORDER):
            self.assertEqual(
                campaign.expected_input_scenario(index),
                1 if index == 0 else campaign.NEXT_SCENARIO[campaign.FULL_ROUTE_ORDER[index - 1]],
            )

    def test_snapshot_reads_exact_serialized_roster_and_inventory(self) -> None:
        gst_size = (
            sequence.GST_WORK_RAM_FILE_OFFSET
            + max(address + size for address, size in sequence.MANUAL_SLOT_WORK_RAM_SEGMENTS)
        )
        gst = bytearray(gst_size)
        record = bytearray(sequence.MANUAL_SLOT_CHECKSUM_DATA_SIZE)
        record[0:2] = (10).to_bytes(2, "big")
        commander = sequence.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET + 8 * sequence.MANUAL_SLOT_COMMANDER_RECORD_SIZE
        record[commander + sequence.MANUAL_SLOT_COMMANDER_CLASS_OFFSET] = 0x07
        record[commander + sequence.MANUAL_SLOT_COMMANDER_MP_OFFSET] = 1
        record[commander + sequence.MANUAL_SLOT_COMMANDER_LEVEL_OFFSET] = 10
        record[commander + sequence.MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET] = 15
        record[commander + sequence.MANUAL_SLOT_COMMANDER_AT_OFFSET] = 22
        record[commander + sequence.MANUAL_SLOT_COMMANDER_DF_OFFSET] = 20
        item = sequence.MANUAL_SLOT_ITEM_INVENTORY_OFFSET
        record[item : item + 4] = bytes((0x1A, 0xFF, 0x03, 0x01))
        record[item + 4 :] = b"\xFF" * (len(record) - item - 4)
        cursor = 0
        for address, size in sequence.MANUAL_SLOT_WORK_RAM_SEGMENTS:
            start = sequence.GST_WORK_RAM_FILE_OFFSET + address
            gst[start : start + size] = record[cursor : cursor + size]
            cursor += size
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.gst"
            path.write_bytes(gst)
            snapshot = campaign.state_snapshot(path)
        self.assertEqual(snapshot["scenario"], 10)
        self.assertEqual(
            snapshot["commanders"][8],
            {
                "commander_id": 9,
                "class_id": 0x07,
                "mp": 1,
                "level": 10,
                "experience": 15,
                "at": 22,
                "df": 20,
                "hire_mask": 0,
            },
        )
        self.assertEqual(
            snapshot["inventory"],
            [
                {"slot": 0, "item_id": 0x1A, "owner": 0xFF},
                {"slot": 1, "item_id": 0x03, "owner": 0x01},
            ],
        )

    def test_plan_has_a_strict_ordered_chain_per_profile(self) -> None:
        args = argparse.Namespace(
            profiles=["pure", "normal", "hard"],
            probe_root=ROOT / "tmp/probes",
            run_id="test-chain",
        )
        report = campaign.build_plan(args)
        self.assertTrue(report["continuous_save_chain"])
        self.assertEqual(len(report["tasks"]), 93)
        normal = [row for row in report["tasks"] if row["profile"] == "normal"]
        self.assertEqual([row["scenario"] for row in normal], list(campaign.FULL_ROUTE_ORDER))
        self.assertEqual(normal[12]["expected_input_scenario"], 13)
        self.assertEqual(normal[12]["expected_next_scenario"], 13)

    def test_profile_run_rejects_a_changed_record_between_chapters(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            seed = root / "seed.gst"
            produced = root / "save_menu.gst"
            seed.write_bytes(b"seed")
            produced.write_bytes(b"produced")
            args = argparse.Namespace(
                seed_gsts={"normal": seed},
                release_roms={
                    "normal": {"path": "normal.md", "sha256": "1" * 64}
                },
                attempts=1,
                output_root=root,
                run_id="continuity",
            )
            snapshots = [
                {"scenario": 1, "record_sha256": "seed"},
                {"scenario": 1, "record_sha256": "seed"},
                {"scenario": 2, "record_sha256": "chapter-1-output"},
                {"scenario": 2, "record_sha256": "mutated-before-chapter-2"},
                {"scenario": 1, "record_sha256": "seed"},
            ]
            with (
                mock.patch.object(campaign, "FULL_ROUTE_ORDER", (1, 2)),
                mock.patch.object(campaign, "NEXT_SCENARIO", {1: 2, 2: None}),
                mock.patch.object(
                    campaign,
                    "state_snapshot",
                    side_effect=snapshots,
                ),
                mock.patch.object(
                    campaign.result_parallel,
                    "run_one",
                    return_value={"returncode": 0, "status": "pass"},
                ),
                mock.patch.object(
                    campaign,
                    "save_menu_gst",
                    return_value=produced,
                ),
            ):
                report = campaign.run_profile(args, "normal", ":777")

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["results"][-1]["scenario"], 2)
        self.assertEqual(
            report["results"][-1]["status"],
            "save_chain_record_mismatch",
        )

    def test_missing_required_save_is_retried_before_failing_step(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            seed = root / "seed.gst"
            seed.write_bytes(b"seed")
            output = root / "task"
            produced = output / "states/save_menu.gst"
            args = argparse.Namespace(
                seed_gsts={"normal": seed},
                release_roms={
                    "normal": {"path": "normal.md", "sha256": "1" * 64}
                },
                attempts=2,
                output_root=root,
                run_id="retry-save",
            )
            calls = 0

            def run_one(*_args):
                nonlocal calls
                calls += 1
                output.mkdir(parents=True, exist_ok=True)
                if calls == 2:
                    produced.parent.mkdir(parents=True, exist_ok=True)
                    produced.write_bytes(b"next")
                return {"returncode": 0, "status": "pass"}

            def snapshot(path: Path):
                if path == produced:
                    return {"scenario": 2, "record_sha256": "next"}
                return {"scenario": 1, "record_sha256": "seed"}

            with (
                mock.patch.object(campaign, "FULL_ROUTE_ORDER", (1,)),
                mock.patch.object(campaign, "NEXT_SCENARIO", {1: 2}),
                mock.patch.object(campaign, "state_snapshot", side_effect=snapshot),
                mock.patch.object(
                    campaign.result_parallel,
                    "task_output",
                    return_value=output,
                ),
                mock.patch.object(
                    campaign.result_parallel,
                    "run_one",
                    side_effect=run_one,
                ),
                mock.patch.object(
                    campaign,
                    "save_menu_gst",
                    return_value=produced,
                ),
                mock.patch.object(
                    campaign.matrix,
                    "terminate_blastem_processes",
                ),
            ):
                report = campaign.run_profile(args, "normal", ":777")

        self.assertEqual(report["status"], "pass")
        self.assertEqual(calls, 2)
        attempts = report["results"][0]["attempt_history"]
        self.assertEqual(
            [attempt["status"] for attempt in attempts],
            ["missing_save_menu_gst", "pass"],
        )
        self.assertEqual(report["results"][0]["output_state"]["scenario"], 2)


if __name__ == "__main__":
    unittest.main()

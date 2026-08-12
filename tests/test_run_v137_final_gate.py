from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PIL import Image

from tools import run_v137_final_gate as gate


class V137FinalGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        canonical_source = gate.DEFAULT_SOURCE_ROM.read_bytes()
        self.source = self.root / "source.md"
        self.source.write_bytes(canonical_source)
        self.release_paths = {}
        self.releases = {}
        for index, profile in enumerate(gate.PROFILES, 1):
            path = self.root / f"{profile}.md"
            payload = bytearray(canonical_source)
            payload.extend(
                b"\xFF" * (gate.RELEASE_ROM_BYTES - len(canonical_source))
            )
            payload[0x3FEE00 + index] = index
            trigger = gate.scenario6_probe.builder.SCENARIO6_RUNESTONE_TRIGGER
            accessible = (
                gate.scenario6_probe.builder.SCENARIO6_RUNESTONE_TRIGGER_ACCESSIBLE
            )
            payload[trigger:trigger + len(accessible)] = accessible
            for class_id, gauge in {
                0x04: 24,
                0x05: 32,
                0x08: 16,
                0x09: 24,
                0x0A: 24,
                0x2B: 32,
                0x2C: 24,
            }.items():
                offset = (
                    gate.class_probe.CLASS_RECORD_TABLE
                    + class_id * gate.class_probe.CLASS_RECORD_SIZE
                    + gate.class_probe.CLASS_EXPERIENCE_FACTOR_OFFSET
                )
                payload[offset] = gauge // 8
            checksum = sum(
                int.from_bytes(payload[offset : offset + 2], "big")
                for offset in range(0x200, len(payload), 2)
            ) & 0xFFFF
            payload[0x18E:0x190] = checksum.to_bytes(2, "big")
            path.write_bytes(payload)
            self.release_paths[profile] = path
            digest = gate.sha256_path(path)
            self.releases[profile] = gate.hash_locked_release_snapshot(
                path, digest
            )
        self.output = self.root / "gate-output"
        identity_hashes = {
            profile: str(self.releases[profile]["sha256"])
            for profile in gate.PROFILES
        }
        for attribute, value in (
            ("RELEASE_ROM_SHA256", identity_hashes),
            ("RELEASE_IDENTITY_FINALIZED", True),
            ("RELEASE_IDENTITY_GENERATION", "unit-test-final"),
        ):
            patcher = mock.patch.object(gate.release_identity, attribute, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        blank_label_fingerprint = hashlib.sha256(
            bytes(
                (gate.JOIN_CANDIDATE_LABEL_BOX[2]
                - gate.JOIN_CANDIDATE_LABEL_BOX[0])
                * (gate.JOIN_CANDIDATE_LABEL_BOX[3]
                - gate.JOIN_CANDIDATE_LABEL_BOX[1])
            )
        ).hexdigest()
        fingerprint_patch = mock.patch.object(
            gate,
            "JOIN_CANDIDATE_LABEL_FINGERPRINT",
            {slug: blank_label_fingerprint for slug in gate.JOIN_CHARACTER},
        )
        fingerprint_patch.start()
        self.addCleanup(fingerprint_patch.stop)
        scope_verifier_patch = mock.patch.dict(
            gate.SUPPLEMENTAL_SCOPE_VERIFIERS,
            {
                requirement.verifier_id: gate.verify_scope_acceptance_summary
                for requirement in gate.REQUIRED_SCOPE_CONTRACT
            },
            clear=True,
        )
        scope_verifier_patch.start()
        self.addCleanup(scope_verifier_patch.stop)
        self.plan = gate.build_plan(
            run_id="v137-final-test",
            output_root=self.output,
            release_roms=self.releases,
            source_rom=gate.snapshot_file(self.source),
            workers=2,
            display_base=850,
        )
        self.manifest = self.output / "plan.json"

    def write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def rewrite_join_evidence(self, row: dict[str, object]) -> None:
        evidence_path = Path(str(row["evidence_path"]))
        evidence = {
            key: value
            for key, value in row.items()
            if key not in {"attempt_history", "evidence_sha256"}
        }
        self.write_json(evidence_path, evidence)
        row["evidence_sha256"] = gate.sha256_path(evidence_path)

    @staticmethod
    def write_join_gst(
        path: Path,
        *,
        commander_id: int,
        runtime: dict[str, int],
        scenario: int,
    ) -> str:
        gst_work_ram_offset = 0x2478
        payload = bytearray(gst_work_ram_offset + 0x10000)
        runtime_start = gst_work_ram_offset + 0x603C
        for offset, value in (
            (0x00, runtime["class_id"]),
            (0x01, commander_id),
            (0x06, runtime["x"]),
            (0x07, runtime["y"]),
            (0x2E, runtime["level"]),
            (0x2F, runtime["experience"]),
            (0x39, runtime["mp"]),
            (0x3A, runtime["at"]),
            (0x3B, runtime["df"]),
        ):
            payload[runtime_start + offset] = value

        record = bytearray(0x1A6)
        record[0:2] = scenario.to_bytes(2, "big")
        commander_start = 0x030 + (commander_id - 1) * 0x018
        for offset, value in (
            (0x00, runtime["class_id"]),
            (0x01, runtime["mp"]),
            (0x02, runtime["level"]),
            (0x03, runtime["experience"]),
            (0x04, runtime["at"]),
            (0x05, runtime["df"]),
        ):
            record[commander_start + offset] = value
        record[commander_start + 0x0A:commander_start + 0x0C] = b"\x00\x00"
        for offset in range(0x156, 0x1A6, 2):
            record[offset:offset + 2] = b"\xFF\xFF"
        cursor = 0
        for address, size in ((0xA49C, 0x154), (0xBD6E, 0x002), (0xC7F2, 0x050)):
            start = gst_work_ram_offset + address
            payload[start:start + size] = record[cursor:cursor + size]
            cursor += size
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return hashlib.sha256(record).hexdigest()

    def phase(self, phase_id: str) -> dict[str, object]:
        return next(
            phase for phase in self.plan["phases"] if phase["id"] == phase_id
        )

    def summary_path(self, phase_id: str, label: str | None = None) -> Path:
        phase = self.phase(phase_id)
        entries = phase["summaries"]
        if label is None:
            self.assertEqual(len(entries), 1)
            return Path(entries[0]["path"])
        return Path(next(row["path"] for row in entries if row["label"] == label))

    def release_model(self, profile: str) -> dict[str, object]:
        return {
            "path": str(self.release_paths[profile]),
            "sha256": self.releases[profile]["sha256"],
            "bytes": gate.RELEASE_ROM_BYTES,
        }

    def materialize_passing_summaries(self) -> None:
        seeds = {}
        common_record_sha256 = hashlib.sha256(b"common-fresh-record").hexdigest()
        for profile in gate.PROFILES:
            summary = self.summary_path("fresh_s1_seed", profile)
            gst = summary.parent / "fresh_s1_preparation.gst"
            gst.parent.mkdir(parents=True, exist_ok=True)
            gst.write_bytes(f"fresh-{profile}".encode())
            digest = gate.sha256_path(gst)
            seeds[profile] = {"path": str(gst), "sha256": digest}
            self.write_json(
                summary,
                {
                    "status": "pass",
                    "command": "run",
                    "profile": profile,
                    "run_id": self.plan["run_id"],
                    "virtual_display": ":880",
                    "rom": self.release_model(profile),
                    "fresh_title_to_new_game": True,
                    "isolation": {"empty_runtime_verified": True},
                    "snapshot": {
                        "scenario": 1,
                        "record_sha256": common_record_sha256,
                    },
                    "target_roster": {
                        str(commander_id): {
                            "commander_id": commander_id,
                            **expected,
                        }
                        for commander_id, expected in gate.EXPECTED_FRESH_ROSTER.items()
                    },
                    "scenario_1_gst": seeds[profile],
                },
            )

        probe_rows = []
        probes = {}
        probe_summary = self.summary_path("current_result_probes")
        source_payload = self.source.read_bytes()
        for scenario in gate.SCENARIOS:
            row = {"scenario": scenario, "status": "pass"}
            if scenario == 27:
                row["builder_module"] = gate.scenario27_probe.__name__
                row["builder_kwargs"] = {"allow_balanced_input": False}
                row["diagnostic_delta"] = {}
            for profile in gate.PROFILES:
                filename = "s27-ending.md" if scenario == 27 else f"s{scenario:02d}.md"
                probe = probe_summary.parent / profile / filename
                probe.parent.mkdir(parents=True, exist_ok=True)
                if scenario == 27:
                    candidate = self.release_paths[profile].read_bytes()
                    payload = bytearray(candidate)
                    gate.scenario27_probe.patch_probe(
                        payload,
                        source_payload,
                        allow_balanced_input=profile == "hard",
                    )
                    probe.write_bytes(payload)
                    row["diagnostic_delta"][profile] = (
                        gate.diagnostic_delta_report(candidate, payload)
                    )
                else:
                    probe.write_bytes(f"probe-{profile}-{scenario}".encode())
                report = {
                    "path": str(probe),
                    "sha256": gate.sha256_path(probe),
                    "bytes": probe.stat().st_size,
                    "checksum_valid": True,
                }
                row[profile] = report
                probes[(profile, scenario)] = report
            probe_rows.append(row)
        self.write_json(
            probe_summary,
            {
                "status": "pass",
                "run_id": self.plan["run_id"],
                "candidate_roms": {
                    profile: self.release_model(profile)
                    for profile in gate.PROFILES
                },
                "source_rom": {
                    "path": str(self.source),
                    "sha256": gate.release_identity.JAPANESE_SOURCE_ROM_SHA256,
                    "expected_sha256": (
                        gate.release_identity.JAPANESE_SOURCE_ROM_SHA256
                    ),
                    "bytes": gate.release_identity.JAPANESE_SOURCE_ROM_BYTES,
                    "expected_bytes": (
                        gate.release_identity.JAPANESE_SOURCE_ROM_BYTES
                    ),
                    "hash_locked": True,
                },
                "scenarios": list(gate.SCENARIOS),
                "probe_count": 93,
                "probes": probe_rows,
            },
        )

        for phase_id, status in (
            ("preparation_s01_s31", "captured_exact_unreviewed"),
            ("gray_acted_s01_s31", "pass"),
        ):
            for profile in gate.PROFILES:
                self.write_json(
                    self.summary_path(phase_id, profile),
                    {
                        "status": "pass",
                        "profile": profile,
                        "run_id": self.plan["run_id"],
                        "rom": self.release_model(profile),
                        "seed": seeds[profile],
                        "seed_unchanged": True,
                        "scenarios": list(gate.SCENARIOS),
                        "passed_scenarios": 31,
                        "total_scenarios": 31,
                        "results": [
                            {
                                "scenario": scenario,
                                "display": ":882",
                                "returncode": 0,
                                "status": status,
                            }
                            for scenario in gate.SCENARIOS
                        ],
                    },
                )

        visual_rows = []
        preparation_root = Path(self.phase("preparation_s01_s31")["root"])
        for profile in gate.PROFILES:
            for scenario in gate.SCENARIOS:
                case_root = (
                    preparation_root
                    / profile
                    / f"s{scenario:02d}"
                    / self.plan["run_id"]
                )
                pre_root = case_root / "pre"
                source_paths = {
                    "overview": pre_root / "root.png",
                    "allied": pre_root / "allied/commander_01_root.png",
                    "arrangement": pre_root / "arrangement/menu.png",
                    "shop": case_root / "shop/menu.png",
                    "fixed": pre_root / "fixed/map_entry.png",
                }
                groups = []
                review_case_root = (
                    preparation_root
                    / "visual_review"
                    / profile
                    / f"s{scenario:02d}"
                    / self.plan["run_id"]
                )
                for group, source in source_paths.items():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    source.write_bytes(f"{profile}-{scenario}-{group}".encode())
                    sheet = review_case_root / f"{group}_01.png"
                    sheet.parent.mkdir(parents=True, exist_ok=True)
                    sheet.write_bytes(f"sheet-{profile}-{scenario}-{group}".encode())
                    groups.append(
                        {
                            "group": group,
                            "source_count": 1,
                            "sheet_count": 1,
                            "sheets": [
                                {
                                    "path": str(sheet),
                                    "sha256": gate.sha256_path(sheet),
                                    "sources": [
                                        {
                                            "path": str(source),
                                            "sha256": gate.sha256_path(source),
                                        }
                                    ],
                                }
                            ],
                        }
                    )
                evidence_path = case_root / "evidence.json"
                self.write_json(
                    evidence_path,
                    {
                        "status": "captured_exact_unreviewed",
                        "profile": profile,
                        "scenario": scenario,
                        "run_id": self.plan["run_id"],
                        "scenario_identity": {
                            "status": "pass",
                            "requested_scenario": scenario,
                            "identified_scenario": scenario,
                        },
                    },
                )
                manifest_path = review_case_root / "manifest.json"
                reviewed_at = "2026-08-11T12:00:00+09:00"
                reviewer = "unit-test-reviewer"
                self.write_json(
                    manifest_path,
                    {
                        "status": "manual_review_pass",
                        "profile": profile,
                        "scenario": scenario,
                        "run_id": self.plan["run_id"],
                        "capture_root": str(pre_root),
                        "review_requirements": [
                            {"id": value}
                            for value in gate.PREPARATION_REVIEW_REQUIREMENT_IDS
                        ],
                        "groups": groups,
                        "review_decision": {
                            "decision": "pass",
                            "reviewer": reviewer,
                            "reviewed_at": reviewed_at,
                            "approved_requirement_ids": list(
                                gate.PREPARATION_REVIEW_REQUIREMENT_IDS
                            ),
                        },
                    },
                )
                visual_rows.append(
                    {
                        "profile": profile,
                        "scenario": scenario,
                        "run_id": self.plan["run_id"],
                        "status": "pass",
                        "manifest": {
                            "path": str(manifest_path),
                            "sha256": gate.sha256_path(manifest_path),
                        },
                        "preparation_evidence": {
                            "path": str(evidence_path),
                            "sha256": gate.sha256_path(evidence_path),
                        },
                        "seed": seeds[profile],
                        "reviewer": reviewer,
                        "reviewed_at": reviewed_at,
                        "approved_requirement_ids": list(
                            gate.PREPARATION_REVIEW_REQUIREMENT_IDS
                        ),
                        "reviewed_sheet_count": 4,
                        "reviewed_source_count": 4,
                    }
                )
        self.write_json(
            self.summary_path("preparation_s01_s31", "manual-visual-review"),
            {
                "status": "pass",
                "run_id": self.plan["run_id"],
                "profiles": list(gate.PROFILES),
                "scenarios": list(gate.SCENARIOS),
                "candidate_roms": {
                    profile: self.release_model(profile)
                    for profile in gate.PROFILES
                },
                "reviewed_cases": 93,
                "required_cases": 93,
                "results": visual_rows,
            },
        )

        def scenario_for_case(case: str) -> int:
            if "jessica" in case:
                return 11
            if "keith" in case:
                return 8 if case.startswith("legacy-later") else 7
            return 11 if case.startswith("legacy-later") else 10

        def join_summary(groups: list[str], cases: tuple[str, ...]) -> dict[str, object]:
            expected_raw = {
                str(gate.JOIN_CHARACTER[slug]["commander_id"]): value
                for slug, value in gate.JOIN_RAW_EXPERIENCE.items()
            }
            wrapper_sha = "c" * 64
            expected_scenarios = sorted({scenario_for_case(case) for case in cases})
            phase_id = (
                "legacy_later_join"
                if groups == ["legacy-later"]
                else "natural_and_legacy_join"
            )
            evidence_root = (
                self.summary_path(phase_id).parent / "evidence"
            )
            pending_representatives = gate.expected_join_pending_representatives(cases)
            policy_profiles = [
                {
                    "profile": profile,
                    "candidate_rom": self.release_model(profile),
                    "wrapper_offset": "0x31E000",
                    "wrapper_size": 128,
                    "wrapper_sha256": wrapper_sha,
                    "matches_current_builder": True,
                    "raw_experience_by_commander": expected_raw,
                    "probes": [
                        {
                            "scenario": scenario,
                            "path": probes[(profile, scenario)]["path"],
                            "wrapper_sha256": wrapper_sha,
                            "byte_identical_to_release": True,
                        }
                        for scenario in expected_scenarios
                    ],
                }
                for profile in gate.PROFILES
            ]
            reports = []
            for profile in gate.PROFILES:
                rows = []
                for case in cases:
                    scenario = scenario_for_case(case)
                    slug = gate.join_character_slug(case)
                    character = gate.JOIN_CHARACTER[slug]
                    result_class, result_level, result_experience = (
                        gate.expected_join_result(case)
                    )
                    raw = gate.JOIN_RAW_EXPERIENCE[slug]
                    gauge = gate.class_probe.class_change_experience(
                        self.release_paths[profile].read_bytes(),
                        result_class,
                    )
                    runtime = {
                        "class_id": result_class,
                        "level": result_level,
                        "experience": result_experience,
                        "x": 6,
                        "y": 18,
                        "mp": 0,
                        "at": 0,
                        "df": 0,
                    }
                    candidate_runtime = {
                        "class_id": character["tier1_class"],
                        "level": 10,
                        # Stock result processing may award EXP before the
                        # LV10 choice screen appears.
                        "experience": 0x23,
                        "x": 6,
                        "y": 18,
                        "mp": 0,
                        "at": 0,
                        "df": 0,
                    }
                    pre_completion_runtime = {
                        **candidate_runtime,
                        "class_id": (
                            0x01
                            if case.startswith("legacy-")
                            else character["tier1_class"]
                        ),
                        "level": (
                            int(case.rsplit("-lv", 1)[1])
                            if case.startswith("legacy-")
                            else 10
                        ),
                        "experience": character["tier1_experience"],
                    }
                    case_root = (
                        evidence_root
                        / profile
                        / case
                        / self.plan["run_id"]
                        / "full-flow"
                        / "attempt-1"
                    )
                    gst_reports = {}
                    gst_record_sha256 = {}
                    stage_runtimes = {
                        "pre-completion": pre_completion_runtime,
                        "candidate": candidate_runtime,
                        "candidate-resumed": candidate_runtime,
                        "applied": runtime,
                        "applied-resumed": runtime,
                        "result": runtime,
                        "result-resumed": runtime,
                        "save": runtime,
                    }
                    for stage in (
                        "pre-completion",
                        "candidate",
                        "candidate-resumed",
                        "applied",
                        "applied-resumed",
                        "result",
                        "result-resumed",
                        "save",
                    ):
                        gst = case_root / f"{stage}.gst"
                        gst_record_sha256[stage] = self.write_join_gst(
                            gst,
                            commander_id=int(character["commander_id"]),
                            runtime=stage_runtimes[stage],
                            scenario=scenario + 1,
                        )
                        gst_reports[stage] = {
                            "gst": str(gst),
                            "gst_sha256": gate.sha256_path(gst),
                        }
                    capture_reports = {}
                    for stage in (
                        "candidate",
                        "candidate-resumed",
                        "candidate-selected",
                        "applied",
                        "applied-resumed",
                        "result",
                        "result-resumed",
                        "save",
                    ):
                        capture = case_root / f"{stage}.png"
                        image = Image.new("RGB", (320, 240))
                        surface_points = (
                            gate.result_surface.RESULT_POINTS
                            if stage in {"result", "result-resumed"}
                            else (
                                gate.result_surface.SAVE_POINTS
                                if stage == "save"
                                else {}
                            )
                        )
                        for point, color in surface_points.items():
                            image.putpixel(point, color)
                        image.save(capture)
                        capture_reports[stage] = {
                            "path": str(capture),
                            "sha256": gate.sha256_path(capture),
                        }
                    marker_reports = {}
                    marker_address = str(character["marker_address"])
                    marker_offset = (int(marker_address, 16) - 0x00400001) // 2
                    for stage, value in (
                        ("candidate", gate.JOIN_PENDING_MARKER),
                        ("applied", 0),
                        ("result", 0),
                        ("save", 0),
                    ):
                        marker = case_root / f"{stage}-marker.sram"
                        payload = bytearray(0x2000)
                        payload[marker_offset] = value
                        marker.write_bytes(payload)
                        marker_reports[stage] = {
                            "path": str(marker),
                            "sha256": gate.sha256_path(marker),
                            "bytes": 0x2000,
                            "source_path": str(case_root / "live/save.sram"),
                            "address": marker_address,
                            "sram_offset": f"0x{marker_offset:04X}",
                            "value": value,
                        }
                    for stage in ("candidate", "applied", "result"):
                        quicksave = case_root / f"{stage}-quicksave.gst"
                        quicksave.write_bytes(
                            Path(gst_reports[stage]["gst"]).read_bytes()
                        )
                    rows.append(
                        {
                            "status": "pass",
                            "attempt": 1,
                            "run_id": self.plan["run_id"],
                            "profile": profile,
                            "case": case,
                            "scenario": scenario,
                            "next_scenario": scenario + 1,
                            "display": ":850",
                            "virtual_display": True,
                            "seed": seeds[profile],
                            "probe": probes[(profile, scenario)],
                            "character": {
                                "commander_id": character["commander_id"],
                                "tier1_class": character["tier1_class"],
                                "candidate_labels": gate.RUNESTONE_EXPECTED[slug][
                                    "candidate_labels"
                                ],
                                "candidate_label_fingerprint": (
                                    gate.JOIN_CANDIDATE_LABEL_FINGERPRINT[slug]
                                ),
                            },
                            "selection": {
                                "selected_class": result_class,
                            },
                            "join_experience": {
                                "policy": "one_fixed_raw_grant_no_target_level_pump",
                                "profile_invariant": True,
                                "branch_invariant": True,
                                "raw_experience": raw,
                            },
                            "progression_expectation": {
                                "policy": "one_fixed_raw_grant_no_target_level_pump",
                                "profile_invariant": True,
                                "commander_id": character["commander_id"],
                                "selected_class": result_class,
                                "raw_experience": raw,
                                "class_experience_gauge": gauge,
                                "expected_result_class": result_class,
                                "expected_result_level": result_level,
                                "expected_result_experience": result_experience,
                                "reaches_another_class_choice": False,
                                "next_candidates": [],
                            },
                            "pre_completion": {
                                **gst_reports["pre-completion"],
                                "runtime": pre_completion_runtime,
                            },
                            "candidate": {
                                **gst_reports["candidate"],
                                "capture": capture_reports["candidate"],
                                "labels": gate.RUNESTONE_EXPECTED[slug][
                                    "candidate_labels"
                                ],
                                "label_fingerprint": (
                                    gate.JOIN_CANDIDATE_LABEL_FINGERPRINT[slug]
                                ),
                                "runtime": candidate_runtime,
                                "pending_join_marker": marker_reports["candidate"],
                                "pending_flush_resume": {
                                    "status": "pass",
                                    "policy": (
                                        "process_exit_flush_then_byte_identical_"
                                        "gst_cli_resume"
                                    ),
                                    "checkpoint_gst": gst_reports["candidate"][
                                        "gst"
                                    ],
                                    "checkpoint_gst_sha256": gst_reports[
                                        "candidate"
                                    ]["gst_sha256"],
                                    "runtime_quicksave": str(
                                        case_root / "candidate-quicksave.gst"
                                    ),
                                    "runtime_quicksave_sha256": gst_reports[
                                        "candidate"
                                    ]["gst_sha256"],
                                    "flushed_marker": marker_reports["candidate"],
                                    "flush": {
                                        "status": "pass",
                                        "policy": "process_exit_flush",
                                        "flushed_marker": marker_reports["candidate"],
                                        "expected_marker": gate.JOIN_PENDING_MARKER,
                                    },
                                    "expected_marker": gate.JOIN_PENDING_MARKER,
                                    "resume_method": "blastem_cli_savestate",
                                    "resume_gst_argument": gst_reports[
                                        "candidate"
                                    ]["gst"],
                                    "resumed": True,
                                },
                                "resumed_capture": capture_reports[
                                    "candidate-resumed"
                                ],
                                "resumed_gst": gst_reports["candidate-resumed"][
                                    "gst"
                                ],
                                "resumed_gst_sha256": gst_reports[
                                    "candidate-resumed"
                                ]["gst_sha256"],
                                "resumed_runtime": candidate_runtime,
                                "selected_capture": capture_reports[
                                    "candidate-selected"
                                ],
                            },
                            "applied_immediate": {
                                **gst_reports["applied"],
                                "capture": capture_reports["applied"],
                                "runtime": runtime,
                                "progression_settlement": {
                                    "status": "settled",
                                    "stock_scan_consumption": True,
                                    "selected_class": result_class,
                                    "raw_experience": raw,
                                    "class_experience_gauge": gauge,
                                    "consumed_raw_experience": (
                                        (result_level - 1) * gauge
                                    ),
                                    "remaining_raw_experience": (
                                        result_experience
                                    ),
                                    "expected_final": {
                                        "class_id": result_class,
                                        "level": result_level,
                                        "experience": result_experience,
                                    },
                                },
                                "consumed_join_marker": marker_reports["applied"],
                                "consumed_flush_resume": {
                                    "status": "pass",
                                    "policy": (
                                        "process_exit_flush_then_byte_identical_"
                                        "gst_cli_resume"
                                    ),
                                    "checkpoint_gst": gst_reports["applied"][
                                        "gst"
                                    ],
                                    "checkpoint_gst_sha256": gst_reports[
                                        "applied"
                                    ]["gst_sha256"],
                                    "runtime_quicksave": str(
                                        case_root / "applied-quicksave.gst"
                                    ),
                                    "runtime_quicksave_sha256": gst_reports[
                                        "applied"
                                    ]["gst_sha256"],
                                    "flushed_marker": marker_reports["applied"],
                                    "flush": {
                                        "status": "pass",
                                        "policy": "process_exit_flush",
                                        "flushed_marker": marker_reports["applied"],
                                        "expected_marker": 0,
                                    },
                                    "expected_marker": 0,
                                    "resume_method": "blastem_cli_savestate",
                                    "resume_gst_argument": gst_reports["applied"][
                                        "gst"
                                    ],
                                    "resumed": True,
                                },
                                "resumed_capture": capture_reports[
                                    "applied-resumed"
                                ],
                                "resumed_gst": gst_reports["applied-resumed"][
                                    "gst"
                                ],
                                "resumed_gst_sha256": gst_reports[
                                    "applied-resumed"
                                ]["gst_sha256"],
                                "resumed_runtime": runtime,
                            },
                            "battle_result": {
                                **gst_reports["result"],
                                "capture": capture_reports["result"],
                                "runtime": runtime,
                                "consumed_join_marker": marker_reports["result"],
                                "consumed_flush_resume": {
                                    "status": "pass",
                                    "policy": (
                                        "process_exit_flush_then_byte_identical_"
                                        "gst_cli_resume"
                                    ),
                                    "checkpoint_gst": gst_reports["result"]["gst"],
                                    "checkpoint_gst_sha256": gst_reports["result"][
                                        "gst_sha256"
                                    ],
                                    "runtime_quicksave": str(
                                        case_root / "result-quicksave.gst"
                                    ),
                                    "runtime_quicksave_sha256": gst_reports[
                                        "result"
                                    ]["gst_sha256"],
                                    "flushed_marker": marker_reports["result"],
                                    "flush": {
                                        "status": "pass",
                                        "policy": "process_exit_flush",
                                        "flushed_marker": marker_reports["result"],
                                        "expected_marker": 0,
                                    },
                                    "expected_marker": 0,
                                    "resume_method": "blastem_cli_savestate",
                                    "resume_gst_argument": gst_reports["result"][
                                        "gst"
                                    ],
                                    "resumed": True,
                                },
                                "resumed_capture": capture_reports[
                                    "result-resumed"
                                ],
                                "resumed_gst": gst_reports["result-resumed"]["gst"],
                                "resumed_gst_sha256": gst_reports["result-resumed"][
                                    "gst_sha256"
                                ],
                                "resumed_runtime": runtime,
                            },
                            "save_menu": {
                                **gst_reports["save"],
                                "capture": capture_reports["save"],
                                "record_sha256": gst_record_sha256["save"],
                                "scenario": scenario + 1,
                                "runtime": runtime,
                                "serialized_commander": {
                                    "commander_id": character["commander_id"],
                                    "class_id": runtime["class_id"],
                                    "mp": runtime["mp"],
                                    "level": runtime["level"],
                                    "experience": runtime["experience"],
                                    "at": runtime["at"],
                                    "df": runtime["df"],
                                    "hire_mask": 0,
                                },
                                "consumed_join_marker": marker_reports["save"],
                                "consumed_flush": {
                                    "status": "pass",
                                    "policy": "process_exit_flush",
                                    "flushed_marker": marker_reports["save"],
                                    "expected_marker": 0,
                                },
                            },
                            "skipped_other_candidate_screens": [],
                            "attempt_history": [
                                {"attempt": 1, "status": "pass", "error": None}
                            ],
                        }
                    )
                pending_rows = []
                pending_references = {}
                for key, representative_case in pending_representatives.items():
                    source_row = next(
                        row for row in rows if row["case"] == representative_case
                    )
                    pending_root = (
                        evidence_root
                        / profile
                        / representative_case
                        / self.plan["run_id"]
                        / "pending-probe"
                        / "attempt-1"
                    )
                    pending_root.mkdir(parents=True, exist_ok=True)
                    pending_gst_reports = {}
                    for stage in ("pre-completion", "candidate"):
                        source_stage = (
                            source_row["pre_completion"]
                            if stage == "pre-completion"
                            else source_row["candidate"]
                        )
                        pending_gst = pending_root / f"{stage}.gst"
                        pending_gst.write_bytes(Path(source_stage["gst"]).read_bytes())
                        pending_gst_reports[stage] = {
                            "gst": str(pending_gst),
                            "gst_sha256": gate.sha256_path(pending_gst),
                        }
                    pending_capture = pending_root / "candidate.png"
                    pending_capture.write_bytes(
                        Path(source_row["candidate"]["capture"]["path"]).read_bytes()
                    )
                    pending_capture_report = {
                        "path": str(pending_capture),
                        "sha256": gate.sha256_path(pending_capture),
                    }
                    slug = gate.join_character_slug(representative_case)
                    character = gate.JOIN_CHARACTER[slug]
                    marker_address = str(character["marker_address"])
                    marker_offset = (int(marker_address, 16) - 0x00400001) // 2
                    pending_marker_path = pending_root / "pending-marker.sram"
                    pending_marker_payload = bytearray(0x2000)
                    pending_marker_payload[marker_offset] = gate.JOIN_PENDING_MARKER
                    pending_marker_path.write_bytes(pending_marker_payload)
                    pending_marker = {
                        "path": str(pending_marker_path),
                        "sha256": gate.sha256_path(pending_marker_path),
                        "bytes": 0x2000,
                        "source_path": str(pending_root / "live/save.sram"),
                        "address": marker_address,
                        "sram_offset": f"0x{marker_offset:04X}",
                        "value": gate.JOIN_PENDING_MARKER,
                    }
                    runtime_name = (
                        f"join-pending-{profile}-{representative_case}-"
                        f"{self.plan['run_id']}-a1"
                    )
                    pending_evidence = pending_root / "evidence.json"
                    pending_row = {
                        "status": "pass",
                        "attempt": 1,
                        "run_id": self.plan["run_id"],
                        "phase": "pending_marker_probe",
                        "execution_policy": gate.JOIN_EXECUTION_POLICY,
                        "pending_probe_key": key,
                        "profile": profile,
                        "case": representative_case,
                        "group": gate.expected_join_group(representative_case),
                        "scenario": source_row["scenario"],
                        "next_scenario": source_row["next_scenario"],
                        "legacy_level": gate.expected_join_legacy_level(
                            representative_case
                        ),
                        "display": ":850",
                        "virtual_display": True,
                        "runtime_name": runtime_name,
                        "runtime_isolation": {
                            "policy": "replace_existing_named_home_before_launch",
                            "runtime_home": str(
                                evidence_root.parent / "unit-runtimes" / runtime_name
                            ),
                            "phase_unique": True,
                        },
                        "evidence_path": str(pending_evidence),
                        "seed": source_row["seed"],
                        "probe": source_row["probe"],
                        "character": source_row["character"],
                        "selection": {
                            "candidate_index": 1,
                            "selected_class": gate.expected_join_result(
                                representative_case
                            )[0],
                        },
                        "join_experience": source_row["join_experience"],
                        "progression_expectation": source_row[
                            "progression_expectation"
                        ],
                        "pre_completion": {
                            **pending_gst_reports["pre-completion"],
                            "runtime": source_row["pre_completion"]["runtime"],
                        },
                        "candidate": {
                            **pending_gst_reports["candidate"],
                            "capture": pending_capture_report,
                            "labels": source_row["candidate"]["labels"],
                            "label_fingerprint": source_row["candidate"][
                                "label_fingerprint"
                            ],
                            "runtime": source_row["candidate"]["runtime"],
                            "pending_join_marker": pending_marker,
                            "pending_flush": {
                                "status": "pass",
                                "policy": "process_exit_flush",
                                "flushed_marker": pending_marker,
                                "expected_marker": gate.JOIN_PENDING_MARKER,
                            },
                        },
                    }
                    self.write_json(pending_evidence, pending_row)
                    pending_row["attempt_history"] = [
                        {"attempt": 1, "status": "pass", "error": None}
                    ]
                    pending_row["evidence_sha256"] = gate.sha256_path(pending_evidence)
                    pending_rows.append(pending_row)
                    pending_references[key] = {
                        "status": "pass",
                        "run_id": self.plan["run_id"],
                        "pending_probe_key": key,
                        "profile": profile,
                        "case": representative_case,
                        "scenario": source_row["scenario"],
                        "legacy_level": gate.expected_join_legacy_level(
                            representative_case
                        ),
                        "runtime_name": runtime_name,
                        "evidence_path": str(pending_evidence),
                        "evidence_sha256": pending_row["evidence_sha256"],
                        "probe": source_row["probe"],
                        "seed": source_row["seed"],
                        "candidate_gst": pending_row["candidate"]["gst"],
                        "candidate_gst_sha256": pending_row["candidate"][
                            "gst_sha256"
                        ],
                        "pending_marker": pending_marker,
                    }

                for row in rows:
                    case = row["case"]
                    full_root = (
                        evidence_root
                        / profile
                        / case
                        / self.plan["run_id"]
                        / "full-flow"
                        / "attempt-1"
                    )
                    runtime_name = (
                        f"join-full-{profile}-{case}-{self.plan['run_id']}-a1"
                    )
                    row.update(
                        {
                            "phase": "full_flow",
                            "execution_policy": gate.JOIN_EXECUTION_POLICY,
                            "pending_probe_key": (
                                gate.expected_join_pending_probe_key(case)
                            ),
                            "group": gate.expected_join_group(case),
                            "legacy_level": gate.expected_join_legacy_level(case),
                            "runtime_name": runtime_name,
                            "runtime_isolation": {
                                "policy": "replace_existing_named_home_before_launch",
                                "runtime_home": str(
                                    evidence_root.parent
                                    / "unit-runtimes"
                                    / runtime_name
                                ),
                                "phase_unique": True,
                            },
                            "evidence_path": str(full_root / "evidence.json"),
                            "pending_marker_probe": pending_references[
                                gate.expected_join_pending_probe_key(case)
                            ],
                        }
                    )
                    row["selection"]["candidate_index"] = (
                        gate.expected_join_candidate_index(case)
                    )
                    candidate = row["candidate"]
                    candidate["continuous_to_applied_state"] = True
                    for field in (
                        "pending_join_marker",
                        "pending_flush_resume",
                        "resumed_capture",
                        "resumed_gst",
                        "resumed_gst_sha256",
                        "resumed_runtime",
                    ):
                        candidate.pop(field, None)
                    for section_name in ("applied_immediate", "battle_result"):
                        section = row[section_name]
                        for field in (
                            "consumed_join_marker",
                            "consumed_flush_resume",
                            "resumed_capture",
                            "resumed_gst",
                            "resumed_gst_sha256",
                            "resumed_runtime",
                        ):
                            section.pop(field, None)
                    row["applied_immediate"]["continuous_to_battle_result"] = True
                    row["battle_result"]["continuous_from_applied_state"] = True
                    row["save_menu"]["continuous_from_battle_result"] = True
                    full_evidence = Path(row["evidence_path"])
                    evidence_row = {
                        key: value
                        for key, value in row.items()
                        if key != "attempt_history"
                    }
                    self.write_json(full_evidence, evidence_row)
                    row["evidence_sha256"] = gate.sha256_path(full_evidence)

                reports.append(
                    {
                        "profile": profile,
                        "display": ":850",
                        "status": "pass",
                        "passed_pending_probes": len(pending_rows),
                        "total_pending_probes": len(pending_rows),
                        "pending_marker_probes": pending_rows,
                        "passed_cases": len(rows),
                        "total_cases": len(rows),
                        "results": rows,
                    }
                )
            return {
                "status": "pass",
                "run_id": self.plan["run_id"],
                "profiles": list(gate.PROFILES),
                "case_groups": groups,
                "cases": list(cases),
                "virtual_displays": {profile: ":850" for profile in gate.PROFILES},
                "maximum_simultaneous_emulators": len(gate.PROFILES),
                "execution_policy": gate.JOIN_EXECUTION_POLICY,
                "original_experience_basis": {
                    "status": "pass",
                    "policy": "numeric_level_cumulative_raw_excluding_residual_bar",
                    "rows": [
                        {
                            "commander_id": gate.JOIN_CHARACTER[slug][
                                "commander_id"
                            ],
                            "original_second_tier_class": original["class_id"],
                            "original_second_tier_level": original["level"],
                            "original_residual_experience_excluded": original[
                                "residual"
                            ],
                            "class_experience_gauge": (
                                32 if slug == "keith" else 24
                            ),
                            "fixed_raw_experience": gate.JOIN_RAW_EXPERIENCE[slug],
                        }
                        for slug, original in gate.JOIN_ORIGINAL_BASIS.items()
                    ],
                },
                "production_experience_policy": {
                    "status": "pass",
                    "policy": "profile_and_branch_invariant_one_time_raw_experience",
                    "profile_invariant": True,
                    "branch_invariant": True,
                    "target_level_pump_absent": True,
                    "class_specific_adjustment_absent": True,
                    "raw_experience_by_commander": expected_raw,
                    "expected_wrapper_sha256": wrapper_sha,
                    "profile_wrapper_sha256": wrapper_sha,
                    "profiles": policy_profiles,
                },
                "passed_profiles": len(gate.PROFILES),
                "total_profiles": len(gate.PROFILES),
                "results": reports,
            }

        self.write_json(
            self.summary_path("natural_and_legacy_join"),
            join_summary(
                ["natural", "legacy"],
                (*gate.NATURAL_CASES, *gate.LEGACY_CASES),
            ),
        )
        self.write_json(
            self.summary_path("legacy_later_join"),
            join_summary(["legacy-later"], gate.LEGACY_LATER_CASES),
        )

        campaign_reports = []
        campaign_inputs = {}
        campaign_root = self.summary_path("continuous_campaign_route").parent
        for profile in gate.PROFILES:
            rows = []
            input_path = Path(seeds[profile]["path"])
            input_gst_sha256 = seeds[profile]["sha256"]
            input_record = common_record_sha256
            for index, scenario in enumerate(gate.FULL_ROUTE_ORDER):
                expected_next = gate.NEXT_SCENARIO[scenario]
                output = None
                if expected_next is not None:
                    output_path = campaign_root / profile / f"step-{index + 1:02d}.gst"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(
                        f"campaign-{profile}-{index + 1:02d}".encode()
                    )
                    output = {
                        "scenario": expected_next,
                        "path": str(output_path),
                        "gst_sha256": gate.sha256_path(output_path),
                        "record_sha256": hashlib.sha256(
                            f"{profile}-record-{index + 1:02d}".encode()
                        ).hexdigest(),
                    }
                input_state = {
                    "scenario": scenario,
                    "path": str(input_path),
                    "gst_sha256": input_gst_sha256,
                    "record_sha256": input_record,
                }
                campaign_inputs[(profile, scenario)] = {
                    "path": str(input_path),
                    "sha256": input_gst_sha256,
                    "record_sha256": input_record,
                    "route_index": index,
                    "source": (
                        "fresh_s1_seed"
                        if scenario == 1
                        else "continuous_campaign_input"
                    ),
                }
                rows.append(
                    {
                        "profile": profile,
                        "scenario": scenario,
                        "route_index": index,
                        "display": ":870",
                        "status": "pass",
                        "returncode": 0,
                        "run_id": self.plan["run_id"],
                        "manual_intervention": False,
                        "rom": probes[(profile, scenario)]["path"],
                        "input_state": input_state,
                        "output_state": output,
                        "expected_next_scenario": expected_next,
                        "attempt": 1,
                        "retry_policy": "external_fresh_process_only",
                        "fresh_process_attempt": 1,
                        "runtime_session": {
                            "pid": 10000 + index,
                            "proc_start_time_ticks": 20000 + index,
                            "runtime_home": str(
                                campaign_root
                                / "runtime"
                                / profile
                                / f"step-{index + 1:02d}-attempt-1"
                            ),
                            "observed_home": str(
                                campaign_root
                                / "runtime"
                                / profile
                                / f"step-{index + 1:02d}-attempt-1"
                            ),
                            "display": ":870",
                            "observed_display": ":870",
                            "isolated_virtual_display": True,
                        },
                        "input_seed_gst": {
                            "path": str(input_path),
                            "sha256": input_gst_sha256,
                        },
                        "attempt_history": [
                            {
                                "attempt": 1,
                                "returncode": 0,
                                "status": "pass",
                                "elapsed_seconds": 1.0,
                                "xvfb_restarted_before_attempt": False,
                                "fresh_process_attempt": 1,
                                "runtime_session": {
                                    "pid": 10000 + index,
                                    "proc_start_time_ticks": 20000 + index,
                                    "runtime_home": str(
                                        campaign_root
                                        / "runtime"
                                        / profile
                                        / f"step-{index + 1:02d}-attempt-1"
                                    ),
                                    "observed_home": str(
                                        campaign_root
                                        / "runtime"
                                        / profile
                                        / f"step-{index + 1:02d}-attempt-1"
                                    ),
                                    "display": ":870",
                                    "observed_display": ":870",
                                    "isolated_virtual_display": True,
                                },
                                "input_seed_gst": {
                                    "path": str(input_path),
                                    "sha256": input_gst_sha256,
                                },
                            }
                        ],
                        "command": [
                            "tools/run_scenario28_31_result_surface.py",
                            "--fresh-process-attempt",
                            "1",
                        ],
                    }
                )
                if output is not None:
                    input_path = Path(output["path"])
                    input_gst_sha256 = output["gst_sha256"]
                    input_record = output["record_sha256"]
            campaign_reports.append(
                {
                    "profile": profile,
                    "status": "pass",
                    "run_id": self.plan["run_id"],
                    "display": ":870",
                    "release_rom": self.release_model(profile),
                    "manual_intervention": False,
                    "passed_steps": 31,
                    "total_steps": 31,
                    "initial_seed": {
                        "path": seeds[profile]["path"],
                        "gst_sha256": seeds[profile]["sha256"],
                        "record_sha256": common_record_sha256,
                        "scenario": 1,
                    },
                    "results": rows,
                }
            )
        self.write_json(
            self.summary_path("continuous_campaign_route"),
            {
                "status": "pass",
                "run_id": self.plan["run_id"],
                "profiles": list(gate.PROFILES),
                "release_roms": {
                    profile: self.release_model(profile)
                    for profile in gate.PROFILES
                },
                "release_roms_after": {
                    profile: self.release_model(profile)
                    for profile in gate.PROFILES
                },
                "release_roms_unchanged": True,
                "route_order": list(gate.FULL_ROUTE_ORDER),
                "continuous_save_chain": True,
                "manual_intervention": False,
                "automation_only": True,
                "attempts_per_step": 2,
                "passed_profiles": 3,
                "total_profiles": 3,
                "results": campaign_reports,
            },
        )

        campaign_summary = self.summary_path("continuous_campaign_route")
        campaign_snapshot = {
            "path": str(campaign_summary),
            "sha256": gate.sha256_path(campaign_summary),
        }
        for profile in gate.PROFILES:
            summary = self.summary_path("first_turn_s01_s31", profile)
            first_turn_rows = []
            scenario_seeds = {
                str(scenario): campaign_inputs[(profile, scenario)]
                for scenario in gate.SCENARIOS
            }
            for scenario in gate.SCENARIOS:
                case_root = summary.parent / f"s{scenario:02d}"
                loader_results = case_root / "loader.json"
                first_turn_results = case_root / "first_turn.json"
                entry_gst = case_root / "entry.gst"
                entry_gst.parent.mkdir(parents=True, exist_ok=True)
                entry_gst.write_bytes(f"entry-{profile}-{scenario}".encode())
                entry_sha256 = gate.sha256_path(entry_gst)
                scenario_seed = campaign_inputs[(profile, scenario)]
                loader_entry = {
                    "number": scenario,
                    "seed": scenario_seed["path"],
                    "seed_sha256": scenario_seed["sha256"],
                    "gst": str(entry_gst),
                    "gst_sha256": entry_sha256,
                }
                first_turn_entry = {
                    "kind": "loader_smoke",
                    "manifest": str(loader_results),
                    "manifest_rom_sha256": self.releases[profile]["sha256"],
                    "gst": str(entry_gst),
                    "gst_sha256": entry_sha256,
                    "manifest_gst_sha256": entry_sha256,
                }
                self.write_json(
                    loader_results,
                    {
                        "hard_rom": {
                            "sha256": self.releases[profile]["sha256"]
                        },
                        "scenarios": [loader_entry],
                    },
                )
                self.write_json(
                    first_turn_results,
                    {
                        "scenarios": [
                            {
                                "number": scenario,
                                "entry_evidence": first_turn_entry,
                            }
                        ]
                    },
                )
                loader_results_sha256 = gate.sha256_path(loader_results)
                first_turn_results_sha256 = gate.sha256_path(
                    first_turn_results
                )
                first_turn_rows.append(
                    {
                        "scenario": scenario,
                        "display": ":881",
                        "status": "pass",
                        "loader_results": str(loader_results),
                        "first_turn_results": str(first_turn_results),
                        "loader_results_sha256": loader_results_sha256,
                        "first_turn_results_sha256": (
                            first_turn_results_sha256
                        ),
                        "entry_source_lineage": {
                            "status": "pass",
                            "seed": {
                                "path": scenario_seed["path"],
                                "sha256": scenario_seed["sha256"],
                            },
                            "source": scenario_seed,
                            "loader_manifest": str(loader_results),
                            "loader_results_sha256": loader_results_sha256,
                            "loader_manifest_rom_sha256": self.releases[
                                profile
                            ]["sha256"],
                            "loader_entry_gst": {
                                "path": str(entry_gst),
                                "sha256": entry_sha256,
                            },
                            "first_turn_manifest": str(first_turn_results),
                            "first_turn_results_sha256": (
                                first_turn_results_sha256
                            ),
                            "first_turn_entry": first_turn_entry,
                            "checks": {
                                name: True
                                for name in gate.FIRST_TURN_LINEAGE_CHECKS
                            },
                            "all_checks_pass": True,
                        },
                    }
                )
            self.write_json(
                summary,
                {
                    "status": "pass",
                    "profile": profile,
                    "run_id": self.plan["run_id"],
                    "rom": self.release_model(profile),
                    "seed": seeds[profile],
                    "seed_before": seeds[profile],
                    "seed_after": seeds[profile],
                    "seed_unchanged": True,
                    "campaign": campaign_snapshot,
                    "campaign_before": campaign_snapshot,
                    "campaign_after": campaign_snapshot,
                    "campaign_unchanged": True,
                    "scenario_seeds": scenario_seeds,
                    "scenario_seeds_after": scenario_seeds,
                    "scenario_seeds_unchanged": True,
                    "coverage": {
                        "requested": list(gate.SCENARIOS),
                        "passed": list(gate.SCENARIOS),
                        "failed": [],
                    },
                    "scenarios": first_turn_rows,
                },
            )

        runestone_rows = [
            {
                "profile": profile,
                "character": character,
                "current_tier": tier,
                "status": "pass",
                "returncode": 0,
                "display": ":890",
                "candidate_labels": gate.RUNESTONE_EXPECTED[character][
                    "candidate_labels"
                ],
                "selected_class": gate.RUNESTONE_EXPECTED[character][
                    "selected_class"
                ],
                "candidate_label_surface": {
                    "status": "pass",
                    "expected_fingerprint": gate.RUNESTONE_EXPECTED[character][
                        "label_fingerprint"
                    ],
                    "observed_fingerprints": [
                        gate.RUNESTONE_EXPECTED[character]["label_fingerprint"]
                    ]
                    * 3,
                },
                "state": {
                    "class_id": gate.RUNESTONE_EXPECTED[character][
                        "selected_class"
                    ],
                    "commander_id_after_apply": gate.RUNESTONE_EXPECTED[character][
                        "commander_id"
                    ],
                    "level": 1,
                    "experience": 0,
                    "equipped_item_after_use": "0x00",
                },
                "production_resume": {
                    "status": "pass",
                    "resume_operand": "0x014D0C",
                    "expected_production_target": "0x31E000",
                    "release_target": "0x31E000",
                    "probe_target": "0x31E000",
                    "operand_byte_identical": True,
                    "wrapper_size": 128,
                    "wrapper_byte_identical": True,
                    "release_wrapper_matches_current_builder": True,
                    "release_wrapper_sha256": "a" * 64,
                    "probe_wrapper_sha256": "a" * 64,
                    "expected_wrapper_sha256": "a" * 64,
                },
                "marker_setup": {
                    "status": "pass",
                    "entry_target": "0x3FF000",
                    "probe_wrapper": "0x3FF000",
                    "marker_address": gate.RUNESTONE_EXPECTED[character][
                        "marker_address"
                    ],
                    "clear_instruction": (
                        "4239"
                        + gate.RUNESTONE_EXPECTED[character]["marker_address"][
                            2:
                        ].lower()
                    ),
                    "clear_instruction_offset": "0x3FF000",
                    "stock_handler_target": "0x01480C",
                    "clear_precedes_stock_handler": True,
                    "release_probe_region_empty": True,
                    "setup_sha256": "b" * 64,
                    "expected_setup_sha256": "b" * 64,
                },
            }
            for profile in gate.PROFILES
            for character in ("keith", "lester", "jessica")
            for tier in (2, 3, 4, 5)
        ]
        for row in runestone_rows:
            character = str(row["character"])
            tier = int(row["current_tier"])
            profile = str(row["profile"])
            expected_character = gate.RUNESTONE_EXPECTED[character]
            marker_address = str(expected_character["marker_address"])
            marker_offset = (int(marker_address, 16) - 0x00400001) // 2
            marker_path = (
                self.summary_path("runestone_restart").parent
                / "unit-runestone-evidence"
                / profile
                / character
                / f"tier-{tier}-save.sram"
            )
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            marker_path.write_bytes(bytes(0x2000))
            row["runtime_join_marker"] = {
                "status": "pass",
                "path": str(marker_path),
                "sha256": gate.sha256_path(marker_path),
                "bytes": 0x2000,
                "address": marker_address,
                "sram_offset": f"0x{marker_offset:04X}",
                "value": 0,
            }
        self.write_json(
            self.summary_path("runestone_restart"),
            {
                "status": "pass",
                "run_id": self.plan["run_id"],
                "profiles": list(gate.PROFILES),
                "tiers": [2, 3, 4, 5],
                "characters": ["keith", "lester", "jessica"],
                "passed_tasks": 36,
                "total_tasks": 36,
                "release_roms_before": {
                    profile: self.release_model(profile)
                    for profile in gate.PROFILES
                },
                "release_roms_after": {
                    profile: self.release_model(profile)
                    for profile in gate.PROFILES
                },
                "release_roms_unchanged": True,
                "results": runestone_rows,
            },
        )

        for profile in gate.PROFILES:
            s6_summary = self.summary_path(
                "scenario6_actual_runestone", profile
            )
            s6_root = s6_summary.parent
            s6_probe = s6_root / "scenario6-runestone-probe.md"
            s6_probe_payload = bytes(
                gate.scenario6_probe.build_probe(
                    self.release_paths[profile].read_bytes(),
                    self.source.read_bytes(),
                )
            )
            s6_probe.parent.mkdir(parents=True, exist_ok=True)
            s6_probe.write_bytes(s6_probe_payload)
            s6_states = {}
            for state_name, coordinate, acted in (
                ("before_move", (6, 4), 0),
                ("runestone_dialogue", (7, 4), 1),
                ("after_item_acquisition", (7, 4), 1),
            ):
                gst = s6_root / "states" / f"{state_name}.gst"
                self.write_join_gst(
                    gst,
                    commander_id=1,
                    runtime={
                        "class_id": 0x04,
                        "level": 1,
                        "experience": 0,
                        "x": coordinate[0],
                        "y": coordinate[1],
                        "mp": 0,
                        "at": 23,
                        "df": 18,
                    },
                    scenario=6,
                )
                payload = bytearray(gst.read_bytes())
                runtime = 0x2478 + 0x603C
                payload[runtime + 2] = acted
                payload[runtime + 3] = 10
                if state_name == "after_item_acquisition":
                    inventory = 0x2478 + 0xC7F2
                    payload[inventory:inventory + 2] = bytes((0x1A, 0xFF))
                gst.write_bytes(payload)
                s6_states[state_name] = gst
            s6_images = {}
            for image_name in (
                "preparation",
                "active_command",
                "move_target",
                "after_move_before_standby",
                "runestone_dialogue",
                "after_item_acquisition",
            ):
                image_path = s6_root / "images" / f"{image_name}.png"
                image_path.parent.mkdir(parents=True, exist_ok=True)
                image = Image.new("RGB", (320, 240), (0, 0, 0))
                for x in range(10, 310):
                    for y in range(95, 185):
                        image.putpixel((x, y), (0, 0, 100))
                for x in range(20, 80):
                    for y in range(105, 115):
                        image.putpixel((x, y), (255, 255, 255))
                image.save(image_path)
                s6_images[image_name] = image_path
            before_inventory = gate.scenario6_surface.inventory_records(
                s6_states["before_move"]
            )
            after_inventory = gate.scenario6_surface.inventory_records(
                s6_states["after_item_acquisition"]
            )
            self.write_json(
                s6_summary,
                {
                    "schema_version": 1,
                    "status": "pass",
                    "run_id": self.plan["run_id"],
                    "profile": profile,
                    "scenario": 6,
                    "virtual_display": ":860",
                    "candidate": self.release_model(profile),
                    "seed": seeds[profile],
                    "probe": {
                        "path": str(s6_probe),
                        "sha256": gate.sha256_path(s6_probe),
                        "md_checksum": s6_probe_payload[0x18E:0x190].hex().upper(),
                        "delta_from_candidate": (
                            gate.scenario6_surface.probe_delta_report(
                                self.release_paths[profile].read_bytes(),
                                s6_probe_payload,
                            )
                        ),
                    },
                    "scenario_identity": {"status": "pass"},
                    "movement": {
                        "expected_start": [6, 4],
                        "expected_destination": [7, 4],
                        "before": gate.scenario6_surface.commander_state(
                            s6_states["before_move"]
                        ),
                        "dialogue": gate.scenario6_surface.commander_state(
                            s6_states["runestone_dialogue"]
                        ),
                        "after_acquisition": (
                            gate.scenario6_surface.commander_state(
                                s6_states["after_item_acquisition"]
                            )
                        ),
                    },
                    "inventory_acquisition": (
                        gate.scenario6_surface.runestone_acquisition_report(
                            before_inventory,
                            after_inventory,
                        )
                    ),
                    "evidence": {
                        **{
                            name: {
                                "path": str(image_path),
                                "sha256": gate.sha256_path(image_path),
                            }
                            for name, image_path in s6_images.items()
                        },
                        **{
                            evidence_name: {
                                "path": str(s6_states[state_name]),
                                "sha256": gate.sha256_path(
                                    s6_states[state_name]
                                ),
                            }
                            for evidence_name, state_name in (
                                ("before_move_gst", "before_move"),
                                (
                                    "runestone_dialogue_gst",
                                    "runestone_dialogue",
                                ),
                                (
                                    "after_item_acquisition_gst",
                                    "after_item_acquisition",
                                ),
                            )
                        },
                    },
                },
            )

        mounted_jobs = []
        for job_index, (profile, case) in enumerate(
            (profile, case)
            for profile in gate.PROFILES
            for case in ("keith", "lester")
        ):
            expected = gate.MOUNTED_EXPECTED[case]
            root = (
                self.summary_path("mounted_lord_combat").parent
                / "unit-mounted-evidence"
                / profile
                / case
            )
            root.mkdir(parents=True, exist_ok=True)

            def artifact(name: str, suffix: str) -> dict[str, object]:
                path = root / f"{name}.{suffix}"
                path.write_bytes(f"{profile}-{case}-{name}".encode())
                return {
                    "path": str(path),
                    "sha256": gate.sha256_path(path),
                    "dimensions": [320, 240],
                }

            runtime_checks = {
                name: True
                for name in (
                    "class_is_selected_mounted_lord",
                    "commander_identity_preserved",
                    "alive_and_visible",
                    "level_reset_to_one",
                    "experience_reset_to_zero",
                    "class_stats_match_mounted_source",
                    "display_at_matches",
                    "display_df_matches",
                )
            }

            def runtime(name: str) -> dict[str, object]:
                gst = artifact(name, "gst")
                return {
                    "status": "pass",
                    "path": gst["path"],
                    "sha256": gst["sha256"],
                    "checks": runtime_checks,
                    "values": {
                        "class_id": expected["class_id"],
                        "commander_id": expected["commander_id"],
                        "hp": 10,
                        "x": 12,
                        "y": 16,
                        "level": 1,
                        "experience": 0,
                        "at": 23,
                        "df": 18,
                        "class_stats": expected["class_stats"],
                        "move": expected["move"],
                        "a_plus": expected["a_plus"],
                        "d_plus": expected["d_plus"],
                    },
                }

            diagnostic_rom = artifact("diagnostic", "md")
            diagnostic_manifest = artifact("diagnostic", "json")
            samples = []
            for sample_index in range(4):
                sample = artifact(f"battle-{sample_index}", "png")
                sample.update(
                    {
                        "battle_surface_visible": sample_index < 2,
                        "attacker_crop_sha256": (
                            hashlib.sha256(
                                f"crop-{sample_index}".encode()
                            ).hexdigest()
                        ),
                    }
                )
                samples.append(sample)
            combat_gst = artifact("combat", "gst")
            evidence_path = root / "evidence.json"
            evidence = {
                "status": "pass",
                "case": case,
                "profile_input": self.release_model(profile),
                "diagnostic": {
                    "rom": diagnostic_rom["path"],
                    "rom_sha256": diagnostic_rom["sha256"],
                    "manifest": diagnostic_manifest["path"],
                    "manifest_sha256": diagnostic_manifest["sha256"],
                    "changed_byte_count": 65,
                    "exact_derivative_verified_before_launch": True,
                },
                "runtime_isolation": {
                    "runtime_home": str(root / "runtime"),
                    "required_absent_before_launch": True,
                    "existing_blastem_pids_before_launch": [],
                    "reuse_runtime_state": False,
                },
                "class_change": {
                    "trigger": artifact("trigger", "png"),
                    "candidate_first": artifact("candidate-first", "png"),
                    "candidate_mounted_lord": artifact(
                        "candidate-mounted", "png"
                    ),
                    "selected_candidate_index": 2,
                    "selected_class_id": expected["class_id"],
                },
                "map": {
                    "capture": artifact("map", "png"),
                    "runtime": runtime("map-runtime"),
                    "sprite": {
                        "status": "pass",
                        "sprite_id": "0x0100",
                        "wrong_sprite_id": "0x0200",
                        "checks": {
                            name: True
                            for name in (
                                "mapped_to_reviewed_mounted_sprite",
                                "frames_differ_from_wrong_class",
                                "rom_payload_loaded_into_vram",
                                "actual_plane_a_unit_uses_verified_payload",
                            )
                        },
                    },
                },
                "status_detail_and_exp": {
                    "runtime": runtime("status-runtime"),
                    "surface": {
                        **artifact("status", "png"),
                        "status": "pass",
                        "checks": {
                            name: True
                            for name in (
                                "command_panel_visible",
                                "status_detail_panel_visible",
                                "bottom_status_and_exp_bar_visible",
                                "runtime_status_is_exact",
                                "class_name_source_is_selected_class",
                                "exp_bar_source_is_zero",
                            )
                        },
                        "expected_visible_values": {
                            "class": expected["class_name"],
                            "level": 1,
                            "experience": 0,
                            "at": 23,
                            "df": 18,
                            "move": expected["move"],
                            "a_plus": expected["a_plus"],
                            "d_plus": expected["d_plus"],
                        },
                    },
                },
                "side_view_attack": {
                    "animation": {
                        "status": "pass",
                        "battle_frame_count": 2,
                        "unique_attacker_crop_count": 2,
                        "passing_combat_state_count": 1,
                        "checks": {
                            name: True
                            for name in (
                                "multiple_live_battle_frames_captured",
                                "side_view_attacker_region_animated",
                                "commander_specific_combat_payload_observed",
                            )
                        },
                    },
                    "samples": samples,
                    "combat_states": [
                        {
                            "status": "pass",
                            "path": combat_gst["path"],
                            "sha256": combat_gst["sha256"],
                            "resource": {
                                "status": "pass",
                                "raw_resource_id": expected["combat_resource"],
                                "forbidden_fallbacks": [
                                    {
                                        "loaded_at_combat_destination": False
                                    }
                                ],
                                "checks": {
                                    name: True
                                    for name in (
                                        "commander_override_resource_selected",
                                        "expected_payload_at_battle_destination",
                                        "expected_payload_present_in_vram",
                                        "sister_vampire_or_generic_fallback_absent",
                                    )
                                },
                            },
                        }
                    ],
                },
            }
            self.write_json(evidence_path, evidence)
            mounted_jobs.append(
                {
                    "profile": profile,
                    "case": case,
                    "display": f":{850 + job_index}",
                    "status": "pass",
                    "evidence": str(evidence_path),
                    "evidence_sha256": gate.sha256_path(evidence_path),
                }
            )
        self.write_json(
            self.summary_path("mounted_lord_combat"),
            {
                "status": "pass",
                "pass_count": 6,
                "job_count": 6,
                "profiles": {
                    profile: self.release_model(profile)
                    for profile in gate.PROFILES
                },
                "jobs": mounted_jobs,
            },
        )

        for profile in gate.PROFILES:
            records = [
                {"fixed_record_index": index, "protected_mismatches": {}}
                for index in range(10)
            ]
            self.write_json(
                self.summary_path("scenario27_final_and_ending", profile),
                {
                    "status": "pass",
                    "profile": profile,
                    "scenario": 27,
                    "run_id": self.plan["run_id"],
                    "rom": probes[(profile, 27)],
                    "seed": seeds[profile],
                    "seed_unchanged": True,
                    "diagnostic_runtime_stage": {
                        "harness_only": True,
                        "natural_full_battle_clear": False,
                        "product_release_rom_changed": False,
                        "start_callback_operand_address": "0x00F2E0",
                        "start_wrapper_address": "0x3FEF00",
                        "stock_start_entry_address": "0x022C1E",
                        "wrapper_sha256": hashlib.sha256(
                            gate.scenario27_probe.completion_hp_wrapper_code()
                        ).hexdigest(),
                        "runtime_hp_address": "0xFFFF66FF",
                        "bernhardt": {
                            "class_id": 0x4E,
                            "name_id": 0x0E,
                            "defeated_flag": 0,
                            "defeated": False,
                            "hp": 1,
                            "x": 15,
                            "y": 15,
                        },
                        "ordinary_stock_attack_death_and_ending_handlers": True,
                    },
                    "fin": {"sha256": hashlib.sha256(b"Fin").hexdigest()},
                    "bernhardt_runtime_state": {
                        "class_id": 0x4E,
                        "name_id": 0x0E,
                        "hp": 0,
                    },
                    "scenario_identity": {
                        "fixed_record_layout": {
                            "status": "pass",
                            "fixed_record_count": 10,
                            "mismatch_count": 0,
                            "checked_fields": [
                                "class_id",
                                "name_id",
                                "side_id",
                                "level",
                                "x",
                                "y",
                                "mercenaries",
                            ],
                            "records": records,
                        }
                    },
                },
            )
        self.materialize_passing_scope_contract()

    def materialize_passing_scope_contract(self) -> None:
        contract = self.plan["required_scope_contract"]
        requirements = {
            requirement.requirement_id: requirement
            for requirement in gate.REQUIRED_SCOPE_CONTRACT
        }
        for row in contract["requirements"]:
            requirement = requirements[row["id"]]
            summary = Path(row["summary_path"])
            root = summary.parent
            domain_report = root / "domain-verifier-report.json"
            ledger = root / "acceptance-unit-ledger.json"
            evidence = root / "runtime-evidence.bin"
            self.write_json(
                domain_report,
                {
                    "status": "pass",
                    "requirement_id": requirement.requirement_id,
                    "verifier_id": requirement.verifier_id,
                },
            )
            observed_units = requirement.expected_acceptance_units or 1
            self.write_json(
                ledger,
                {
                    "status": "pass",
                    "requirement_id": requirement.requirement_id,
                    "unit_count": observed_units,
                },
            )
            evidence.parent.mkdir(parents=True, exist_ok=True)
            evidence.write_bytes(
                f"exact-runtime-{requirement.requirement_id}".encode()
            )
            self.write_json(
                summary,
                {
                    "schema_version": 1,
                    "kind": "langrisser_ii_korean_v137_scope_acceptance",
                    "status": "pass",
                    "requirement_id": requirement.requirement_id,
                    "run_id": self.plan["run_id"],
                    "base_phase_coverage": list(
                        requirement.base_phase_coverage
                    ),
                    "release_acceptance_eligible": True,
                    "diagnostic_only": False,
                    "missing_requirements": [],
                    "exact_release_inputs": {
                        profile: self.release_model(profile)
                        for profile in gate.PROFILES
                    },
                    "acceptance_units_observed": observed_units,
                    "acceptance_unit_ledger": {
                        "path": str(ledger),
                        "sha256": gate.sha256_path(ledger),
                        "unit_count": observed_units,
                    },
                    "domain_verifier": {
                        "id": requirement.verifier_id,
                        "status": "pass",
                        "report": {
                            "path": str(domain_report),
                            "sha256": gate.sha256_path(domain_report),
                        },
                    },
                    "evidence_artifacts": [
                        {
                            "path": str(evidence),
                            "sha256": gate.sha256_path(evidence),
                        }
                    ],
                    "checks": {
                        "domain_semantics_verified": True,
                        "exact_release_lineage_verified": True,
                        "fresh_run_lineage_verified": True,
                        "no_known_scope_gap": True,
                    },
                },
            )

    def write_plan(self) -> None:
        self.write_json(self.manifest, self.plan)

    def test_plan_has_fixed_order_exact_hashes_and_612_checks(self):
        self.assertEqual(self.plan["expected_phase_order"], list(gate.PHASE_IDS))
        self.assertEqual(self.plan["expected_gate_pass_count"], 612)
        self.assertEqual(
            [phase["expected_pass_count"] for phase in self.plan["phases"]],
            [3, 93, 93, 93, 93, 93, 45, 18, 36, 3, 6, 36],
        )
        for order, phase in enumerate(self.plan["phases"], 1):
            self.assertEqual(phase["order"], order)
            self.assertEqual(
                phase["dependencies"],
                list(gate.EXPECTED_PHASE_DEPENDENCIES[phase["id"]]),
            )
            self.assertEqual(
                phase["exact_release_inputs"],
                {
                    profile: self.release_model(profile)
                    for profile in gate.PROFILES
                },
            )
            self.assertEqual(phase["command_count"], len(phase["commands"]))
            for command in phase["commands"]:
                self.assertEqual(command["argv"][0], gate.sys.executable)
                self.assertTrue(command["shell"])
                self.assertTrue(Path(command["summary_path"]).is_absolute())
        total = self.plan["expected_total_acceptance_units"]
        self.assertEqual(total["base_gate_units"], 612)
        self.assertIsNone(total["supplemental_units"])
        self.assertIsNone(total["total_units"])
        self.assertEqual(
            total["status"], gate.SCOPE_EXTENSION_COUNT_STATUS
        )
        scope = self.plan["required_scope_contract"]
        self.assertEqual(scope["required_ids"], list(gate.REQUIRED_SCOPE_IDS))
        self.assertTrue(scope["complete_only_when_all_requirements_pass"])
        self.assertTrue(scope["verifier_registry_frozen_at_plan"])
        self.assertTrue(scope["final_plan_eligible_at_creation"])
        self.assertEqual(
            scope["retired_run_ids"], list(gate.RETIRED_FINAL_GATE_RUN_IDS)
        )
        self.assertEqual(
            scope["next_final_run_id_floor"],
            "v137-final-fresh-20260812-06",
        )
        self.assertEqual(
            [row["id"] for row in scope["requirements"]],
            list(gate.REQUIRED_SCOPE_IDS),
        )
        self.assertTrue(
            self.plan["final_gate"]["base_612_alone_is_never_final_acceptance"]
        )

    def test_scope_contract_distinguishes_s18_crown_and_real_public_versions(self):
        requirements = {
            row.requirement_id: row for row in gate.REQUIRED_SCOPE_CONTRACT
        }

        items = requirements["all_item_acquisition_paths"]
        self.assertIn("all 22 hidden-tile handlers", items.requirement)
        self.assertIn("Scenario 18's conditional Crown", items.requirement)
        self.assertNotIn("23 hidden-item", items.requirement)

        self.assertNotIn("historical_saves_v130_v136", requirements)
        historical = requirements["historical_saves_v131_v136"]
        self.assertEqual(historical.expected_acceptance_units, 51)
        self.assertIn("v1.3.1 through v1.3.6", historical.requirement)
        self.assertIn("17 version/profile targets", historical.requirement)
        self.assertIn("Keith, Lester, and Jessica (51 cases)", historical.requirement)
        self.assertIn("v1.3.0 has no public patch artifact", historical.missing_proof)

    def test_first_turn_commands_use_exact_profile_seed_and_campaign(self):
        phase = self.phase("first_turn_s01_s31")
        self.assertEqual(
            list(gate.PHASE_IDS[:4]),
            [
                "fresh_s1_seed",
                "current_result_probes",
                "continuous_campaign_route",
                "first_turn_s01_s31",
            ],
        )
        self.assertEqual(
            phase["dependencies"],
            [
                "fresh_s1_seed",
                "current_result_probes",
                "continuous_campaign_route",
            ],
        )
        expected_campaign = self.summary_path("continuous_campaign_route")
        for command in phase["commands"]:
            profile = command["label"]
            argv = command["argv"]
            self.assertEqual(argv.count("--seed-gst"), 1)
            seed = argv[argv.index("--seed-gst") + 1]
            expected = (
                Path(self.phase("fresh_s1_seed")["root"])
                / profile
                / self.plan["run_id"]
                / "fresh_s1_preparation.gst"
            )
            self.assertEqual(Path(seed), expected)
            self.assertEqual(argv.count("--campaign-summary"), 1)
            campaign = argv[argv.index("--campaign-summary") + 1]
            self.assertEqual(Path(campaign), expected_campaign)

    def test_gray_commands_use_exact_profile_seed_and_campaign(self):
        phase = self.phase("gray_acted_s01_s31")
        expected_campaign = self.summary_path("continuous_campaign_route")
        for command in phase["commands"]:
            profile = command["label"]
            argv = command["argv"]
            self.assertEqual(argv.count("--seed-gst"), 1)
            seed = Path(argv[argv.index("--seed-gst") + 1])
            self.assertEqual(
                seed,
                Path(self.phase("fresh_s1_seed")["root"])
                / profile
                / self.plan["run_id"]
                / "fresh_s1_preparation.gst",
            )
            self.assertEqual(argv.count("--campaign-summary"), 1)
            self.assertEqual(
                Path(argv[argv.index("--campaign-summary") + 1]),
                expected_campaign,
            )

    def test_join_progression_settlement_accepts_stock_intermediate_scan(self):
        expectation = {
            "selected_class": 0x05,
            "raw_experience": 144,
            "class_experience_gauge": 32,
            "expected_result_class": 0x05,
            "expected_result_level": 5,
            "expected_result_experience": 16,
        }
        report = gate.join_progression_settlement(
            {"class_id": 0x05, "level": 2, "experience": 112},
            expectation,
        )
        self.assertEqual(report["status"], "settling")
        self.assertEqual(report["consumed_raw_experience"], 32)
        self.assertEqual(report["remaining_raw_experience"], 112)
        with self.assertRaisesRegex(ValueError, "outside the settlement range"):
            gate.join_progression_settlement(
                {"class_id": 0x05, "level": 1, "experience": 144},
                expectation,
            )
        with self.assertRaisesRegex(ValueError, "finite-grant settlement step"):
            gate.join_progression_settlement(
                {"class_id": 0x05, "level": 2, "experience": 111},
                expectation,
            )

    def test_hash_locked_release_snapshot_rejects_wrong_sha(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            gate.hash_locked_release_snapshot(
                self.release_paths["pure"],
                "0" * 64,
            )

    def test_noncanonical_japanese_source_blocks_a_new_final_plan(self):
        changed = self.root / "changed-source.md"
        payload = bytearray(self.source.read_bytes())
        payload[0x100] ^= 1
        changed.write_bytes(payload)
        with self.assertRaisesRegex(ValueError, "source ROM SHA-256 mismatch"):
            gate.build_plan(
                run_id="changed-source",
                output_root=self.output,
                release_roms=self.releases,
                source_rom=gate.snapshot_file(changed),
                workers=2,
                display_base=850,
            )

    def test_invalidated_central_identity_blocks_a_new_final_plan(self):
        with (
            mock.patch.object(
                gate.release_identity,
                "RELEASE_IDENTITY_FINALIZED",
                False,
            ),
            self.assertRaisesRegex(ValueError, "invalidated pending"),
        ):
            gate.build_plan(
                run_id="invalidated-identity",
                output_root=self.output,
                release_roms=self.releases,
                source_rom=gate.snapshot_file(self.source),
                workers=2,
                display_base=850,
            )

    def test_phase_root_overrides_must_be_unique_and_inside_new_run_root(self):
        outside = self.root / "outside"
        with self.assertRaisesRegex(ValueError, "outside the new run root"):
            gate.build_plan(
                run_id="outside-test",
                output_root=self.output,
                release_roms=self.releases,
                source_rom=gate.snapshot_file(self.source),
                workers=2,
                display_base=850,
                phase_roots={"fresh_s1_seed": outside},
                validation_root=self.output,
            )
        shared = self.output / "shared"
        with self.assertRaisesRegex(ValueError, "distinct root"):
            gate.build_plan(
                run_id="duplicate-test",
                output_root=self.output,
                release_roms=self.releases,
                source_rom=gate.snapshot_file(self.source),
                workers=2,
                display_base=850,
                phase_roots={
                    "fresh_s1_seed": shared,
                    "current_result_probes": shared,
                },
                validation_root=self.output,
            )

    def test_new_plan_rejects_existing_run_root(self):
        self.output.mkdir()
        with self.assertRaisesRegex(FileExistsError, "run root already exists"):
            gate.build_plan(
                run_id="existing-run-test",
                output_root=self.output,
                release_roms=self.releases,
                source_rom=gate.snapshot_file(self.source),
                workers=2,
                display_base=850,
            )

    def test_final_plan_permanently_rejects_retired_01_through_05_ids(self):
        for run_id in (
            *gate.RETIRED_FINAL_GATE_RUN_IDS,
            "v137-final-fresh-20260812-00",
            "v137-final-fresh-20260812-5",
        ):
            with self.subTest(run_id=run_id), self.assertRaisesRegex(
                ValueError, "permanently retired development evidence"
            ):
                gate.build_plan(
                    run_id=run_id,
                    output_root=self.output,
                    release_roms=self.releases,
                    source_rom=gate.snapshot_file(self.source),
                    workers=2,
                    display_base=850,
                )

    def test_phase_root_overrides_must_not_overlap(self):
        shared = self.output / "shared"
        with self.assertRaisesRegex(ValueError, "must not overlap"):
            gate.build_plan(
                run_id="overlap-test",
                output_root=self.output,
                release_roms=self.releases,
                source_rom=gate.snapshot_file(self.source),
                workers=2,
                display_base=850,
                phase_roots={
                    "fresh_s1_seed": shared,
                    "current_result_probes": shared / "nested",
                },
                validation_root=self.output,
            )

    def test_plan_rejects_low_numbered_physical_display_range(self):
        with self.assertRaisesRegex(ValueError, "isolated Xvfb"):
            gate.build_plan(
                run_id="physical-display-test",
                output_root=self.output,
                release_roms=self.releases,
                source_rom=gate.snapshot_file(self.source),
                workers=2,
                display_base=1,
            )

    def test_command_policy_rejects_desktop_and_low_numbered_displays(self):
        invalid_commands = (
            ["runner", "--display", ":0"],
            ["runner", "--virtual-display", ":99"],
            ["runner", "--display-base", "1"],
            ["runner", "--desktop-display"],
            ["runner", "--display", ":104.0"],
            ["runner", "--display", "localhost:104"],
        )
        for argv in invalid_commands:
            with self.subTest(argv=argv):
                errors = []
                gate.verify_command_display_policy(argv, errors)
                self.assertTrue(errors)
        for argv in (
            ["runner", "--display", ":100"],
            ["runner", "--virtual-display", ":850"],
            ["runner", "--display-base", "820"],
        ):
            with self.subTest(argv=argv):
                errors = []
                gate.verify_command_display_policy(argv, errors)
                self.assertEqual(errors, [])

    def test_verify_passes_only_with_all_612_checks_and_unchanged_roms(self):
        self.materialize_passing_summaries()
        self.write_plan()
        report = gate.verify_plan_manifest(self.manifest)
        self.assertEqual(report["status"], "pass", report)
        self.assertEqual(report["observed_gate_pass_count"], 612)
        self.assertTrue(report["release_roms_unchanged"])
        self.assertTrue(report["no_phase_skipped"])
        self.assertTrue(report["all_phase_summaries_present"])
        self.assertTrue(report["all_phase_counts_exact"])
        self.assertEqual(
            [phase["status"] for phase in report["phases"]],
            ["pass"] * len(gate.PHASE_DEFINITIONS),
        )
        scope = report["required_scope_contract"]
        self.assertEqual(scope["status"], "pass")
        self.assertTrue(scope["all_verifiers_present"])
        self.assertTrue(scope["all_evidence_present"])
        self.assertTrue(scope["all_requirements_pass"])

    def test_base_612_cannot_pass_without_one_required_scope_evidence(self):
        self.materialize_passing_summaries()
        target = self.plan["required_scope_contract"]["requirements"][0]
        Path(target["summary_path"]).unlink()
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)

        self.assertEqual(report["observed_gate_pass_count"], 612)
        self.assertEqual(report["status"], "fail")
        scope = report["required_scope_contract"]
        self.assertFalse(scope["all_evidence_present"])
        row = scope["requirements"][0]
        self.assertEqual(row["status"], "fail")
        self.assertTrue(
            any(
                "missing supplemental verifier/evidence" in error
                for error in row["errors"]
            ),
            report,
        )

    def test_registered_evidence_cannot_replace_a_missing_scope_verifier(self):
        self.materialize_passing_summaries()
        target = gate.REQUIRED_SCOPE_CONTRACT[-1]
        del gate.SUPPLEMENTAL_SCOPE_VERIFIERS[target.verifier_id]
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)

        self.assertEqual(report["observed_gate_pass_count"], 612)
        self.assertEqual(report["status"], "fail")
        scope = report["required_scope_contract"]
        self.assertFalse(scope["all_verifiers_present"])
        row = next(
            item
            for item in scope["requirements"]
            if item["id"] == target.requirement_id
        )
        self.assertTrue(row["evidence_present"])
        self.assertFalse(row["verifier_present"])
        self.assertTrue(
            any(
                "missing supplemental verifier/evidence" in error
                for error in row["errors"]
            ),
            report,
        )

    def test_verify_rejects_s27_probe_builder_identity_and_kwargs_mutation(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("current_result_probes")
        data = json.loads(summary.read_text(encoding="utf-8"))
        row = next(item for item in data["probes"] if item["scenario"] == 27)
        row["builder_module"] = "tools.build_scenario26_clear_probe_rom"
        row["builder_kwargs"] = {"allow_balanced_input": True}
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            item for item in report["phases"]
            if item["id"] == "current_result_probes"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("S27 builder module identity differs" in error for error in phase["errors"]),
            report,
        )
        self.assertTrue(
            any("S27 builder kwargs differ" in error for error in phase["errors"]),
            report,
        )

    def test_verify_rejects_internally_reported_extra_s27_probe_byte(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("current_result_probes")
        data = json.loads(summary.read_text(encoding="utf-8"))
        row = next(item for item in data["probes"] if item["scenario"] == 27)
        probe_report = row["normal"]
        probe_path = Path(probe_report["path"])
        payload = bytearray(probe_path.read_bytes())
        payload[0x300000] ^= 1
        probe_path.write_bytes(payload)
        probe_report["sha256"] = gate.sha256_path(probe_path)
        row["diagnostic_delta"]["normal"] = gate.diagnostic_delta_report(
            self.release_paths["normal"].read_bytes(),
            payload,
        )
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            item for item in report["phases"]
            if item["id"] == "current_result_probes"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(
                "not the exact canonical S27 builder derivative" in error
                or "exact changed-byte set differs" in error
                for error in phase["errors"]
            ),
            report,
        )

    def test_verify_rejects_s27_hp1_runtime_stage_semantic_mutations(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("scenario27_final_and_ending", "hard")
        data = json.loads(summary.read_text(encoding="utf-8"))
        stage = data["diagnostic_runtime_stage"]
        stage["harness_only"] = False
        stage["natural_full_battle_clear"] = True
        stage["product_release_rom_changed"] = True
        stage["start_callback_operand_address"] = "0x00F2E2"
        stage["start_wrapper_address"] = "0x3FEE00"
        stage["stock_start_entry_address"] = "0x022C20"
        stage["wrapper_sha256"] = "0" * 64
        stage["runtime_hp_address"] = "0xFFFF6600"
        stage["bernhardt"]["hp"] = 2
        stage["ordinary_stock_attack_death_and_ending_handlers"] = False
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            item for item in report["phases"]
            if item["id"] == "scenario27_final_and_ending"
        )
        self.assertEqual(report["status"], "fail")
        for field in (
            "harness_only",
            "natural_full_battle_clear",
            "product_release_rom_changed",
            "start_callback_operand_address",
            "start_wrapper_address",
            "stock_start_entry_address",
            "wrapper_sha256",
            "runtime_hp_address",
            "bernhardt.hp",
            "ordinary_stock_attack_death_and_ending_handlers",
        ):
            with self.subTest(field=field):
                self.assertTrue(
                    any(field in error for error in phase["errors"]),
                    report,
                )

    def test_verify_fails_when_any_phase_summary_is_missing(self):
        self.write_plan()
        report = gate.verify_plan_manifest(self.manifest)
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["all_phase_summaries_present"])
        self.assertFalse(report["no_phase_skipped"])
        self.assertEqual(report["observed_gate_pass_count"], 0)

    def test_verify_fails_when_release_rom_changed_after_plan(self):
        self.write_plan()
        with self.release_paths["normal"].open("r+b") as stream:
            stream.seek(0x100)
            stream.write(b"changed")
        report = gate.verify_plan_manifest(self.manifest)
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["release_roms_unchanged"])
        self.assertTrue(
            any("normal" in error and "SHA" in error for error in report["errors"])
        )

    def test_verify_reports_missing_release_rom_without_crashing(self):
        self.materialize_passing_summaries()
        self.release_paths["hard"].unlink()
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)

        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["release_roms_unchanged"])
        phase = next(
            item
            for item in report["phases"]
            if item["id"] == "natural_and_legacy_join"
        )
        self.assertTrue(
            any(
                "exact release ROM cannot be read" in error
                for error in phase["errors"]
            ),
            report,
        )

    def test_verify_rejects_scenario6_seed_outside_fresh_lineage(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("scenario6_actual_runestone", "hard")
        data = json.loads(summary.read_text(encoding="utf-8"))
        stale = summary.parent / "historical-s27.gst"
        stale.write_bytes(b"historical-hard-s27")
        data["seed"] = {
            "path": str(stale),
            "sha256": gate.sha256_path(stale),
        }
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        self.assertEqual(report["status"], "fail")
        phase = next(
            row
            for row in report["phases"]
            if row["id"] == "scenario6_actual_runestone"
        )
        self.assertTrue(
            any(
                "scenario6/hard" in error
                and "seed path differs from fresh hard seed" in error
                for error in phase["errors"]
            ),
            report,
        )

    def test_verify_rejects_scenario6_probe_or_runtime_inventory_tamper(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("scenario6_actual_runestone", "normal")
        data = json.loads(summary.read_text(encoding="utf-8"))
        probe = Path(data["probe"]["path"])
        with probe.open("r+b") as stream:
            stream.seek(gate.scenario6_probe.FIRST_PLAYER_DEPLOYMENT + 2)
            current = stream.read(1)
            stream.seek(-1, 1)
            stream.write(bytes((current[0] ^ 1,)))
        data["probe"]["sha256"] = gate.sha256_path(probe)
        data["inventory_acquisition"]["changed_record_count"] = 2
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row
            for row in report["phases"]
            if row["id"] == "scenario6_actual_runestone"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(
                "exact source-locked derivative" in error
                or "reported inventory delta differs from GST" in error
                for error in phase["errors"]
            ),
            report,
        )

    def test_verify_rejects_parallel_surface_seed_outside_fresh_lineage(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("preparation_s01_s31", "normal")
        data = json.loads(summary.read_text(encoding="utf-8"))
        stale = summary.parent / "historical-s27.gst"
        stale.write_bytes(b"historical-normal-s27")
        data["seed"] = {
            "path": str(stale),
            "sha256": gate.sha256_path(stale),
        }
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row for row in report["phases"] if row["id"] == "preparation_s01_s31"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(
                "seed path differs from fresh normal seed" in error
                for error in phase["errors"]
            ),
            report,
        )

    def test_verify_rejects_changed_visual_review_source(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("preparation_s01_s31", "manual-visual-review")
        data = json.loads(summary.read_text(encoding="utf-8"))
        manifest_path = Path(data["results"][0]["manifest"]["path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source = Path(manifest["groups"][0]["sheets"][0]["sources"][0]["path"])
        source.write_bytes(b"changed-after-manual-review")
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row for row in report["phases"] if row["id"] == "preparation_s01_s31"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("review source file/hash/path differs" in error for error in phase["errors"]),
            report,
        )

    def test_verify_rejects_campaign_without_exact_automatic_save_chain(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("continuous_campaign_route")
        data = json.loads(summary.read_text(encoding="utf-8"))
        normal = next(row for row in data["results"] if row["profile"] == "normal")
        normal["results"][1]["input_state"]["gst_sha256"] = "0" * 64
        normal["results"][1]["manual_intervention"] = True
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row
            for row in report["phases"]
            if row["id"] == "continuous_campaign_route"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(
                "manual-intervention proof differs" in error
                or "input GST/hash proof broke" in error
                for error in phase["errors"]
            ),
            report,
        )

    def test_verify_rejects_first_turn_summary_from_another_run(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("first_turn_s01_s31", "pure")
        data = json.loads(summary.read_text(encoding="utf-8"))
        data["run_id"] = "historical-run"
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row for row in report["phases"] if row["id"] == "first_turn_s01_s31"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("run_id" in error for error in phase["errors"]), report)

    def test_verify_rejects_first_turn_old_seed_fallback(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("first_turn_s01_s31", "normal")
        data = json.loads(summary.read_text(encoding="utf-8"))
        stale = summary.parent / "captures-analysis-fallback.gst"
        stale.write_bytes(b"historical-normal-seed")
        stale_seed = {
            "path": str(stale),
            "sha256": gate.sha256_path(stale),
        }
        data["seed"] = stale_seed
        data["seed_before"] = stale_seed
        data["seed_after"] = stale_seed
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row for row in report["phases"] if row["id"] == "first_turn_s01_s31"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(
                "seed path differs from fresh normal seed" in error
                for error in phase["errors"]
            ),
            report,
        )

    def test_verify_rejects_late_loader_reusing_raw_s1_seed(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("first_turn_s01_s31", "hard")
        data = json.loads(summary.read_text(encoding="utf-8"))
        raw_s1_source = dict(data["scenario_seeds"]["1"])
        data["scenario_seeds"]["25"] = raw_s1_source
        data["scenario_seeds_after"]["25"] = raw_s1_source
        target = next(row for row in data["scenarios"] if row["scenario"] == 25)
        target["entry_source_lineage"]["seed"] = {
            "path": raw_s1_source["path"],
            "sha256": raw_s1_source["sha256"],
        }
        target["entry_source_lineage"]["source"] = raw_s1_source
        loader_path = Path(target["loader_results"])
        loader = json.loads(loader_path.read_text(encoding="utf-8"))
        loader["scenarios"][0]["seed"] = raw_s1_source["path"]
        loader["scenarios"][0]["seed_sha256"] = raw_s1_source["sha256"]
        self.write_json(loader_path, loader)
        loader_sha256 = gate.sha256_path(loader_path)
        target["loader_results_sha256"] = loader_sha256
        target["entry_source_lineage"]["loader_results_sha256"] = loader_sha256
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row for row in report["phases"] if row["id"] == "first_turn_s01_s31"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(
                "S25 loader entry-source" in error
                and "continuous campaign input" in error.lower()
                for error in phase["errors"]
            ),
            report,
        )

    def test_verify_rereads_tampered_loader_and_first_turn_manifests(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("first_turn_s01_s31", "pure")
        data = json.loads(summary.read_text(encoding="utf-8"))
        target = next(row for row in data["scenarios"] if row["scenario"] == 20)

        stale = summary.parent / "historical-loader-seed.gst"
        stale.write_bytes(b"historical-loader-seed")
        loader_results = Path(target["loader_results"])
        loader = json.loads(loader_results.read_text(encoding="utf-8"))
        loader["scenarios"][0]["seed"] = str(stale)
        loader["scenarios"][0]["seed_sha256"] = gate.sha256_path(stale)
        self.write_json(loader_results, loader)
        loader_sha256 = gate.sha256_path(loader_results)
        target["loader_results_sha256"] = loader_sha256
        target["entry_source_lineage"]["loader_results_sha256"] = (
            loader_sha256
        )

        first_turn_results = Path(target["first_turn_results"])
        first_turn = json.loads(first_turn_results.read_text(encoding="utf-8"))
        first_turn["scenarios"][0]["entry_evidence"]["kind"] = "deep_runtime"
        self.write_json(first_turn_results, first_turn)
        first_turn_sha256 = gate.sha256_path(first_turn_results)
        target["first_turn_results_sha256"] = first_turn_sha256
        target["entry_source_lineage"]["first_turn_results_sha256"] = (
            first_turn_sha256
        )
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row for row in report["phases"] if row["id"] == "first_turn_s01_s31"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(
                "S20 loader entry-source" in error
                and "loader manifest seed lineage differs" in error
                for error in phase["errors"]
            ),
            report,
        )
        self.assertTrue(
            any(
                "S20 loader entry-source" in error
                and "first-turn entry evidence differs" in error
                for error in phase["errors"]
            ),
            report,
        )

    def test_verify_rejects_first_turn_command_lineage_argument_tamper(self):
        self.materialize_passing_summaries()
        phase = self.phase("first_turn_s01_s31")
        phase["dependencies"] = ["current_result_probes"]
        pure = next(row for row in phase["commands"] if row["label"] == "pure")
        seed_position = pure["argv"].index("--seed-gst")
        pure["argv"][seed_position + 1] = str(self.root / "historical.gst")
        campaign_position = pure["argv"].index("--campaign-summary")
        pure["argv"][campaign_position + 1] = str(
            self.root / "historical-campaign.json"
        )
        normal = next(
            row for row in phase["commands"] if row["label"] == "normal"
        )
        campaign_position = normal["argv"].index("--campaign-summary")
        del normal["argv"][campaign_position:campaign_position + 2]
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        verified = next(
            row for row in report["phases"] if row["id"] == "first_turn_s01_s31"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("phase dependencies" in error for error in verified["errors"]),
            report,
        )
        self.assertTrue(
            any(
                "--seed-gst differs from fresh pure seed" in error
                for error in verified["errors"]
            ),
            report,
        )
        self.assertTrue(
            any(
                "--campaign-summary" in error
                and "continuous campaign" in error.lower()
                for error in verified["errors"]
            ),
            report,
        )
        self.assertTrue(
            any(
                "exactly one --campaign-summary" in error
                for error in verified["errors"]
            ),
            report,
        )

    def test_verify_rejects_runestone_without_exact_three_label_surface(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("runestone_restart")
        data = json.loads(summary.read_text(encoding="utf-8"))
        target = next(
            row
            for row in data["results"]
            if row["profile"] == "normal"
            and row["character"] == "keith"
            and row["current_tier"] == 5
        )
        target["candidate_label_surface"]["observed_fingerprints"][1] = "0" * 64
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        self.assertEqual(report["status"], "fail")
        phase = next(
            row for row in report["phases"] if row["id"] == "runestone_restart"
        )
        self.assertTrue(
            any("three-label fingerprint proof" in error for error in phase["errors"]),
            report,
        )

    def test_verify_rejects_join_pre_completion_drift(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("natural_and_legacy_join")
        data = json.loads(summary.read_text(encoding="utf-8"))
        row = next(
            row
            for profile in data["results"]
            if profile["profile"] == "pure"
            for row in profile["results"]
            if row["case"] == "natural-keith-default"
        )
        row["pre_completion"]["runtime"]["experience"] = 15
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row
            for row in report["phases"]
            if row["id"] == "natural_and_legacy_join"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("pre-completion class/LV/EXP differs" in error for error in phase["errors"]),
            report,
        )

    def test_verify_rejects_live_sram_read_without_process_exit_flush(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("natural_and_legacy_join")
        data = json.loads(summary.read_text(encoding="utf-8"))
        row = next(
            row
            for profile in data["results"]
            if profile["profile"] == "normal"
            for row in profile["pending_marker_probes"]
            if row["pending_probe_key"] == "natural:keith"
        )
        row["candidate"].pop("pending_flush")
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row
            for row in report["phases"]
            if row["id"] == "natural_and_legacy_join"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("process-exit flush report is missing" in error for error in phase["errors"]),
            report,
        )

    def test_verify_rejects_full_flow_bound_to_wrong_pending_probe(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("natural_and_legacy_join")
        data = json.loads(summary.read_text(encoding="utf-8"))
        profile = next(
            row for row in data["results"] if row["profile"] == "hard"
        )
        target = next(
            row
            for row in profile["results"]
            if row["case"] == "natural-keith-hawk-lord"
        )
        wrong = next(
            row
            for row in profile["results"]
            if row["case"] == "natural-lester-default"
        )
        target["pending_marker_probe"] = wrong["pending_marker_probe"]
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row
            for row in report["phases"]
            if row["id"] == "natural_and_legacy_join"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(
                "pending-marker reference differs" in error
                or "wrong pending-probe key" in error
                for error in phase["errors"]
            ),
            report,
        )

    def test_verify_rejects_pending_and_full_flow_reusing_runtime_home(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("natural_and_legacy_join")
        data = json.loads(summary.read_text(encoding="utf-8"))
        profile = next(
            row for row in data["results"] if row["profile"] == "pure"
        )
        pending = next(
            row
            for row in profile["pending_marker_probes"]
            if row["pending_probe_key"] == "natural:keith"
        )
        target = next(
            row
            for row in profile["results"]
            if row["case"] == "natural-keith-default"
        )
        reused_home = pending["runtime_isolation"]["runtime_home"]
        target["runtime_isolation"]["runtime_home"] = reused_home
        evidence_path = Path(target["evidence_path"])
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["runtime_isolation"]["runtime_home"] = reused_home
        self.write_json(evidence_path, evidence)
        target["evidence_sha256"] = gate.sha256_path(evidence_path)
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row
            for row in report["phases"]
            if row["id"] == "natural_and_legacy_join"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("reused one runtime home" in error for error in phase["errors"]),
            report,
        )

    def test_verify_rejects_branch_specific_join_experience(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("natural_and_legacy_join")
        data = json.loads(summary.read_text(encoding="utf-8"))
        row = next(
            row
            for profile in data["results"]
            if profile["profile"] == "hard"
            for row in profile["results"]
            if row["case"] == "natural-lester-croco-lord"
        )
        row["join_experience"]["raw_experience"] += 1
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row
            for row in report["phases"]
            if row["id"] == "natural_and_legacy_join"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("fixed raw EXP contract differs" in error for error in phase["errors"]),
            report,
        )

    def test_verify_reparses_join_runtime_from_hash_bound_gst(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("natural_and_legacy_join")
        data = json.loads(summary.read_text(encoding="utf-8"))
        row = next(
            row
            for profile in data["results"]
            if profile["profile"] == "hard"
            for row in profile["results"]
            if row["case"] == "natural-lester-default"
        )
        # MP is not part of the mathematical result tuple, so only an
        # independent GST parse can reject this internally consistent report.
        row["applied_immediate"]["runtime"]["mp"] = 1
        self.rewrite_join_evidence(row)
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            item
            for item in report["phases"]
            if item["id"] == "natural_and_legacy_join"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("reported runtime differs from GST" in error for error in phase["errors"]),
            report,
        )

    def test_verify_recomputes_candidate_label_fingerprint_from_png(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("natural_and_legacy_join")
        data = json.loads(summary.read_text(encoding="utf-8"))
        row = next(
            row
            for profile in data["results"]
            if profile["profile"] == "normal"
            for row in profile["results"]
            if row["case"] == "natural-jessica-default"
        )
        capture = Path(row["candidate"]["capture"]["path"])
        with Image.open(capture) as opened:
            image = opened.convert("RGB")
        image.putpixel(
            (
                gate.JOIN_CANDIDATE_LABEL_BOX[0],
                gate.JOIN_CANDIDATE_LABEL_BOX[1],
            ),
            (255, 255, 255),
        )
        image.save(capture)
        row["candidate"]["capture"]["sha256"] = gate.sha256_path(capture)
        self.rewrite_join_evidence(row)
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            item
            for item in report["phases"]
            if item["id"] == "natural_and_legacy_join"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("live label fingerprint" in error for error in phase["errors"]),
            report,
        )

    def test_verify_reclassifies_result_and_save_surfaces_from_png(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("natural_and_legacy_join")
        data = json.loads(summary.read_text(encoding="utf-8"))
        row = next(
            row
            for profile in data["results"]
            if profile["profile"] == "pure"
            for row in profile["results"]
            if row["case"] == "natural-jessica-default"
        )
        for section_name, point in (
            ("battle_result", next(iter(gate.result_surface.RESULT_POINTS))),
            ("save_menu", next(iter(gate.result_surface.SAVE_POINTS))),
        ):
            capture_report = row[section_name]["capture"]
            capture = Path(capture_report["path"])
            with Image.open(capture) as opened:
                image = opened.convert("RGB")
            image.putpixel(point, (0, 0, 0))
            image.save(capture)
            capture_report["sha256"] = gate.sha256_path(capture)
        self.rewrite_join_evidence(row)
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            item
            for item in report["phases"]
            if item["id"] == "natural_and_legacy_join"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("live surface is not" in error for error in phase["errors"]),
            report,
        )

    def test_verify_rejects_stale_join_case_run_id_replay(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("natural_and_legacy_join")
        data = json.loads(summary.read_text(encoding="utf-8"))
        row = data["results"][0]["results"][0]
        row["run_id"] = "historical-join-run"
        self.rewrite_join_evidence(row)
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            item
            for item in report["phases"]
            if item["id"] == "natural_and_legacy_join"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("run_id" in error for error in phase["errors"]),
            report,
        )

    def test_verify_rejects_cross_case_primary_artifact_reuse(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("natural_and_legacy_join")
        data = json.loads(summary.read_text(encoding="utf-8"))
        profile = next(
            item for item in data["results"] if item["profile"] == "pure"
        )
        first = next(
            row
            for row in profile["results"]
            if row["case"] == "natural-keith-default"
        )
        second = next(
            row
            for row in profile["results"]
            if row["case"] == "natural-keith-hawk-lord"
        )
        second["candidate"]["gst"] = first["candidate"]["gst"]
        second["candidate"]["gst_sha256"] = first["candidate"]["gst_sha256"]
        self.rewrite_join_evidence(second)
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            item
            for item in report["phases"]
            if item["id"] == "natural_and_legacy_join"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("reuses primary evidence" in error for error in phase["errors"]),
            report,
        )

    def test_verify_rejects_cross_case_marker_artifact_reuse(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("natural_and_legacy_join")
        data = json.loads(summary.read_text(encoding="utf-8"))
        profile = next(
            item for item in data["results"] if item["profile"] == "normal"
        )
        first = next(
            row
            for row in profile["results"]
            if row["case"] == "natural-keith-default"
        )
        second = next(
            row
            for row in profile["results"]
            if row["case"] == "natural-keith-hawk-lord"
        )
        second["save_menu"]["consumed_join_marker"] = first["save_menu"][
            "consumed_join_marker"
        ]
        second["save_menu"]["consumed_flush"]["flushed_marker"] = first[
            "save_menu"
        ]["consumed_join_marker"]
        self.rewrite_join_evidence(second)
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            item
            for item in report["phases"]
            if item["id"] == "natural_and_legacy_join"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("reuses primary evidence" in error for error in phase["errors"]),
            report,
        )

    def test_verify_reads_zero_grant_gauge_from_release_rom(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("natural_and_legacy_join")
        data = json.loads(summary.read_text(encoding="utf-8"))
        row = next(
            row
            for profile in data["results"]
            if profile["profile"] == "normal"
            for row in profile["results"]
            if row["case"] == "natural-keith-hawk-lord"
        )
        row["progression_expectation"]["class_experience_gauge"] = 24
        row["applied_immediate"]["progression_settlement"][
            "class_experience_gauge"
        ] = 24
        self.rewrite_join_evidence(row)
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            item
            for item in report["phases"]
            if item["id"] == "natural_and_legacy_join"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("gauge differs from release ROM" in error for error in phase["errors"]),
            report,
        )

    def test_verify_rejects_unconsumed_runestone_join_marker(self):
        self.materialize_passing_summaries()
        summary = self.summary_path("runestone_restart")
        data = json.loads(summary.read_text(encoding="utf-8"))
        row = next(
            row
            for row in data["results"]
            if row["profile"] == "hard"
            and row["character"] == "lester"
            and row["current_tier"] == 5
        )
        marker = row["runtime_join_marker"]
        marker_path = Path(marker["path"])
        payload = bytearray(marker_path.read_bytes())
        offset = int(marker["sram_offset"], 16)
        payload[offset] = gate.JOIN_PENDING_MARKER
        marker_path.write_bytes(payload)
        marker["sha256"] = gate.sha256_path(marker_path)
        marker["value"] = gate.JOIN_PENDING_MARKER
        marker["status"] = "pass"
        self.write_json(summary, data)
        self.write_plan()

        report = gate.verify_plan_manifest(self.manifest)
        phase = next(
            row for row in report["phases"] if row["id"] == "runestone_restart"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any("runtime join marker" in error for error in phase["errors"]),
            report,
        )

    def test_verify_rejects_reordered_or_removed_phase(self):
        phases = self.plan["phases"]
        phases[0], phases[1] = phases[1], phases[0]
        self.write_plan()
        report = gate.verify_plan_manifest(self.manifest)
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["exact_phase_order"])
        self.assertFalse(report["no_phase_skipped"])

    def test_verify_rejects_duplicate_or_mismatched_run_id_option(self):
        self.materialize_passing_summaries()
        fresh = self.phase("fresh_s1_seed")
        fresh["commands"][0]["argv"].extend(
            ["--run-id", "different-final-run"]
        )
        self.write_plan()
        report = gate.verify_plan_manifest(self.manifest)
        self.assertEqual(report["status"], "fail")
        fresh_report = next(
            phase for phase in report["phases"] if phase["id"] == "fresh_s1_seed"
        )
        self.assertTrue(
            any("duplicate --run-id" in error for error in fresh_report["errors"])
        )


if __name__ == "__main__":
    unittest.main()

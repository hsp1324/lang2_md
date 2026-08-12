import hashlib
from pathlib import Path
import tempfile
import unittest

from tools import run_blastem_sequence as sequence
from tools import run_scenario27_ending_page_supplement as supplement
from tools import v137_release_identity as release_identity


def blank_record() -> bytearray:
    record = bytearray(sequence.MANUAL_SLOT_CHECKSUM_DATA_SIZE)
    record[:2] = (27).to_bytes(2, "big")
    return record


def set_stats(record: bytearray, slot: int, kills: int, retreats: int) -> None:
    base = (
        sequence.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
        + slot * sequence.MANUAL_SLOT_COMMANDER_RECORD_SIZE
    )
    record[base + 0x12 : base + 0x14] = kills.to_bytes(2, "big")
    record[base + 0x14] = retreats


def gst_for_record(record: bytes) -> bytes:
    payload = bytearray(sequence.GST_WORK_RAM_FILE_OFFSET + 0x10000)
    cursor = 0
    for address, size in sequence.MANUAL_SLOT_WORK_RAM_SEGMENTS:
        start = sequence.GST_WORK_RAM_FILE_OFFSET + address
        payload[start : start + size] = record[cursor : cursor + size]
        cursor += size
    return bytes(payload)



class Scenario27EndingPageSupplementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roms = {
            profile: path.read_bytes()
            for profile, path in release_identity.RELEASE_ROM_PATHS.items()
        }

    def test_saved_kill_and_retreat_offsets_match_the_disassembled_selector(self):
        record = blank_record()
        set_stats(record, 5, 0x1234, 0x56)
        self.assertEqual(
            supplement.serialized_roster_stats(bytes(record), 5),
            (0x1234, 0x56),
        )

    def test_normal_epilogue_slots_use_the_stock_status_commander_mapping(self):
        rom = self.roms["normal"]
        self.assertEqual(
            [
                supplement.ending_status_roster_index(rom, slot)
                for slot in range(8)
            ],
            [5, 3, 6, 2, 7, 8, 4, 9],
        )
        record = blank_record()
        set_stats(record, 0, 0, 0)
        set_stats(record, 5, 150, 0)
        group = supplement.be32(rom, supplement.EPILOGUE_GROUP_POINTER_TABLE)
        self.assertEqual(
            supplement.selected_epilogue_pointer(rom, bytes(record), 0),
            supplement.be32(rom, group + 12 + 8),
        )
        set_stats(record, 0, 150, 0)
        set_stats(record, 5, 0, 0)
        self.assertEqual(
            supplement.selected_epilogue_pointer(rom, bytes(record), 0),
            supplement.be32(rom, group + 8),
        )

    def test_post_battle_runtime_stats_drive_boundary_selectors(self):
        record = blank_record()
        set_stats(record, 0, 0xC7, 0)
        set_stats(record, 1, 0, 0)
        self.assertEqual(supplement.ending_visit_sequence_index(record, 14), 13)
        gst = bytearray(gst_for_record(bytes(record)))
        runtime_group = (
            sequence.GST_WORK_RAM_FILE_OFFSET
            + supplement.RUNTIME_GROUP_BASE
        )
        gst[runtime_group + 1] = 1
        gst[runtime_group + supplement.RUNTIME_HP_OFFSET] = 10
        gst[
            runtime_group + supplement.RUNTIME_SCENARIO_KILLS_OFFSET
        ] = 1
        selected, report = supplement.selector_record_from_runtime_roster(
            bytes(record),
            bytes(gst),
        )
        self.assertEqual(supplement.ending_visit_sequence_index(selected, 14), 12)
        self.assertEqual(report["stats"][0]["selector_kill_delta"], 1)
        self.assertTrue(
            all(row["selector_retreat_delta"] == 0 for row in report["stats"])
        )

    def test_visit_sequence_boundary_branches_are_exact(self):
        record = blank_record()
        self.assertEqual(supplement.ending_visit_sequence_index(record, 0), 0)
        set_stats(record, 5, 0, 2)
        self.assertEqual(supplement.ending_visit_sequence_index(record, 0), 1)

        set_stats(record, 8, 0x62, 0)
        self.assertEqual(supplement.ending_visit_sequence_index(record, 5), 7)
        set_stats(record, 8, 0x61, 0)
        self.assertEqual(supplement.ending_visit_sequence_index(record, 5), 8)
        set_stats(record, 8, 0x9B, 1)
        self.assertEqual(supplement.ending_visit_sequence_index(record, 5), 8)
        set_stats(record, 8, 0x9A, 1)
        self.assertEqual(supplement.ending_visit_sequence_index(record, 5), 9)
        set_stats(record, 8, 0xFFFF, 2)
        self.assertEqual(supplement.ending_visit_sequence_index(record, 5), 9)

        set_stats(record, 0, 0xC8, 0)
        set_stats(record, 1, 0, 0)
        self.assertEqual(supplement.ending_visit_sequence_index(record, 14), 12)
        set_stats(record, 0, 0xC7, 0)
        self.assertEqual(supplement.ending_visit_sequence_index(record, 14), 13)
        self.assertIsNone(supplement.ending_visit_sequence_index(record, 15))

    def test_special_epilogue_selector_boundaries_match_stock_bls_branches(self):
        record = blank_record()
        set_stats(record, 0, 0xC8, 0)
        set_stats(record, 1, 0x28, 0)
        self.assertEqual(supplement.epilogue_special_index(record, 14), 0)
        set_stats(record, 0, 0xC9, 0)
        self.assertEqual(supplement.epilogue_special_index(record, 14), 1)
        set_stats(record, 1, 0x28, 1)
        self.assertEqual(supplement.epilogue_special_index(record, 14), 2)
        set_stats(record, 1, 0x29, 1)
        self.assertEqual(supplement.epilogue_special_index(record, 14), 3)
        set_stats(record, 1, 0x49, 1)
        self.assertEqual(supplement.epilogue_special_index(record, 14), 4)
        set_stats(record, 1, 0x28, 2)
        self.assertEqual(supplement.epilogue_special_index(record, 14), 5)
        set_stats(record, 1, 0x29, 2)
        self.assertEqual(supplement.epilogue_special_index(record, 14), 6)
        set_stats(record, 1, 0x49, 2)
        self.assertEqual(supplement.epilogue_special_index(record, 14), 7)

        set_stats(record, 0, 0x92, 0)
        self.assertEqual(supplement.epilogue_special_index(record, 15), 0)
        set_stats(record, 0, 0x93, 0)
        self.assertEqual(supplement.epilogue_special_index(record, 15), 1)
        set_stats(record, 0, 0xC9, 1)
        self.assertEqual(supplement.epilogue_special_index(record, 15), 2)
        set_stats(record, 1, 0, 0)
        self.assertEqual(supplement.epilogue_special_index(record, 15), 3)

    def test_zero_stat_model_is_identical_across_exact_release_profiles(self):
        record = bytes(blank_record())
        models = {
            profile: supplement.build_expected_page_model(rom, record)
            for profile, rom in self.roms.items()
        }
        self.assertEqual(
            {model["expected_semantic_digest"] for model in models.values()},
            {next(iter(models.values()))["expected_semantic_digest"]},
        )
        for model in models.values():
            self.assertEqual(model["expected_closing_montage_pages"], 10)
            self.assertEqual(model["expected_visit_pages"], 48)
            self.assertEqual(model["expected_epilogue_pages"], 98)
            self.assertEqual(model["expected_page_count"], 156)
            self.assertEqual(len(model["slots"]), 16)
            self.assertEqual(
                [
                    row["epilogue"]["record_index"]
                    if row["epilogue"] is not None
                    else None
                    for row in model["slots"]
                ],
                [0, 9, 18, 27, 36, 45, 54, 63, 72, 73, 74, 75, 76, 77, 78, 86],
            )

    def test_model_uses_rom_token_digests_not_declared_text_as_a_golden(self):
        model = supplement.build_expected_page_model(
            self.roms["normal"], bytes(blank_record())
        )
        montage = model["expected_pages"][0]
        dialogue = model["expected_dialogue_pages"][0]
        self.assertEqual(montage["kind"], "closing_montage")
        self.assertEqual(dialogue["kind"], "ending_visit")
        for page in (montage, dialogue):
            self.assertEqual(len(page["token_sha256"]), 64)
            self.assertNotIn("capture", page)
            self.assertNotIn("text_fingerprint_sha256", page)
        self.assertIn("Japanese routine", model["selector_anchors"]["ending_visit_branch"])

    def test_selector_ranges_are_source_locked_in_every_release(self):
        for profile, rom in self.roms.items():
            with self.subTest(profile=profile):
                rows = supplement.validate_selector_source_ranges(rom)
                self.assertEqual(rows.keys(), supplement.SELECTOR_SOURCE_RANGES.keys())
                self.assertTrue(all(row["source_locked"] for row in rows.values()))
        corrupted = bytearray(self.roms["normal"])
        corrupted[0x01DC64] ^= 1
        with self.assertRaisesRegex(ValueError, "epilogue_selector"):
            supplement.validate_selector_source_ranges(bytes(corrupted))

    def test_closing_montage_calls_and_renderer_are_source_locked(self):
        for profile, rom in self.roms.items():
            with self.subTest(profile=profile):
                result = supplement.validate_closing_montage_renderer(rom)
                self.assertTrue(result["source_locked"])
                self.assertEqual(len(result["loader_calls"]), 10)
        corrupted = bytearray(self.roms["normal"])
        corrupted[supplement.CLOSING_MONTAGE_RECORDS[3][1]] ^= 1
        with self.assertRaisesRegex(ValueError, "loader source changed"):
            supplement.validate_closing_montage_renderer(bytes(corrupted))

    def test_closing_montage_glyph_converter_matches_stock_plane_math(self):
        rom = bytearray(
            supplement.CLOSING_MONTAGE_GLYPH_ROM_BASE
            + 2 * supplement.CLOSING_MONTAGE_GLYPH_SOURCE_BYTES
        )
        glyph = (
            supplement.CLOSING_MONTAGE_GLYPH_ROM_BASE
            + supplement.CLOSING_MONTAGE_GLYPH_SOURCE_BYTES
        )
        # The first pixel has both input planes set, producing colour nibble 3.
        rom[glyph : glyph + 2] = bytes.fromhex("8080")
        rendered = supplement.closing_montage_glyph_vram(bytes(rom), [1])
        self.assertEqual(len(rendered), supplement.CLOSING_MONTAGE_GLYPH_VRAM_BYTES)
        self.assertEqual(rendered[:4], bytes.fromhex("30000000"))
        self.assertEqual(rendered[4:], bytes(len(rendered) - 4))

    def test_closing_montage_runtime_vram_match_is_release_derived(self):
        rom = self.roms["normal"]
        model = supplement.build_expected_page_model(rom, bytes(blank_record()))
        first = model["closing_montage"][0]
        source = int(first["source_address"], 16)
        tokens = [
            supplement.be16(rom, source + index * 2)
            for index in range(first["token_count"])
        ]
        rendered = supplement.closing_montage_glyph_vram(rom, tokens)
        vram = bytearray(supplement.GST_VRAM_BYTES)
        start = supplement.CLOSING_MONTAGE_VRAM_START
        vram[start : start + len(rendered)] = rendered
        matches = supplement.active_closing_montage(bytes(vram), model)
        self.assertEqual([row["record_index"] for row in matches], [0])
        surface = {
            "ending_frame": 1,
            "runtime": {"closing_montage_matches": matches},
        }
        observed, extras = supplement.assign_semantic_montage([surface], model)
        self.assertEqual(
            [row["semantic"] for row in observed],
            model["expected_montage_pages"][:1],
        )
        self.assertEqual(extras, [])
        vram[start] ^= 1
        self.assertEqual(supplement.active_closing_montage(bytes(vram), model), [])

    def test_montage_assignment_keeps_the_last_stable_surface_for_a_record(self):
        expected = {
            "slot": None,
            "kind": "closing_montage",
            "source_address": "0x0A6BA8",
            "record_index": 0,
            "page_index": 0,
            "token_count": 1,
            "token_sha256": "a" * 64,
        }
        match = {
            "source_address": expected["source_address"],
            "record_index": expected["record_index"],
            "vram_prefix_sha256": "b" * 64,
        }
        model = {"expected_montage_pages": [expected]}
        surfaces = [
            {
                "ending_frame": frame,
                "runtime": {"closing_montage_matches": [match]},
            }
            for frame in (10, 20, 30)
        ]
        observed, extras = supplement.assign_semantic_montage(surfaces, model)
        self.assertEqual(observed[0]["ending_frame"], 30)
        self.assertEqual(
            [row["ending_frame"] for row in extras],
            [10, 20],
        )
        self.assertTrue(
            all(
                row["classification"]
                == "partial_or_intermediate_montage_surface"
                for row in extras
            )
        )

    def test_montage_assignment_flags_a_trailing_exact_duplicate(self):
        expected = [
            {
                "slot": None,
                "kind": "closing_montage",
                "source_address": source,
                "record_index": index,
                "page_index": 0,
                "token_count": 1,
                "token_sha256": str(index) * 64,
            }
            for index, source in enumerate(("0x0A6BA8", "0x0A6BEA"), 1)
        ]

        def surface(page: dict[str, object]) -> dict[str, object]:
            return {
                "runtime": {
                    "closing_montage_matches": [
                        {
                            "source_address": page["source_address"],
                            "record_index": page["record_index"],
                            "vram_prefix_sha256": "f" * 64,
                        }
                    ]
                }
            }

        observed, extras = supplement.assign_semantic_montage(
            [surface(expected[0]), surface(expected[1]), surface(expected[0])],
            {"expected_montage_pages": expected},
        )
        self.assertEqual([row["semantic"] for row in observed], expected)
        self.assertTrue(extras[-1]["fatal_semantic_extra"])
        self.assertEqual(
            extras[-1]["classification"],
            "unexpected_exact_montage_surface",
        )

    def test_selected_normal_descriptor_rejects_a_missing_sentinel(self):
        rom = bytearray(self.roms["normal"])
        group = supplement.be32(rom, supplement.EPILOGUE_GROUP_POINTER_TABLE)
        # Preserve the first eight real descriptors but remove every possible
        # terminator/fit from the bounded scan.
        for index in range(32):
            start = group + index * 12
            rom[start : start + 12] = bytes.fromhex(
                "0001 0000 0001 0000 00000000"
            )
        with self.assertRaisesRegex(ValueError, "unterminated"):
            supplement.selected_epilogue_pointer(
                bytes(rom), bytes(blank_record()), 0
            )

    def test_visit_runtime_buffer_has_independent_control_geometry(self):
        words = [0x7001, 0x7002, 0xFFFD, 0x7003, 0xFFFF]
        actual = supplement.runtime_visit_buffer(words, 7)
        expected_words = [
            0xFFF7,
            7,
            0xFFF7,
            0,
            0x7001,
            0x7002,
            0xFFFA,
            24,
            0xFFFB,
            0x7003,
            0xFFFA,
            16,
            0xFFFC,
        ]
        self.assertEqual(
            actual,
            b"".join(word.to_bytes(2, "big") for word in expected_words),
        )
        self.assertEqual(
            supplement.runtime_visit_page_end_offsets(actual),
            [16, 24],
        )

    def test_visit_runtime_buffer_preserves_leading_and_empty_pages(self):
        actual = supplement.runtime_visit_buffer(
            [0xFFFD, 0xFFFD, 0x7001, 0xFFFF],
            7,
        )
        expected_words = [
            0xFFF7,
            7,
            0xFFF7,
            0,
            0xFFFA,
            8,
            0xFFFB,
            0xFFFA,
            8,
            0xFFFB,
            0x7001,
            0xFFFA,
            16,
            0xFFFC,
        ]
        self.assertEqual(
            actual,
            b"".join(word.to_bytes(2, "big") for word in expected_words),
        )

    def test_runtime_object_scan_requires_callback_and_selected_record_range(self):
        model = supplement.build_expected_page_model(
            self.roms["normal"], bytes(blank_record())
        )
        epilogue = model["slots"][0]["epilogue"]
        pointer = int(epilogue["pointer"], 16)
        ram = bytearray(0x10000)
        # This is the last valid 14-byte aligned object in the scan range.
        offset = supplement.TEXT_OBJECT_SCAN_END - 14
        ram[offset : offset + 2] = supplement.TEXT_OBJECT_CALLBACK.to_bytes(2, "big")
        ram[offset + 2 : offset + 6] = pointer.to_bytes(4, "big")
        ram[offset + 0xA : offset + 0xC] = (3).to_bytes(2, "big")
        ram[offset + 0xC : offset + 0xE] = (5).to_bytes(2, "big")
        record_words = supplement.record_words(
            self.roms["normal"],
            pointer,
            limit=supplement.EPILOGUE_RELOC_LIMIT,
        )
        first_page = supplement.split_record_pages(record_words)[0]
        runtime_page = list(first_page)
        for index in range(len(runtime_page) - 1):
            if runtime_page[index] == 0xFFF7 and runtime_page[index + 1] == 0:
                runtime_page[index + 1] = 5
        page_bytes = b"".join(
            word.to_bytes(2, "big") for word in runtime_page + [0xFFFF]
        )
        start = supplement.ENDING_VISIT_BUFFER_RAM_OFFSET
        ram[start : start + len(page_bytes)] = page_bytes
        objects = supplement.active_epilogue_objects(bytes(ram), model)
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["slot"], 0)
        self.assertEqual(objects[0]["display_countdown"], 3)
        self.assertEqual(
            [row["page_index"] for row in objects[0]["runtime_page_matches"]],
            [0],
        )
        ram[offset : offset + 2] = b"\0\0"
        self.assertEqual(supplement.active_epilogue_objects(bytes(ram), model), [])


    def test_semantic_assignment_keeps_non_page_dialogue_as_extra(self):
        expected_page = {
            "slot": 0,
            "kind": "ending_visit",
            "source_address": "0x0954E2",
            "record_index": 0,
            "page_index": 0,
            "token_count": 1,
            "token_sha256": "a" * 64,
            "runtime_end_pointer": "0xFFFFAA44",
        }
        model = {
            "expected_pages": [expected_page],
            "slots": [
                {
                    "slot": 0,
                    "ending_visits": [
                        {
                            "source_address": "0x0954E2",
                            "runtime_buffer_sha256": "b" * 64,
                            "pages": [
                                {
                                    "page_index": 0,
                                    "runtime_end_pointer": "0xFFFFAA44",
                                }
                            ],
                        }
                    ],
                    "epilogue": None,
                }
            ],
        }
        extra = {
            "ordinal": 1,
            "runtime": {
                "slot": 0,
                "visit_buffer_sha256": None,
                "dialogue_stream_pointer": "0x00000000",
                "epilogue_objects": [],
            },
        }
        page = {
            "ordinal": 2,
            "runtime": {
                "slot": 0,
                "visit_buffer_sha256": "b" * 64,
                "dialogue_stream_pointer": "0xFFFFAA44",
                # A retired text object from another slot may remain in the
                # pool; it must not hide the current slot's visit buffer.
                "epilogue_objects": [
                    {"slot": 15, "source_address": "0x094F1A"}
                ],
            },
        }
        observed, extras = supplement.assign_semantic_pages([extra, page], model)
        self.assertEqual([row["semantic"] for row in observed], [expected_page])
        self.assertEqual(len(extras), 1)
        self.assertEqual(extras[0]["classification"], "non_page_dialogue_surface")

    def test_epilogue_assignment_requires_the_exact_runtime_page(self):
        expected_page = {
            "slot": 0,
            "kind": "epilogue",
            "source_address": "0x094000",
            "record_index": 0,
            "page_index": 2,
            "token_count": 1,
            "token_sha256": "a" * 64,
            "dynamic_name_word_offsets": [],
        }
        model = {
            "expected_pages": [expected_page],
            "expected_dialogue_pages": [expected_page],
            "slots": [{"slot": 0, "ending_visits": [], "epilogue": {}}],
        }
        wrong = {
            "runtime": {
                "slot": 0,
                "visit_buffer_sha256": None,
                "dialogue_stream_pointer": "0x00000000",
                "epilogue_objects": [
                    {
                        "slot": 0,
                        "source_address": "0x094000",
                        "runtime_page_matches": [{"page_index": 1}],
                    }
                ],
            }
        }
        right = {
            "runtime": {
                "slot": 0,
                "visit_buffer_sha256": None,
                "dialogue_stream_pointer": "0x00000000",
                "epilogue_objects": [
                    {
                        "slot": 0,
                        "source_address": "0x094000",
                        "runtime_page_matches": [{"page_index": 2}],
                    }
                ],
            }
        }
        observed, extras = supplement.assign_semantic_pages(
            [wrong, right],
            model,
        )
        self.assertEqual([row["semantic"] for row in observed], [expected_page])
        self.assertEqual(extras[0]["page_index"], 1)
        self.assertTrue(extras[0]["fatal_semantic_extra"])
        self.assertEqual(
            extras[0]["classification"],
            "unexpected_exact_page_surface",
        )

    def test_semantic_assignment_flags_duplicate_and_out_of_order_exact_pages(self):
        pages = [
            {
                "slot": 0,
                "kind": "epilogue",
                "source_address": source,
                "record_index": index,
                "page_index": 0,
                "token_count": 1,
                "token_sha256": str(index) * 64,
            }
            for index, source in enumerate(("0x094000", "0x094100"), 1)
        ]
        model = {
            "expected_pages": pages,
            "expected_dialogue_pages": pages,
            "slots": [{"slot": 0, "ending_visits": [], "epilogue": {}}],
        }

        def surface(source: str) -> dict[str, object]:
            return {
                "runtime": {
                    "slot": 0,
                    "visit_buffer_sha256": None,
                    "dialogue_stream_pointer": "0x00000000",
                    "epilogue_objects": [
                        {
                            "slot": 0,
                            "source_address": source,
                            "runtime_page_matches": [{"page_index": 0}],
                        }
                    ],
                }
            }

        observed, extras = supplement.assign_semantic_pages(
            [
                surface("0x094000"),
                surface("0x094100"),
                surface("0x094000"),
            ],
            model,
        )
        self.assertEqual([row["semantic"] for row in observed], pages)
        self.assertTrue(any(row["fatal_semantic_extra"] for row in extras))

        observed, extras = supplement.assign_semantic_pages(
            [
                surface("0x094000"),
                surface("0x094999"),
                surface("0x094100"),
            ],
            model,
        )
        self.assertEqual([row["semantic"] for row in observed], pages)
        self.assertTrue(any(row["fatal_semantic_extra"] for row in extras))

    def test_blank_accepted_dialogue_text_is_never_visual_proof(self):
        self.assertFalse(
            supplement.dialogue_text_surfaces_nonblank(
                [{"text_fingerprint_white_pixels": 0}]
            )
        )
        self.assertTrue(
            supplement.dialogue_text_surfaces_nonblank(
                [{"text_fingerprint_white_pixels": 1}]
            )
        )

    def test_campaign_seed_requires_byte_exact_s31_to_s27_transition(self):
        record = bytes(blank_record())
        gst = gst_for_record(record)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "s31-save.gst"
            path.write_bytes(gst)
            state = {
                "path": str(path),
                "gst_sha256": hashlib.sha256(gst).hexdigest(),
                "record_sha256": hashlib.sha256(record).hexdigest(),
                "scenario": 27,
            }
            summary = {
                "results": [
                    {
                        "profile": "pure",
                        "results": [
                            {"scenario": 31, "output_state": state},
                            {"scenario": 27, "input_state": dict(state)},
                        ],
                    }
                ]
            }
            actual, lineage = supplement.exact_campaign_seed(summary, "pure")
            self.assertEqual(actual, path.resolve())
            self.assertTrue(lineage["exact_transition"])
            summary["results"][0]["results"][1]["input_state"][
                "record_sha256"
            ] = "0" * 64
            with self.assertRaisesRegex(ValueError, "not the exact"):
                supplement.exact_campaign_seed(summary, "pure")

    def test_campaign_acceptance_uses_only_exact_pre_s27_lineage(self):
        route = list(supplement.campaign.FULL_ROUTE_ORDER)
        record = bytes(blank_record())
        gst = gst_for_record(record)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "s27-input.gst"
            path.write_bytes(gst)
            state = {
                "path": str(path),
                "gst_sha256": hashlib.sha256(gst).hexdigest(),
                "record_sha256": hashlib.sha256(record).hexdigest(),
                "scenario": 27,
            }
            reports = []
            for profile in supplement.PROFILES:
                rows = [
                    {
                        "scenario": scenario,
                        "route_index": index,
                        "status": "pass",
                    }
                    for index, scenario in enumerate(route)
                ]
                rows[-2]["output_state"] = dict(state)
                rows[-1]["input_state"] = dict(state)
                if profile == "pure":
                    rows[-1]["status"] = "failed_attempt"
                reports.append({"profile": profile, "results": rows})
            summary = {
                "run_id": "campaign-run",
                "route_order": route,
                "continuous_save_chain": True,
                "automation_only": True,
                "manual_intervention": False,
                "release_roms_unchanged": True,
                "results": reports,
            }

            result = supplement.validate_campaign_summary_for_supplement(summary)
            self.assertTrue(result["accepted"])
            self.assertFalse(result["terminal_s27_results_used_as_evidence"])
            self.assertEqual(
                [
                    row["retained_s27_status_not_used"]
                    for row in result["retained_exact_s27_inputs"]
                ],
                ["failed_attempt", "pass", "pass"],
            )

            summary["results"][0]["results"][0]["status"] = "failed_attempt"
            with self.assertRaisesRegex(ValueError, "pre-S27 failure"):
                supplement.validate_campaign_summary_for_supplement(summary)


    def test_cross_profile_fingerprint_check_is_corroboration_not_golden(self):
        semantic = {
            "slot": 0,
            "kind": "epilogue",
            "source_address": "0x094000",
            "record_index": 0,
            "page_index": 0,
            "token_count": 1,
            "token_sha256": "a" * 64,
        }
        reports = [
            {
                "profile": profile,
                "observed_semantic_pages": [
                    {
                        "semantic": semantic,
                        "text_fingerprint_sha256": fingerprint,
                        "capture": {"sha256": profile * 8},
                    }
                ],
            }
            for profile, fingerprint in (
                ("pure", "f" * 64),
                ("normal", "f" * 64),
                ("hard", "f" * 64),
            )
        ]
        result = supplement.cross_profile_report(reports)
        self.assertTrue(
            result["stable_text_fingerprints_match_where_semantics_match"]
        )
        reports[-1]["observed_semantic_pages"][0][
            "text_fingerprint_sha256"
        ] = "0" * 64
        result = supplement.cross_profile_report(reports)
        self.assertFalse(
            result["stable_text_fingerprints_match_where_semantics_match"]
        )
        self.assertIn("corroboration only", result["note"])

    def test_cross_profile_logical_identity_catches_token_drift_and_missing_pages(self):
        reports = []
        for profile in supplement.PROFILES:
            reports.append(
                {
                    "profile": profile,
                    "observed_semantic_pages": [
                        {
                            "semantic": {
                                "slot": 0,
                                "kind": "epilogue",
                                "source_address": "0x094000",
                                "record_index": 0,
                                "page_index": 0,
                                "token_count": 1,
                                "token_sha256": (
                                    "b" * 64 if profile == "hard" else "a" * 64
                                ),
                            },
                            "text_fingerprint_sha256": "f" * 64,
                            "capture": {"sha256": profile * 8},
                        }
                    ],
                }
            )
        result = supplement.cross_profile_report(reports)
        self.assertEqual(result["shared_semantic_page_count"], 1)
        self.assertFalse(result["release_tokens_match_for_logical_pages"])
        self.assertEqual(len(result["release_token_mismatches"]), 1)

        result = supplement.cross_profile_report(reports[:-1])
        self.assertFalse(result["all_logical_pages_present_once_per_profile"])
        self.assertEqual(
            result["profile_coverage_mismatches"][0]["missing_profiles"],
            ["hard"],
        )

    def test_cross_profile_montage_uses_runtime_vram_not_dialogue_crop(self):
        semantic = {
            "slot": None,
            "kind": "closing_montage",
            "source_address": "0x0A6BA8",
            "record_index": 0,
            "page_index": 0,
            "token_count": 1,
            "token_sha256": "a" * 64,
        }
        reports = [
            {
                "profile": profile,
                "observed_semantic_pages": [
                    {
                        "semantic": semantic,
                        "vram_match": {"vram_prefix_sha256": "a" * 64},
                        "capture": {"sha256": profile * 8},
                    }
                ],
            }
            for profile in ("pure", "normal", "hard")
        ]
        result = supplement.cross_profile_report(reports)
        self.assertTrue(
            result["stable_text_fingerprints_match_where_semantics_match"]
        )
        self.assertEqual(
            set(result["shared_semantic_pages"][0]["fingerprint_kinds"].values()),
            {"release_derived_runtime_vram_prefix"},
        )

    def test_cross_profile_empty_reports_never_pass_fail_closed_checks(self):
        result = supplement.cross_profile_report([])
        self.assertFalse(result["semantic_pages_nonempty"])
        self.assertFalse(result["all_expected_profiles_reported"])
        self.assertFalse(result["all_logical_pages_present_once_per_profile"])
        self.assertFalse(result["release_tokens_match_for_logical_pages"])
        self.assertFalse(
            result["stable_text_fingerprints_match_where_semantics_match"]
        )


if __name__ == "__main__":
    unittest.main()

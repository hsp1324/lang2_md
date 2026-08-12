import ast
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from tools import run_blastem_sequence as blastem
from tools import run_legacy_5a_runestone_release_matrix as legacy
from tools import run_preparation_surface_matrix as preparation


def synthetic_scenario12_gst(path: Path) -> None:
    record = bytearray(blastem.MANUAL_SLOT_CHECKSUM_DATA_SIZE)
    record[:2] = legacy.SCENARIO_NUMBER.to_bytes(2, "big")
    name = blastem.MANUAL_SLOT_HERO_NAME_OFFSET
    record[name : name + len(blastem.KO_DEFAULT_HERO_NAME)] = (
        blastem.KO_DEFAULT_HERO_NAME
    )
    for commander_id in range(1, blastem.MANUAL_SLOT_COMMANDER_COUNT + 1):
        start = (
            blastem.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
            + (commander_id - 1) * blastem.MANUAL_SLOT_COMMANDER_RECORD_SIZE
        )
        record[start + blastem.MANUAL_SLOT_COMMANDER_CLASS_OFFSET] = 1
        record[start + blastem.MANUAL_SLOT_COMMANDER_LEVEL_OFFSET] = 1
        record[start + blastem.MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET] = 0
    inventory = blastem.MANUAL_SLOT_ITEM_INVENTORY_OFFSET
    inventory_end = inventory + (
        blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT
        * blastem.MANUAL_SLOT_ITEM_INVENTORY_RECORD_SIZE
    )
    record[inventory:inventory_end] = b"\xff" * (inventory_end - inventory)

    highest = max(
        preparation.GST_WORK_RAM_FILE_OFFSET + address + size
        for address, size in preparation.MANUAL_SLOT_WORK_RAM_SEGMENTS
    )
    gst = bytearray(highest)
    source = 0
    for address, size in preparation.MANUAL_SLOT_WORK_RAM_SEGMENTS:
        start = preparation.GST_WORK_RAM_FILE_OFFSET + address
        gst[start : start + size] = record[source : source + size]
        source += size
    path.write_bytes(gst)


def synthetic_scenario12_command_gst(path: Path) -> None:
    payload = bytearray(blastem.GST_WORK_RAM_FILE_OFFSET + 0x10000)
    ram = blastem.GST_WORK_RAM_FILE_OFFSET

    elwin = ram + legacy.RUNTIME_GROUP_BASE
    payload[elwin] = 0x01
    payload[elwin + 1] = 0x01
    payload[elwin + legacy.RUNTIME_HP_OFFSET] = 10
    payload[elwin + legacy.RUNTIME_X_OFFSET] = 15
    payload[elwin + legacy.RUNTIME_Y_OFFSET] = 23

    commanders = (
        (4, 0x0B, 7, 5, 3, 0, 20, 27),
        (5, 0x0C, 9, 9, 47, legacy.RUNESTONE_ITEM_ID, 23, 28),
        (6, 0x11, 10, 5, 2, 0, 15, 29),
    )
    for group, class_id, name_id, level, exp, item, x, y in commanders:
        start = ram + legacy.RUNTIME_GROUP_BASE + group * legacy.RUNTIME_GROUP_SIZE
        payload[start] = class_id
        payload[start + 1] = name_id
        payload[start + legacy.RUNTIME_SIDE_OFFSET] = 0x01
        payload[start + legacy.RUNTIME_HP_OFFSET] = 10
        payload[start + legacy.RUNTIME_X_OFFSET] = x
        payload[start + legacy.RUNTIME_Y_OFFSET] = y
        payload[start + legacy.EQUIPPED_ITEM_OFFSET] = item
        payload[start + 0x2E] = level
        payload[start + 0x2F] = exp

    enemy = (
        ram
        + legacy.RUNTIME_GROUP_BASE
        + legacy.STAGED_ENEMY_GROUP * legacy.RUNTIME_GROUP_SIZE
    )
    payload[enemy] = legacy.STAGED_ENEMY_CLASS
    payload[enemy + 1] = legacy.STAGED_ENEMY_NAME
    payload[enemy + legacy.RUNTIME_HP_OFFSET] = 10
    payload[enemy + legacy.RUNTIME_X_OFFSET] = 17
    payload[enemy + legacy.RUNTIME_Y_OFFSET] = 10
    payload[enemy + legacy.RUNTIME_SIDE_OFFSET] = 0x04
    payload[enemy + legacy.RUNTIME_AT_MODIFIER_OFFSET] = 31
    payload[enemy + legacy.RUNTIME_DF_MODIFIER_OFFSET] = 30
    coordinates = ((16, 10), (18, 10), (17, 9), (17, 11), (16, 11), (18, 9))
    for member, (x, y) in enumerate(coordinates, start=1):
        start = enemy + member * legacy.RUNTIME_MEMBER_SIZE
        payload[start] = 0x82
        payload[start + 1] = legacy.STAGED_ENEMY_NAME
        payload[start + legacy.RUNTIME_HP_OFFSET] = 10
        payload[start + legacy.RUNTIME_X_OFFSET] = x
        payload[start + legacy.RUNTIME_Y_OFFSET] = y
    sentinel = enemy + legacy.STAGED_ENEMY_SENTINEL * legacy.RUNTIME_MEMBER_SIZE
    payload[sentinel] = 0xFF
    payload[sentinel + 1] = legacy.STAGED_ENEMY_NAME
    payload[sentinel + legacy.RUNTIME_HP_OFFSET] = 10

    payload[ram + legacy.SELECTED_GROUP_INDEX_ADDRESS] = 5
    payload[ram + legacy.SELECTED_MEMBER_INDEX_ADDRESS] = 0
    selected_pointer = (
        legacy.RUNTIME_GROUP_ABSOLUTE_BASE + 5 * legacy.RUNTIME_GROUP_SIZE
    )
    payload[
        ram + legacy.SELECTED_GROUP_POINTER_ADDRESS : ram
        + legacy.SELECTED_GROUP_POINTER_ADDRESS
        + 4
    ] = selected_pointer.to_bytes(4, "big")
    payload[
        ram + legacy.SELECTED_MEMBER_POINTER_ADDRESS : ram
        + legacy.SELECTED_MEMBER_POINTER_ADDRESS
        + 4
    ] = selected_pointer.to_bytes(4, "big")
    payload[ram + legacy.CURSOR_X_ADDRESS] = 23
    payload[ram + legacy.CURSOR_Y_ADDRESS] = 28
    path.write_bytes(payload)


class Legacy5ARunestoneReleaseMatrixTests(unittest.TestCase):
    def test_acceptance_callgraph_has_no_external_gst_restore_path(self) -> None:
        source = Path(legacy.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        removed_mutators = {
            "stage_adjacent_combat_fixture",
            "validate_loaded_combat_fixture",
            "exact_savestate_relaunch_command",
            "restore_external_runtime_gst",
            "ordinary_attack_to_candidate_surface",
        }
        self.assertTrue(removed_mutators.isdisjoint(functions))

        reachable = set()
        pending = ["run_attempt"]
        while pending:
            name = pending.pop()
            if name in reachable:
                continue
            reachable.add(name)
            node = functions[name]
            for call in (
                candidate
                for candidate in ast.walk(node)
                if isinstance(candidate, ast.Call)
            ):
                if isinstance(call.func, ast.Name) and call.func.id in functions:
                    pending.append(call.func.id)

        forbidden_command_literals = {
            "-s",
            "--savestate",
            "--save-state",
            "--load-state",
            "restore-gst",
        }
        for name in sorted(reachable):
            node = functions[name]
            called_attributes = {
                call.func.attr
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
            }
            self.assertTrue(
                {"load_gst", "restore_gst", "load_savestate"}.isdisjoint(
                    called_attributes
                ),
                f"{name} can load an external runtime state",
            )
            for call in (
                candidate
                for candidate in ast.walk(node)
                if isinstance(candidate, ast.Call)
                and isinstance(candidate.func, ast.Attribute)
                and candidate.func.attr == "run_command"
            ):
                command_literals = {
                    value.value
                    for argument in (*call.args, *[kw.value for kw in call.keywords])
                    for value in ast.walk(argument)
                    if isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                }
                self.assertTrue(
                    forbidden_command_literals.isdisjoint(command_literals),
                    f"{name} launches an external runtime state",
                )

        # The only reachable `-s` literal is a fail-closed inspection of the
        # already-running BlastEm argv, never a launch argument.
        identity_source = ast.get_source_segment(
            source, functions["live_process_identity"]
        )
        self.assertIn('or "-s" in argv', identity_source)

    def test_runtime_commanders_ignores_post_combat_scratch_name_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            gst = Path(temporary) / "post-combat.gst"
            synthetic_scenario12_command_gst(gst)
            payload = bytearray(gst.read_bytes())
            scratch = (
                blastem.GST_WORK_RAM_FILE_OFFSET
                + legacy.RUNTIME_GROUP_BASE
                + 36 * legacy.RUNTIME_GROUP_SIZE
            )
            payload[scratch] = 0x00
            payload[scratch + 1] = 10
            payload[scratch + legacy.RUNTIME_SIDE_OFFSET] = 0x00
            payload[scratch + legacy.RUNTIME_HP_OFFSET] = 10
            gst.write_bytes(payload)

            commanders = legacy.runtime_commanders(gst)

        self.assertEqual(sorted(commanders), [7, 9, 10])
        self.assertEqual(commanders[10]["runtime_group"], 6)

    def test_battle_result_overlay_detector_is_exact_panel_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plain = root / "plain.png"
            popup = root / "popup.png"
            banner = root / "banner.png"
            Image.new("RGB", (320, 240), "black").save(plain)
            image = Image.new("RGB", (320, 240), "black")
            draw = ImageDraw.Draw(image)
            draw.rectangle(
                legacy.BATTLE_RESULT_PANEL,
                fill=legacy.STOCK_DARK_BLUE,
            )
            image.save(popup)
            image = Image.new("RGB", (320, 240), "black")
            draw = ImageDraw.Draw(image)
            draw.rectangle(
                legacy.BATTLE_CLASS_READY_BANNER,
                fill=legacy.STOCK_DARK_BLUE,
            )
            image.save(banner)
            self.assertFalse(legacy.battle_result_overlay_visible(plain))
            self.assertTrue(legacy.battle_result_overlay_visible(popup))
            self.assertTrue(legacy.battle_result_overlay_visible(banner))

    def test_battle_result_overlay_rejects_subthreshold_map_blue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "map-blue.png"
            image = Image.new("RGB", (320, 240), "black")
            draw = ImageDraw.Draw(image)
            lower = legacy.BATTLE_RESULT_PANEL
            banner = legacy.BATTLE_CLASS_READY_BANNER
            draw.rectangle(
                (lower[0], lower[1], lower[0] + 76, lower[3] - 1),
                fill=legacy.STOCK_DARK_BLUE,
            )
            draw.rectangle(
                (banner[0], banner[1], banner[0] + 17, banner[3] - 1),
                fill=legacy.STOCK_DARK_BLUE,
            )
            image.save(path)
            self.assertFalse(legacy.battle_result_overlay_visible(path))

    def test_game_save_confirmation_requires_map_and_hides_start_menu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "save-confirmation.png"
            image = Image.new("RGB", (320, 240), "black")
            draw = ImageDraw.Draw(image)
            draw.rectangle((40, 30, 200, 145), fill=legacy.STOCK_DARK_BLUE)
            image.save(path)
            with (
                patch.object(
                    legacy.blastem,
                    "battle_map_surface_visible",
                    return_value=True,
                ),
                patch.object(
                    legacy.movement.first_turn,
                    "start_menu_visible",
                    return_value=False,
                ),
            ):
                self.assertTrue(legacy.game_save_confirmation_visible(path))
            with patch.object(
                legacy.blastem,
                "battle_map_surface_visible",
                return_value=False,
            ):
                self.assertFalse(legacy.game_save_confirmation_visible(path))
            with (
                patch.object(
                    legacy.blastem,
                    "battle_map_surface_visible",
                    return_value=True,
                ),
                patch.object(
                    legacy.movement.first_turn,
                    "start_menu_visible",
                    return_value=True,
                ),
            ):
                self.assertFalse(legacy.game_save_confirmation_visible(path))

    def test_commander_status_panel_uses_exact_stock_panel_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plain = root / "plain.png"
            status = root / "status.png"
            Image.new("RGB", (320, 240), "black").save(plain)
            image = Image.new("RGB", (320, 240), "black")
            ImageDraw.Draw(image).rectangle(
                legacy.COMMANDER_STATUS_PANEL,
                fill=legacy.STOCK_DARK_BLUE,
            )
            image.save(status)
            with patch.object(
                legacy.blastem,
                "battle_map_surface_visible",
                return_value=True,
            ):
                self.assertFalse(legacy.commander_status_panel_visible(plain))
                self.assertTrue(legacy.commander_status_panel_visible(status))

    def test_game_save_confirmation_cursor_distinguishes_yes_and_no(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = []
            for selected in (0, 1):
                path = root / f"selected-{selected}.png"
                image = Image.new("RGB", (320, 240), legacy.STOCK_DARK_BLUE)
                ImageDraw.Draw(image).rectangle(
                    legacy.SAVE_CONFIRMATION_CURSOR_BOXES[selected],
                    fill="white",
                )
                image.save(path)
                with patch.object(
                    legacy,
                    "game_save_confirmation_visible",
                    return_value=True,
                ):
                    rows.append(
                        legacy.game_save_confirmation_cursor_row(path)
                    )
            self.assertEqual(rows, [0, 1])

    def test_bare_battle_map_rejects_every_known_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "map.png"
            Image.new("RGB", (320, 240), "black").save(path)
            with (
                patch.object(
                    legacy.blastem,
                    "battle_map_surface_visible",
                    return_value=True,
                ),
                patch.object(
                    legacy.blastem,
                    "battle_command_menu_visible",
                    return_value=False,
                ),
                patch.object(
                    legacy,
                    "commander_status_panel_visible",
                    return_value=False,
                ),
                patch.object(
                    legacy,
                    "battle_result_overlay_visible",
                    return_value=False,
                ),
                patch.object(
                    legacy.movement.first_turn,
                    "start_menu_visible",
                    return_value=False,
                ),
            ):
                self.assertTrue(legacy.bare_battle_map_visible(path))
                with patch.object(
                    legacy,
                    "commander_status_panel_visible",
                    return_value=True,
                ):
                    self.assertFalse(legacy.bare_battle_map_visible(path))

    def test_applied_state_stability_wait_does_not_select_commander(self) -> None:
        class Recorder:
            def __init__(self, root: Path) -> None:
                self.output = root
                self.sent = []

            def capture(self, relative):
                path = self.output / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (320, 240), "black").save(path)
                return path

            def save_gst(self, relative):
                path = self.output / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"gst")
                return path

            def send(self, keys, *, delay):
                self.sent.append((list(keys), delay))

        target = {
            "class_id": 0x2C,
            "level": 1,
            "experience": 1,
            "equipped_item": 0,
        }
        empty = [
            (0xFF, 0xFF)
        ] * blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT
        with tempfile.TemporaryDirectory() as temporary:
            recorder = Recorder(Path(temporary))
            with (
                patch.object(
                    legacy,
                    "runtime_commanders",
                    return_value={9: target},
                ),
                patch.object(
                    legacy,
                    "inventory_records_from_gst",
                    return_value=empty,
                ),
                patch.object(legacy, "image_report", side_effect=lambda path: {"path": str(path)}),
                patch.object(legacy, "state_report", side_effect=lambda path: {"path": str(path)}),
                patch.object(legacy.time, "sleep"),
            ):
                report = legacy.settle_applied_state(
                    recorder,
                    character="lester",
                    expected_experience=1,
                    max_confirmations=3,
                )
        self.assertEqual(report["status"], "pass")
        self.assertIn("stable_after_passive_wait", report)
        self.assertEqual(recorder.sent, [])

    def test_candidate_advance_stops_sending_c_when_tactical_map_returns(self) -> None:
        class Recorder:
            def __init__(self, root: Path) -> None:
                self.output = root
                self.sent = []

            def capture(self, relative):
                path = self.output / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"frame")
                return path

            def send(self, keys, *, delay):
                self.sent.append((list(keys), delay))

            def save_gst(self, relative):
                path = self.output / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"gst")
                return path

        with tempfile.TemporaryDirectory() as temporary:
            recorder = Recorder(Path(temporary))

            def map_visible(path: Path) -> bool:
                return "advance_001" in path.name or "post_combat_settle" in path.name

            with (
                patch.object(
                    legacy.application,
                    "class_change_candidate_surface_visible",
                    return_value=False,
                ),
                patch.object(legacy.blastem, "game_over_visible", return_value=False),
                patch.object(legacy.blastem, "title_screen_visible", return_value=False),
                patch.object(
                    legacy.blastem,
                    "battle_map_surface_visible",
                    side_effect=map_visible,
                ),
                patch.object(legacy, "battle_result_overlay_visible", return_value=False),
                patch.object(
                    legacy,
                    "runtime_commanders",
                    return_value={9: {"level": 9}},
                ),
                patch.object(
                    legacy,
                    "runtime_member",
                    return_value={"hp": 1, "defeated_flag": 0},
                ),
                patch.object(legacy.time, "sleep"),
            ):
                with self.assertRaisesRegex(
                    legacy.CombatRetryRequired,
                    "retry with fresh RNG",
                ):
                    legacy.advance_to_candidate_surface(
                        recorder,
                        max_advances=20,
                        character="lester",
                        enemy_group=14,
                        enemy_member=2,
                    )
        # One C advances the non-map battle frame.  No C is sent after the map
        # appears, so the enemy under the cursor cannot be selected repeatedly.
        self.assertEqual(recorder.sent, [(["c"], 0.8)])

    def test_candidate_advance_waits_for_delayed_levelup_result(self) -> None:
        class Recorder:
            def __init__(self, root: Path) -> None:
                self.output = root
                self.sent = []

            def capture(self, relative):
                path = self.output / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"frame")
                return path

            def send(self, keys, *, delay):
                self.sent.append((list(keys), delay))

            def save_gst(self, relative):
                path = self.output / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"gst")
                return path

        with tempfile.TemporaryDirectory() as temporary:
            recorder = Recorder(Path(temporary))

            def candidate_visible(path: Path) -> bool:
                return path.name == "advance_001.png"

            def result_visible(path: Path) -> bool:
                return path.name == "post_combat_settle_000_00.png"

            with (
                patch.object(
                    legacy.application,
                    "class_change_candidate_surface_visible",
                    side_effect=candidate_visible,
                ),
                patch.object(legacy.blastem, "game_over_visible", return_value=False),
                patch.object(legacy.blastem, "title_screen_visible", return_value=False),
                patch.object(
                    legacy.blastem,
                    "battle_map_surface_visible",
                    return_value=True,
                ),
                patch.object(
                    legacy,
                    "battle_result_overlay_visible",
                    side_effect=result_visible,
                ),
                patch.object(legacy.time, "sleep"),
            ):
                candidate = legacy.advance_to_candidate_surface(
                    recorder,
                    max_advances=20,
                    character="lester",
                    enemy_group=14,
                    enemy_member=2,
                )
        self.assertEqual(candidate.name, "advance_001.png")
        self.assertEqual(recorder.sent, [(["c"], 0.8)])

    def test_live_candidate_contract_requires_consumed_runestone(self) -> None:
        source = Path(legacy.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "live_move_and_attack_to_candidate"
        )
        function_source = ast.get_source_segment(source, function)
        self.assertIn('candidate_target["equipped_item"] != 0', function_source)
        self.assertIn(
            "candidate_inventory_records != expected_empty_inventory",
            function_source,
        )
        self.assertNotIn(
            'candidate_target["equipped_item"] != RUNESTONE_ITEM_ID',
            function_source,
        )

    def test_cases_are_separate_representative_tier3_rows(self) -> None:
        self.assertEqual(list(legacy.CASES), ["keith", "lester", "jessica"])
        self.assertEqual(
            [row["current_class"] for row in legacy.CASES.values()],
            [0x0B, 0x0C, 0x11],
        )
        for character, row in legacy.CASES.items():
            with self.subTest(character=character):
                self.assertEqual(row["tier"], 3)
                self.assertEqual(len(row["candidate_classes"]), 3)
                self.assertEqual(len(row["candidate_labels"]), 3)
                self.assertEqual(len(row["label_fingerprint"]), 64)

    def test_release_roms_are_exact_hash_locked_inputs(self) -> None:
        for profile, path in legacy.RELEASE_ROM_PATHS.items():
            with self.subTest(profile=profile):
                report = legacy.validate_release_rom(
                    path,
                    legacy.RELEASE_ROM_SHA256[profile],
                )
                self.assertEqual(
                    report["sha256"],
                    legacy.RELEASE_ROM_SHA256[profile],
                )
                self.assertEqual(report["bytes"], 0x400000)

    def test_fixture_uses_real_three_marker_offsets_and_valid_slot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            seed = root / "scenario12.gst"
            fixture = root / "old-save.sram"
            synthetic_scenario12_gst(seed)
            report = legacy.build_old_save_fixture(
                seed,
                legacy.RELEASE_ROM_PATHS["pure"],
                fixture,
                character="lester",
            )
            payload = fixture.read_bytes()

            self.assertEqual(report["status"], "pass")
            self.assertEqual(
                report["policy"], "external_checksum_valid_old_save_no_rom_patch"
            )
            self.assertEqual(len(payload), blastem.BLASTEM_SRAM_SIZE)
            self.assertEqual(
                blastem.manual_slot_scenario_number(fixture),
                legacy.SCENARIO_NUMBER,
            )
            self.assertEqual(
                report["commander_after"],
                {
                    "commander_id": 9,
                    "class_id": 0x0C,
                    "level": 9,
                    "experience": 47,
                },
            )
            self.assertEqual(report["inventory"]["runestone_count"], 1)
            self.assertEqual(
                report["bounded_live_combat_stats"]["after"],
                {"commander_id": 9, "at": 80, "df": 80},
            )
            self.assertEqual(
                report["scenario_objective_guard"]["after"],
                {"commander_id": 1, "at": 0, "df": 99},
            )
            self.assertEqual(
                report["inventory"]["runestones"][0]["owner"],
                blastem.MANUAL_SLOT_ITEM_UNEQUIPPED_OWNER,
            )
            base = blastem.MANUAL_SLOT_BASES[0]
            self.assertEqual(
                [
                    payload[
                        base
                        + blastem.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
                        + index * blastem.MANUAL_SLOT_COMMANDER_RECORD_SIZE
                        + legacy.EQUIPPED_ITEM_OFFSET
                    ]
                    for index in range(blastem.MANUAL_SLOT_COMMANDER_COUNT)
                ],
                [0] * blastem.MANUAL_SLOT_COMMANDER_COUNT,
            )
            markers = report["legacy_markers"]
            self.assertEqual(markers["status"], "pass")
            self.assertEqual(
                [row["address"] for row in markers["markers"]],
                ["0x00403FE7", "0x00403FE9", "0x00403FEB"],
            )
            self.assertEqual(
                [row["sram_offset"] for row in markers["markers"]],
                ["0x1FF3", "0x1FF4", "0x1FF5"],
            )
            self.assertEqual(
                [row["value"] for row in markers["markers"]],
                [0x5A, 0x5A, 0x5A],
            )

    def test_stock_exp_scan_locks_full_gauge_fallthrough_and_item_gate(self) -> None:
        for profile, rom in legacy.RELEASE_ROM_PATHS.items():
            with self.subTest(profile=profile):
                report = legacy.stock_exp_class_scan_report(rom)
                self.assertEqual(report["status"], "pass")
                self.assertEqual(
                    report["scan_sha256"],
                    legacy.STOCK_EXP_CLASS_SCAN_SHA256,
                )
                self.assertEqual(
                    report["exp_compare_subtract_level_increment_bytes"],
                    legacy.STOCK_LEVEL_UP_GATE_BYTES.hex().upper(),
                )
                self.assertEqual(
                    report["runestone_item_gate_bytes"],
                    legacy.STOCK_RUNESTONE_ITEM_GATE_BYTES.hex().upper(),
                )



    def test_exact_cursor_navigation_reaches_each_scenario12_target(self) -> None:
        source = (15, 23)
        expected = {
            "keith": ["right"] * 5 + ["down"] * 4,
            "lester": ["right"] * 8 + ["down"] * 5,
            "jessica": ["down"] * 6,
        }
        targets = {
            "keith": (20, 27),
            "lester": (23, 28),
            "jessica": (15, 29),
        }
        for character, target in targets.items():
            with self.subTest(character=character):
                self.assertEqual(
                    legacy.exact_cursor_navigation(source, target),
                    expected[character],
                )


    def test_cleared_marker_report_requires_all_three_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "save.sram"
            payload = bytearray(blastem.BLASTEM_SRAM_SIZE)
            path.write_bytes(payload)
            self.assertEqual(
                legacy.marker_report(path, 0)["status"],
                "pass",
            )
            payload[legacy.marker_offset(9)] = 0x5A
            path.write_bytes(payload)
            report = legacy.marker_report(path, 0)
            self.assertEqual(report["status"], "fail")
            self.assertEqual(report["markers"][1]["value"], 0x5A)

    def test_real_equipment_transfer_moves_runestone_into_target_field(self) -> None:
        before = [(legacy.RUNESTONE_ITEM_ID, 0xFF)] + [(0xFF, 0xFF)] * (
            blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT - 1
        )
        after = [(legacy.RUNESTONE_ITEM_ID, 7)] + [(0xFF, 0xFF)] * (
            blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT - 1
        )
        target_before = {"commander_id": 7, "equipped_item": 0}
        target_after = {
            "commander_id": 7,
            "equipped_item": legacy.RUNESTONE_ITEM_ID,
        }
        self.assertEqual(
            legacy.runestone_equipment_transfer_report(
                before,
                after,
                target_before,
                target_after,
            )["status"],
            "pass",
        )

        corruptions = [
            (before, before, target_before, target_after),
            (
                before,
                after,
                target_before,
                {"commander_id": 7, "equipped_item": 0},
            ),
            (
                [(legacy.RUNESTONE_ITEM_ID, 9), *before[1:]],
                after,
                target_before,
                target_after,
            ),
            (
                before,
                [(legacy.RUNESTONE_ITEM_ID, 9), *after[1:]],
                target_before,
                target_after,
            ),
        ]
        for values in corruptions:
            with self.subTest(values=values[2:]):
                self.assertEqual(
                    legacy.runestone_equipment_transfer_report(*values)["status"],
                    "fail",
                )

    def test_late_roster_navigation_uses_second_page(self) -> None:
        commander_count = 7

        def navigation(target_position: int) -> list[str]:
            result = []
            for position in range(1, target_position):
                result.extend(
                    preparation.allied_next_navigation(
                        position,
                        commander_count,
                    )
                )
            return result

        self.assertEqual(navigation(5), ["down"] * 4)
        self.assertEqual(
            navigation(6),
            ["down"] * 4 + ["right", "up"],
        )
        self.assertEqual(
            navigation(7),
            ["down"] * 4 + ["right", "up", "down"],
        )

    def test_lester_and_jessica_regrant_predictions_are_not_lv1_exp0(self) -> None:
        expected = {
            "lester": (0x2C, 7, 0, 0x90),
            "jessica": (0x08, 7, 0, 0x60),
        }
        for character, values in expected.items():
            with self.subTest(character=character):
                prediction = legacy.progression_without_join_regrant(
                    legacy.RELEASE_ROM_PATHS["pure"],
                    character,
                )
                self.assertEqual(
                    (
                        prediction["class_id"],
                        prediction["level"],
                        prediction["experience"],
                        prediction["join_raw_experience"],
                    ),
                    values,
                )
                self.assertNotEqual(
                    (
                        prediction["level"],
                        prediction["experience"],
                    ),
                    (1, 0),
                )

    def test_regrant_prediction_includes_stock_runestone_residual_exp(self) -> None:
        prediction = legacy.progression_without_join_regrant(
            legacy.RELEASE_ROM_PATHS["pure"],
            "lester",
            1,
        )
        self.assertEqual(
            (
                prediction["level"],
                prediction["experience"],
                prediction["initial_experience"],
            ),
            (7, 1, 1),
        )

    def test_application_contract_accepts_stock_residual_exp(self) -> None:
        before = {
            7: {
                "class_id": 0x0B,
                "level": 5,
                "experience": 3,
                "equipped_item": 0,
            },
            9: {
                "class_id": 0x0C,
                "level": 10,
                "experience": 1,
                "equipped_item": 0,
            },
            10: {
                "class_id": 0x11,
                "level": 5,
                "experience": 0,
                "equipped_item": 0,
            },
        }
        after = {commander_id: dict(row) for commander_id, row in before.items()}
        after[9].update(class_id=0x2C, level=1, experience=1)
        empty = [(0xFF, 0xFF)] * blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT
        report = legacy.application_acceptance_report(
            character="lester",
            before_commanders=before,
            after_commanders=after,
            after_inventory=empty,
            expected_experience=1,
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["observed_target"]["experience"], 1)

    def test_non_target_lester_jessica_contract_checks_progress_only(self) -> None:
        before = {
            9: {
                "class_id": 7,
                "level": 5,
                "experience": 16,
                "equipped_item": 0,
                "x": 1,
            },
            10: {
                "class_id": 8,
                "level": 7,
                "experience": 0,
                "equipped_item": 0,
                "x": 2,
            },
        }
        after = {commander_id: dict(row) for commander_id, row in before.items()}
        after[9]["x"] = 3
        report = legacy.unchanged_non_target_lester_jessica(
            before,
            after,
            target_commander_id=7,
        )
        self.assertEqual(report["status"], "pass")
        after[10]["experience"] = 0x60
        self.assertEqual(
            legacy.unchanged_non_target_lester_jessica(
                before,
                after,
                target_commander_id=7,
            )["status"],
            "fail",
        )

    def test_application_acceptance_rejects_regrant_and_unconsumed_item(self) -> None:
        before = {
            7: {
                "class_id": 0x0B,
                "level": 9,
                "experience": 40,
                "equipped_item": 0x1A,
            },
            9: {
                "class_id": 0x0C,
                "level": 5,
                "experience": 16,
                "equipped_item": 0,
            },
            10: {
                "class_id": 0x11,
                "level": 5,
                "experience": 0,
                "equipped_item": 0,
            },
        }
        after = {commander_id: dict(row) for commander_id, row in before.items()}
        after[9].update(
            class_id=legacy.CASES["lester"]["selected_class"],
            level=1,
            experience=0,
            equipped_item=0,
        )
        empty = [(0xFF, 0xFF)] * blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT
        self.assertEqual(
            legacy.application_acceptance_report(
                character="lester",
                before_commanders=before,
                after_commanders=after,
                after_inventory=empty,
            )["status"],
            "pass",
        )

        regranted = {commander_id: dict(row) for commander_id, row in after.items()}
        regranted[9].update(level=7, experience=0)
        self.assertEqual(
            legacy.application_acceptance_report(
                character="lester",
                before_commanders=before,
                after_commanders=regranted,
                after_inventory=empty,
            )["status"],
            "fail",
        )
        substituted = list(empty)
        substituted[0] = (0x10, 0xFF)
        self.assertEqual(
            legacy.application_acceptance_report(
                character="lester",
                before_commanders=before,
                after_commanders=after,
                after_inventory=substituted,
            )["status"],
            "fail",
        )
        damaged_keith = {
            commander_id: dict(row) for commander_id, row in after.items()
        }
        damaged_keith[7]["experience"] += 1
        self.assertEqual(
            legacy.application_acceptance_report(
                character="lester",
                before_commanders=before,
                after_commanders=damaged_keith,
                after_inventory=empty,
            )["status"],
            "fail",
        )
        unconsumed = list(empty)
        unconsumed[0] = (legacy.RUNESTONE_ITEM_ID, 0xFF)
        self.assertEqual(
            legacy.application_acceptance_report(
                character="lester",
                before_commanders=before,
                after_commanders=after,
                after_inventory=unconsumed,
            )["status"],
            "fail",
        )

    def test_class_candidate_cursor_detector_reads_all_three_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            boxes = (
                (31, 103, 51, 127),
                (31, 127, 51, 151),
                (31, 151, 51, 176),
            )
            for expected_row, box in enumerate(boxes, 1):
                path = root / f"candidate-{expected_row}.png"
                image = Image.new("RGB", (320, 240))
                draw = ImageDraw.Draw(image)
                draw.rectangle(
                    (box[0], box[1], box[0] + 10, box[1] + 10),
                    fill="white",
                )
                image.save(path)
                self.assertEqual(
                    legacy.class_candidate_cursor_row(path), expected_row
                )
    def test_plan_has_exact_nine_tasks_and_no_probe_rom(self) -> None:
        seed = preparation.DEFAULT_SEED_GST
        args = SimpleNamespace(
            run_id="unit",
            profiles=list(legacy.PROFILES),
            characters=list(legacy.CASES),
            workers=3,
            display_base=960,
            roms=dict(legacy.RELEASE_ROM_PATHS),
            expected_rom_sha256=dict(legacy.RELEASE_ROM_SHA256),
            seeds={profile: seed for profile in legacy.PROFILES},
            expected_seed_sha256={profile: None for profile in legacy.PROFILES},
        )
        report = legacy.plan_matrix(args)
        self.assertEqual(report["status"], "planned")
        self.assertEqual(report["task_count"], 9)
        self.assertFalse(report["existing_tier_2_to_5_matrix_modified"])
        self.assertTrue(all(row["rom_patch"] is None for row in report["tasks"]))
        self.assertTrue(
            all(row["same_live_process_from_title_load"] for row in report["tasks"])
        )
        self.assertTrue(
            all(row["gst_relaunch_count"] == 0 for row in report["tasks"])
        )
        self.assertTrue(
            all(not row["external_runtime_state_loaded"] for row in report["tasks"])
        )
        self.assertEqual(
            {(row["profile"], row["character"]) for row in report["tasks"]},
            {
                (profile, character)
                for profile in legacy.PROFILES
                for character in legacy.CASES
            },
        )

    def test_release_run_rejects_partial_profiles_and_unlocked_seeds(self) -> None:
        with self.assertRaisesRegex(ValueError, "pure, normal, and hard"):
            legacy.run_matrix(SimpleNamespace(profiles=["pure"]))
        with self.assertRaisesRegex(ValueError, "exact seed SHA-256"):
            legacy.run_matrix(
                SimpleNamespace(
                    profiles=list(legacy.PROFILES),
                    expected_seed_sha256={profile: None for profile in legacy.PROFILES},
                )
            )

    def test_diagnostic_preflight_may_select_one_profile(self) -> None:
        args = legacy.parse_args(
            [
                "plan",
                "--profiles",
                "pure",
                "--characters",
                "lester",
                "--evidence-scope",
                "preflight_diagnostic_only",
                "--seed-pure",
                str(preparation.DEFAULT_SEED_GST),
                "--run-id",
                "unit-pure-preflight",
            ]
        )
        self.assertEqual(args.profiles, ["pure"])
        self.assertEqual(args.characters, ["lester"])

        with self.assertRaises(SystemExit):
            legacy.parse_args(
                [
                    "plan",
                    "--profiles",
                    "pure",
                    "--evidence-scope",
                    "final_acceptance",
                    "--seed-pure",
                    str(preparation.DEFAULT_SEED_GST),
                    "--run-id",
                    "unit-pure-final",
                ]
            )

    def test_launch_uses_ordinary_load_and_external_sram(self) -> None:
        class Recorder:
            def __init__(self, root: Path) -> None:
                self.output = root / "output"
                self.output.mkdir()
                self.runtime_home = root / "runtime/name"
                self.display = ":960"
                self.commands = []
                self.sent = []

            def run_command(self, command):
                self.commands.append(command)

            def send(self, keys, *, delay):
                self.sent.append((keys, delay))

            def capture(self, relative):
                path = self.output / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"capture")
                return path

            def save_gst(self, relative):
                path = self.output / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"gst")
                return path

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = root / "fixture.sram"
            fixture.write_bytes(bytes(blastem.BLASTEM_SRAM_SIZE))
            recorder = Recorder(root)
            with patch.object(
                preparation,
                "verify_runtime_scenario_identity",
                return_value={"status": "pass", "identified_scenario": 12},
            ):
                report = legacy.launch_fixture_to_preparation(
                    recorder,
                    rom=legacy.RELEASE_ROM_PATHS["pure"],
                    fixture=fixture,
                    runtime_name="unit",
                    output=recorder.output,
                    max_confirmations=10,
                )

        first = recorder.commands[0]
        self.assertIn("load-screen", first)
        self.assertIn("--manual-slot-srm", first)
        self.assertNotIn("scenario-select", first)
        self.assertNotIn("--manual-slot-gst", first)
        self.assertEqual(recorder.sent, [(["down"], 0.8), (["c"], 1.6)])
        self.assertEqual(
            report["manual_slot_1_selected"]["path"],
            legacy.relative(recorder.output / "load/manual_slot_1_selected.png"),
        )
        self.assertEqual(
            report["method"], "ordinary_title_load_slot_then_confirm_to_preparation"
        )


if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PIL import Image, ImageDraw

from scripts import build_korean_jp_probe as builder
from tools import analyze_preparation_vram_ownership as gst_layout
from tools import build_mounted_lord_combat_probe_rom as probe
from tools import run_mounted_lord_combat_regression as runtime
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout
from tools.v137_release_identity import RELEASE_ROM_PATHS, RELEASE_ROM_SHA256


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / builder.IN_ROM
NORMAL = RELEASE_ROM_PATHS["normal"]
PURE = RELEASE_ROM_PATHS["pure"]
HARD = RELEASE_ROM_PATHS["hard"]
EXACT_RELEASE_SHA256 = {
    RELEASE_ROM_PATHS[profile]: digest
    for profile, digest in RELEASE_ROM_SHA256.items()
}
GST_TEMPLATE = ROOT / "captures/analysis/19fb_keith_natural_class_change_after.gst"


class MountedLordCombatProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        missing = [path for path in (SOURCE, NORMAL, PURE, HARD) if not path.is_file()]
        if missing:
            raise unittest.SkipTest(f"local verification ROMs are absent: {missing}")
        cls.source = SOURCE.read_bytes()
        cls.normal = NORMAL.read_bytes()

    def patched(self, case_key: str, payload: bytes | None = None):
        before = self.normal if payload is None else payload
        data = bytearray(before)
        _, manifest = probe.patch_probe(data, self.source, probe.CASES[case_key])
        return before, bytes(data), manifest

    def test_all_exact_release_profiles_satisfy_both_production_contracts(self):
        for path in (PURE, NORMAL, HARD):
            payload = path.read_bytes()
            for case in probe.CASES.values():
                with self.subTest(profile=path.name, case=case.key):
                    self.assertEqual(
                        probe.sha256(payload), EXACT_RELEASE_SHA256[path]
                    )
                    report = probe.production_contract(payload, self.source, case)
                    self.assertEqual(report["class_id"], f"0x{case.class_id:02X}")
                    self.assertEqual(
                        report["commander_combat_resource_id"],
                        f"0x{case.expected_commander_resource_id:04X}",
                    )
                    self.assertNotEqual(
                        report["map_sprite_id"],
                        report["wrong_map_sprite_id"],
                    )

    def test_all_exact_release_profiles_derive_byte_locked_diagnostics(self):
        for path in (PURE, NORMAL, HARD):
            payload = path.read_bytes()
            for case in probe.CASES.values():
                diagnostic = bytearray(payload)
                _, manifest = probe.patch_probe(
                    diagnostic,
                    self.source,
                    case,
                )
                with self.subTest(profile=path.name, case=case.key):
                    self.assertEqual(
                        probe.verify_probe(
                            payload,
                            bytes(diagnostic),
                            self.source,
                            case,
                            manifest,
                        ),
                        manifest,
                    )
                    self.assertEqual(
                        manifest["scope"]["changed_byte_count"],
                        65,
                    )

    def test_diagnostic_is_exactly_reproducible_and_every_delta_is_declared(self):
        for case in probe.CASES.values():
            before, after, manifest = self.patched(case.key)
            with self.subTest(case=case.key):
                verified = probe.verify_probe(
                    before,
                    after,
                    self.source,
                    case,
                    manifest,
                )
                changed = probe.changed_offsets(before, after)
                listed = {
                    int(row["offset"], 16) for row in manifest["byte_deltas"]
                }
                self.assertEqual(changed, listed)
                self.assertEqual(verified, manifest)
                self.assertEqual(
                    manifest["input_rom"]["sha256"],
                    probe.sha256(before),
                )
                self.assertEqual(
                    manifest["source_rom"]["sha256"],
                    probe.sha256(self.source),
                )
                self.assertEqual(
                    len(changed),
                    manifest["scope"]["changed_byte_count"],
                )
                self.assertEqual(len(changed), 65)

    def test_diagnostic_never_changes_production_class_sprite_or_combat_data(self):
        protected = []
        protected.append(
            (
                builder.COMMANDER_SPRITE_POINTER_TABLE,
                builder.GENERIC_CLASS_SPRITE_TABLE + 157 * 2,
            )
        )
        protected.append(
            (
                builder.COMMANDER_COMBAT_POINTER_TABLE,
                builder.GENERIC_COMBAT_DESCRIPTOR_TABLE
                + 157 * builder.GENERIC_COMBAT_DESCRIPTOR_SIZE,
            )
        )
        protected.append(
            (
                probe.CLASS_RECORD_TABLE,
                probe.CLASS_RECORD_TABLE + 157 * probe.CLASS_RECORD_SIZE,
            )
        )
        for case in probe.CASES.values():
            before, after, manifest = self.patched(case.key)
            with self.subTest(case=case.key):
                self.assertFalse(
                    manifest["scope"]
                    ["production_class_sprite_combat_text_event_bytes_changed"]
                )
                for start, end in protected:
                    self.assertEqual(after[start:end], before[start:end])

    def test_only_bald_combat_fields_are_changed_inside_scenario_records(self):
        before, after, _ = self.patched("keith")
        layout = scenario_layout(before, 1)
        records_start = layout.records_offset
        records_end = records_start + layout.record_count * FIXED_RECORD_SIZE
        bald = records_start + probe.BALD_RECORD_INDEX * FIXED_RECORD_SIZE
        expected = {
            bald + FIELD_OFFSETS["at"],
            bald + FIELD_OFFSETS["df"],
            bald + FIELD_OFFSETS["x"],
            bald + FIELD_OFFSETS["y"],
            *range(
                bald + FIELD_OFFSETS["mercenaries"],
                bald + FIELD_OFFSETS["mercenaries"] + 6,
            ),
        }
        actual = {
            offset
            for offset in range(records_start, records_end)
            if before[offset] != after[offset]
        }
        self.assertEqual(actual, expected)
        self.assertEqual(
            after[bald + FIELD_OFFSETS["x"] : bald + FIELD_OFFSETS["y"] + 1],
            bytes((probe.PROBE_BALD_X, probe.PROBE_BALD_Y)),
        )
        self.assertEqual(
            after[
                bald + FIELD_OFFSETS["mercenaries"] :
                bald + FIELD_OFFSETS["mercenaries"] + 6
            ],
            b"\xFF" * 6,
        )

    def test_manifest_tampering_is_rejected(self):
        before, after, manifest = self.patched("lester")
        tampered = json.loads(json.dumps(manifest))
        tampered["byte_deltas"][0]["after"] = "0x00"
        with self.assertRaisesRegex(ValueError, "manifest does not match"):
            probe.verify_probe(
                before,
                after,
                self.source,
                probe.CASES["lester"],
                tampered,
            )

    def test_changed_commander_combat_alias_is_rejected_before_derivation(self):
        data = bytearray(self.normal)
        case = probe.CASES["keith"]
        offset, _ = probe.commander_combat_records(data, case.commander_id)[
            case.class_id
        ]
        data[offset + 3] ^= 1
        with self.assertRaisesRegex(ValueError, "combat override differs"):
            probe.production_contract(data, self.source, case)

    def test_occupied_probe_wrapper_is_rejected(self):
        data = bytearray(self.normal)
        data[probe.class_probe.PROBE_WRAPPER] = 0
        with self.assertRaisesRegex(ValueError, "wrapper region is not empty"):
            probe.patch_probe(data, self.source, probe.CASES["keith"])


class MountedLordRuntimeAssertionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NORMAL.is_file() or not GST_TEMPLATE.is_file():
            raise unittest.SkipTest("local ROM/GST runtime templates are absent")
        cls.rom = NORMAL.read_bytes()
        cls.gst_template = GST_TEMPLATE.read_bytes()

    def synthetic_gst(
        self,
        directory: Path,
        case: probe.MountedLordCase,
        *,
        include_map_sprite: bool = False,
    ) -> Path:
        data = bytearray(self.gst_template)
        record = gst_layout.GST_VRAM_OFFSET  # keep source constants explicit below
        del record
        work = runtime.matrix.GST_WORK_RAM_FILE_OFFSET + runtime.RUNTIME_RECORD
        data[work : work + runtime.RUNTIME_RECORD_SIZE] = b"\x00" * runtime.RUNTIME_RECORD_SIZE
        data[work + runtime.RUNTIME_CLASS_OFFSET] = case.class_id
        data[work + runtime.RUNTIME_COMMANDER_OFFSET] = case.commander_id
        data[work + runtime.RUNTIME_HP_OFFSET] = 10
        data[work + runtime.RUNTIME_X_OFFSET] = 11
        data[work + runtime.RUNTIME_Y_OFFSET] = 17
        data[work + runtime.RUNTIME_LEVEL_OFFSET] = 1
        data[work + runtime.RUNTIME_EXPERIENCE_OFFSET] = 0
        data[work + runtime.RUNTIME_AT_OFFSET] = runtime.EXPECTED_RUNTIME_AT
        data[work + runtime.RUNTIME_DF_OFFSET] = runtime.EXPECTED_RUNTIME_DF
        stats = work + runtime.RUNTIME_CLASS_STATS_OFFSET
        data[stats : stats + len(case.expected_runtime_stats)] = (
            case.expected_runtime_stats
        )

        if include_map_sprite:
            registers = data[
                gst_layout.GST_VDP_REG_OFFSET :
                gst_layout.GST_VDP_REG_OFFSET + gst_layout.GST_VDP_REG_COUNT
            ]
            width = {0: 32, 1: 64, 3: 128}[registers[16] & 0x03]
            plane_a = (registers[2] & 0x38) << 10

        if include_map_sprite:
            sprite_id = probe.map_sprite_id(
                self.rom,
                case.commander_id,
                case.class_id,
            )
            expected = probe.map_sprite_frames(self.rom, sprite_id)[0]
            vram = gst_layout.GST_VRAM_OFFSET
            data[vram + 0x8000 : vram + 0x8000 + len(expected)] = expected
            for tile, x, y in (
                (0x400, 10, 10),
                (0x401, 10, 11),
                (0x402, 11, 10),
                (0x403, 11, 11),
            ):
                cell = vram + plane_a + (y * width + x) * 2
                data[cell : cell + 2] = tile.to_bytes(2, "big")

        path = directory / f"{case.key}.gst"
        path.write_bytes(data)
        return path

    def test_runtime_state_asserts_exact_class_level_exp_and_status_stats(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for case in probe.CASES.values():
                report = runtime.runtime_state_report(
                    self.synthetic_gst(directory, case),
                    case,
                )
                with self.subTest(case=case.key):
                    self.assertEqual(report["status"], "pass")
                    self.assertEqual(report["values"]["experience"], 0)
                    self.assertEqual(
                        report["values"]["class_stats"],
                        case.expected_runtime_stats.hex().upper(),
                    )

    def test_locked_input_reader_rejects_a_changed_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.md"
            path.write_bytes(b"exact")
            expected = runtime.sha256_path(path)
            self.assertEqual(
                runtime.locked_file_bytes(path, expected, "test ROM"),
                b"exact",
            )
            path.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "SHA-256 changed"):
                runtime.locked_file_bytes(path, expected, "test ROM")

    def test_idle_preflight_refuses_any_existing_blastem(self):
        with mock.patch.object(
            runtime.blastem_sequence,
            "running_blastem_pids",
            return_value=[123, 456],
        ):
            with self.assertRaisesRegex(RuntimeError, "123, 456"):
                runtime.require_idle_emulator()

    def test_map_sprite_assertion_requires_rom_payload_and_plane_a_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for case in probe.CASES.values():
                gst = self.synthetic_gst(
                    directory,
                    case,
                    include_map_sprite=True,
                )
                report = runtime.map_sprite_runtime_report(self.rom, gst, case)
                with self.subTest(case=case.key):
                    self.assertEqual(report["status"], "pass")
                    self.assertTrue(
                        report["checks"]
                        ["actual_plane_a_unit_uses_verified_payload"]
                    )
                    self.assertNotEqual(
                        report["sprite_id"],
                        report["wrong_sprite_id"],
                    )

    def test_combat_vram_accepts_only_commander_mounted_resource(self):
        for case in probe.CASES.values():
            _, _, payload = runtime.commander_combat_resource(self.rom, case)
            vram = bytearray(0x10000)
            start = runtime.COMBAT_VRAM_DESTINATION
            vram[start : start + len(payload)] = payload
            report = runtime.combat_vram_report(self.rom, bytes(vram), case)
            with self.subTest(case=case.key):
                self.assertEqual(report["status"], "pass")
                self.assertTrue(
                    report["checks"]
                    ["sister_vampire_or_generic_fallback_absent"]
                )

            fallback_id = case.forbidden_generic_resource_id
            _, fallback = runtime.decoded_resource(self.rom, fallback_id)
            wrong_vram = bytearray(0x10000)
            wrong_vram[start : start + len(fallback)] = fallback
            wrong = runtime.combat_vram_report(
                self.rom,
                bytes(wrong_vram),
                case,
            )
            with self.subTest(case=case.key, fallback=True):
                self.assertEqual(wrong["status"], "fail")
                self.assertTrue(
                    any(
                        row["loaded_at_combat_destination"]
                        for row in wrong["forbidden_fallbacks"]
                    )
                )

    def test_status_and_battle_surface_detectors_are_layout_based(self):
        case = probe.CASES["keith"]
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            gst = self.synthetic_gst(directory, case)
            state = runtime.runtime_state_report(gst, case)

            status_image = Image.new("RGB", (320, 240), (49, 174, 0))
            draw = ImageDraw.Draw(status_image)
            for box in (
                runtime.STATUS_COMMAND_PANEL,
                runtime.STATUS_DETAIL_PANEL,
                runtime.STATUS_BOTTOM_BAR,
            ):
                draw.rectangle(box, fill=runtime.DARK_BLUE)
            status_path = directory / "status.png"
            status_image.save(status_path)
            status = runtime.status_surface_report(
                status_path,
                state,
                case,
            )
            self.assertEqual(status["status"], "pass")
            self.assertTrue(status["checks"]["exp_bar_source_is_zero"])

            battle_image = Image.new("RGB", (320, 240), (49, 49, 49))
            draw = ImageDraw.Draw(battle_image)
            draw.rectangle(runtime.BATTLE_UI_SURFACE, fill=runtime.DARK_BLUE)
            battle_path = directory / "battle.png"
            battle_image.save(battle_path)
            battle = runtime.battle_surface_report(battle_path)
            self.assertTrue(battle["battle_surface_visible"])

    def test_attack_animation_requires_changed_live_frames_and_combat_payload(self):
        samples = [
            {
                "battle_surface_visible": True,
                "attacker_crop_sha256": "a",
            },
            {
                "battle_surface_visible": True,
                "attacker_crop_sha256": "b",
            },
        ]
        states = [{"status": "pass"}]
        self.assertEqual(
            runtime.attack_animation_report(samples, states)["status"],
            "pass",
        )
        samples[1]["attacker_crop_sha256"] = "a"
        self.assertEqual(
            runtime.attack_animation_report(samples, states)["status"],
            "fail",
        )


if __name__ == "__main__":
    unittest.main()

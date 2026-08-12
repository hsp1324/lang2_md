from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]

from tools import build_late_hidden_spawn_probe_rom as builder  # noqa: E402
from tools import run_late_hidden_spawn_surface as runner  # noqa: E402
from tools import run_blastem_sequence as sequence  # noqa: E402
from tools import run_preparation_surface_matrix as matrix  # noqa: E402
from tools.scenario_data import FIXED_RECORD_SIZE, scenario_layout  # noqa: E402


PROFILE_ROMS = {
    "pure": ROOT / "roms/builds/Langrisser II (Korean Original v1.3.7).md",
    "normal": ROOT / "roms/builds/Langrisser II (Korean Normal v1.3.7).md",
    "hard": ROOT / "roms/builds/Langrisser II (Korean Hard v1.3.7).md",
}
SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class LateHiddenSpawnBuilderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE_ROM.read_bytes()
        cls.candidates = {
            profile: path.read_bytes() for profile, path in PROFILE_ROMS.items()
        }

    def test_frozen_release_hashes_are_the_runner_inputs(self) -> None:
        for profile, payload in self.candidates.items():
            with self.subTest(profile=profile):
                self.assertEqual(
                    hashlib.sha256(payload).hexdigest(),
                    runner.EXPECTED_RELEASE_SHA256[profile],
                )

    def test_stock_s22_spatial_trigger_and_reveal_command_are_source_locked(self) -> None:
        expected_spans = (
            (builder.SPATIAL_TRIGGER, builder.SPATIAL_TRIGGER_BYTES),
            (builder.SPATIAL_HANDLER_ENTRY, builder.SPATIAL_HANDLER_ENTRY_BYTES),
            (
                builder.SPATIAL_PHASE_HANDLER_ENTRY,
                builder.SPATIAL_PHASE_HANDLER_PREFIX_BYTES,
            ),
            (builder.REVEAL_TRIGGER, builder.REVEAL_TRIGGER_BYTES),
            (
                builder.REVEAL_DISPATCH_ENTRY,
                builder.REVEAL_DISPATCH_ENTRY_BYTES,
            ),
            (builder.REVEAL_HANDLER_ENTRY, builder.REVEAL_HANDLER_PREFIX_BYTES),
            (builder.REVEAL_COMMAND, builder.REVEAL_COMMAND_BYTES),
        )
        for offset, expected in expected_spans:
            with self.subTest(offset=f"0x{offset:06X}"):
                self.assertEqual(self.source[offset : offset + len(expected)], expected)
                for profile, payload in self.candidates.items():
                    self.assertEqual(
                        payload[offset : offset + len(expected)],
                        expected,
                        profile,
                    )

    def test_stock_s25_opening_reveal_is_source_locked(self) -> None:
        self.assertEqual(
            self.source[
                builder.SCENARIO25_OPENING_EVENT_POINTER :
                builder.SCENARIO25_OPENING_EVENT_POINTER + 4
            ],
            builder.SCENARIO25_OPENING_EVENT_POINTER_BYTES,
        )
        self.assertEqual(
            self.source[
                builder.SCENARIO25_REVEAL_CONTEXT :
                builder.SCENARIO25_REVEAL_CONTEXT
                + len(builder.SCENARIO25_REVEAL_CONTEXT_BYTES)
            ],
            builder.SCENARIO25_REVEAL_CONTEXT_BYTES,
        )
        self.assertEqual(
            self.source[
                builder.SCENARIO25_REVEAL_COMMAND :
                builder.SCENARIO25_REVEAL_COMMAND + 4
            ],
            bytes.fromhex("0D 31 10 0B"),
        )
        for profile, payload in self.candidates.items():
            with self.subTest(profile=profile):
                self.assertEqual(
                    payload[
                        builder.SCENARIO25_REVEAL_CONTEXT :
                        builder.SCENARIO25_REVEAL_CONTEXT
                        + len(builder.SCENARIO25_REVEAL_CONTEXT_BYTES)
                    ],
                    builder.SCENARIO25_REVEAL_CONTEXT_BYTES,
                )

    def test_probe_changes_only_elwin_deployment_and_checksum(self) -> None:
        allowed = set(
            range(
                builder.FIRST_PLAYER_DEPLOYMENT,
                builder.FIRST_PLAYER_DEPLOYMENT + 4,
            )
        ) | {0x18E, 0x18F}
        for profile, candidate in self.candidates.items():
            with self.subTest(profile=profile):
                output, manifest = builder.build_probe(candidate, self.source)
                changed = {
                    index
                    for index, (before, after) in enumerate(zip(candidate, output))
                    if before != after
                }
                self.assertTrue(changed)
                self.assertLessEqual(changed, allowed)
                self.assertEqual(
                    output[
                        builder.FIRST_PLAYER_DEPLOYMENT :
                        builder.FIRST_PLAYER_DEPLOYMENT + 4
                    ],
                    builder.PROBE_ELWIN_DEPLOYMENT,
                )
                self.assertTrue(manifest["target_fixed_record_unchanged"])
                self.assertTrue(manifest["stock_trigger_and_handlers_unchanged"])

    def test_probe_preserves_entire_hidden_bernhardt_record(self) -> None:
        for profile, candidate in self.candidates.items():
            with self.subTest(profile=profile):
                output, _ = builder.build_probe(candidate, self.source)
                layout = scenario_layout(candidate, 22)
                start = (
                    layout.records_offset
                    + builder.BERNHARDT_RECORD_INDEX * FIXED_RECORD_SIZE
                )
                end = start + FIXED_RECORD_SIZE
                self.assertEqual(output[start:end], candidate[start:end])

    def test_tampered_trigger_or_reveal_command_is_rejected(self) -> None:
        for offset, message in (
            (builder.SPATIAL_TRIGGER + 1, "F1 spatial trigger"),
            (builder.REVEAL_TRIGGER + 1, "reveal trigger"),
            (builder.REVEAL_COMMAND + 1, "reveal command"),
            (builder.SCENARIO25_REVEAL_COMMAND + 1, "reveal context"),
        ):
            with self.subTest(offset=f"0x{offset:06X}"):
                changed = bytearray(self.candidates["normal"])
                changed[offset] ^= 1
                with self.assertRaisesRegex(ValueError, message):
                    builder.build_probe(bytes(changed), self.source)


class LateHiddenSpawnRuntimeContractTest(unittest.TestCase):
    def fake_gst(
        self,
        *,
        scenario: int,
        group_index: int,
        coordinate: tuple[int, int],
        hp: int,
        flags: int = 0,
    ) -> Path:
        target = runner.TARGETS[scenario]
        payload = bytearray(sequence.GST_WORK_RAM_FILE_OFFSET + 0x10000)
        start = (
            sequence.GST_WORK_RAM_FILE_OFFSET
            + matrix.RUNTIME_GROUP_BASE
            + group_index * matrix.RUNTIME_GROUP_SIZE
        )
        payload[start] = int(target["class_id"])
        payload[start + 1] = int(target["name_id"])
        payload[start + 2] = flags
        payload[start + 3] = hp
        payload[start + 6] = coordinate[0]
        payload[start + 7] = coordinate[1]
        payload[start + matrix.RUNTIME_SIDE_OFFSET] = int(target["side_id"])
        payload[start + matrix.RUNTIME_LEVEL_OFFSET] = 10
        temporary = tempfile.NamedTemporaryFile(suffix=".gst", delete=False)
        temporary.write(payload)
        temporary.close()
        self.addCleanup(Path(temporary.name).unlink, missing_ok=True)
        return Path(temporary.name)

    def test_runtime_contract_distinguishes_hidden_and_visible_alive(self) -> None:
        for scenario in (22, 25):
            with self.subTest(scenario=scenario):
                hidden_path = self.fake_gst(
                    scenario=scenario,
                    group_index=20,
                    coordinate=(0xFF, 0xFF),
                    hp=0,
                )
                visible_path = self.fake_gst(
                    scenario=scenario,
                    group_index=20,
                    coordinate=tuple(runner.TARGETS[scenario]["reveal_coordinate"]),
                    hp=10,
                )
                hidden = runner.runtime_target(hidden_path, group_index=20)
                visible = runner.runtime_target(visible_path, group_index=20)
                self.assertTrue(runner.target_is_hidden(hidden))
                self.assertFalse(runner.target_is_visible_alive(hidden, scenario))
                self.assertTrue(runner.target_is_visible_alive(visible, scenario))
                self.assertTrue(runner.target_has_live_identity(visible, scenario))

                moved_path = self.fake_gst(
                    scenario=scenario,
                    group_index=20,
                    coordinate=(15, 4),
                    hp=10,
                )
                moved = runner.runtime_target(moved_path, group_index=20)
                self.assertTrue(runner.target_has_live_identity(moved, scenario))
                self.assertFalse(runner.target_is_visible_alive(moved, scenario))

    def test_runtime_spawn_resolver_finds_stock_clone_before_hidden_template(self) -> None:
        template_path = self.fake_gst(
            scenario=25,
            group_index=20,
            coordinate=(0xFF, 0xFF),
            hp=0,
        )
        clone_path = self.fake_gst(
            scenario=25,
            group_index=14,
            coordinate=tuple(runner.TARGETS[25]["reveal_coordinate"]),
            hp=10,
        )
        combined = bytearray(template_path.read_bytes())
        clone = clone_path.read_bytes()
        start = (
            sequence.GST_WORK_RAM_FILE_OFFSET
            + matrix.RUNTIME_GROUP_BASE
            + 14 * matrix.RUNTIME_GROUP_SIZE
        )
        end = start + matrix.RUNTIME_GROUP_SIZE
        combined[start:end] = clone[start:end]
        temporary = tempfile.NamedTemporaryFile(suffix=".gst", delete=False)
        temporary.write(combined)
        temporary.close()
        combined_path = Path(temporary.name)
        self.addCleanup(combined_path.unlink, missing_ok=True)

        resolved = runner.runtime_spawn_target(
            combined_path,
            scenario=25,
            template_group_index=20,
        )
        self.assertEqual(resolved["group_index"], 14)
        self.assertTrue(runner.target_is_visible_alive(resolved, 25))

    def test_all_profile_fixed_targets_keep_structural_identity(self) -> None:
        for profile, path in PROFILE_ROMS.items():
            payload = path.read_bytes()
            for scenario in (22, 25):
                with self.subTest(profile=profile, scenario=scenario):
                    target = runner.validate_fixed_target(payload, scenario)
                    self.assertTrue(target["hidden"])
                    self.assertEqual((target["x"], target["y"]), (0xFF, 0xFF))


if __name__ == "__main__":
    unittest.main()

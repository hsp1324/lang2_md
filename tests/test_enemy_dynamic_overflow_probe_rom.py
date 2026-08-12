from pathlib import Path
import unittest

from tools import build_enemy_dynamic_overflow_probe_rom as probe


ROOT = Path(__file__).resolve().parents[1]
V137_ROMS = {
    "pure": ROOT / "roms/builds/Langrisser II (Korean Original v1.3.7).md",
    "normal": ROOT / "roms/builds/Langrisser II (Korean Normal v1.3.7).md",
    "hard": (
        ROOT
        / "roms/builds/Langrisser II (Korean Hard v1.3.7).md"
    ),
}


class EnemyDynamicOverflowProbeRomTests(unittest.TestCase):
    def make_roms(self):
        size = max(
            probe.VISIBLE_MERCENARY_OFFSET + 1,
            max(probe.SCENARIO_13_LEGACY_RECORDS)
            + probe.MERCENARY_OFFSET
            + probe.MERCENARY_COUNT,
        )
        base = bytearray(size)
        legacy = bytearray(size)
        base[probe.VISIBLE_MERCENARY_OFFSET] = (
            probe.VISIBLE_MERCENARY_EXPECTED_CLASS
        )
        for index, record in enumerate(probe.SCENARIO_13_LEGACY_RECORDS):
            start = record + probe.MERCENARY_OFFSET
            legacy[start : start + probe.MERCENARY_COUNT] = bytes(
                range(0x70 + index, 0x70 + index + probe.MERCENARY_COUNT)
            )
        return base, bytes(legacy)

    def test_copies_legacy_vargas_roster_without_touching_visible_group(self):
        base, legacy = self.make_roms()
        probe.patch_probe(base, legacy)
        self.assertEqual(
            base[probe.VISIBLE_MERCENARY_OFFSET],
            probe.VISIBLE_MERCENARY_EXPECTED_CLASS,
        )
        for record in probe.SCENARIO_13_LEGACY_RECORDS:
            start = record + probe.MERCENARY_OFFSET
            end = start + probe.MERCENARY_COUNT
            self.assertEqual(base[start:end], legacy[start:end])

    def test_optional_visible_darkguard_is_diagnostic_only(self):
        base, legacy = self.make_roms()
        probe.patch_probe(base, legacy, make_darkguard_visible=True)
        self.assertEqual(
            base[probe.VISIBLE_MERCENARY_OFFSET],
            probe.DARK_GUARD_CLASS,
        )

    def test_rejects_unexpected_visible_mercenary_owner(self):
        base, legacy = self.make_roms()
        base[probe.VISIBLE_MERCENARY_OFFSET] = 0x72
        with self.assertRaisesRegex(ValueError, "not Dragonia"):
            probe.patch_probe(base, legacy, make_darkguard_visible=True)

    def test_source_locked_mode_builds_all_exact_v137_profiles(self):
        for profile, path in V137_ROMS.items():
            with self.subTest(profile=profile):
                source = path.read_bytes()
                built, manifest = probe.build_source_locked_v137_probe(source)
                self.assertEqual(manifest["status"], "pass")
                self.assertEqual(manifest["input"]["profile"], profile)
                self.assertEqual(
                    manifest["output"]["sha256"],
                    probe.SOURCE_LOCKED_V137_OUTPUT_SHA256[profile],
                )
                self.assertEqual(
                    manifest["changed_offsets"],
                    [
                        f"0x{offset:06X}"
                        for offset in probe.SOURCE_LOCKED_CHANGED_OFFSETS
                    ],
                )
                self.assertEqual(
                    probe.md_checksum(built),
                    int.from_bytes(built[0x18E:0x190], "big"),
                )
                self.assertEqual(
                    built[probe.VISIBLE_MERCENARY_OFFSET],
                    probe.DARK_GUARD_CLASS,
                )
                for record, literal in probe.SOURCE_LOCKED_ROWS.items():
                    start = record + probe.MERCENARY_OFFSET
                    self.assertEqual(
                        built[start:start + probe.MERCENARY_COUNT],
                        literal,
                    )

    def test_source_locked_manifest_records_literal_provenance(self):
        source = V137_ROMS["pure"].read_bytes()
        _, manifest = probe.build_source_locked_v137_probe(source)
        self.assertEqual(
            manifest["source_lock"]["commit"],
            probe.SOURCE_LOCK_COMMIT,
        )
        self.assertFalse(manifest["source_lock"]["legacy_rom_required"])
        rows = manifest["source_lock"]["literal_rows"]
        self.assertEqual(
            [row["after"] for row in rows],
            [
                "7F 7F 7E 7E 7E 7E",
                "7C 7C 73 73 7A 7A",
            ],
        )
        self.assertEqual(
            manifest["source_lock"]["visible_dark_guard"],
            {
                "offset": "0x1818C2",
                "before": "7D",
                "after": "7C",
            },
        )

    def test_source_locked_mode_rejects_non_release_hash(self):
        source = bytearray(V137_ROMS["pure"].read_bytes())
        source[0x200] ^= 0x01
        with self.assertRaisesRegex(ValueError, "exact current v1.3.7"):
            probe.build_source_locked_v137_probe(bytes(source))


if __name__ == "__main__":
    unittest.main()

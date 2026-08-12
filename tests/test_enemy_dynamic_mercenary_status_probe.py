import copy
import unittest

from tools import run_enemy_dynamic_mercenary_status_probe as probe


def member(
    member_index,
    class_id,
    *,
    hp=10,
    x=5,
    y=5,
):
    return {
        "member_index": member_index,
        "class_id": class_id,
        "commander_id": 0x2A,
        "acted_flag": 0,
        "hp": hp,
        "x": x,
        "y": y,
        "record": "",
    }


def report(
    *,
    owner="dynamic",
    index=2,
    tile="0x0390",
    requested=0x74,
    rendered=0x74,
):
    return {
        "requested_class_id": f"0x{requested:02X}",
        "rendered_class_id": f"0x{rendered:02X}",
        "cache_owner": owner,
        "cache_index": index,
        "base_tile": tile,
        "frames": [
            {"frame": 0, "matches_rom_source": True},
            {"frame": 1, "matches_rom_source": True},
        ],
        "both_frames_match_rom_source": True,
        "one_animation_frame_referenced_by_plane_a": True,
    }


class EnemyDynamicMercenaryStatusProbeTests(unittest.TestCase):
    def target_fixture(self):
        target = {
            **member(1, 0x74, x=8, y=6),
            "group_index": 7,
            "side_id": probe.ENEMY_SIDE_ID,
            "role": "subordinate",
        }
        return target, [target]

    def checks(self, before, hover, *, requested=0x74, hover_cursor=None):
        target, candidates = self.target_fixture()
        if hover_cursor is None:
            hover_cursor = (target["x"], target["y"])
        return probe.cache_contract_checks(
            before,
            hover,
            requested,
            target=target,
            target_after_hover=copy.deepcopy(target),
            target_candidates=candidates,
            hover_cursor=hover_cursor,
            rom_hash_before="rom",
            rom_hash_after="rom",
            seed_hash_before="seed",
            seed_hash_after="seed",
            expected_cache_owner=str(before["cache_owner"]),
            expected_group_index=target["group_index"],
            expected_member_index=target["member_index"],
            expected_rom_sha256="rom",
            expected_seed_sha256="seed",
        )

    def test_default_class_is_common_visible_berserker(self):
        self.assertEqual(probe.DEFAULT_CLASS_ID, 0x74)

    def test_hidden_0x73_cannot_be_selected(self):
        groups = [
            {
                "group_index": 17,
                "side_id": probe.ENEMY_SIDE_ID,
                "members": [
                    member(0, 0x49, x=0xFF, y=0xFF),
                    member(1, 0x73, x=0x00, y=0x00),
                    member(2, 0x73, x=0xFF, y=0xFF),
                ],
            }
        ]
        with self.assertRaisesRegex(RuntimeError, "no live visible"):
            probe.select_visible_enemy_subordinate(groups, 0x73, (16, 3))

    def test_selects_one_deterministic_enemy_subordinate(self):
        groups = [
            {
                "group_index": 2,
                "side_id": 0x01,
                "members": [
                    member(0, 0x74, x=4, y=4),
                    member(1, 0x74, x=5, y=4),
                ],
            },
            {
                "group_index": 8,
                "side_id": probe.ENEMY_SIDE_ID,
                "members": [
                    member(0, 0x74, x=10, y=10),
                    member(1, 0x74, x=8, y=7),
                    member(2, 0x74, x=7, y=7),
                ],
            },
        ]
        selected, candidates = probe.select_visible_enemy_subordinate(
            groups,
            0x74,
            (6, 7),
        )
        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            (selected["group_index"], selected["member_index"]),
            (8, 2),
        )
        self.assertEqual(selected["side_id"], probe.ENEMY_SIDE_ID)
        self.assertEqual(selected["role"], "subordinate")

    def test_owner_or_index_drift_fails_the_contract(self):
        before = report()
        for field, value, check in (
            ("cache_owner", "fixed", "cache_owner_unchanged"),
            ("cache_index", 9, "cache_index_unchanged"),
        ):
            with self.subTest(field=field):
                hover = copy.deepcopy(before)
                hover[field] = value
                checks = self.checks(before, hover)
                self.assertFalse(checks[check])
                self.assertFalse(all(checks.values()))

    def test_offscreen_before_state_only_requires_plane_reference_on_hover(self):
        before = report()
        before["one_animation_frame_referenced_by_plane_a"] = False
        checks = self.checks(before, report())
        self.assertTrue(all(checks.values()), checks)

        hover = report()
        hover["one_animation_frame_referenced_by_plane_a"] = False
        checks = self.checks(report(), hover)
        self.assertFalse(checks["hover_has_required_plane_a_reference"])
        self.assertFalse(all(checks.values()))

    def test_hover_cursor_must_reach_the_exact_selected_target(self):
        checks = self.checks(report(), report(), hover_cursor=(15, 5))
        self.assertFalse(checks["hover_cursor_matches_exact_target"])
        self.assertFalse(all(checks.values()))

    def test_fallback_requested_and_rendered_class_contract(self):
        fallback = report(
            owner="fallback",
            index=3,
            requested=0x72,
            rendered=0x64,
        )
        target, candidates = self.target_fixture()
        target["class_id"] = 0x72
        checks = probe.cache_contract_checks(
            fallback,
            copy.deepcopy(fallback),
            0x72,
            target=target,
            target_after_hover=copy.deepcopy(target),
            target_candidates=candidates,
            hover_cursor=(target["x"], target["y"]),
            rom_hash_before="rom",
            rom_hash_after="rom",
            seed_hash_before="seed",
            seed_hash_after="seed",
            expected_cache_owner="fallback",
            expected_group_index=target["group_index"],
            expected_member_index=target["member_index"],
            expected_rom_sha256="rom",
            expected_seed_sha256="seed",
        )
        self.assertTrue(all(checks.values()), checks)

    def test_observed_owner_cannot_define_the_expected_owner(self):
        target, candidates = self.target_fixture()
        dynamic = report(owner="dynamic")
        checks = probe.cache_contract_checks(
            dynamic,
            copy.deepcopy(dynamic),
            0x74,
            target=target,
            target_after_hover=copy.deepcopy(target),
            target_candidates=candidates,
            hover_cursor=(target["x"], target["y"]),
            rom_hash_before="rom",
            rom_hash_after="rom",
            seed_hash_before="seed",
            seed_hash_after="seed",
            expected_cache_owner="fixed",
            expected_group_index=target["group_index"],
            expected_member_index=target["member_index"],
            expected_rom_sha256="rom",
            expected_seed_sha256="seed",
        )
        self.assertFalse(checks["before_cache_owner_matches_source_lock"])
        self.assertFalse(checks["hover_cache_owner_matches_source_lock"])
        self.assertFalse(all(checks.values()))


if __name__ == "__main__":
    unittest.main()

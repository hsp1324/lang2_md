from pathlib import Path
import unittest

from tools import runtime_verification_inventory as inventory


ROOT = Path(__file__).resolve().parents[1]


class RuntimeVerificationInventoryTests(unittest.TestCase):
    def test_magic_application_evidence_separates_stock_and_forced_paths(self):
        data = inventory.load_inventory()
        evidence = {
            row["surface"]: row for row in data["global_evidence"]
        }["magic_targeting_results"]
        self.assertEqual(evidence["state"], "verified_probe")
        self.assertEqual(evidence["checksum"], "49A2/797C")
        self.assertEqual(evidence["based_on"], "AD01")
        self.assertIn("preserves stock magic", evidence["note"])
        self.assertIn("not production ownership evidence", evidence["note"])
        self.assertIn(
            "captures/run/49a2_magic_00_result_stable.png",
            evidence["captures"],
        )
        self.assertIn(
            "captures/run/797c_magic_16_result_stable.png",
            evidence["captures"],
        )

    def test_summon_application_evidence_is_diagnostic(self):
        data = inventory.load_inventory()
        evidence = {
            row["surface"]: row for row in data["global_evidence"]
        }["summon_targeting_results"]
        self.assertEqual(evidence["checksum"], "C41E")
        self.assertEqual(evidence["based_on"], "AD01")
        self.assertIn("member slot 7", evidence["note"])
        self.assertIn("not natural summon ownership evidence", evidence["note"])
        self.assertIn(
            "captures/run/c41e_summon_00_summoned_status.png",
            evidence["captures"],
        )

    def test_ending_visit_dialogue_evidence_is_renderer_diagnostic(self):
        data = inventory.load_inventory()
        evidence = {
            row["surface"]: row for row in data["global_evidence"]
        }["ending_visit_dialogue"]
        self.assertEqual(evidence["checksum"], "F852")
        self.assertEqual(evidence["based_on"], "E38B")
        self.assertIn("83-page", evidence["note"])
        self.assertIn("not all natural visit-condition selections", evidence["note"])
        self.assertIn(
            "captures/run/f852_ending_dialogue_watch/475.png",
            evidence["captures"],
        )

    def test_inventory_has_all_scenarios_and_surfaces(self):
        data = inventory.load_inventory()
        self.assertEqual(
            [entry["scenario"] for entry in data["scenarios"]],
            list(range(1, 32)),
        )
        for entry in data["scenarios"]:
            for surface in data["surfaces"]:
                self.assertIn(entry.get(surface, "pending"), data["states"])

    def test_current_evidence_matches_production_checksum(self):
        data = inventory.load_inventory()
        self.assertEqual(data["production_checksum"], "DE78")
        title = {
            row["surface"]: row for row in data["global_evidence"]
        }["title_logo_and_main_menu"]
        self.assertEqual(title["state"], "verified_current")
        self.assertEqual(title["checksum"], "6C85")
        self.assertIn(
            "captures/run/6c85_title_uppercase_live_3.png", title["captures"]
        )
        scenario1 = data["scenarios"][0]
        scenario2 = data["scenarios"][1]
        scenario3 = data["scenarios"][2]
        scenario4 = data["scenarios"][3]
        scenario5 = data["scenarios"][4]
        scenario6 = data["scenarios"][5]
        scenario7 = data["scenarios"][6]
        scenario8 = data["scenarios"][7]
        scenario9 = data["scenarios"][8]
        scenario10 = data["scenarios"][9]
        scenario11 = data["scenarios"][10]
        scenario12 = data["scenarios"][11]
        scenario13 = data["scenarios"][12]
        scenario14 = data["scenarios"][13]
        scenario15 = data["scenarios"][14]
        scenario16 = data["scenarios"][15]
        scenario17 = data["scenarios"][16]
        scenario18 = data["scenarios"][17]
        scenario19 = data["scenarios"][18]
        scenario20 = data["scenarios"][19]
        scenario21 = data["scenarios"][20]
        scenario22 = data["scenarios"][21]
        scenario23 = data["scenarios"][22]
        scenario24 = data["scenarios"][23]
        scenario25 = data["scenarios"][24]
        scenario26 = data["scenarios"][25]
        scenario27 = data["scenarios"][26]
        scenario28 = data["scenarios"][27]
        scenario29 = data["scenarios"][28]
        scenario30 = data["scenarios"][29]
        scenario31 = data["scenarios"][30]
        self.assertEqual(scenario1["description"], "verified_current")
        self.assertIn("captures/run/c7ab_s01_body_name4.png", scenario1["captures"])
        self.assertEqual(scenario1["preparation"], "verified_current")
        for capture in (
            "captures/run/212a_s01_prep_current.png",
            "captures/run/212a_s01_hire_current2.png",
            "captures/run/212a_s01_equipment_current.png",
            "captures/run/212a_s01_equipment_exit_b.png",
            "captures/run/212a_s01_equipment_exit_final.png",
            "captures/run/212a_s01_shop_buy_list.png",
            "captures/run/212a_s01_shop_buy_popup.png",
            "captures/run/212a_s01_shop_sell_list.png",
            "captures/run/212a_s01_shop_sell_popup.png",
            "captures/run/212a_s01_arrangement_roster.png",
            "captures/run/212a_s01_hein_prep_panel.png",
            "captures/run/212a_s01_hein_hire_list.png",
        ):
            self.assertIn(capture, scenario1["captures"])
        current_description_progress = set()
        for scenario in data["scenarios"][1:]:
            expected = "verified_current" if scenario["scenario"] in {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31} else (
                "progressed_current"
                if scenario["scenario"] in current_description_progress
                else "historical"
            )
            self.assertEqual(scenario["description"], expected)
        self.assertEqual(scenario27["description"], "verified_current")
        for capture in (
            "captures/run/212a_s27_description_current_01.png",
            "captures/run/212a_s27_description_current_05.png",
            "captures/run/212a_s27_description_current_09.png",
            "captures/run/212a_s27_description_current_14.png",
            "captures/run/212a_s27_description_current_19.png",
            "captures/run/212a_s27_description_current_20.png",
        ):
            self.assertIn(capture, scenario27["captures"])
        self.assertEqual(scenario1["turn_events"], "verified_current")
        self.assertEqual(scenario1["completion"], "verified_probe")
        self.assertIn(
            "captures/run/8aea_s01_clear_post_41.png", scenario1["captures"]
        )
        self.assertIn(
            "captures/run/479f_s01_clear_result_current.png",
            scenario1["captures"],
        )
        self.assertIn(
            "captures/run/479f_s01_clear_save_current.png",
            scenario1["captures"],
        )
        self.assertIn("captures/run/c7ab_s02_body_final2.png", scenario2["captures"])
        self.assertEqual(scenario2["description"], "verified_current")
        self.assertEqual(scenario2["opening_events"], "verified_current")
        self.assertEqual(scenario2["completion"], "verified_probe")
        for capture in (
            "captures/run/489b_s02_description_current_01.png",
            "captures/run/489b_s02_description_current_08.png",
            "captures/run/489b_s02_description_current_14.png",
            "captures/run/489b_s02_description_current_20.png",
            "captures/run/489b_s02_description_current_22.png",
            "captures/run/489b_s02_opening_01.png",
            "captures/run/489b_s02_opening_32.png",
            "captures/run/489b_s02_opening_52.png",
            "captures/run/489b_s02_opening_61.png",
            "captures/run/489b_s02_opening2_18.png",
            "captures/run/212a_s02_arrange_scenario_banner.png",
            "captures/run/212a_s02_loren_status.png",
            "captures/run/212a_s02_loren_popup.png",
            "captures/run/389a_s02_prep_verify_09.png",
            "captures/run/389a_s02_command_final.png",
            "captures/run/389a_s02_escape_12.png",
            "captures/run/389a_s02_escape_17.png",
            "captures/run/389a_s02_escape_18.png",
            "captures/run/389a_s02_escape_19.png",
            "captures/run/389a_s02_next_scenario_selected.png",
        ):
            self.assertIn(capture, scenario2["captures"])
        self.assertEqual(scenario3["description"], "verified_current")
        for capture in (
            "captures/run/489b_s03_description_current_01.png",
            "captures/run/489b_s03_description_current_07.png",
            "captures/run/489b_s03_description_current_11.png",
            "captures/run/489b_s03_description_current_14.png",
            "captures/run/489b_s03_description_current_15.png",
        ):
            self.assertIn(capture, scenario3["captures"])
        self.assertEqual(scenario3["turn_events"], "verified_probe")
        self.assertEqual(scenario3["completion"], "verified_probe")
        for capture in (
            "captures/run/b2bd_s03_turn3_entry_01.png",
            "captures/run/b2bd_s03_zorum_quote_hit1.png",
            "captures/run/b2bdv2_s03_vargas_retreat_13.png",
            "captures/run/b2bdv2_s03_clear_after_result.png",
            "captures/run/b2bdv2_s03_clear_save_slot2.png",
            "captures/run/b2bdv2_s03_next_scenario_selected.png",
            "captures/run/b2bdv2_s04_route.png",
            "captures/run/af5e_s03_imperial_capture_line.png",
            "captures/run/af5e_r3_last_enemy_post_3.png",
        ):
            self.assertIn(capture, scenario3["captures"])
        self.assertIn("save-slot AT 99 / DF 96", scenario3["note"])
        self.assertEqual(scenario4["opening_events"], "verified_current")
        self.assertEqual(scenario4["description"], "verified_current")
        for capture in (
            "captures/run/489b_s04_description_current_01.png",
            "captures/run/489b_s04_description_current_07.png",
            "captures/run/489b_s04_description_current_12.png",
            "captures/run/489b_s04_description_current_13.png",
            "captures/run/489b_s04_description_current_14.png",
        ):
            self.assertIn(capture, scenario4["captures"])
        self.assertEqual(scenario4["turn_events"], "verified_probe")
        self.assertEqual(scenario4["completion"], "verified_probe")
        for capture in (
            "captures/run/79dd_s04_selector_entry.png",
            "captures/run/79dd_s04_prep.png",
            "captures/run/79dd_s04_arrange.png",
            "captures/run/79dd_s04_sortie.png",
            "captures/run/79dd_s04_opening_16.png",
            "captures/run/79dd_s04_after_morgan_attack.png",
            "captures/run/79dd_s04_post_01.png",
            "captures/run/79dd_s04_post_08.png",
            "captures/run/79dd_s04_post_16.png",
            "captures/run/79dd_s04_post_34.png",
            "captures/run/79dd_s04_post_37.png",
            "captures/run/79dd_s04_post_39.png",
            "captures/run/79dd_s04_post_40.png",
            "captures/run/79dd_s04_post_41.png",
            "captures/run/79dd_s04_next_scenario.png",
            "captures/run/40ea_s04_sortie.png",
            "captures/run/40ea_s04_turn2_01.png",
            "captures/run/40ea_s04_turn3_01.png",
            "captures/run/40ea_s04_turn3_07.png",
            "captures/run/40ea_s04_turn5_start.png",
            "captures/run/40ea_s04_turn5_events_01.png",
            "captures/run/40ea_s04_turn5_events_05.png",
            "captures/run/40ea_s04_turn5_events_10.png",
            "captures/run/40ea_s04_turn5_events_15.png",
            "captures/run/40ea_s04_turn5_command.png",
        ):
            self.assertIn(capture, scenario4["captures"])
        self.assertIn("moving only Elwin's first deployment", scenario4["note"])
        self.assertIn("progression probe 40EA preserves every deployment", scenario4["note"])
        self.assertIn("turn 5 Morgan mind-control", scenario4["note"])
        self.assertIn("second Shika cry", scenario4["note"])
        self.assertEqual(scenario5["preparation"], "verified_current")
        self.assertEqual(scenario5["description"], "verified_current")
        for capture in (
            "captures/run/489b_s05_description_current_01.png",
            "captures/run/489b_s05_description_current_06.png",
            "captures/run/489b_s05_description_current_10.png",
            "captures/run/489b_s05_description_current_13.png",
            "captures/run/489b_s05_description_current_14.png",
        ):
            self.assertIn(capture, scenario5["captures"])
        self.assertEqual(scenario5["opening_events"], "verified_current")
        self.assertEqual(scenario5["completion"], "verified_probe")
        for capture in (
            "captures/run/398c_s05_selector.png",
            "captures/run/398c_s05_sortie.png",
            "captures/run/398c_s05_command.png",
            "captures/run/398c_s05_north_commit.png",
            "captures/run/398c_s05_escape_11.png",
            "captures/run/398c_s05_escape_12.png",
            "captures/run/398c_s05_escape_14.png",
            "captures/run/398c_s05_escape_16.png",
            "captures/run/398c_s05_next_scenario.png",
        ):
            self.assertIn(capture, scenario5["captures"])
        self.assertIn("changing only the first Elwin deployment Y", scenario5["note"])
        self.assertIn("20턴 내 북쪽 도착", scenario5["note"])
        self.assertIn("alternate `20턴 내 적 전멸`", scenario5["note"])
        self.assertEqual(scenario6["conditions"], "verified_current")
        self.assertEqual(scenario6["description"], "verified_current")
        for capture in (
            "captures/run/489b_s06_description_current_01.png",
            "captures/run/489b_s06_description_current_08.png",
            "captures/run/489b_s06_description_current_12.png",
            "captures/run/489b_s06_description_current_16.png",
            "captures/run/489b_s06_description_current_17.png",
        ):
            self.assertIn(capture, scenario6["captures"])
        self.assertEqual(scenario6["battle_ui"], "verified_current")
        self.assertEqual(scenario6["turn_events"], "progressed_current")
        self.assertEqual(scenario6["completion"], "verified_probe")
        for capture in (
            "captures/run/5b6b_s06_prep_08.png",
            "captures/run/5b6b_s06_opening_15.png",
            "captures/run/5b6b_s06_t1_hein_panel6.png",
            "captures/run/5b6b_s06_t1_liana_panel.png",
            "captures/run/5b6b_s06_t1_sherry_panel.png",
            "captures/run/5b6b_s06_victory_27.png",
            "captures/run/5b6b_s06_victory_37.png",
            "captures/run/5b6b_s06_victory_38.png",
            "captures/run/5b6b_s06_victory_40.png",
            "captures/run/5b6b_s06_next_scenario.png",
        ):
            self.assertIn(capture, scenario6["captures"])
        self.assertIn("all thirteen fixed records", scenario6["note"])
        self.assertIn("Amulet reward", scenario6["note"])
        self.assertIn("Civilian-loss/no-Amulet", scenario6["note"])
        self.assertEqual(scenario7["opening_events"], "verified_current")
        self.assertEqual(scenario7["description"], "verified_current")
        self.assertEqual(scenario7["completion"], "verified_probe")
        for capture in (
            "captures/run/489b_s07_description_current_01.png",
            "captures/run/489b_s07_description_current_06.png",
            "captures/run/489b_s07_description_current_10.png",
            "captures/run/489b_s07_description_current_14.png",
            "captures/run/489b_s07_description_current_15.png",
        ):
            self.assertIn(capture, scenario7["captures"])
        for capture in (
            "captures/run/1a2e_s07_root_menu3.png",
            "captures/run/1a2e_s07_ginam_target.png",
            "captures/run/1a2e_s07_system_6.png",
            "captures/run/1a2e_s07_system_59.png",
            "captures/run/1a2e_s07_system_60.png",
            "captures/run/1a2e_s07_system_63.png",
            "captures/run/1a2e_s07_system_66.png",
            "captures/run/1a2e_s07_system_68.png",
            "captures/run/1a2e_s07_route_next4.png",
        ):
            self.assertIn(capture, scenario7["captures"])
        self.assertIn("all twelve fixed records", scenario7["note"])
        self.assertIn("Mirage Robe and Runestone", scenario7["note"])
        self.assertIn("civilian-death variants", scenario7["note"])
        self.assertEqual(scenario7["battle_ui"], "verified_current")
        self.assertEqual(scenario7["turn_events"], "progressed_current")
        self.assertEqual(scenario8["conditions"], "verified_current")
        self.assertEqual(scenario8["description"], "verified_current")
        for capture in (
            "captures/run/489b_s08_description_current_01.png",
            "captures/run/489b_s08_description_current_09.png",
            "captures/run/489b_s08_description_current_15.png",
            "captures/run/489b_s08_description_current_20.png",
            "captures/run/489b_s08_description_current_25.png",
            "captures/run/489b_s08_description_current_26.png",
        ):
            self.assertIn(capture, scenario8["captures"])
        self.assertEqual(scenario8["opening_events"], "verified_current")
        self.assertEqual(scenario8["turn_events"], "progressed_current")
        self.assertEqual(scenario8["battle_ui"], "verified_probe")
        self.assertEqual(scenario8["completion"], "verified_probe")
        for capture in (
            "captures/run/2209_s08_after_attack.png",
            "captures/run/2209_s08_event_11.png",
            "captures/run/2209_s08_turn2_command2.png",
            "captures/run/2209_s08_kramer_second_target.png",
            "captures/run/2209_s08_after_second_attack.png",
            "captures/run/2209_s08_victory_5.png",
            "captures/run/2209_s08_victory_23.png",
            "captures/run/2209_s08_victory_26.png",
            "captures/run/2209_s08_next_scenario.png",
        ):
            self.assertIn(capture, scenario8["captures"])
        self.assertIn("all eleven fixed records", scenario8["note"])
        self.assertIn("boss-survival", scenario8["note"])
        self.assertIn("Scenario 8-hidden record", scenario8["note"])
        self.assertEqual(scenario9["description"], "verified_current")
        for capture in (
            "captures/run/489b_s09_description_current_01.png",
            "captures/run/489b_s09_description_current_07.png",
            "captures/run/489b_s09_description_current_12.png",
            "captures/run/489b_s09_description_current_16.png",
            "captures/run/489b_s09_description_current_20.png",
            "captures/run/489b_s09_description_current_21.png",
        ):
            self.assertIn(capture, scenario9["captures"])
        self.assertEqual(scenario9["conditions"], "verified_current")
        self.assertEqual(scenario9["preparation"], "verified_current")
        self.assertEqual(scenario9["opening_events"], "verified_current")
        self.assertEqual(scenario9["battle_ui"], "verified_current")
        self.assertEqual(scenario9["turn_events"], "progressed_current")
        self.assertEqual(scenario9["completion"], "verified_probe")
        for capture in (
            "captures/run/af92_s09_laird_target_selected.png",
            "captures/run/af92_s09_after_laird_attack.png",
            "captures/run/af92_s09_post_62.png",
            "captures/run/af92_s09_post_64.png",
            "captures/run/af92_s09_next_scenario.png",
        ):
            self.assertIn(capture, scenario9["captures"])
        self.assertIn("all thirteen fixed records", scenario9["note"])
        self.assertIn("POINT 3060P", scenario9["note"])
        self.assertIn("host automation behavior", scenario9["note"])
        self.assertEqual(scenario10["description"], "verified_current")
        for capture in (
            "captures/run/d3e8_s10_description_final_01.png",
            "captures/run/d3e8_s10_description_final_07.png",
            "captures/run/d3e8_s10_description_final_09.png",
            "captures/run/d3e8_s10_description_final_15.png",
            "captures/run/d3e8_s10_description_final_19.png",
            "captures/run/d3e8_s10_description_final_20.png",
            "captures/run/4591_s10_victory_17.png",
            "captures/run/4591_s10_victory_19.png",
            "captures/run/4591_s11_route_entry2.png",
        ):
            self.assertIn(capture, scenario10["captures"])
        self.assertEqual(scenario10["conditions"], "verified_current")
        self.assertEqual(scenario10["preparation"], "verified_current")
        self.assertEqual(scenario10["opening_events"], "verified_current")
        self.assertEqual(scenario10["battle_ui"], "verified_probe")
        self.assertEqual(scenario10["turn_events"], "verified_probe")
        self.assertEqual(scenario10["completion"], "verified_probe")
        self.assertIn("all ten hidden turn-event monster records", scenario10["note"])
        self.assertIn("POINT 2470P", scenario10["note"])
        self.assertEqual(scenario11["description"], "verified_current")
        for capture in (
            "captures/run/466a_s11_description_final_01.png",
            "captures/run/466a_s11_description_final_07.png",
            "captures/run/466a_s11_description_final_10.png",
            "captures/run/466a_s11_description_final_13.png",
            "captures/run/466a_s11_description_final_14.png",
            "captures/run/d091_turn9_battle.png",
            "captures/run/d091_turn9_enemy16_battle.png",
            "captures/run/d091_s11_victory_18.png",
            "captures/run/d091_s11_victory_21.png",
            "captures/run/d091_s12_route.png",
            "captures/run/d091_s12_brief_04.png",
        ):
            self.assertIn(capture, scenario11["captures"])
        self.assertEqual(scenario11["conditions"], "verified_current")
        self.assertEqual(scenario11["preparation"], "verified_current")
        self.assertEqual(scenario11["opening_events"], "verified_current")
        self.assertEqual(scenario11["battle_ui"], "verified_current")
        self.assertEqual(scenario11["turn_events"], "verified_probe")
        self.assertEqual(scenario11["completion"], "verified_probe")
        self.assertIn("POINT 3770P", scenario11["note"])
        self.assertIn("real 시나리오 12 save", scenario11["note"])
        self.assertEqual(scenario12["description"], "verified_current")
        for capture in (
            "captures/run/d355_s12_description_final_01.png",
            "captures/run/d355_s12_description_final_03.png",
            "captures/run/d355_s12_description_final_08.png",
            "captures/run/d355_s12_description_final_12.png",
            "captures/run/d355_s12_description_final_19.png",
            "captures/run/d355_s12_description_final_20.png",
        ):
            self.assertIn(capture, scenario12["captures"])
        self.assertIn("captures/run/c7ab_s12_body_final2.png", scenario12["captures"])
        self.assertEqual(scenario12["conditions"], "verified_current")
        self.assertEqual(scenario12["preparation"], "verified_current")
        self.assertEqual(scenario12["opening_events"], "verified_current")
        self.assertEqual(scenario12["battle_ui"], "verified_current")
        self.assertEqual(scenario12["turn_events"], "verified_probe")
        self.assertEqual(scenario12["completion"], "verified_probe")
        for capture in (
            "captures/run/8b33_s12_sherry_target_alive9.png",
            "captures/run/8b33_s12_sherry_alive9_result.png",
            "captures/run/8b33_s12_completion_24.png",
            "captures/run/8b33_s12_next_selected.png",
            "captures/run/8b33_s12_route_selected.png",
            "captures/run/8b33_s13_entry.png",
        ):
            self.assertIn(capture, scenario12["captures"])
        self.assertIn("POINT 4920P", scenario12["note"])
        self.assertIn("not as a fresh 8B33", scenario12["note"])
        self.assertEqual(scenario13["description"], "verified_current")
        for capture in (
            "captures/run/d355_s13_description_current_01.png",
            "captures/run/d355_s13_description_current_05.png",
            "captures/run/d355_s13_description_current_09.png",
            "captures/run/d355_s13_description_current_13.png",
            "captures/run/d355_s13_description_current_14.png",
            "captures/run/d355_s13_description_current_15.png",
        ):
            self.assertIn(capture, scenario13["captures"])
        self.assertIn("captures/run/c7ab_s13_title.png", scenario13["captures"])
        self.assertEqual(scenario13["conditions"], "verified_current")
        self.assertEqual(scenario13["preparation"], "verified_current")
        self.assertEqual(scenario13["opening_events"], "verified_current")
        self.assertEqual(scenario13["battle_ui"], "verified_current")
        self.assertEqual(scenario13["turn_events"], "verified_probe")
        self.assertEqual(scenario13["completion"], "verified_probe")
        for capture in (
            "captures/run/67df_s13_turn1_event_39.png",
            "captures/run/67df_s13_zorum_event_17.png",
            "captures/run/0ccd_s13_start_hp_wrapper.png",
            "captures/run/0ccd_s13_vargas_defeat_after_spell.png",
            "captures/run/0ccd_s13_completion_44.png",
            "captures/run/0ccd_s13_completion_46.png",
            "captures/run/0ccd_s13_next_selected.png",
            "captures/run/0ccd_s14_route.png",
            "captures/run/0ccd_s14_title.png",
        ):
            self.assertIn(capture, scenario13["captures"])
        self.assertIn("POINT 6560P", scenario13["note"])
        self.assertIn("disk SRAM slot 1 at Scenario 14", scenario13["note"])
        self.assertIn("probe continuation", scenario13["note"])
        self.assertEqual(scenario14["description"], "verified_current")
        for capture in (
            "captures/run/ce27_s14_description_final_01.png",
            "captures/run/ce27_s14_description_final_05.png",
            "captures/run/ce27_s14_description_final_09.png",
            "captures/run/ce27_s14_description_final_14.png",
            "captures/run/ce27_s14_description_final_19.png",
            "captures/run/ce27_s14_description_final_20.png",
        ):
            self.assertIn(capture, scenario14["captures"])
        self.assertIn("captures/run/c7ab_s14_body_final2.png", scenario14["captures"])
        self.assertEqual(scenario14["conditions"], "verified_current")
        self.assertEqual(scenario14["preparation"], "verified_current")
        self.assertEqual(scenario14["opening_events"], "verified_current")
        self.assertEqual(scenario14["battle_ui"], "verified_probe")
        self.assertEqual(scenario14["turn_events"], "verified_probe")
        self.assertEqual(scenario14["completion"], "verified_probe")
        for capture in (
            "captures/run/b672_s14_turn2_event_01.png",
            "captures/run/b672_s14_turn3_leon_01.png",
            "captures/run/b672_s14_turn4_history_12.png",
            "captures/run/b658_s14_langrisser_commit.png",
            "captures/run/b658_s14_langrisser_event_25.png",
            "captures/run/b658_s14_save_select.png",
            "captures/run/b658_s14_next_selected.png",
            "captures/run/b658_s15_route.png",
            "captures/run/b658_s15_entry.png",
            "captures/analysis/s14_render_2749/scenario_14_pages_02.png",
        ):
            self.assertIn(capture, scenario14["captures"])
        self.assertIn("record 0x19D4A0", scenario14["note"])
        self.assertIn("POINT 2200P", scenario14["note"])
        self.assertIn("disk SRAM slot 1 at Scenario 15", scenario14["note"])
        self.assertEqual(scenario15["description"], "verified_current")
        for capture in (
            "captures/run/b4c1_s15_description_final_01.png",
            "captures/run/b4c1_s15_description_final_08.png",
            "captures/run/b4c1_s15_description_final_10.png",
            "captures/run/b4c1_s15_description_final_14.png",
            "captures/run/b4c1_s15_description_final_19.png",
            "captures/run/b4c1_s15_description_final_20.png",
        ):
            self.assertIn(capture, scenario15["captures"])
        self.assertIn("captures/run/c7ab_s15_title.png", scenario15["captures"])
        self.assertEqual(scenario15["conditions"], "verified_current")
        self.assertEqual(scenario15["preparation"], "verified_current")
        self.assertEqual(scenario15["opening_events"], "verified_current")
        self.assertEqual(scenario15["battle_ui"], "verified_probe")
        self.assertEqual(scenario15["turn_events"], "progressed_current")
        self.assertEqual(scenario15["completion"], "verified_probe")
        for capture in (
            "captures/run/35a3_s15_command_ready.png",
            "captures/run/35a3_s15_escape_target.png",
            "captures/run/35a3_s15_escape_event_03.png",
            "captures/run/35a3_s15_escape_event_11.png",
            "captures/run/35a3_s15_escape_event_31.png",
            "captures/run/35a3_s15_escape_event_57.png",
            "captures/run/35a3_s15_escape_event_59.png",
            "captures/run/35a3_s15_next_selected.png",
            "captures/run/35a3_s16_entry.png",
            "captures/analysis/s15_render_b766/scenario_15_pages_09.png",
        ):
            self.assertIn(capture, scenario15["captures"])
        self.assertIn("record 0x1A0A6E", scenario15["note"])
        self.assertIn("POINT 4000P", scenario15["note"])
        self.assertIn("disk SRAM slot 1 at Scenario 16", scenario15["note"])
        self.assertEqual(scenario16["description"], "verified_current")
        for capture in (
            "captures/run/3fc0_s16_description_final_01.png",
            "captures/run/3fc0_s16_description_final_07.png",
            "captures/run/3fc0_s16_description_final_12.png",
            "captures/run/3fc0_s16_description_final_17.png",
            "captures/run/3fc0_s16_description_final_25.png",
            "captures/run/3fc0_s16_description_final_26.png",
        ):
            self.assertIn(capture, scenario16["captures"])
        self.assertEqual(scenario16["conditions"], "verified_current")
        self.assertEqual(scenario16["preparation"], "verified_current")
        self.assertEqual(scenario16["opening_events"], "verified_current")
        self.assertEqual(scenario16["battle_ui"], "verified_probe")
        self.assertEqual(scenario16["turn_events"], "progressed_current")
        self.assertEqual(scenario17["description"], "verified_current")
        for capture in (
            "captures/run/b0e8_s17_description_final_01.png",
            "captures/run/b0e8_s17_description_final_06.png",
            "captures/run/b0e8_s17_description_final_10.png",
            "captures/run/b0e8_s17_description_final_15.png",
            "captures/run/b0e8_s17_description_final_22.png",
            "captures/run/b0e8_s17_description_final_23.png",
        ):
            self.assertIn(capture, scenario17["captures"])
        self.assertEqual(scenario17["conditions"], "verified_current")
        self.assertEqual(scenario17["preparation"], "verified_current")
        self.assertEqual(scenario17["opening_events"], "verified_current")
        self.assertEqual(scenario17["battle_ui"], "verified_current")
        self.assertEqual(scenario17["turn_events"], "verified_probe")
        self.assertEqual(scenario17["completion"], "verified_probe")
        for capture in (
            "captures/run/b17c_s17_bernhardt_target.png",
            "captures/run/b17c_s17_boss_defeated.png",
            "captures/run/b17c_s17_after_save.png",
            "captures/run/b17c_s18_entry.png",
        ):
            self.assertIn(capture, scenario17["captures"])
        self.assertEqual(scenario18["description"], "verified_current")
        for capture in (
            "captures/run/77d0_s18_description_final_01.png",
            "captures/run/77d0_s18_description_final_04.png",
            "captures/run/77d0_s18_description_final_08.png",
            "captures/run/77d0_s18_description_final_10.png",
            "captures/run/77d0_s18_description_final_14.png",
            "captures/run/77d0_s18_description_final_15.png",
        ):
            self.assertIn(capture, scenario18["captures"])
        self.assertEqual(scenario18["conditions"], "verified_current")
        self.assertEqual(scenario18["preparation"], "verified_current")
        self.assertEqual(scenario18["opening_events"], "verified_current")
        self.assertEqual(scenario18["battle_ui"], "verified_probe")
        self.assertEqual(scenario18["turn_events"], "verified_probe")
        self.assertEqual(scenario18["completion"], "verified_probe")
        for capture in (
            "captures/run/17f2_s18_dragon_target.png",
            "captures/run/17f2_s18_turn1_after_attack_40.png",
            "captures/run/17f2_s18_dragon_retry01_status.png",
            "captures/run/17f2_s18_clear_12.png",
            "captures/run/17f2_s18_next_selected.png",
            "captures/run/17f2_s19_title.png",
        ):
            self.assertIn(capture, scenario18["captures"])
        self.assertEqual(scenario19["description"], "verified_current")
        for capture in (
            "captures/run/77d0_s19_description_current_01.png",
            "captures/run/77d0_s19_description_current_07.png",
            "captures/run/77d0_s19_description_current_11.png",
            "captures/run/77d0_s19_description_current_14.png",
            "captures/run/77d0_s19_description_current_19.png",
            "captures/run/77d0_s19_description_current_20.png",
        ):
            self.assertIn(capture, scenario19["captures"])
        self.assertEqual(scenario19["conditions"], "verified_current")
        self.assertEqual(scenario19["preparation"], "verified_current")
        self.assertEqual(scenario19["opening_events"], "verified_current")
        self.assertEqual(scenario19["battle_ui"], "verified_probe")
        self.assertEqual(scenario19["turn_events"], "progressed_current")
        self.assertEqual(scenario19["completion"], "verified_probe")
        for capture in (
            "captures/run/2829_s19_imelda_target.png",
            "captures/run/2829_s19_turn1_after_imelda_19.png",
            "captures/run/2829s_s19_after_first_attack.png",
            "captures/run/2829s_s19_reinforcement_ready.png",
            "captures/run/2829s_s19_next_selected.png",
            "captures/run/2829s_s20_title.png",
        ):
            self.assertIn(capture, scenario19["captures"])
        self.assertEqual(scenario20["description"], "verified_current")
        for capture in (
            "captures/run/77d0_s20_description_current_01.png",
            "captures/run/77d0_s20_description_current_05.png",
            "captures/run/77d0_s20_description_current_09.png",
            "captures/run/77d0_s20_description_current_12.png",
            "captures/run/77d0_s20_description_current_16.png",
            "captures/run/77d0_s20_description_current_17.png",
        ):
            self.assertIn(capture, scenario20["captures"])
        self.assertEqual(scenario20["conditions"], "verified_current")
        self.assertEqual(scenario20["preparation"], "verified_current")
        self.assertEqual(scenario20["opening_events"], "verified_current")
        self.assertEqual(scenario20["battle_ui"], "verified_probe")
        self.assertEqual(scenario20["turn_events"], "progressed_current")
        self.assertEqual(scenario21["description"], "verified_current")
        for capture in (
            "captures/run/77d0_s21_description_current_01.png",
            "captures/run/77d0_s21_description_current_05.png",
            "captures/run/77d0_s21_description_current_08.png",
            "captures/run/77d0_s21_description_current_11.png",
            "captures/run/77d0_s21_description_current_14.png",
            "captures/run/77d0_s21_description_current_15.png",
        ):
            self.assertIn(capture, scenario21["captures"])
        self.assertEqual(scenario21["conditions"], "verified_current")
        self.assertEqual(scenario21["preparation"], "verified_current")
        self.assertEqual(scenario21["opening_events"], "verified_current")
        self.assertEqual(scenario21["battle_ui"], "verified_probe")
        self.assertEqual(scenario21["turn_events"], "progressed_current")
        self.assertEqual(scenario22["description"], "verified_current")
        for capture in (
            "captures/run/42e6_s22_description_final_01.png",
            "captures/run/42e6_s22_description_final_06.png",
            "captures/run/42e6_s22_description_final_10.png",
            "captures/run/42e6_s22_description_final_15.png",
            "captures/run/42e6_s22_description_final_23.png",
            "captures/run/42e6_s22_description_final_24.png",
        ):
            self.assertIn(capture, scenario22["captures"])
        self.assertEqual(scenario22["conditions"], "verified_current")
        self.assertEqual(scenario22["preparation"], "verified_current")
        self.assertEqual(scenario22["opening_events"], "verified_current")
        self.assertEqual(scenario22["turn_events"], "verified_current")
        self.assertIn("captures/run/c1c9_s22_opening_10.png", scenario22["captures"])
        self.assertIn("captures/run/c1c9_s22_turn1_30.png", scenario22["captures"])
        self.assertEqual(scenario23["description"], "verified_current")
        for capture in (
            "captures/run/212a_s23_description_final_01.png",
            "captures/run/212a_s23_description_final_05.png",
            "captures/run/212a_s23_description_final_09.png",
            "captures/run/212a_s23_description_final_14.png",
            "captures/run/212a_s23_description_final_19.png",
            "captures/run/212a_s23_description_final_20.png",
        ):
            self.assertIn(capture, scenario23["captures"])
        self.assertIn("captures/run/c7ab_s23_title.png", scenario23["captures"])
        self.assertEqual(scenario23["conditions"], "verified_current")
        self.assertEqual(scenario23["preparation"], "verified_current")
        self.assertEqual(scenario23["opening_events"], "verified_current")
        self.assertEqual(scenario23["turn_events"], "verified_current")
        self.assertIn("captures/run/544b_s23_opening_14.png", scenario23["captures"])
        self.assertIn("captures/run/544b_s23_turn1_39.png", scenario23["captures"])
        self.assertEqual(scenario24["description"], "verified_current")
        for capture in (
            "captures/run/212a_s24_description_current_01.png",
            "captures/run/212a_s24_description_current_05.png",
            "captures/run/212a_s24_description_current_09.png",
            "captures/run/212a_s24_description_current_12.png",
            "captures/run/212a_s24_description_current_16.png",
            "captures/run/212a_s24_description_current_17.png",
        ):
            self.assertIn(capture, scenario24["captures"])
        self.assertEqual(scenario24["conditions"], "verified_current")
        self.assertEqual(scenario24["preparation"], "verified_current")
        self.assertEqual(scenario24["opening_events"], "verified_current")
        self.assertEqual(scenario24["turn_events"], "verified_current")
        self.assertIn("captures/run/544b_s24_opening_11.png", scenario24["captures"])
        self.assertIn("captures/run/544b_s24_turn1_38.png", scenario24["captures"])
        self.assertEqual(scenario25["description"], "verified_current")
        for capture in (
            "captures/run/212a_s25_description_current_01.png",
            "captures/run/212a_s25_description_current_05.png",
            "captures/run/212a_s25_description_current_08.png",
            "captures/run/212a_s25_description_current_11.png",
            "captures/run/212a_s25_description_current_14.png",
            "captures/run/212a_s25_description_current_15.png",
        ):
            self.assertIn(capture, scenario25["captures"])
        self.assertEqual(scenario25["preparation"], "verified_current")
        for capture in (
            "captures/run/212a_s25_prep_current.png",
            "captures/run/212a_s25_equipment_commander_01.png",
            "captures/run/212a_s25_equipment_commander_02.png",
            "captures/run/212a_s25_equipment_commander_03.png",
            "captures/run/212a_s25_equipment_commander_04.png",
            "captures/run/212a_s25_equipment_commander_05.png",
            "captures/run/212a_s25_equipment_commander_06.png",
            "captures/run/212a_s25_equipment_commander_07.png",
            "captures/run/212a_s25_equipment_commander_08.png",
            "captures/run/212a_s25_equipment_commander_09.png",
            "captures/run/212a_s25_arrangement_roster1.png",
            "captures/run/212a_s25_arrangement_roster2.png",
        ):
            self.assertIn(capture, scenario25["captures"])
        self.assertIn("ｸﾛｺﾅｲﾄ", scenario25["note"])
        self.assertIn("레스터/크로코나이트", scenario25["note"])
        self.assertNotIn("레스터/크루세이더", scenario25["note"])
        self.assertEqual(scenario26["description"], "verified_current")
        for capture in (
            "captures/run/212a_s26_description_current_01.png",
            "captures/run/212a_s26_description_current_05.png",
            "captures/run/212a_s26_description_current_08.png",
            "captures/run/212a_s26_description_current_11.png",
            "captures/run/212a_s26_description_current_14.png",
            "captures/run/212a_s26_description_current_15.png",
        ):
            self.assertIn(capture, scenario26["captures"])
        self.assertEqual(scenario26["conditions"], "verified_current")
        self.assertEqual(scenario26["preparation"], "verified_current")
        self.assertEqual(scenario26["opening_events"], "verified_current")
        self.assertEqual(scenario26["turn_events"], "verified_current")
        self.assertEqual(scenario26["battle_ui"], "pending")
        self.assertIn("captures/run/eca0_s26_turn1_actual_50.png", scenario26["captures"])
        self.assertEqual(scenario27["preparation"], "verified_current")
        self.assertEqual(scenario27["conditions"], "verified_current")
        self.assertEqual(scenario27["opening_events"], "verified_current")
        self.assertEqual(scenario27["turn_events"], "verified_current")
        self.assertEqual(scenario27["battle_ui"], "verified_probe")
        self.assertEqual(scenario27["completion"], "verified_probe")
        self.assertIn("captures/run/c7ab_s27_body_final2.png", scenario27["captures"])
        self.assertIn("captures/run/eca0_s27_turn1_55.png", scenario27["captures"])
        self.assertEqual(scenario28["description"], "verified_current")
        self.assertEqual(scenario28["conditions"], "verified_current")
        self.assertEqual(scenario28["preparation"], "verified_current")
        self.assertEqual(scenario28["opening_events"], "verified_current")
        self.assertEqual(scenario28["turn_events"], "verified_current")
        self.assertEqual(scenario28["battle_ui"], "verified_current")
        for capture in (
            "captures/run/eca0_s28_turn1_34.png",
            "captures/run/eca0_s28_turn1_35.png",
            "captures/run/eca0_s28_turn1_36.png",
        ):
            self.assertIn(capture, scenario28["captures"])
        self.assertIn("바바리안 versus 워록", scenario28["note"])
        self.assertIn("captures/run/eca0_s28_turn1_64.png", scenario28["captures"])
        self.assertEqual(scenario29["description"], "verified_current")
        self.assertEqual(scenario29["conditions"], "verified_current")
        self.assertEqual(scenario29["preparation"], "verified_current")
        self.assertEqual(scenario29["opening_events"], "verified_current")
        self.assertEqual(scenario29["turn_events"], "verified_current")
        self.assertEqual(scenario29["battle_ui"], "verified_current")
        for capture in (
            "captures/run/eca0_s29_turn1_18.png",
            "captures/run/eca0_s29_turn1_20.png",
            "captures/run/eca0_s29_turn1_49.png",
            "captures/run/eca0_s29_turn1_50.png",
            "captures/run/eca0_s29_turn1_72.png",
            "captures/run/eca0_s29_turn1_74.png",
        ):
            self.assertIn(capture, scenario29["captures"])
        self.assertIn("리자드맨 versus 파이터", scenario29["note"])
        self.assertIn("드래곤나이트 versus 파이터", scenario29["note"])
        self.assertIn("고렘 versus 호크나이트", scenario29["note"])
        self.assertIn("captures/run/eca0_s29_turn1_95.png", scenario29["captures"])
        self.assertEqual(scenario30["description"], "verified_current")
        self.assertEqual(scenario30["conditions"], "verified_current")
        self.assertEqual(scenario30["preparation"], "verified_current")
        self.assertEqual(scenario30["opening_events"], "verified_current")
        self.assertEqual(scenario30["turn_events"], "verified_current")
        self.assertEqual(scenario30["battle_ui"], "verified_probe")
        for capture in (
            "captures/run/212a_s30_arrangement_current2.png",
            "captures/run/212a_s30_after_deploy.png",
            "captures/run/212a_s30_command_current.png",
            "captures/run/212a_s30_after_failed_turn_end.png",
        ):
            self.assertIn(capture, scenario30["captures"])
        self.assertIn("production-derived 3590", scenario30["note"])
        self.assertIn("SCENARIO ?3", scenario30["note"])
        self.assertIn("captures/run/eca0_s30_turn1_17.png", scenario30["captures"])
        self.assertEqual(scenario31["description"], "verified_current")
        self.assertEqual(scenario31["conditions"], "verified_current")
        self.assertEqual(scenario31["preparation"], "verified_current")
        self.assertEqual(scenario31["opening_events"], "verified_current")
        self.assertEqual(scenario31["turn_events"], "verified_current")
        self.assertEqual(scenario31["battle_ui"], "verified_probe")
        self.assertEqual(scenario31["completion"], "verified_probe")
        self.assertEqual(scenario31["branches_endings"], "pending")
        self.assertIn("captures/run/c7ab_s31_body_final2.png", scenario31["captures"])
        self.assertIn("captures/run/eca0_s31_turn1_01.png", scenario31["captures"])
        for capture in (
            "captures/run/3a5a_s31_clean2_arrange_menu.png",
            "captures/run/3a5a_s31_clean2_deploy_confirm.png",
            "captures/run/3a5a_s31_clean2_opening_20.png",
            "captures/run/3a5a_s31_clean2_move_vargas.png",
            "captures/run/3b62_s31_compact_battle_01.png",
            "captures/run/3b82_s31_compact_hein_demon_dead.png",
            "captures/run/78f8_s31_bernhardt_target.png",
            "captures/run/78f8_s31_victory_27.png",
            "captures/run/78f8_s31_save_slot2_after.png",
            "captures/run/78f8_s31_route_after.png",
        ):
            self.assertIn(capture, scenario31["captures"])
        self.assertIn("production-derived 3A5A", scenario31["note"])
        self.assertIn("발가스/제너럴", scenario31["note"])
        self.assertIn("POINT 10700P", scenario31["note"])
        self.assertIn("final boss death event is required", scenario31["note"])
        for evidence in data["global_evidence"]:
            self.assertIn(evidence["state"], data["states"])
            self.assertTrue(evidence["captures"])

    def test_generated_markdown_is_current(self):
        data = inventory.load_inventory()
        expected = inventory.render_markdown(data)
        actual = inventory.OUTPUT.read_text(encoding="utf-8")
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()

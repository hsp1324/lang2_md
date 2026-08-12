import ast
from pathlib import Path
import unittest

from tools import run_current_result_revalidation_parallel as result_parallel
from tools import send_blastem_keys


ROOT = Path(__file__).resolve().parents[1]
DEPRECATED_RUNNERS = (
    "run_scenario12_result_surface.py",
    "run_scenario13_result_surface.py",
    "run_scenario18_20_result_surface.py",
)
FINAL_ROUTE_SCENARIOS = (11, 12, 13, 18, 19, 20)


class LegacyResultStateRestoreSafetyTests(unittest.TestCase):
    def test_deprecated_runners_contain_no_synthetic_load_key_send(self) -> None:
        for filename in DEPRECATED_RUNNERS:
            source = (ROOT / "tools" / filename).read_text(encoding="utf-8")
            tree = ast.parse(source, filename=filename)
            load_specs = {
                node.value
                for node in ast.walk(tree)
                if isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and (
                    node.value == "load"
                    or node.value.startswith("load:")
                )
            }
            self.assertEqual(load_specs, set(), filename)

    def test_final_route_uses_fresh_probe_runner_for_affected_scenarios(self) -> None:
        for scenario in FINAL_ROUTE_SCENARIOS:
            self.assertEqual(
                result_parallel.RUNNERS[scenario],
                "run_scenario28_31_result_surface.py",
            )
        selected = {
            result_parallel.RUNNERS[scenario]
            for scenario in result_parallel.SCENARIOS
        }
        for filename in DEPRECATED_RUNNERS:
            self.assertNotIn(filename, selected)

    def test_final_gate_reaches_result_routing_via_continuous_campaign(self) -> None:
        gate_source = (ROOT / "tools/run_v137_final_gate.py").read_text(
            encoding="utf-8"
        )
        route_source = (
            ROOT / "tools/run_sequential_campaign_revalidation.py"
        ).read_text(encoding="utf-8")
        self.assertIn("run_sequential_campaign_revalidation.py", gate_source)
        self.assertIn(
            "run_current_result_revalidation_parallel as result_parallel",
            route_source,
        )
        for filename in DEPRECATED_RUNNERS:
            self.assertNotIn(filename, gate_source)
            self.assertNotIn(filename, route_source)

    def test_scenario13_import_in_fresh_runner_is_read_only_gst_parser(self) -> None:
        path = ROOT / "tools/run_scenario28_31_result_surface.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        referenced = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "scenario13_result"
        }
        self.assertEqual(
            referenced,
            {
                "EXPECTED_VARGAS_POSITION",
                "VARGAS_RUNTIME_GROUP",
                "runtime_group",
            },
        )

    def test_key_sender_has_no_misleading_load_alias(self) -> None:
        self.assertNotIn("load", send_blastem_keys.KEYSYMS)


if __name__ == "__main__":
    unittest.main()

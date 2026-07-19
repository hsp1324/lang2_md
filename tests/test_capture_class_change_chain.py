from pathlib import Path
import unittest

from tools.capture_class_change_chain import (
    expected_capture_paths,
    pending_transitions,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "roms/original/Langrisser II (Japan).md").read_bytes()


class CaptureClassChangeChainTests(unittest.TestCase):
    def test_hein_chain_is_already_screen_verified(self):
        self.assertEqual(pending_transitions(SOURCE, 5), [])

    def test_liana_chain_is_already_screen_verified(self):
        self.assertEqual(pending_transitions(SOURCE, 2), [])

    def test_sherry_chain_is_already_screen_verified(self):
        self.assertEqual(pending_transitions(SOURCE, 4), [])

    def test_scott_chain_is_already_screen_verified(self):
        self.assertEqual(pending_transitions(SOURCE, 6), [])

    def test_elwin_chain_has_nine_pending_unique_transitions(self):
        transitions = pending_transitions(SOURCE, 1)
        self.assertEqual(len(transitions), 9)
        self.assertEqual(transitions[0].current_class, 0x04)
        self.assertEqual(transitions[-1].current_class, 0x1A)

    def test_capture_paths_include_prompt_and_each_candidate(self):
        paths = expected_capture_paths(0x903C, 5, 0x0A, 3)
        self.assertEqual(
            [path.name for path in paths],
            [
                "903c_c5_s0a_trigger.png",
                "903c_c5_s0a_candidate1.png",
                "903c_c5_s0a_candidate2.png",
                "903c_c5_s0a_candidate3.png",
            ],
        )


if __name__ == "__main__":
    unittest.main()

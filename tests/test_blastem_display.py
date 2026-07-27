import argparse
import os
import unittest
from unittest.mock import patch

from tools import blastem_display


class BlastEmDisplayTests(unittest.TestCase):
    def test_default_is_isolated_virtual_display(self):
        self.assertEqual(blastem_display.DEFAULT_VIRTUAL_DISPLAY, ":104")

    def test_normalizes_default_screen_suffix(self):
        self.assertEqual(blastem_display.normalize_display(":104.0"), ":104")
        self.assertEqual(blastem_display.normalize_display(":104.1"), ":104.1")

    def test_rejects_invalid_display(self):
        for value in ("0", "localhost:0", "", ":bad"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "invalid X11 display"):
                    blastem_display.normalize_display(value)

    def test_virtual_mode_overrides_inherited_desktop(self):
        args = argparse.Namespace(
            desktop_display=False,
            virtual_display=":104.0",
        )
        with patch.dict(
            os.environ,
            {
                "DISPLAY": ":0",
                "WAYLAND_DISPLAY": "wayland-0",
                "SDL_VIDEODRIVER": "wayland",
            },
        ):
            self.assertTrue(blastem_display.configure_display(args))
            self.assertEqual(os.environ["DISPLAY"], ":104")
            self.assertNotIn("WAYLAND_DISPLAY", os.environ)
            self.assertEqual(os.environ["SDL_VIDEODRIVER"], "x11")

    def test_physical_display_requires_explicit_opt_in(self):
        args = argparse.Namespace(
            desktop_display=False,
            virtual_display=":0",
        )
        with self.assertRaisesRegex(ValueError, "refusing virtual-display :0"):
            blastem_display.configure_display(args)

        args.desktop_display = True
        with patch.dict(
            os.environ,
            {
                "DISPLAY": ":0",
                "WAYLAND_DISPLAY": "wayland-0",
                "SDL_VIDEODRIVER": "wayland",
            },
        ):
            self.assertFalse(blastem_display.configure_display(args))
            self.assertEqual(os.environ["DISPLAY"], ":0")
            self.assertEqual(os.environ["WAYLAND_DISPLAY"], "wayland-0")
            self.assertEqual(os.environ["SDL_VIDEODRIVER"], "wayland")

    def test_child_sequence_transport_matches_display_mode(self):
        self.assertEqual(
            blastem_display.sequence_display_args(False),
            ["--xlib-capture", "--software-renderer"],
        )
        self.assertEqual(
            blastem_display.sequence_display_args(True),
            ["--desktop-display"],
        )


if __name__ == "__main__":
    unittest.main()

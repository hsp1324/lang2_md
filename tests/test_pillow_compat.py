from __future__ import annotations

import unittest

from PIL import Image

from tools.pillow_compat import flattened_image_data


class _LegacyImage:
    def getdata(self) -> tuple[str, ...]:
        return ("legacy",)


class _ModernImage:
    def get_flattened_data(self) -> tuple[str, ...]:
        return ("modern",)

    def getdata(self) -> tuple[str, ...]:
        raise AssertionError("modern Pillow path must take precedence")


class PillowCompatTests(unittest.TestCase):
    def test_legacy_getdata_fallback(self) -> None:
        self.assertEqual(
            tuple(flattened_image_data(_LegacyImage())),
            ("legacy",),
        )

    def test_modern_flattened_data_precedes_deprecated_api(self) -> None:
        self.assertEqual(
            tuple(flattened_image_data(_ModernImage())),
            ("modern",),
        )

    def test_installed_pillow_pixel_iteration(self) -> None:
        image = Image.new("RGBA", (2, 1), (1, 2, 3, 4))
        self.assertEqual(
            tuple(flattened_image_data(image)),
            ((1, 2, 3, 4), (1, 2, 3, 4)),
        )


if __name__ == "__main__":
    unittest.main()

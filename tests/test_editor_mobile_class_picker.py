from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "editor/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "editor/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "editor/static/styles.css").read_text(encoding="utf-8")


def test_mobile_virtual_keyboard_resize_does_not_close_class_picker() -> None:
    assert 'window.addEventListener("resize", closePicker)' not in APP
    assert 'window.addEventListener("resize", repositionOpenPicker)' in APP
    assert 'window.visualViewport?.addEventListener("resize", repositionOpenPicker)' in APP


def test_touch_open_does_not_force_virtual_keyboard() -> None:
    assert '"(hover: hover) and (pointer: fine)"' in APP
    assert "if (shouldAutoFocusPickerSearch())" in APP
    assert "assetPickerSearch.focus({preventScroll: true})" in APP


def test_picker_tracks_visual_viewport_and_uses_dynamic_height() -> None:
    assert "const viewport = window.visualViewport" in APP
    assert "positionPicker(pickerState.anchor)" in APP
    assert "100dvh" in CSS
    assert '<link rel="stylesheet" href="/styles.css?v=' in HTML
    assert '<script src="/app.js?v=' in HTML

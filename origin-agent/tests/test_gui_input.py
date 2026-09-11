import copy
import ctypes
from types import SimpleNamespace

import pytest

from origin_agent.gui import GuiCommand, Position
from origin_agent.gui_input import Input, VisualInput, capture_target, parse_keys


@pytest.mark.parametrize(
    "shortcut", ["WIN+R", "ALT+TAB", "ALT+F4", "CTRL+ESC", "CTRL+ALT+DELETE", "CTRL+CTRL+A", "CTRL+unknown"]
)
def test_desktop_and_ambiguous_shortcuts_rejected(shortcut):
    with pytest.raises(ValueError):
        parse_keys(shortcut)


def test_origin_shortcuts_and_windows_input_layout():
    assert parse_keys("ctrl+shift+a") == ([0x11, 0x10], 65)
    assert parse_keys("ALT+ENTER") == ([0x12], 13)
    assert ctypes.sizeof(Input) == 40  # Supported Windows x64; Linux CI uses the same fixed-width layout.


@pytest.mark.parametrize(
    "extra",
    [
        {"position": {"x": 1, "y": 0}},
        {"position": {"x": float("nan"), "y": 0}},
        {"position": {"x": 0.5, "y": -0.1}},
        {},
    ],
)
def test_visual_click_rejects_outside_or_missing_coordinates(extra):
    with pytest.raises(ValueError):
        GuiCommand(action="click", observation_id="a" * 32, target_id="w:1", **extra)


def test_capture_binding_requires_the_observed_foreground_popup():
    target = {"id": "w:1", "rect": [10, 20, 110, 220]}
    view = {"windows": [target], "capture": {"window_id": "w:1", "rect": target["rect"]}}
    assert capture_target(view, view, target) == view["capture"]
    changed = copy.deepcopy(view)
    changed["capture"]["window_id"] = "w:2"
    with pytest.raises(ValueError, match="screenshot"):
        capture_target(changed, view, target)
    changed = {**view, "windows": [target, {"id": "w:2", "popup": True}]}
    with pytest.raises(ValueError, match="popup"):
        capture_target(view, changed, target)


def test_visual_mapping_uses_client_pixels_and_refuses_covering_windows():
    adapter = VisualInput.__new__(VisualInput)
    adapter.hwnd = 1
    adapter.capture = {"rect": [10, 20, 310, 520], "client_rect": [18, 50, 302, 512]}
    assert adapter.point(Position(x=0, y=0)) == (18, 50)
    adapter.backend = SimpleNamespace(
        check_process=lambda: None, owned=lambda h: h == 1, _info=lambda _: {"rect": adapter.capture["rect"]}
    )
    adapter.u = SimpleNamespace(
        IsWindowVisible=lambda _: True,
        GetForegroundWindow=lambda: 1,
        WindowFromPoint=lambda _: 2,
        GetAncestor=lambda *_: 2,
    )
    with pytest.raises(ValueError, match="covered"):
        adapter.guard((100, 100))

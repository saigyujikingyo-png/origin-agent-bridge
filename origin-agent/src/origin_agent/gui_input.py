"""Screenshot-bound input for owned Origin windows; no arbitrary desktop automation."""

import ctypes as C
import time
from ctypes import wintypes as W

MODIFIERS = {"CTRL": 0x11, "SHIFT": 0x10, "ALT": 0x12}
KEYS = {
    "ENTER": 0x0D,
    "TAB": 9,
    "ESC": 0x1B,
    "SPACE": 0x20,
    "BACKSPACE": 8,
    "DELETE": 0x2E,
    "INSERT": 0x2D,
    "HOME": 0x24,
    "END": 0x23,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
}
KEYS.update({f"F{i}": 0x6F + i for i in range(1, 13)})
KEYS.update({chr(i): i for i in [*range(0x30, 0x3A), *range(0x41, 0x5B)]})


def parse_keys(value):
    parts = value.upper().split("+")
    if (
        not parts
        or parts[-1] not in KEYS
        or len(set(parts)) != len(parts)
        or any(p not in MODIFIERS for p in parts[:-1])
    ):
        raise ValueError("Use one key or CTRL/SHIFT/ALT plus one named key, such as CTRL+A or ENTER")
    modifiers, key = parts[:-1], parts[-1]
    if (
        ("ALT" in modifiers and key in ("TAB", "ESC", "F4", "SPACE"))
        or ("CTRL" in modifiers and key == "ESC")
        or ("CTRL" in modifiers and "ALT" in modifiers and key == "DELETE")
    ):
        raise ValueError("Desktop switching/closing shortcuts are not Origin GUI actions")
    return [MODIFIERS[p] for p in modifiers], KEYS[key]


def capture_target(previous, current, target):
    capture = previous.get("capture")
    if not capture or capture["window_id"] != target["id"]:
        raise ValueError("Visual input requires the latest screenshot and its captured window ID")
    if capture["rect"] != target["rect"]:
        raise ValueError("Captured window moved; take a new screenshot")
    popups = [w["id"] for w in current["windows"] if w.get("popup")]
    if popups and target["id"] not in popups:
        raise ValueError("A popup is open; observe and operate that popup")
    return capture


class Mouse(C.Structure):
    _fields_ = [
        ("dx", C.c_int32),
        ("dy", C.c_int32),
        ("data", C.c_uint32),
        ("flags", C.c_uint32),
        ("time", C.c_uint32),
        ("extra", C.c_size_t),
    ]


class Keyboard(C.Structure):
    _fields_ = [
        ("vk", C.c_uint16),
        ("scan", C.c_uint16),
        ("flags", C.c_uint32),
        ("time", C.c_uint32),
        ("extra", C.c_size_t),
    ]


class Payload(C.Union):
    _fields_ = [("mouse", Mouse), ("keyboard", Keyboard)]


class Input(C.Structure):
    _fields_ = [("type", C.c_uint32), ("payload", Payload)]


def keyboard(vk, *, up=False, scan=0):
    return Input(1, Payload(keyboard=Keyboard(vk, scan, (2 if up else 0) | (4 if scan else 0), 0, 0)))


class VisualInput:
    def __init__(self, backend, target, capture):
        self.backend, self.target, self.capture = backend, target, capture
        self.u, self.hwnd = backend.u, target["hwnd"]
        for name, args, result in (
            ("GetForegroundWindow", [], W.HWND),
            ("WindowFromPoint", [W.POINT], W.HWND),
            ("GetAncestor", [W.HWND, W.UINT], W.HWND),
            ("AttachThreadInput", [W.DWORD, W.DWORD, W.BOOL], W.BOOL),
            ("BringWindowToTop", [W.HWND], W.BOOL),
            ("GetAsyncKeyState", [C.c_int], C.c_short),
            ("GetSystemMetrics", [C.c_int], C.c_int),
            ("SendInput", [W.UINT, C.POINTER(Input), C.c_int], W.UINT),
        ):
            function = getattr(self.u, name)
            function.argtypes, function.restype = args, result

    def guard(self, point=None):
        self.backend.check_process()
        if not self.backend.owned(self.hwnd) or not self.u.IsWindowVisible(self.hwnd):
            raise ValueError("Captured Origin window is no longer available")
        if self.backend._info(self.hwnd)["rect"] != self.capture["rect"]:
            raise ValueError("Origin window moved after capture")
        foreground = self.u.GetForegroundWindow()
        if foreground != self.hwnd:
            raise ValueError("Origin lost foreground; observe again before input")
        if point:
            hit = self.u.WindowFromPoint(W.POINT(*point))
            if not self.backend.owned(hit) or self.u.GetAncestor(hit, 2) != self.hwnd:
                raise ValueError("The captured point is covered or belongs to another window")

    def prepare(self):
        if any(self.u.GetAsyncKeyState(key) & 0x8000 for key in (1, 2, 4, 0x10, 0x11, 0x12, 0x5B, 0x5C)):
            raise ValueError("User input is active; retry from a fresh observation when keys are released")
        self.u.SetForegroundWindow(self.hwnd)
        if self.u.GetForegroundWindow() != self.hwnd:
            kernel = C.WinDLL("kernel32", use_last_error=True)
            kernel.GetCurrentThreadId.restype = W.DWORD
            current = kernel.GetCurrentThreadId()
            foreground = self.u.GetWindowThreadProcessId(self.u.GetForegroundWindow(), None)
            attached = (
                foreground and foreground != current and self.u.AttachThreadInput(current, foreground, True)
            )
            try:
                self.u.BringWindowToTop(self.hwnd)
                self.u.SetForegroundWindow(self.hwnd)
            finally:
                if attached:
                    self.u.AttachThreadInput(current, foreground, False)
        self.guard()

    def send(self, events):
        values = (Input * len(events))(*events)
        if self.u.SendInput(len(events), values, C.sizeof(Input)) != len(events):
            raise RuntimeError("Windows input delivery was incomplete; observe instead of replaying input")

    def point(self, position):
        left, top, right, bottom = self.capture["client_rect"]
        return left + round(position.x * (right - left - 1)), top + round(position.y * (bottom - top - 1))

    def mouse(self, flags, point=None, data=0):
        x = y = 0
        if point:
            left, top = self.u.GetSystemMetrics(76), self.u.GetSystemMetrics(77)
            width, height = self.u.GetSystemMetrics(78), self.u.GetSystemMetrics(79)
            if width < 2 or height < 2:
                raise RuntimeError("Interactive desktop geometry is unavailable")
            x, y = (
                round((point[0] - left) * 65535 / (width - 1)),
                round((point[1] - top) * 65535 / (height - 1)),
            )
            flags |= 0xC001  # MOVE | ABSOLUTE | VIRTUALDESK
        return Input(0, Payload(mouse=Mouse(x, y, data & 0xFFFFFFFF, flags, 0, 0)))

    def execute(self, command):
        self.prepare()
        action = command.action
        if action == "keys":
            modifiers, key = parse_keys(command.keys)
            events = [
                *(keyboard(k) for k in modifiers),
                keyboard(key),
                keyboard(key, up=True),
                *(keyboard(k, up=True) for k in reversed(modifiers)),
            ]
            try:
                self.send(events)
            finally:
                self.send([keyboard(k, up=True) for k in [key, *reversed(modifiers)]])
        elif action == "type_text":
            raw = command.text.encode("utf-16-le")
            # No clipboard; chunks remain small enough to recheck foreground between them.
            for offset in range(0, len(raw), 64):
                self.guard()
                codes = [
                    int.from_bytes(raw[i : i + 2], "little")
                    for i in range(offset, min(offset + 64, len(raw)), 2)
                ]
                self.send(
                    [
                        event
                        for code in codes
                        for event in (keyboard(0, scan=code), keyboard(0, scan=code, up=True))
                    ]
                )
        else:
            start = self.point(command.position)
            self.guard(start)
            if action == "scroll":
                self.send([self.mouse(0, start), self.mouse(0x0800, data=command.wheel * 120)])
            elif action == "click":
                down, up = (0x8, 0x10) if command.button == "right" else (0x2, 0x4)
                count = 2 if command.button == "double" else 1
                try:
                    self.send(
                        [
                            self.mouse(0, start),
                            *[e for _ in range(count) for e in (self.mouse(down), self.mouse(up))],
                        ]
                    )
                finally:
                    self.send([self.mouse(up)])
            elif action == "drag":
                end = self.point(command.destination)
                self.guard(end)
                try:
                    self.send([self.mouse(0, start), self.mouse(0x2)])
                    for step in range(1, 11):
                        point = tuple(round(a + (b - a) * step / 10) for a, b in zip(start, end, strict=True))
                        self.guard(point)
                        self.send([self.mouse(0, point)])
                        time.sleep(0.025)
                finally:
                    self.send([self.mouse(0x4)])

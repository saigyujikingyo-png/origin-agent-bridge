"""Owned-process Win32 menus and standard controls; no desktop-wide input."""

import ctypes as C
import os
import time
from ctypes import wintypes as W

import psutil


class NativeGui:
    def __init__(self, runtime):
        if os.name != "nt":
            raise RuntimeError("Origin GUI requires Windows")
        self.pid = runtime["origin_pid"]
        self.created = runtime["origin_created"]
        self.u = C.WinDLL("user32", use_last_error=True)
        self.callback = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
        signatures = {
            "EnumWindows": ([self.callback, W.LPARAM], W.BOOL),
            "EnumChildWindows": ([W.HWND, self.callback, W.LPARAM], W.BOOL),
            "GetWindowThreadProcessId": ([W.HWND, C.POINTER(W.DWORD)], W.DWORD),
            "GetWindowTextW": ([W.HWND, W.LPWSTR, C.c_int], C.c_int),
            "GetClassNameW": ([W.HWND, W.LPWSTR, C.c_int], C.c_int),
            "GetWindowRect": ([W.HWND, C.POINTER(W.RECT)], W.BOOL),
            "GetWindow": ([W.HWND, W.UINT], W.HWND),
            "GetParent": ([W.HWND], W.HWND),
            "GetDlgCtrlID": ([W.HWND], C.c_int),
            "GetWindowLongW": ([W.HWND, C.c_int], W.LONG),
            "GetMenu": ([W.HWND], W.HMENU),
            "GetSubMenu": ([W.HMENU, C.c_int], W.HMENU),
            "GetMenuItemCount": ([W.HMENU], C.c_int),
            "GetMenuItemID": ([W.HMENU, C.c_int], W.UINT),
            "GetMenuState": ([W.HMENU, W.UINT, W.UINT], W.UINT),
            "GetMenuStringW": ([W.HMENU, W.UINT, W.LPWSTR, C.c_int, W.UINT], C.c_int),
            "IsWindow": ([W.HWND], W.BOOL),
            "IsWindowVisible": ([W.HWND], W.BOOL),
            "IsWindowEnabled": ([W.HWND], W.BOOL),
            "SetForegroundWindow": ([W.HWND], W.BOOL),
            "PostMessageW": ([W.HWND, W.UINT, W.WPARAM, W.LPARAM], W.BOOL),
            "SendMessageTimeoutW": (
                [W.HWND, W.UINT, W.WPARAM, W.LPARAM, W.UINT, W.UINT, C.POINTER(C.c_size_t)],
                W.LPARAM,
            ),
        }
        for name, (args, result) in signatures.items():
            func = getattr(self.u, name)
            func.argtypes, func.restype = args, result
        self.check_process()
        self.accessibility = None

    def check_process(self):
        process = psutil.Process(self.pid)
        if abs(process.create_time() - self.created) > 0.01 or process.name().lower() != "origin64.exe":
            raise RuntimeError("Owned Origin process identity changed")
        return process

    def owned(self, hwnd):
        pid = W.DWORD()
        self.u.GetWindowThreadProcessId(hwnd, C.byref(pid))
        return self.u.IsWindow(hwnd) and pid.value == self.pid

    def send(self, hwnd, message, wparam=0, lparam=0):
        self.check_process()
        if not self.owned(hwnd):
            raise ValueError("Window is not owned by this Origin session")
        result = C.c_size_t()
        if not self.u.SendMessageTimeoutW(hwnd, message, wparam, lparam, 0x22, 500, C.byref(result)):
            raise RuntimeError("Origin control did not respond; observe before retrying")
        return result.value

    def _info(self, hwnd, *, control=False):
        title, klass = C.create_unicode_buffer(512), C.create_unicode_buffer(128)
        self.u.GetWindowTextW(hwnd, title, len(title))
        self.u.GetClassNameW(hwnd, klass, len(klass))
        style = self.u.GetWindowLongW(hwnd, -16) & 0xFFFFFFFF
        if control and klass.value.lower() == "edit":
            if style & 0x20:  # ES_PASSWORD: neither expose nor edit password fields.
                return None
            self.send(hwnd, 0x000D, len(title), C.addressof(title))
        rect = W.RECT()
        self.u.GetWindowRect(hwnd, C.byref(rect))
        return {
            "id": f"{'c' if control else 'w'}:{hwnd:x}",
            "hwnd": hwnd,
            "class": klass.value,
            "text": title.value,
            "enabled": bool(self.u.IsWindowEnabled(hwnd)),
            "rect": [rect.left, rect.top, rect.right, rect.bottom],
            "style": style,
            "parent": int(self.u.GetParent(hwnd) or 0),
            "popup": bool(style & 0x80000000 and self.u.GetWindow(hwnd, 4)),
        }

    def _windows(self):
        windows = []

        @self.callback
        def collect(hwnd, _):
            if self.owned(hwnd) and self.u.IsWindowVisible(hwnd):
                info = self._info(hwnd)
                if info["class"] not in ("tooltips_class32", "SysShadow"):
                    windows.append(info)
            return len(windows) < 32

        self.u.EnumWindows(collect, 0)
        windows.sort(key=lambda w: (not w["popup"], w["id"]))
        return windows

    def observe(self, query=""):
        # A dialog can disappear between enumeration and a UIA cache read. Retry reads only;
        # never replay input whose outcome may already have reached Origin.
        for attempt in range(3):
            try:
                return self._observe(query)
            except Exception as exc:
                hresult = getattr(exc, "hresult", 0) & 0xFFFFFFFF
                if attempt == 2 or hresult not in (0x80040201, 0x80010108, 0x80131505):
                    raise
                self.accessibility = None
                time.sleep(0.05)

    def _observe(self, query=""):
        self.check_process()
        windows = self._windows()
        if not windows:
            raise RuntimeError("No visible owned Origin window; begin a GUI transaction first")
        targets = []
        visited = 0
        deadline = time.monotonic() + 4
        truncated = False
        needle = query.casefold()

        def append(node):
            nonlocal truncated
            if node and (not needle or needle in (node["text"] + " " + node.get("class", "")).casefold()):
                if len(targets) < 160:
                    targets.append(node)
                else:
                    truncated = True

        def menus(hwnd, menu, trail, enabled, depth=0):
            nonlocal visited, truncated
            if depth > 10:
                truncated = True
                return
            for pos in range(self.u.GetMenuItemCount(menu)):
                visited += 1
                if visited > 3000 or time.monotonic() > deadline:
                    truncated = True
                    return
                label = C.create_unicode_buffer(512)
                self.u.GetMenuStringW(menu, pos, label, len(label), 0x400)
                name = label.value.replace("&", "").split("\t")[0]
                available = enabled and not (self.u.GetMenuState(menu, pos, 0x400) & 3)
                child = self.u.GetSubMenu(menu, pos)
                if child:
                    menus(hwnd, child, [*trail, name], available, depth + 1)
                else:
                    command = self.u.GetMenuItemID(menu, pos)
                    if name and command not in (0, 0xFFFFFFFF):
                        append(
                            {
                                "id": f"m:{hwnd:x}:{menu:x}:{pos}",
                                "kind": "menu",
                                "hwnd": hwnd,
                                "menu": menu,
                                "command": command,
                                "text": " > ".join([*trail, name]),
                                "enabled": bool(available),
                            }
                        )

        # Origin's MFC dialogs do not always disable their owner. Scope input to the
        # visible popup while retaining every window in the context-change guard.
        active_windows = [w for w in windows if w["popup"]] or windows
        for window in active_windows:
            hwnd = window["hwnd"]

            @self.callback
            def control(child, _, window=window):
                nonlocal visited, truncated
                visited += 1
                if visited > 3000 or time.monotonic() > deadline:
                    truncated = True
                    return False
                if self.owned(child) and self.u.IsWindowVisible(child):
                    try:
                        node = self._info(child, control=True)
                    except RuntimeError:
                        truncated = True
                        return False
                    if node:
                        node.update(
                            kind="control", window_id=window["id"], control_id=self.u.GetDlgCtrlID(child)
                        )
                        node["enabled"] = node["enabled"] and window["enabled"]
                        append(node)
                return True

            self.u.EnumChildWindows(hwnd, control, 0)
            menu = self.u.GetMenu(hwnd)
            if menu:
                menus(hwnd, menu, [], window["enabled"])
        from .gui_accessibility import Accessibility

        if self.accessibility is None:
            self.accessibility = Accessibility(self.pid)
        accessible, limited = self.accessibility.observe(active_windows, query)
        combined = accessible + targets
        return {
            "process": {"pid": self.pid, "created": self.created},
            "observed_at": time.time(),
            "query": query,
            "targets": combined[:160],
            "truncated": truncated or limited or len(combined) > 160,
            "windows": [{k: v for k, v in w.items() if k not in ("style", "parent")} for w in windows],
            "blocked": any(not w["enabled"] or w["popup"] or w["class"] == "#32770" for w in windows),
        }

    def invoke(self, node):
        self.check_process()
        hwnd = node["hwnd"]
        if not self.owned(hwnd) or not self.u.IsWindowEnabled(hwnd):
            raise ValueError("Origin target is unavailable")
        if node["kind"] == "accessible":
            self.accessibility.invoke(node)
            return
        if node["kind"] == "menu":
            message, wparam = 0x0111, node["command"]  # WM_COMMAND, asynchronous for modal dialogs.
        elif node["kind"] == "control" and node["class"].lower() == "button":
            message, wparam = 0x00F5, 0  # BM_CLICK
            self.u.SetForegroundWindow(self.u.GetWindow(hwnd, 4) or self.u.GetParent(hwnd))
        else:
            raise ValueError("This target is not a native menu or standard Button")
        if not self.u.PostMessageW(hwnd, message, wparam, 0):
            raise RuntimeError("Origin rejected the GUI message")

    def dismiss(self, node):
        self.check_process()
        hwnd = node["hwnd"]
        if not node["id"].startswith("w:") or not node.get("popup") or not self.owned(hwnd):
            raise ValueError("dismiss requires an observed owned popup window")
        # Scoped Escape, not desktop-wide keyboard input. Observe to determine whether it closed.
        if not self.u.PostMessageW(hwnd, 0x0100, 0x1B, 1):
            raise RuntimeError("Origin rejected popup dismissal")
        self.u.PostMessageW(hwnd, 0x0101, 0x1B, 0xC0000001)

    def set_text(self, node, text):
        if node["kind"] != "control" or node["class"].lower() != "edit":
            raise ValueError("set_text requires an observed standard Edit control")
        if node["style"] & (0x20 | 0x800):  # Password or read-only edit.
            raise ValueError("This Edit control is not writable")
        buffer = C.create_unicode_buffer(text)
        if not self.send(node["hwnd"], 0x000C, 0, C.addressof(buffer)):
            raise RuntimeError("Origin rejected text input")
        readback = C.create_unicode_buffer(4097)
        self.send(node["hwnd"], 0x000D, len(readback), C.addressof(readback))
        if readback.value != text:
            raise RuntimeError("Origin text readback differs; observe before retrying")

    def capture(self, observation, path):
        from PIL import ImageGrab

        self.check_process()
        candidates = [w for w in observation["windows"] if w["enabled"] and w["class"] == "#32770"]
        if not candidates:
            candidates = [w for w in observation["windows"] if w["enabled"] and w["popup"]]
        if not candidates:
            candidates = observation["windows"]
        target = max(candidates, key=lambda w: (w["rect"][2] - w["rect"][0]) * (w["rect"][3] - w["rect"][1]))
        if not self.owned(target["hwnd"]):
            raise ValueError("Screenshot window is no longer owned")
        result = ImageGrab.grab(window=target["hwnd"])
        if min(result.size) < 20:
            raise RuntimeError("Origin window capture is empty")
        result.save(path, format="PNG")
        return target["id"]

    def terminate_owned(self):
        process = self.check_process()
        process.terminate()
        process.wait(timeout=5)

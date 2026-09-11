"""Windows UI Automation for Origin's MFC menus and accessible custom controls."""

import hashlib
import os
import sys
import time
from pathlib import Path


class Accessibility:
    def __init__(self, pid):
        # OriginExt uses MTA; comtypes must join the existing apartment instead of requesting STA.
        sys.coinit_flags = 0
        from comtypes.client import CreateObject, GetModule

        self.types = GetModule(str(Path(os.environ["SystemRoot"]) / "System32/UIAutomationCore.dll"))
        self.client = CreateObject(self.types.CUIAutomation8, interface=self.types.IUIAutomation2)
        self.client.ConnectionTimeout = 1000
        self.client.TransactionTimeout = 1500
        self.pid = pid
        self.elements = {}
        self.cache = self.client.CreateCacheRequest()
        for prop in (30001, 30002, 30003, 30005, 30010, 30011, 30012, 30019, 30020, 30022):
            self.cache.AddProperty(prop)

    def observe(self, windows, query):
        nodes, truncated = [], False
        seen = set()
        self.elements = {}
        start = time.monotonic()
        for window in windows:
            root = self.client.ElementFromHandle(window["hwnd"])
            values = root.FindAllBuildCache(4, self.client.CreateTrueCondition(), self.cache)
            for index in range(min(values.Length, 2000)):
                if time.monotonic() - start > 4:
                    truncated = True
                    break
                element = values.GetElement(index)
                if (
                    element.CachedProcessId != self.pid
                    or element.CachedIsPassword
                    or element.CachedIsOffscreen
                ):
                    continue
                name, kind = element.CachedName or "", element.CachedControlType
                if not name or (query and query.casefold() not in name.casefold()):
                    continue
                # Interactive roles only; native windows/controls remain available separately.
                if kind not in (50000, 50002, 50003, 50004, 50007, 50011, 50013, 50019, 50024):
                    continue
                if len(nodes) >= 160:
                    truncated = True
                    continue
                rect = element.CachedBoundingRectangle
                bounds = (rect.left, rect.top, rect.right, rect.bottom)
                if rect.right <= rect.left or rect.bottom <= rect.top:
                    continue
                signature = (name, kind, bounds)
                if signature in seen:
                    continue
                seen.add(signature)
                # Legacy MFC providers can return an empty runtime ID for every toolbar item.
                # Bind fallback identity to its window, full-tree position, name, role and bounds.
                identity = [
                    window["hwnd"],
                    list(element.GetRuntimeId()),
                    index,
                    name,
                    kind,
                    rect.left,
                    rect.top,
                    rect.right,
                    rect.bottom,
                ]
                key = "a:" + hashlib.sha256(str(identity).encode()).hexdigest()[:24]
                self.elements[key] = element
                nodes.append(
                    {
                        "id": key,
                        "kind": "accessible",
                        "text": name[:512],
                        "class": element.CachedClassName,
                        "role": kind,
                        "automation_id": element.CachedAutomationId,
                        "hwnd": window["hwnd"],
                        "window_id": window["id"],
                        "enabled": bool(element.CachedIsEnabled and window["enabled"]),
                        "rect": [rect.left, rect.top, rect.right, rect.bottom],
                    }
                )
            truncated = truncated or values.Length > 2000
        return nodes, truncated

    def invoke(self, node):
        element = self.elements.get(node["id"])
        if element is None or element.CurrentProcessId != self.pid or not element.CurrentIsEnabled:
            raise ValueError("Accessible target is stale or not owned")
        # Menus expose ExpandCollapse; legacy MFC items may only expose IAccessible.
        for pattern_id, interface, method in (
            (10005, "IUIAutomationExpandCollapsePattern", "Expand"),
            (10000, "IUIAutomationInvokePattern", "Invoke"),
            (10018, "IUIAutomationLegacyIAccessiblePattern", "DoDefaultAction"),
        ):
            pointer = element.GetCurrentPattern(pattern_id)
            if pointer:
                getattr(pointer.QueryInterface(getattr(self.types, interface)), method)()
                return
        raise ValueError("Accessible target has no supported invoke or expand pattern")

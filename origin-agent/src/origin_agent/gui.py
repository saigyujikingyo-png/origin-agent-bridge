"""Compact GUI contract and observation-bound target validation."""

import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .storage import valid_id

INPUT_ACTIONS = {
    "invoke",
    "set_text",
    "dismiss",
    "select",
    "toggle",
    "expand",
    "collapse",
    "click",
    "drag",
    "keys",
    "type_text",
    "scroll",
}
VISUAL_ACTIONS = {"click", "drag", "keys", "type_text", "scroll"}


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float = Field(ge=0, lt=1, allow_inf_nan=False)
    y: float = Field(ge=0, lt=1, allow_inf_nan=False)


class GuiCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal[
        "begin",
        "observe",
        "invoke",
        "set_text",
        "dismiss",
        "select",
        "toggle",
        "expand",
        "collapse",
        "click",
        "drag",
        "keys",
        "type_text",
        "scroll",
        "commit",
        "rollback",
    ]
    observation_id: str | None = None
    target_id: str | None = Field(default=None, max_length=100)
    text: str | None = Field(default=None, max_length=4096)
    query: str = Field(default="", max_length=120)
    screenshot: bool = False
    position: Position | None = None
    destination: Position | None = None
    button: Literal["left", "right", "double"] = "left"
    keys: str | None = Field(default=None, max_length=40)
    wheel: int | None = Field(default=None, ge=-10, le=10)

    @model_validator(mode="after")
    def contract(self):
        if self.action in INPUT_ACTIONS:
            if not self.observation_id or not self.target_id:
                raise ValueError("GUI input requires a recent observation_id and its target_id")
            valid_id(self.observation_id)
        elif self.observation_id or self.target_id:
            raise ValueError("Targets apply only to GUI input")
        if (self.action in ("set_text", "type_text")) != (self.text is not None):
            raise ValueError("text is required only for set_text/type_text")
        if self.text is not None and "\x00" in self.text:
            raise ValueError("NUL is not valid GUI text")
        if (self.action in ("click", "drag", "scroll")) != (self.position is not None):
            raise ValueError("position is required only for click/drag/scroll")
        if (self.action == "drag") != (self.destination is not None):
            raise ValueError("destination is required only for drag")
        if (self.action == "keys") != (self.keys is not None):
            raise ValueError("keys is required only for the keys action")
        if (self.action == "scroll") != (self.wheel is not None) or self.wheel == 0:
            raise ValueError("scroll requires a nonzero wheel value")
        if self.button != "left" and self.action != "click":
            raise ValueError("button applies only to click")
        if self.keys:
            from .gui_input import parse_keys

            parse_keys(self.keys)
        return self


def resolve_target(previous, current, target_id, *, now=None):
    """Reject stale/reused handles and changed modal context before any input."""
    now = time.time() if now is None else now
    if now - previous["observed_at"] > 120:
        raise ValueError("GUI observation expired; observe again")
    if previous["process"] != current["process"] or previous["windows"] != current["windows"]:
        raise ValueError("GUI window context changed; observe again")
    old_matches = [n for n in previous["targets"] + previous["windows"] if n["id"] == target_id]
    new_matches = [n for n in current["targets"] + current["windows"] if n["id"] == target_id]
    if len(old_matches) != 1 or len(new_matches) != 1:
        raise ValueError("GUI target is missing or ambiguous; observe again")
    old, new = old_matches[0], new_matches[0]
    if old != new:
        raise ValueError("GUI target changed or was not observed; observe again")
    if not new["enabled"]:
        raise ValueError("GUI target is disabled")
    return new


def public_observation(value):
    return {
        **{k: value[k] for k in ("observed_at", "blocked", "truncated", "query")},
        "backend": "win32+uia",
        "windows": [{k: v for k, v in w.items() if k != "hwnd"} for w in value["windows"]],
        "targets": [
            {k: v for k, v in n.items() if k not in ("hwnd", "menu", "command", "parent", "style")}
            for n in value["targets"]
        ],
    }

"""Numeric tick formatting through the native per-axis properties.

Reference: https://docs.originlab.com/labtalk/ref/layer-axis-label-obj/
No worksheet values, units, scales or global Origin preferences are changed.
"""


def tick_format(mode, bounds):
    if mode not in {"auto", "decimal", "scientific"}:
        raise ValueError("Unknown tick format")
    if mode != "auto":
        return mode
    magnitude = max(abs(bounds[0]), abs(bounds[1]))
    return "scientific" if 0 < magnitude < 0.001 or magnitude >= 100000 else "decimal"


def format_ticks(layer, style):
    expected = {}
    for axis in ("x", "y"):
        mode = tick_format(getattr(style, f"{axis}_tick_format"), getattr(layer, f"{axis}lim"))
        prop = f"{axis}.label.numFormat"
        value = 2 if mode == "scientific" else 1
        layer.set_int(prop, value)
        expected[prop] = value
        if mode == "scientific":
            # Let Origin choose precision instead of rounding every mantissa to an integer.
            places = f"{axis}.label.decPlaces"
            layer.set_int(places, -1)
            expected[places] = -1
    return expected

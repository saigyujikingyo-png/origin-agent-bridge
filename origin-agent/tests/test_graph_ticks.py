import pytest
from pydantic import ValidationError

from origin_agent.graph_ticks import tick_format
from origin_agent.models import ChartStyle


@pytest.mark.parametrize(
    "bounds,expected",
    [
        ((0.00002, 0.00012), "scientific"),
        ((-0.00012, -0.00002), "scientific"),
        ((-0.00001, 0.00001), "scientific"),
        ((0, 0), "decimal"),
        ((0, 0.001), "decimal"),
        ((0, 99999), "decimal"),
        ((0, 100000), "scientific"),
        ((0, -1000000), "scientific"),
        ((1, 8), "decimal"),
    ],
)
def test_numeric_ranges_choose_readable_notation(bounds, expected):
    assert tick_format("auto", bounds) == expected


def test_explicit_notation_and_closed_style_schema():
    assert tick_format("decimal", (0.00002, 0.00012)) == "decimal"
    assert tick_format("scientific", (1, 8)) == "scientific"
    style = ChartStyle(x_tick_format="decimal", y_tick_format="scientific")
    assert style.x_tick_format == "decimal"
    for field in ("x_tick_format", "y_tick_format"):
        with pytest.raises(ValidationError):
            ChartStyle(**{field: "arbitrary LabTalk"})

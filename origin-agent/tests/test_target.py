import pytest

from origin_agent.target import assess_target, require_target


def test_unprobed_installation_is_not_a_verified_target():
    assert assess_target(None)["status"] == "not_probed"


def test_measured_edinburgh_baseline_is_accepted_without_claiming_full_coverage():
    engine = {"version": 10.350243, "bitness": 64, "edition": "Origin", "demo": 0}
    require_target(engine)
    assessment = assess_target(engine)
    assert assessment["status"] == "match"
    assert assessment["target"]["full_functionality_verified"] is False


@pytest.mark.parametrize(
    "changes",
    [
        {"version": 10.350244},
        {"version": float("nan")},
        {"version": None},
        {"edition": "OriginPro"},
        {"bitness": 32},
        {"demo": 1},
    ],
)
def test_unverified_build_or_license_cannot_be_used_as_the_target(changes):
    engine = {"version": 10.350243, "bitness": 64, "edition": "Origin", "demo": 0, **changes}
    with pytest.raises(RuntimeError, match="tested|confirmed|64-bit"):
        require_target(engine)

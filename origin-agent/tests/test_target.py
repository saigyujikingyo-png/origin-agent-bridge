import pytest

from origin_agent.target import assess_target, require_target, target_profile


def test_unprobed_installation_is_not_a_verified_target():
    assessment = assess_target(None)
    assert assessment["status"] == "not_probed"
    assert assessment["matched_baseline"] is None


@pytest.mark.parametrize(
    ("version", "baseline_id", "acceptance"),
    [
        (10.300197, "origin-2026-sr1", "pending"),
        (10.350243, "origin-2026b-sr2", "documented_cases_passed"),
    ],
)
def test_measured_baselines_are_identified_without_claiming_full_coverage(version, baseline_id, acceptance):
    engine = {"version": version, "bitness": 64, "edition": "Origin", "demo": 0}
    require_target(engine)
    assessment = assess_target(engine)
    assert assessment["status"] == "match"
    assert assessment["matched_baseline"]["id"] == baseline_id
    assert assessment["matched_baseline"]["native_acceptance"] == acceptance
    assert assessment["target"]["full_functionality_verified"] is False


@pytest.mark.parametrize("version", [10.300197, 10.350243])
@pytest.mark.parametrize(
    "changes",
    [
        {"version": 10.350244},
        {"version": 10.300198},
        {"version": 10.30018031},
        {"version": float("nan")},
        {"version": float("inf")},
        {"version": None},
        {"version": "10.30.197"},
        {"edition": "OriginPro"},
        {"bitness": 32},
        {"demo": 1},
        {"demo": None},
    ],
)
def test_other_builds_or_unconfirmed_license_are_rejected(version, changes):
    engine = {"version": version, "bitness": 64, "edition": "Origin", "demo": 0, **changes}
    with pytest.raises(RuntimeError, match="supported|confirmed|64-bit"):
        require_target(engine)
    assert assess_target(engine)["matched_baseline"] is None


def test_returned_metadata_cannot_mutate_the_allowlist():
    original = target_profile()
    profile = target_profile()
    profile["baselines"][0]["version"] = 99
    assessment = assess_target({"version": 10.300197, "bitness": 64, "edition": "Origin", "demo": 0})
    assessment["matched_baseline"]["version"] = 99
    assessment["target"]["baselines"].clear()
    assert target_profile() == original

"""Explicit Origin builds selected for the personally shared Edinburgh package."""

import math
from copy import deepcopy

TARGET = {
    "id": "edinburgh-origin-2026-and-2026b-x64",
    "label": "Origin 2026 SR1 (10.300197) or 2026b SR2 (10.350243), Windows x64, Origin edition",
    "baselines": [
        {
            "id": "origin-2026-sr1",
            "label": "Origin 2026 SR1",
            "version": 10.300197,
            "native_acceptance": "pending",
        },
        {
            "id": "origin-2026b-sr2",
            "label": "Origin 2026b SR2",
            "version": 10.350243,
            "native_acceptance": "documented_cases_passed",
        },
    ],
    "bitness": 64,
    "edition": "Origin",
    "distribution": "personal sharing",
    "full_functionality_verified": False,
}


def target_profile() -> dict:
    """Return a detached descriptor; matching a build does not certify its workflows."""
    return deepcopy(TARGET)


def assess_target(engine: dict | None) -> dict:
    assessment = {
        "status": "not_probed",
        "target": target_profile(),
        "matched_baseline": None,
        "scope": "Build, bitness, edition and activation checks; not full functional acceptance",
    }
    if not engine:
        return assessment
    reasons = []
    try:
        version = float(engine["version"])
    except (KeyError, TypeError, ValueError, OverflowError):
        version = math.nan
    baseline = next(
        (
            item
            for item in TARGET["baselines"]
            if math.isclose(version, item["version"], rel_tol=0, abs_tol=1e-7)
        ),
        None,
    )
    if baseline is None:
        reasons.append("Origin build must be an explicitly supported 10.300197 or 10.350243 baseline")
    if engine.get("bitness") != TARGET["bitness"]:
        reasons.append("Origin must be 64-bit")
    if engine.get("edition") != TARGET["edition"]:
        reasons.append("Origin edition differs from the supported Origin edition")
    if engine.get("demo") != 0:
        reasons.append("Origin activation is not confirmed outside Demo mode")
    assessment.update(
        status="mismatch" if reasons else "match",
        reasons=reasons,
        matched_baseline=deepcopy(baseline) if not reasons else None,
    )
    return assessment


def require_target(engine: dict) -> None:
    assessment = assess_target(engine)
    if assessment["status"] != "match":
        reasons = assessment.get("reasons", ["Origin has not been probed"])
        raise RuntimeError("This build targets " + TARGET["label"] + ": " + "; ".join(reasons))

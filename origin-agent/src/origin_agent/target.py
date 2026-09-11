"""The one Origin baseline selected for the personally shared Edinburgh build."""

import math

TARGET = {
    "id": "edinburgh-origin-2026b-sr2-x64",
    "label": "Origin 2026b SR2 (10.350243), Windows x64, Origin edition",
    "version": 10.350243,
    "bitness": 64,
    "edition": "Origin",
    "distribution": "personal sharing",
    "full_functionality_verified": False,
}


def assess_target(engine: dict | None) -> dict:
    if not engine:
        return {"status": "not_probed", "target": dict(TARGET)}
    reasons = []
    try:
        version_matches = math.isclose(float(engine["version"]), TARGET["version"], rel_tol=0, abs_tol=1e-7)
    except (KeyError, TypeError, ValueError):
        version_matches = False
    if not version_matches:
        reasons.append("Origin build differs from the tested 10.350243 baseline")
    if engine.get("bitness") != TARGET["bitness"]:
        reasons.append("Origin must be 64-bit")
    if engine.get("edition") != TARGET["edition"]:
        reasons.append("Origin edition differs from the tested baseline")
    if engine.get("demo") != 0:
        reasons.append("Origin activation is not confirmed outside Demo mode")
    return {"status": "mismatch" if reasons else "match", "reasons": reasons, "target": dict(TARGET)}


def require_target(engine: dict) -> None:
    assessment = assess_target(engine)
    if assessment["status"] != "match":
        reasons = assessment.get("reasons", ["Origin has not been probed"])
        raise RuntimeError("This build targets " + TARGET["label"] + ": " + "; ".join(reasons))

from __future__ import annotations

from copy import deepcopy
from typing import Any

from libtools.geometry_checks import ShapeInfo, check_completeness, check_fit, check_overlap
from libtools.registry import Entry
from libtools.report import Check, Report


def validate_output(entry: Entry, shapes: list[ShapeInfo], common_volume_fn) -> Report:
    expect = _normalize_expect(entry.expect)
    checks = [Check("compiles", True, "")]

    completeness_violations = check_completeness(shapes, expect)
    checks.append(
        Check("completeness", not completeness_violations, "; ".join(completeness_violations))
    )

    overlap_violations = check_overlap(shapes, common_volume_fn, expect)
    checks.append(Check("overlap", not overlap_violations, "; ".join(overlap_violations)))

    fit_violations = check_fit(shapes, expect)
    checks.append(Check("fit", not fit_violations, "; ".join(fit_violations)))

    return Report(
        id=entry.id,
        layer=entry.layer,
        status=entry.status,
        tier="output",
        checks=checks,
    )


def failure_report(entry_or_ids: Entry | tuple[str, str, str], detail: str) -> Report:
    if isinstance(entry_or_ids, Entry):
        entry_id = entry_or_ids.id
        layer = entry_or_ids.layer
        status = entry_or_ids.status
    else:
        entry_id, layer, status = entry_or_ids

    return Report(
        id=entry_id,
        layer=layer,
        status=status,
        tier="output",
        checks=[Check("compiles", False, detail)],
    )


def _normalize_expect(expect: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(expect)
    bbox = normalized.get("envelope", {}).get("bbox_in")
    if not isinstance(bbox, dict):
        return normalized

    for axis in ("x", "y", "z"):
        value = bbox.get(axis)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            bbox[axis] = [0.0, float(value)]

    return normalized

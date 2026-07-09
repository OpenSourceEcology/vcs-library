from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from itertools import combinations


_AXES = ("x", "y", "z")


@dataclass
class ShapeInfo:
    name: str
    valid: bool
    closed: bool
    volume_in3: float
    bbox_in: dict


def check_completeness(shapes: list[ShapeInfo], expect: dict) -> list[str]:
    violations: list[str] = []

    for shape in shapes:
        if not shape.valid:
            violations.append(f"{shape.name}: valid is False")
        if not shape.closed:
            violations.append(f"{shape.name}: closed is False")
        if shape.volume_in3 <= 0:
            violations.append(f"{shape.name}: volume_in3 must be > 0, actual {shape.volume_in3}")

    solids_expect = expect.get("solids", {})
    min_count = solids_expect.get("min_count")
    if min_count is not None and len(shapes) < min_count:
        violations.append(f"solids min_count shortfall: expected {min_count}, actual {len(shapes)}")

    for role in solids_expect.get("roles", []):
        pattern = role.get("pattern")
        if not pattern:
            continue

        actual = sum(1 for shape in shapes if fnmatch(shape.name, pattern))
        if "count" in role:
            expected = role["count"]
            if actual != expected:
                violations.append(
                    f"role pattern {pattern!r}: expected {expected}, actual {actual}"
                )
        elif actual < 1:
            violations.append(
                f"role pattern {pattern!r}: expected at least 1, actual {actual}"
            )

    return violations


def check_overlap(shapes, common_volume_fn, expect) -> list[str]:
    violations: list[str] = []
    overlap_expect = expect.get("overlap", {})
    tolerance = overlap_expect.get("tolerance_in3", 0.001)
    allowed_contact = overlap_expect.get("allowed_contact", [])

    for left, right in combinations(shapes, 2):
        if not _bboxes_strictly_intersect(left.bbox_in, right.bbox_in):
            continue

        volume = common_volume_fn(left, right)
        if volume <= tolerance:
            continue
        if _is_allowed_contact(left.name, right.name, allowed_contact):
            continue

        violations.append(
            f"{left.name} overlaps {right.name}: common volume {volume} in3 exceeds tolerance {tolerance}"
        )

    return violations


def check_fit(shapes: list[ShapeInfo], expect: dict) -> list[str]:
    envelope_expect = expect.get("envelope", {})
    envelope_bbox = envelope_expect.get("bbox_in")
    if not envelope_bbox or not shapes:
        return []

    tolerance = envelope_expect.get("tolerance_in", 0.0)
    union_bbox = _union_bbox(shapes)
    violations: list[str] = []

    for axis in _AXES:
        actual_min, actual_max = union_bbox[axis]
        allowed_min = envelope_bbox[axis][0] - tolerance
        allowed_max = envelope_bbox[axis][1] + tolerance

        if actual_min < allowed_min:
            violations.append(
                f"fit {axis} min out of envelope: actual {actual_min}, allowed {allowed_min}"
            )
        if actual_max > allowed_max:
            violations.append(
                f"fit {axis} max out of envelope: actual {actual_max}, allowed {allowed_max}"
            )

    return violations


def _bboxes_strictly_intersect(left: dict, right: dict) -> bool:
    for axis in _AXES:
        if min(left[axis][1], right[axis][1]) <= max(left[axis][0], right[axis][0]):
            return False
    return True


def _is_allowed_contact(left_name: str, right_name: str, allowed_contact) -> bool:
    for pattern_left, pattern_right in allowed_contact:
        if fnmatch(left_name, pattern_left) and fnmatch(right_name, pattern_right):
            return True
        if fnmatch(left_name, pattern_right) and fnmatch(right_name, pattern_left):
            return True
    return False


def _union_bbox(shapes: list[ShapeInfo]) -> dict:
    return {
        axis: [
            min(shape.bbox_in[axis][0] for shape in shapes),
            max(shape.bbox_in[axis][1] for shape in shapes),
        ]
        for axis in _AXES
    }

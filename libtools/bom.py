from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from libtools.geometry_checks import ShapeInfo


INFERENCE_TOLERANCE_IN = 1.0 / 32.0

_LUMBER_SECTIONS = (
    ("2x4", (1.5, 3.5)),
    ("2x6", (1.5, 5.5)),
    ("2x8", (1.5, 7.25)),
    ("2x10", (1.5, 9.25)),
    ("2x12", (1.5, 11.25)),
)
_SHEET_THICKNESSES = (0.4375, 0.5, 0.75)
_CSV_COLUMNS = (
    "count",
    "description",
    "cut_length_in",
    "material_class",
    "total_volume_in3",
    "sourcing",
)


@dataclass(frozen=True)
class BomLine:
    count: int
    description: str
    cut_length_in: float | None
    material_class: str
    total_volume_in3: float


def shape_dimensions(shape: ShapeInfo) -> tuple[float, float, float]:
    return tuple(
        float(shape.bbox_in[axis][1]) - float(shape.bbox_in[axis][0])
        for axis in ("x", "y", "z")
    )


def infer_member(dims_in: Iterable[float]) -> tuple[str, float | None, str]:
    dims = tuple(sorted(float(dim) for dim in dims_in))

    for nominal, section in _LUMBER_SECTIONS:
        if _same_pair(dims[:2], section):
            return nominal, dims[2], "lumber"

    for thickness in _SHEET_THICKNESSES:
        if _close(dims[0], thickness):
            return f"{_format_dim(thickness)} in sheet", dims[2], "sheet"

    return " x ".join(_format_dim(dim) for dim in dims), None, "other"


def group_shapes(shapes: Iterable[ShapeInfo]) -> list[BomLine]:
    groups: list[dict] = []

    for shape in shapes:
        dims = tuple(sorted(shape_dimensions(shape)))
        for group in groups:
            if _same_dims(dims, group["dims"]):
                group["count"] += 1
                group["volume"] += float(shape.volume_in3)
                break
        else:
            groups.append({"dims": dims, "count": 1, "volume": float(shape.volume_in3)})

    lines = []
    for group in groups:
        description, cut_length, material_class = infer_member(group["dims"])
        lines.append(
            BomLine(
                count=group["count"],
                description=description,
                cut_length_in=cut_length,
                material_class=material_class,
                total_volume_in3=group["volume"],
            )
        )

    return sorted(lines, key=lambda line: line.total_volume_in3, reverse=True)


def write_bom_csv(shapes: Iterable[ShapeInfo], path: Path) -> list[BomLine]:
    lines = group_shapes(shapes)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CSV_COLUMNS)
        writer.writeheader()
        for line in lines:
            writer.writerow(
                {
                    "count": line.count,
                    "description": line.description,
                    "cut_length_in": _format_number(line.cut_length_in),
                    "material_class": line.material_class,
                    "total_volume_in3": _format_number(line.total_volume_in3),
                    "sourcing": "",
                }
            )
    return lines


def _same_pair(actual: tuple[float, float], expected: tuple[float, float]) -> bool:
    return all(_close(left, right) for left, right in zip(actual, sorted(expected)))


def _same_dims(left: tuple[float, float, float], right: tuple[float, float, float]) -> bool:
    return all(_close(left_dim, right_dim) for left_dim, right_dim in zip(left, right))


def _close(left: float, right: float) -> bool:
    return abs(left - right) <= INFERENCE_TOLERANCE_IN


def _format_dim(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _format_number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.3f}".rstrip("0").rstrip(".")

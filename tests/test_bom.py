import csv

import pytest

from libtools.bom import group_shapes, infer_member, shape_dimensions, write_bom_csv
from libtools.geometry_checks import ShapeInfo


def fake_shape(name, dims, volume=None):
    return ShapeInfo(
        name=name,
        valid=True,
        closed=True,
        volume_in3=volume if volume is not None else dims[0] * dims[1] * dims[2],
        bbox_in={
            "x": [0.0, dims[0]],
            "y": [0.0, dims[1]],
            "z": [0.0, dims[2]],
        },
    )


@pytest.mark.parametrize(
    ("dims", "description", "cut_length", "material_class"),
    [
        ((1.5, 3.5, 96.0), "2x4", 96.0, "lumber"),
        ((1.5, 5.5, 92.625), "2x6", 92.625, "lumber"),
        ((1.5, 7.25, 88.0), "2x8", 88.0, "lumber"),
        ((1.5, 9.25, 72.0), "2x10", 72.0, "lumber"),
        ((1.5, 11.25, 60.0), "2x12", 60.0, "lumber"),
        ((0.4375, 48.0, 96.0), "0.4375 in sheet", 96.0, "sheet"),
        ((0.5, 48.0, 96.0), "0.5 in sheet", 96.0, "sheet"),
        ((0.75, 48.0, 96.0), "0.75 in sheet", 96.0, "sheet"),
        ((2.0, 3.0, 4.0), "2 x 3 x 4", None, "other"),
    ],
)
def test_nominal_inference_table(dims, description, cut_length, material_class):
    assert infer_member(dims) == (description, cut_length, material_class)


def test_nominal_inference_accepts_tolerance_edge():
    description, cut_length, material_class = infer_member((1.5 + 1 / 32, 5.5, 92.625))

    assert description == "2x6"
    assert cut_length == 92.625
    assert material_class == "lumber"


def test_nominal_inference_rejects_beyond_tolerance():
    description, cut_length, material_class = infer_member((1.5 + 1 / 32 + 0.001, 5.5, 92.625))

    assert description == "1.5322 x 5.5 x 92.625"
    assert cut_length is None
    assert material_class == "other"


def test_shape_dimensions_uses_bbox_spans():
    shape = ShapeInfo(
        name="offset",
        valid=True,
        closed=True,
        volume_in3=1.0,
        bbox_in={"x": [5.0, 7.0], "y": [-1.0, 2.5], "z": [10.0, 16.0]},
    )

    assert shape_dimensions(shape) == (2.0, 3.5, 6.0)


def test_grouping_identical_members_with_permuted_axes_and_tolerance():
    shapes = [
        fake_shape("a", (1.5, 5.5, 92.625), 100.0),
        fake_shape("b", (5.5, 1.5, 92.625), 110.0),
        fake_shape("c", (1.5, 5.5 + 1 / 64, 92.625), 120.0),
    ]

    lines = group_shapes(shapes)

    assert len(lines) == 1
    assert lines[0].count == 3
    assert lines[0].description == "2x6"
    assert lines[0].total_volume_in3 == 330.0


def test_grouping_sorts_by_total_volume_descending():
    lines = group_shapes(
        [
            fake_shape("small", (1.5, 3.5, 10), 52.5),
            fake_shape("large", (1.5, 5.5, 20), 165.0),
        ]
    )

    assert [line.description for line in lines] == ["2x6", "2x4"]


def test_write_bom_csv_shape_and_blank_sourcing(tmp_path):
    path = tmp_path / "entry.bom.csv"

    lines = write_bom_csv([fake_shape("stud", (1.5, 5.5, 92.625))], path)

    assert len(lines) == 1
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    assert rows == [
        {
            "count": "1",
            "description": "2x6",
            "cut_length_in": "92.625",
            "material_class": "lumber",
            "total_volume_in3": "764.156",
            "sourcing": "",
        }
    ]

import xml.etree.ElementTree as ET
from pathlib import Path

from libtools.fab_drawing import (
    VIEW_BOXES,
    assemble_fallback_svg,
    layout_view,
    project_bboxes,
    transform_point,
    write_fab_drawing,
)
from libtools.geometry_checks import ShapeInfo
from libtools.registry import Entry


def fake_shape(name, bbox, volume=1.0):
    return ShapeInfo(
        name=name,
        valid=True,
        closed=True,
        volume_in3=volume,
        bbox_in=bbox,
    )


def fake_entry(exterior_face="-y"):
    return Entry(
        id="sample",
        layer="module",
        path=Path("library/modules/sample"),
        meta={"interface": {"exterior_face": exterior_face}},
        expect={},
        schema_path=Path("schema.py"),
        compiler_path=Path("compiler.py"),
        status="active",
    )


def test_project_bboxes_front_y_axis_uses_x_and_z_polygon():
    shapes = [
        fake_shape(
            "box",
            {"x": [2.0, 6.0], "y": [10.0, 12.0], "z": [1.0, 5.0]},
        )
    ]

    polygons = project_bboxes(shapes, "y")

    assert polygons[0].points == ((2.0, 1.0), (6.0, 1.0), (6.0, 5.0), (2.0, 5.0))


def test_project_bboxes_side_x_axis_uses_y_and_z_polygon():
    shapes = [
        fake_shape(
            "box",
            {"x": [2.0, 6.0], "y": [10.0, 12.0], "z": [1.0, 5.0]},
        )
    ]

    polygons = project_bboxes(shapes, "x")

    assert polygons[0].points == ((10.0, 1.0), (12.0, 1.0), (12.0, 5.0), (10.0, 5.0))


def test_layout_view_scale_to_fit_respects_view_box_padding():
    polygons = project_bboxes(
        [
            fake_shape(
                "wide",
                {"x": [0.0, 100.0], "y": [0.0, 5.0], "z": [0.0, 50.0]},
            )
        ],
        "y",
    )

    layout = layout_view(polygons, (0.0, 0.0, 200.0, 120.0), padding=10.0)
    transformed = [transform_point(point, layout) for point in layout.polygons[0].points]
    xs = [point[0] for point in transformed]
    ys = [point[1] for point in transformed]

    assert min(xs) >= 10.0
    assert max(xs) <= 190.0
    assert min(ys) >= 10.0
    assert max(ys) <= 110.0
    assert layout.scale == 1.8


def test_layout_view_centers_tall_geometry():
    polygons = project_bboxes(
        [
            fake_shape(
                "tall",
                {"x": [0.0, 10.0], "y": [0.0, 5.0], "z": [0.0, 100.0]},
            )
        ],
        "y",
    )

    layout = layout_view(polygons, (0.0, 0.0, 200.0, 120.0), padding=10.0)
    transformed = [transform_point(point, layout) for point in layout.polygons[0].points]
    xs = [point[0] for point in transformed]

    assert min(xs) > 10.0
    assert max(xs) < 190.0
    assert layout.scale == 1.0


def test_fallback_page_assembly_produces_valid_svg():
    svg = assemble_fallback_svg(
        fake_entry(),
        [
            fake_shape(
                "stud",
                {"x": [0.0, 1.5], "y": [0.0, 5.5], "z": [0.0, 92.625]},
                volume=764.15625,
            )
        ],
    )

    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert "fab_drawing_path=projection" in svg
    assert "BOM cut table" in svg
    assert "Overall dimensions" in svg
    assert "2x6" in svg


def test_fallback_uses_exterior_face_for_front_projection():
    shape = fake_shape(
        "box",
        {"x": [0.0, 10.0], "y": [0.0, 3.0], "z": [0.0, 20.0]},
    )

    default_svg = assemble_fallback_svg(fake_entry("-y"), [shape])
    x_face_svg = assemble_fallback_svg(fake_entry("+x"), [shape])

    assert default_svg != x_face_svg
    assert "fab_drawing_path=projection" in x_face_svg


def test_write_fab_drawing_falls_back_and_stamps_projection(monkeypatch, tmp_path):
    def fail_techdraw(entry, doc, out_path):
        raise RuntimeError("no techdraw")

    monkeypatch.setattr("libtools.fab_drawing._write_techdraw_svg", fail_techdraw)
    path = tmp_path / "sample.fab.svg"

    generation_path = write_fab_drawing(
        fake_entry(),
        [
            fake_shape(
                "stud",
                {"x": [0.0, 1.5], "y": [0.0, 5.5], "z": [0.0, 92.625]},
                volume=764.15625,
            )
        ],
        doc=object(),
        out_path=path,
    )

    assert generation_path == "projection"
    text = path.read_text(encoding="utf-8")
    assert "fab_drawing_path=projection" in text
    ET.fromstring(text)


def test_write_fab_drawing_accepts_and_stamps_techdraw(monkeypatch, tmp_path):
    def write_svg(entry, doc, out_path):
        out_path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>',
            encoding="utf-8",
        )

    monkeypatch.setattr("libtools.fab_drawing._write_techdraw_svg", write_svg)
    path = tmp_path / "sample.fab.svg"

    generation_path = write_fab_drawing(fake_entry(), [], doc=object(), out_path=path)

    assert generation_path == "techdraw"
    assert "fab_drawing_path=techdraw" in path.read_text(encoding="utf-8")

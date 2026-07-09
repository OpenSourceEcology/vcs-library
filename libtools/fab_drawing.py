from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path

from libtools.bom import BomLine, group_shapes
from libtools.geometry_checks import ShapeInfo


PAGE_WIDTH = 1100.0
PAGE_HEIGHT = 850.0
VIEW_BOXES = {
    "front": (70.0, 100.0, 520.0, 430.0),
    "side": (650.0, 100.0, 380.0, 430.0),
}


@dataclass(frozen=True)
class ProjectedPolygon:
    name: str
    points: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class ViewLayout:
    polygons: tuple[ProjectedPolygon, ...]
    scale: float
    offset: tuple[float, float]
    model_bbox: tuple[float, float, float, float]
    view_box: tuple[float, float, float, float]


def write_fab_drawing(entry, shapes: list[ShapeInfo], doc, out_path: Path) -> str:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_techdraw_svg(entry, doc, out_path)
        _stamp_svg(out_path, "techdraw")
        return "techdraw"
    except Exception as exc:
        fallback_svg = assemble_fallback_svg(entry, shapes, diagnostics=f"TechDraw unavailable: {exc}")
        out_path.write_text(fallback_svg, encoding="utf-8")
        return "projection"


def assemble_fallback_svg(entry, shapes: list[ShapeInfo], note: str = "", diagnostics: str = "") -> str:
    exterior_face = entry.meta.get("interface", {}).get("exterior_face", "-y")
    front_axis = _projection_axis(exterior_face)
    side_axis = "x" if front_axis != "x" else "y"
    front = layout_view(project_bboxes(shapes, front_axis), VIEW_BOXES["front"])
    side = layout_view(project_bboxes(shapes, side_axis), VIEW_BOXES["side"])
    bom_lines = group_shapes(shapes)
    dims = _overall_dimensions(shapes)

    body = "\n".join(
        [
            '<g id="views">',
            _render_view("Front", front),
            _render_view("Side", side),
            "</g>",
            _render_dimensions(dims),
            _render_bom_table(bom_lines),
            f'<text x="70" y="805" class="small">ORTHOGRAPHIC PROJECTION — NOT TO SCALE</text>',
            f'<text x="380" y="805" class="small">{escape(note)}</text>' if note else "",
        ]
    )
    template = _template_text()
    path_comment = "fab_drawing_path=projection"
    if diagnostics:
        path_comment += " " + escape(diagnostics)
    return template.replace("<!-- SLOT_GENERATION_PATH -->", f"<!-- {path_comment} -->").replace(
        "<!-- FAB_CONTENT -->", body
    )


def project_bboxes(shapes: list[ShapeInfo], axis: str) -> list[ProjectedPolygon]:
    x_axis, y_axis = _view_axes(axis)
    polygons = []
    for shape in shapes:
        bbox = shape.bbox_in
        xmin, xmax = bbox[x_axis]
        ymin, ymax = bbox[y_axis]
        polygons.append(
            ProjectedPolygon(
                name=shape.name,
                points=((xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)),
            )
        )
    return polygons


def layout_view(
    polygons: list[ProjectedPolygon], view_box: tuple[float, float, float, float], padding: float = 24.0
) -> ViewLayout:
    if not polygons:
        return ViewLayout(tuple(), 1.0, (view_box[0], view_box[1]), (0.0, 0.0, 0.0, 0.0), view_box)

    xs = [point[0] for polygon in polygons for point in polygon.points]
    ys = [point[1] for polygon in polygons for point in polygon.points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    model_w = max(max_x - min_x, 0.001)
    model_h = max(max_y - min_y, 0.001)
    box_x, box_y, box_w, box_h = view_box
    scale = min((box_w - 2 * padding) / model_w, (box_h - 2 * padding) / model_h)
    offset_x = box_x + (box_w - model_w * scale) / 2 - min_x * scale
    offset_y = box_y + (box_h + model_h * scale) / 2 + min_y * scale
    return ViewLayout(tuple(polygons), scale, (offset_x, offset_y), (min_x, min_y, max_x, max_y), view_box)


def transform_point(point: tuple[float, float], layout: ViewLayout) -> tuple[float, float]:
    x, y = point
    return (layout.offset[0] + x * layout.scale, layout.offset[1] - y * layout.scale)


def _write_techdraw_svg(entry, doc, out_path: Path) -> None:
    import FreeCAD as App
    import TechDraw

    template_path = Path(__file__).resolve().parent / "templates" / "fab_page.svg"
    solids = [
        obj
        for obj in doc.Objects
        if getattr(getattr(obj, "Shape", None), "Solids", None)
    ]
    if not solids:
        raise RuntimeError("no solids for TechDraw export")

    page = doc.addObject("TechDraw::DrawPage", f"{entry.id}_Fab_Page")
    page.Template = doc.addObject("TechDraw::DrawSVGTemplate", f"{entry.id}_Fab_Template")
    page.Template.Template = str(template_path)
    front = doc.addObject("TechDraw::DrawViewPart", f"{entry.id}_Front_View")
    front.Source = solids
    front.Direction = _techdraw_direction(entry.meta.get("interface", {}).get("exterior_face", "-y"), App)
    front.X = 330
    front.Y = 320
    front.ScaleType = "Automatic"
    side = doc.addObject("TechDraw::DrawViewPart", f"{entry.id}_Side_View")
    side.Source = solids
    side.Direction = App.Vector(1, 0, 0)
    side.X = 825
    side.Y = 320
    side.ScaleType = "Automatic"
    page.addView(front)
    page.addView(side)
    doc.recompute()
    try:
        import TechDrawGui

        TechDrawGui.exportPageAsSvg(page, str(out_path))
    except Exception:
        TechDraw.writeDXFPage(page, str(out_path))
    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise RuntimeError("TechDraw export produced no output")
    text = out_path.read_text(encoding="utf-8", errors="ignore").lstrip()
    if "<svg" not in text[:500] and "<?xml" not in text[:100]:
        raise RuntimeError("TechDraw export did not produce SVG")


def _stamp_svg(path: Path, generation_path: str) -> None:
    text = path.read_text(encoding="utf-8")
    comment = f"<!-- fab_drawing_path={generation_path} -->\n"
    if "<svg" in text:
        insert_at = text.find(">", text.find("<svg")) + 1
        text = text[:insert_at] + "\n" + comment + text[insert_at:]
    else:
        text = comment + text
    path.write_text(text, encoding="utf-8")


def _render_view(title: str, layout: ViewLayout) -> str:
    box_x, box_y, box_w, box_h = layout.view_box
    parts = [
        f'<g id="{title.lower()}-view">',
        f'<text x="{box_x}" y="{box_y - 24}" class="label">{title}</text>',
        f'<rect x="{box_x}" y="{box_y}" width="{box_w}" height="{box_h}" class="view-frame"/>',
    ]
    for index, polygon in enumerate(layout.polygons):
        points = " ".join(
            f"{x:.2f},{y:.2f}" for x, y in (transform_point(point, layout) for point in polygon.points)
        )
        shade = 235 - (index % 5) * 18
        parts.append(
            f'<polygon points="{points}" fill="rgb({shade},{shade},{shade})" class="member">'
            f"<title>{escape(polygon.name)}</title></polygon>"
        )
    parts.append("</g>")
    return "\n".join(parts)


def _render_dimensions(dims: tuple[float, float, float]) -> str:
    width, depth, height = dims
    return (
        '<g id="overall-dimensions">'
        '<text x="70" y="580" class="label">Overall dimensions</text>'
        f'<text x="70" y="610" class="body">W {width:.2f} in   D {depth:.2f} in   H {height:.2f} in</text>'
        "</g>"
    )


def _render_bom_table(lines: list[BomLine]) -> str:
    rows = [
        '<g id="bom-table">',
        '<text x="650" y="580" class="label">BOM cut table</text>',
        '<text x="650" y="610" class="small">Qty</text>',
        '<text x="710" y="610" class="small">Description</text>',
        '<text x="930" y="610" class="small">Length</text>',
    ]
    for idx, line in enumerate(lines[:8]):
        y = 638 + idx * 24
        cut = "" if line.cut_length_in is None else f'{line.cut_length_in:.2f}"'
        rows.extend(
            [
                f'<text x="650" y="{y}" class="body">{line.count}</text>',
                f'<text x="710" y="{y}" class="body">{escape(line.description)}</text>',
                f'<text x="930" y="{y}" class="body">{cut}</text>',
            ]
        )
    rows.append("</g>")
    return "\n".join(rows)


def _overall_dimensions(shapes: list[ShapeInfo]) -> tuple[float, float, float]:
    if not shapes:
        return (0.0, 0.0, 0.0)
    return tuple(
        max(shape.bbox_in[axis][1] for shape in shapes) - min(shape.bbox_in[axis][0] for shape in shapes)
        for axis in ("x", "y", "z")
    )


def _projection_axis(face: str) -> str:
    return face[-1] if face in {"+x", "-x", "+y", "-y"} else "y"


def _view_axes(axis: str) -> tuple[str, str]:
    if axis == "x":
        return ("y", "z")
    if axis == "y":
        return ("x", "z")
    return ("x", "y")


def _techdraw_direction(face: str, app_module):
    if face == "+x":
        return app_module.Vector(1, 0, 0)
    if face == "-x":
        return app_module.Vector(-1, 0, 0)
    if face == "+y":
        return app_module.Vector(0, 1, 0)
    return app_module.Vector(0, -1, 0)


def _template_text() -> str:
    return (Path(__file__).resolve().parent / "templates" / "fab_page.svg").read_text(encoding="utf-8")

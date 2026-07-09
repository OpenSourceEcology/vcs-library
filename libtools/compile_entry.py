from __future__ import annotations

import importlib.util
import os
import sys
import traceback
from pathlib import Path
from types import ModuleType

# freecadcmd executes this file as a script with an embedded interpreter that
# ignores PYTHONPATH, so the package parent must be put on sys.path here.
_PACKAGE_PARENT = str(Path(__file__).resolve().parent.parent)
if _PACKAGE_PARENT not in sys.path:
    sys.path.insert(0, _PACKAGE_PARENT)

from libtools.geometry_checks import ShapeInfo
from libtools.output_validator import failure_report, validate_output
from libtools.registry import Entry, discover, load_schema
from libtools.report import write_report


_MM_PER_IN = 25.4


def extract_shapes(doc) -> tuple[list[ShapeInfo], callable]:
    live_shapes = {}
    shapes: list[ShapeInfo] = []

    for obj in doc.Objects:
        shape = getattr(obj, "Shape", None)
        solids = getattr(shape, "Solids", None) if shape is not None else None
        if shape is None or not solids:
            continue

        name = getattr(obj, "Label", None) or getattr(obj, "Name", "")
        live_shapes[name] = shape
        bbox = shape.BoundBox
        shapes.append(
            ShapeInfo(
                name=name,
                valid=bool(shape.isValid() and solids),
                closed=bool(shape.isClosed()),
                volume_in3=shape.Volume / (_MM_PER_IN**3),
                bbox_in={
                    "x": [bbox.XMin / _MM_PER_IN, bbox.XMax / _MM_PER_IN],
                    "y": [bbox.YMin / _MM_PER_IN, bbox.YMax / _MM_PER_IN],
                    "z": [bbox.ZMin / _MM_PER_IN, bbox.ZMax / _MM_PER_IN],
                },
            )
        )

    def common_volume_fn(a: ShapeInfo, b: ShapeInfo) -> float:
        return live_shapes[a.name].common(live_shapes[b.name]).Volume / (_MM_PER_IN**3)

    return shapes, common_volume_fn


def run(root: str, entry_id: str, out_dir: str, reports_dir: str) -> int:
    entry: Entry | None = None
    try:
        root_path = Path(root)
        out_path = Path(out_dir)
        reports_path = Path(reports_dir)
        entries = discover(root_path)
        entries_by_id = {candidate.id: candidate for candidate in entries}
        entry = entries_by_id[entry_id]

        schema = load_schema(entry)
        compiler = _load_compiler(entry.compiler_path)

        import FreeCAD as App

        doc = App.newDocument(schema["document_name"])
        compiler.compile(schema, doc)
        doc.recompute()

        out_path.mkdir(parents=True, exist_ok=True)
        doc.saveAs(str(out_path / f"{entry.id}.FCStd"))

        shapes, common_volume_fn = extract_shapes(doc)
        report = validate_output(entry, shapes, common_volume_fn)
        write_report(report, reports_path)

        if report.passed:
            print(f"PASS {entry.id}")
        else:
            failed_count = sum(1 for check in report.checks if not check.passed)
            print(f"FAIL {entry.id} ({failed_count} failed checks)")

        return 0 if report.passed or entry.status == "wip" else 1
    except Exception:
        detail = traceback.format_exc()
        report_key: Entry | tuple[str, str, str]
        report_key = entry if entry is not None else (entry_id, "unknown", "active")
        report = failure_report(report_key, detail)
        write_report(report, Path(reports_dir))
        print(f"FAIL {entry_id} (compile failed)")
        status = entry.status if entry is not None else "active"
        return 0 if status == "wip" else 1


def main() -> int:
    return run(
        os.environ["LIBTOOLS_ROOT"],
        os.environ["LIBTOOLS_ENTRY"],
        os.environ["LIBTOOLS_OUT"],
        os.environ["LIBTOOLS_REPORTS"],
    )


def _load_compiler(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"_libtools_compiler_{path.parent.name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load compiler from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from libtools.code_validator import validate_code
from libtools import compile_entry
from libtools.export_json import export_entry
from libtools.registry import RegistryError, discover
from libtools.report import write_report


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        return args.func(args)
    except RegistryError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 2


def validate_code_main(argv: Sequence[str] | None = None) -> int:
    return main(["validate-code", *(sys.argv[1:] if argv is None else argv)])


def validate_output_main(argv: Sequence[str] | None = None) -> int:
    return main(["validate-output", *(sys.argv[1:] if argv is None else argv)])


def generate_slots_main(argv: Sequence[str] | None = None) -> int:
    return main(["generate-slots", *(sys.argv[1:] if argv is None else argv)])


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="libtools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_code_parser = subparsers.add_parser("validate-code")
    validate_code_parser.add_argument("--root", type=Path, default=Path("."))
    validate_code_parser.add_argument("--reports-dir", type=Path)
    validate_code_parser.add_argument("--all", action="store_true")
    validate_code_parser.add_argument("ids", nargs="*")
    validate_code_parser.set_defaults(func=_validate_code_command)

    validate_output_parser = subparsers.add_parser("validate-output")
    validate_output_parser.add_argument("--root", type=Path, default=Path("."))
    validate_output_parser.add_argument("--reports-dir", type=Path)
    validate_output_parser.add_argument("--out-dir", type=Path)
    validate_output_parser.add_argument("--all", action="store_true")
    validate_output_parser.add_argument("ids", nargs="*")
    validate_output_parser.set_defaults(func=_validate_output_command)

    generate_slots_parser = subparsers.add_parser("generate-slots")
    generate_slots_parser.add_argument("--root", type=Path, default=Path("."))
    generate_slots_parser.add_argument("--reports-dir", type=Path)
    generate_slots_parser.add_argument("--out-dir", type=Path, default=Path("slots"))
    generate_slots_parser.add_argument("--all", action="store_true")
    generate_slots_parser.add_argument("ids", nargs="*")
    generate_slots_parser.set_defaults(func=_generate_slots_command)

    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("--root", type=Path, default=Path("."))
    compile_parser.add_argument("--out-dir", type=Path)
    compile_parser.add_argument("id")
    compile_parser.set_defaults(func=_compile_command)

    export_json_parser = subparsers.add_parser("export-json")
    export_json_parser.add_argument("--root", type=Path, default=Path("."))
    export_json_parser.add_argument("--out-dir", type=Path)
    export_json_parser.add_argument("--all", action="store_true")
    export_json_parser.add_argument("ids", nargs="*")
    export_json_parser.set_defaults(func=_export_json_command)

    return parser


def _validate_code_command(args: argparse.Namespace) -> int:
    selected = _select_entries(args.root, args.all, args.ids)
    if isinstance(selected, int):
        return selected
    reports_dir = args.reports_dir if args.reports_dir is not None else args.root / "reports"

    active_failed = False
    for entry in selected:
        report = validate_code(entry)
        write_report(report, reports_dir)
        failed_count = sum(1 for check in report.checks if not check.passed)
        if report.passed:
            print(f"PASS {entry.id}")
        elif entry.status == "wip":
            print(f"WIP-FAIL {entry.id} ({failed_count} failed checks; report-only)")
        else:
            active_failed = True
            print(f"FAIL {entry.id} ({failed_count} failed checks)")

    return 1 if active_failed else 0


def _validate_output_command(args: argparse.Namespace) -> int:
    selected = _select_entries(args.root, args.all, args.ids)
    if isinstance(selected, int):
        return selected

    reports_dir = args.reports_dir if args.reports_dir is not None else args.root / "reports"
    out_dir = args.out_dir if args.out_dir is not None else args.root / "out"

    active_failed = False
    for entry in selected:
        try:
            _run_driver(entry, args.root, out_dir, reports_dir)
        except FileNotFoundError:
            print(
                f"freecadcmd not found: {os.environ.get('FREECADCMD', 'freecadcmd')}",
                file=sys.stderr,
            )
            return 2

        report_path = reports_dir / f"{entry.id}.json"
        if not report_path.is_file():
            print(f"wrote no report: {entry.id}", file=sys.stderr)
            if entry.status != "wip":
                active_failed = True
            continue

        report = json.loads(report_path.read_text(encoding="utf-8"))
        failed_count = sum(1 for check in report.get("checks", []) if not check.get("passed"))
        if report.get("passed"):
            print(f"PASS {entry.id}")
        elif entry.status == "wip":
            print(f"WIP-FAIL {entry.id} ({failed_count} failed checks; report-only)")
        else:
            active_failed = True
            print(f"FAIL {entry.id} ({failed_count} failed checks)")

    return 1 if active_failed else 0


def _generate_slots_command(args: argparse.Namespace) -> int:
    selected = _select_entries(args.root, args.all, args.ids)
    if isinstance(selected, int):
        return selected

    reports_dir = args.reports_dir if args.reports_dir is not None else args.root / "reports"
    slots_dir = args.out_dir if args.out_dir.is_absolute() else args.root / args.out_dir
    cad_out_dir = args.root / "out"

    active_failed = False
    for entry in selected:
        try:
            _run_driver(entry, args.root, cad_out_dir, reports_dir, slots=True, slots_out_dir=slots_dir)
        except FileNotFoundError:
            print(
                f"freecadcmd not found: {os.environ.get('FREECADCMD', 'freecadcmd')}",
                file=sys.stderr,
            )
            return 2

        report_path = reports_dir / f"{entry.id}.json"
        if not report_path.is_file():
            print(f"wrote no report: {entry.id}", file=sys.stderr)
            if entry.status != "wip":
                active_failed = True
            continue

        report = json.loads(report_path.read_text(encoding="utf-8"))
        failed_count = sum(1 for check in report.get("checks", []) if not check.get("passed"))
        if report.get("passed"):
            bom_path = slots_dir / f"{entry.id}.bom.csv"
            fab_path = slots_dir / f"{entry.id}.fab.svg"
            if bom_path.is_file() and fab_path.is_file():
                print(f"PASS {entry.id}")
            else:
                print(f"missing slot output: {entry.id}", file=sys.stderr)
                if entry.status != "wip":
                    active_failed = True
        elif entry.status == "wip":
            print(f"WIP-FAIL {entry.id} ({failed_count} failed checks; report-only)")
        else:
            active_failed = True
            print(f"FAIL {entry.id} ({failed_count} failed checks)")

    return 1 if active_failed else 0


def _compile_command(args: argparse.Namespace) -> int:
    selected = _select_entries(args.root, False, [args.id])
    if isinstance(selected, int):
        return selected

    out_dir = args.out_dir if args.out_dir is not None else args.root / "out"
    reports_dir = args.root / "reports"
    try:
        return _run_driver(selected[0], args.root, out_dir, reports_dir)
    except FileNotFoundError:
        print(
            f"freecadcmd not found: {os.environ.get('FREECADCMD', 'freecadcmd')}",
            file=sys.stderr,
        )
        return 2


def _export_json_command(args: argparse.Namespace) -> int:
    selected = _select_entries(args.root, args.all, args.ids)
    if isinstance(selected, int):
        return selected

    out_dir = args.out_dir if args.out_dir is not None else args.root / "exported"
    out_dir.mkdir(parents=True, exist_ok=True)

    for entry in selected:
        path = out_dir / f"{entry.id}.json"
        path.write_text(
            json.dumps(export_entry(entry), indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        print(f"EXPORT {entry.id} {path}")

    return 0


def _select_entries(root: Path, all_entries: bool, ids: Sequence[str]):
    if all_entries and ids:
        print("cannot combine --all with explicit IDs", file=sys.stderr)
        return 2
    if not all_entries and not ids:
        print("must pass --all or at least one ID", file=sys.stderr)
        return 2

    if not root.is_dir():
        print(f"bad root: {root}", file=sys.stderr)
        return 2
    if not (root / "library").is_dir():
        print(f"bad root: {root} has no library directory", file=sys.stderr)
        return 2

    entries = discover(root)
    entries_by_id = {entry.id: entry for entry in entries}

    if all_entries:
        return entries

    unknown = [entry_id for entry_id in ids if entry_id not in entries_by_id]
    if unknown:
        print(f"unknown id: {unknown[0]}", file=sys.stderr)
        return 2
    return [entries_by_id[entry_id] for entry_id in ids]


# Env vars that make freecadcmd's embedded interpreter resolve another
# Python's stdlib (observed as "No module named 'math'" under CI toolcache
# Pythons). The driver child must not inherit them.
_HOSTILE_ENV_VARS = (
    "PYTHONHOME",
    "PYTHONSTARTUP",
    "pythonLocation",
    "Python_ROOT_DIR",
    "Python2_ROOT_DIR",
    "Python3_ROOT_DIR",
    "LD_LIBRARY_PATH",
    "DYLD_LIBRARY_PATH",
    "VIRTUAL_ENV",
)


def _driver_env(
    entry,
    root: Path,
    out_dir: Path,
    reports_dir: Path,
    *,
    slots: bool = False,
    slots_out_dir: Path | None = None,
) -> dict:
    env = os.environ.copy()
    for name in _HOSTILE_ENV_VARS:
        env.pop(name, None)

    # freecadcmd must import libtools: put the package's parent directory and
    # the library root on PYTHONPATH, nothing else.
    package_parent = Path(compile_entry.__file__).resolve().parent.parent
    pythonpath_parts = [str(package_parent), str(Path(root).resolve())]
    env.update(
        {
            "LIBTOOLS_ROOT": str(root),
            "LIBTOOLS_ENTRY": entry.id,
            "LIBTOOLS_OUT": str(out_dir),
            "LIBTOOLS_REPORTS": str(reports_dir),
            "PYTHONPATH": os.pathsep.join(dict.fromkeys(pythonpath_parts)),
        }
    )
    if slots:
        env["LIBTOOLS_SLOTS"] = "1"
        env["LIBTOOLS_SLOTS_OUT"] = str(slots_out_dir if slots_out_dir is not None else out_dir)
    return env


def _run_driver(
    entry,
    root: Path,
    out_dir: Path,
    reports_dir: Path,
    *,
    slots: bool = False,
    slots_out_dir: Path | None = None,
) -> int:
    freecadcmd = os.environ.get("FREECADCMD", "freecadcmd")
    driver_path = Path(compile_entry.__file__)
    env = _driver_env(entry, root, out_dir, reports_dir, slots=slots, slots_out_dir=slots_out_dir)
    result = subprocess.run([freecadcmd, str(driver_path)], env=env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

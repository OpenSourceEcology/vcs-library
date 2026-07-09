from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from libtools.code_validator import validate_code
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="libtools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_code_parser = subparsers.add_parser("validate-code")
    validate_code_parser.add_argument("--root", type=Path, default=Path("."))
    validate_code_parser.add_argument("--reports-dir", type=Path)
    validate_code_parser.add_argument("--all", action="store_true")
    validate_code_parser.add_argument("ids", nargs="*")
    validate_code_parser.set_defaults(func=_validate_code_command)

    return parser


def _validate_code_command(args: argparse.Namespace) -> int:
    if args.all and args.ids:
        print("cannot combine --all with explicit IDs", file=sys.stderr)
        return 2
    if not args.all and not args.ids:
        print("must pass --all or at least one ID", file=sys.stderr)
        return 2

    root = args.root
    if not root.is_dir():
        print(f"bad root: {root}", file=sys.stderr)
        return 2
    if not (root / "library").is_dir():
        print(f"bad root: {root} has no library directory", file=sys.stderr)
        return 2

    reports_dir = args.reports_dir if args.reports_dir is not None else root / "reports"
    entries = discover(root)
    entries_by_id = {entry.id: entry for entry in entries}

    if args.all:
        selected = entries
    else:
        unknown = [entry_id for entry_id in args.ids if entry_id not in entries_by_id]
        if unknown:
            print(f"unknown id: {unknown[0]}", file=sys.stderr)
            return 2
        selected = [entries_by_id[entry_id] for entry_id in args.ids]

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


if __name__ == "__main__":
    raise SystemExit(main())

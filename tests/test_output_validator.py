import json
from pathlib import Path
from shutil import copytree

import yaml

from libtools.cli import main
from libtools.geometry_checks import ShapeInfo
from libtools.output_validator import failure_report, validate_output
from libtools.registry import discover
from libtools.report import Check, Report, write_report


FIXTURE_ROOT = Path(__file__).parent / "fixtures"


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "fixture"
    copytree(FIXTURE_ROOT / "library", root / "library")
    return root


def fake_shape(name, bbox_in, valid=True, closed=True, volume_in3=1.0):
    return ShapeInfo(
        name=name,
        valid=valid,
        closed=closed,
        volume_in3=volume_in3,
        bbox_in=bbox_in,
    )


def box_common_volume(a, b):
    volume = 1.0
    for axis in ("x", "y", "z"):
        low = max(a.bbox_in[axis][0], b.bbox_in[axis][0])
        high = min(a.bbox_in[axis][1], b.bbox_in[axis][1])
        volume *= max(0.0, high - low)
    return volume


def good_entry():
    return next(entry for entry in discover(FIXTURE_ROOT) if entry.id == "good_entry")


def test_validate_output_clean_shapes_passes_with_expected_check_names():
    entry = good_entry()
    shapes = [
        fake_shape("left_box", {"x": [0.0, 11.0], "y": [0.0, 12.0], "z": [0.0, 1.5]}),
        fake_shape("right_box", {"x": [13.0, 24.0], "y": [0.0, 12.0], "z": [0.0, 1.5]}),
    ]

    report = validate_output(entry, shapes, box_common_volume)

    assert report.passed is True
    assert [check.name for check in report.checks] == ["compiles", "completeness", "overlap", "fit"]


def test_validate_output_overlapping_pair_fails_overlap_only():
    entry = good_entry()
    shapes = [
        fake_shape("left_box", {"x": [0.0, 13.0], "y": [0.0, 12.0], "z": [0.0, 1.5]}),
        fake_shape("right_box", {"x": [12.0, 24.0], "y": [0.0, 12.0], "z": [0.0, 1.5]}),
    ]

    report = validate_output(entry, shapes, box_common_volume)
    checks = {check.name: check for check in report.checks}

    assert report.passed is False
    assert checks["compiles"].passed is True
    assert checks["completeness"].passed is True
    assert checks["overlap"].passed is False
    assert checks["fit"].passed is True


def test_failure_report_has_single_failed_compiles_check_with_detail():
    report = failure_report(good_entry(), "traceback detail")

    assert report.id == "good_entry"
    assert report.tier == "output"
    assert report.passed is False
    assert len(report.checks) == 1
    assert report.checks[0].name == "compiles"
    assert report.checks[0].passed is False
    assert "traceback detail" in report.checks[0].detail


def write_canned_report(reports_dir: Path, entry, passed: bool):
    report = Report(
        id=entry.id,
        layer=entry.layer,
        status=entry.status,
        tier="output",
        checks=[Check("compiles", passed, "" if passed else "failed")],
    )
    write_report(report, reports_dir)


def test_cli_validate_output_passes_with_canned_report(monkeypatch, capsys, tmp_path):
    reports_dir = tmp_path / "reports"

    def run_driver(entry, root, out_dir, reports_dir):
        write_canned_report(reports_dir, entry, True)
        return 0

    monkeypatch.setattr("libtools.cli._run_driver", run_driver)

    code = main(
        [
            "validate-output",
            "--root",
            str(FIXTURE_ROOT),
            "--reports-dir",
            str(reports_dir),
            "good_entry",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert "PASS good_entry" in captured.out


def test_cli_validate_output_active_failure_returns_one(monkeypatch, capsys, tmp_path):
    reports_dir = tmp_path / "reports"

    def run_driver(entry, root, out_dir, reports_dir):
        write_canned_report(reports_dir, entry, False)
        return 1

    monkeypatch.setattr("libtools.cli._run_driver", run_driver)

    code = main(
        [
            "validate-output",
            "--root",
            str(FIXTURE_ROOT),
            "--reports-dir",
            str(reports_dir),
            "bad_entry",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "FAIL bad_entry" in captured.out


def test_cli_validate_output_wip_failure_is_report_only(monkeypatch, capsys, tmp_path):
    root = copy_fixture(tmp_path)
    meta_path = root / "library" / "parts" / "bad_entry" / "meta.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta["status"] = "wip"
    meta_path.write_text(yaml.safe_dump(meta), encoding="utf-8")

    def run_driver(entry, root, out_dir, reports_dir):
        write_canned_report(reports_dir, entry, False)
        return 1

    monkeypatch.setattr("libtools.cli._run_driver", run_driver)

    code = main(["validate-output", "--root", str(root), "bad_entry"])

    captured = capsys.readouterr()
    assert code == 0
    assert "WIP-FAIL bad_entry" in captured.out


def test_cli_validate_output_missing_report_is_active_failure(monkeypatch, capsys, tmp_path):
    def run_driver(entry, root, out_dir, reports_dir):
        return 0

    monkeypatch.setattr("libtools.cli._run_driver", run_driver)

    code = main(["validate-output", "--root", str(FIXTURE_ROOT), "good_entry"])

    captured = capsys.readouterr()
    assert code == 1
    assert "wrote no report: good_entry" in captured.err


def test_cli_validate_output_missing_freecadcmd_is_usage_error(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("FREECADCMD", str(tmp_path / "missing-freecadcmd"))

    code = main(["validate-output", "--root", str(FIXTURE_ROOT), "good_entry"])

    captured = capsys.readouterr()
    assert code == 2
    assert "freecadcmd not found" in captured.err

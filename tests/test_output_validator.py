import json
import os
from pathlib import Path
from shutil import copytree

import yaml

import libtools.cli
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


def test_driver_env_strips_hostile_vars_and_pins_pythonpath(monkeypatch, tmp_path):
    from libtools.cli import _driver_env

    monkeypatch.setenv("PYTHONHOME", "/opt/hostedtoolcache/Python/3.12.0")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/opt/hostedtoolcache/Python/3.12.0/lib")
    monkeypatch.setenv("pythonLocation", "/opt/hostedtoolcache/Python/3.12.0")
    monkeypatch.setenv("PYTHONPATH", "/somewhere/else")

    entry = next(e for e in discover(FIXTURE_ROOT) if e.id == "good_entry")
    env = _driver_env(entry, FIXTURE_ROOT, tmp_path / "out", tmp_path / "reports")

    assert "PYTHONHOME" not in env
    assert "LD_LIBRARY_PATH" not in env
    assert "pythonLocation" not in env
    assert "/somewhere/else" not in env["PYTHONPATH"]
    assert env["LIBTOOLS_ENTRY"] == "good_entry"
    # libtools must stay importable inside the freecadcmd child.
    package_parent = Path(libtools.cli.__file__).resolve().parent.parent
    assert str(package_parent) in env["PYTHONPATH"].split(os.pathsep)


def test_driver_env_sets_slot_generation_contract(tmp_path):
    from libtools.cli import _driver_env

    entry = next(e for e in discover(FIXTURE_ROOT) if e.id == "good_entry")
    env = _driver_env(
        entry,
        FIXTURE_ROOT,
        tmp_path / "out",
        tmp_path / "reports",
        slots=True,
        slots_out_dir=tmp_path / "slots",
    )

    assert env["LIBTOOLS_SLOTS"] == "1"
    assert env["LIBTOOLS_OUT"] == str(tmp_path / "out")
    assert env["LIBTOOLS_SLOTS_OUT"] == str(tmp_path / "slots")


def test_cli_generate_slots_passes_when_outputs_exist(monkeypatch, capsys, tmp_path):
    reports_dir = tmp_path / "reports"
    slots_dir = tmp_path / "slots"

    def run_driver(entry, root, out_dir, reports_dir, *, slots=False, slots_out_dir=None):
        assert slots is True
        assert out_dir == FIXTURE_ROOT / "out"
        assert slots_out_dir == slots_dir
        write_canned_report(reports_dir, entry, True)
        slots_out_dir.mkdir(parents=True, exist_ok=True)
        (slots_out_dir / f"{entry.id}.bom.csv").write_text("count,description\n", encoding="utf-8")
        (slots_out_dir / f"{entry.id}.fab.svg").write_text("<svg></svg>", encoding="utf-8")
        return 0

    monkeypatch.setattr("libtools.cli._run_driver", run_driver)

    code = main(
        [
            "generate-slots",
            "--root",
            str(FIXTURE_ROOT),
            "--reports-dir",
            str(reports_dir),
            "--out-dir",
            str(slots_dir),
            "good_entry",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert "PASS good_entry" in captured.out


def test_cli_generate_slots_active_compile_failure_returns_one(monkeypatch, capsys, tmp_path):
    reports_dir = tmp_path / "reports"

    def run_driver(entry, root, out_dir, reports_dir, *, slots=False, slots_out_dir=None):
        write_canned_report(reports_dir, entry, False)
        return 1

    monkeypatch.setattr("libtools.cli._run_driver", run_driver)

    code = main(
        [
            "generate-slots",
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


def test_cli_generate_slots_wip_failure_is_report_only(monkeypatch, capsys, tmp_path):
    root = copy_fixture(tmp_path)
    meta_path = root / "library" / "parts" / "bad_entry" / "meta.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta["status"] = "wip"
    meta_path.write_text(yaml.safe_dump(meta), encoding="utf-8")

    def run_driver(entry, root, out_dir, reports_dir, *, slots=False, slots_out_dir=None):
        write_canned_report(reports_dir, entry, False)
        return 1

    monkeypatch.setattr("libtools.cli._run_driver", run_driver)

    code = main(["generate-slots", "--root", str(root), "bad_entry"])

    captured = capsys.readouterr()
    assert code == 0
    assert "WIP-FAIL bad_entry" in captured.out


def test_cli_generate_slots_missing_freecadcmd_is_usage_error(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("FREECADCMD", str(tmp_path / "missing-freecadcmd"))

    code = main(["generate-slots", "--root", str(FIXTURE_ROOT), "good_entry"])

    captured = capsys.readouterr()
    assert code == 2
    assert "freecadcmd not found" in captured.err

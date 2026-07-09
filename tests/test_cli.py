import json
from pathlib import Path
from shutil import copytree

from libtools.cli import main


FIXTURE_ROOT = Path(__file__).parent / "fixtures"


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "fixture"
    copytree(FIXTURE_ROOT / "library", root / "library")
    return root


def test_validate_code_all_reports_active_failures(capsys, tmp_path):
    reports_dir = tmp_path / "reports"

    code = main(
        [
            "validate-code",
            "--root",
            str(FIXTURE_ROOT),
            "--reports-dir",
            str(reports_dir),
            "--all",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "PASS good_entry" in captured.out
    assert "FAIL bad_entry" in captured.out


def test_validate_code_wip_failures_are_report_only(capsys, tmp_path):
    root = copy_fixture(tmp_path)
    meta_path = root / "library" / "parts" / "bad_entry" / "meta.yaml"
    meta_path.write_text(
        meta_path.read_text(encoding="utf-8").replace("status: active", "status: wip"),
        encoding="utf-8",
    )

    code = main(["validate-code", "--root", str(root), "--all"])

    captured = capsys.readouterr()
    assert code == 0
    assert "WIP-FAIL bad_entry" in captured.out


def test_validate_code_unknown_id_is_usage_error(capsys):
    code = main(["validate-code", "--root", str(FIXTURE_ROOT), "missing_entry"])

    captured = capsys.readouterr()
    assert code == 2
    assert "unknown id: missing_entry" in captured.err


def test_validate_code_writes_documented_report_shape(tmp_path):
    root = copy_fixture(tmp_path)
    reports_dir = tmp_path / "reports"

    code = main(["validate-code", "--root", str(root), "--reports-dir", str(reports_dir), "--all"])

    assert code == 1
    good = json.loads((reports_dir / "good_entry.json").read_text(encoding="utf-8"))
    bad = json.loads((reports_dir / "bad_entry.json").read_text(encoding="utf-8"))

    assert set(good) == {"id", "layer", "status", "tier", "checks", "passed"}
    assert good["id"] == "good_entry"
    assert good["tier"] == "code"
    assert good["passed"] is True
    assert all(set(check) == {"name", "passed", "detail"} for check in good["checks"])
    assert bad["id"] == "bad_entry"
    assert bad["passed"] is False

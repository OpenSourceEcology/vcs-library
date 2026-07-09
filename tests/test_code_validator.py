from pathlib import Path
from shutil import copytree

from libtools.code_validator import validate_code
from libtools.registry import discover


FIXTURE_ROOT = Path(__file__).parent / "fixtures"
CHECK_NAMES = [
    "schema_data_only",
    "schema_required_fields",
    "unit_suffix_discipline",
    "param_admissibility",
    "compiler_contract",
    "meta_complete",
    "interface_consistent",
]


def entries_by_id(root: Path):
    return {entry.id: entry for entry in discover(root)}


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "fixture"
    copytree(FIXTURE_ROOT / "library", root / "library")
    return root


def test_good_entry_passes_all_code_checks():
    report = validate_code(entries_by_id(FIXTURE_ROOT)["good_entry"])

    assert report.passed is True
    assert [check.name for check in report.checks] == CHECK_NAMES
    assert all(check.passed for check in report.checks)
    assert report.id == "good_entry"
    assert report.layer == "part"
    assert report.status == "active"
    assert report.tier == "code"


def test_bad_entry_reports_expected_failures_and_keeps_independent_passes():
    report = validate_code(entries_by_id(FIXTURE_ROOT)["bad_entry"])

    failed = {check.name for check in report.checks if not check.passed}
    passed = {check.name for check in report.checks if check.passed}

    assert [check.name for check in report.checks] == CHECK_NAMES
    assert failed == {
        "schema_required_fields",
        "unit_suffix_discipline",
        "param_admissibility",
        "compiler_contract",
    }
    assert passed == {"schema_data_only", "meta_complete", "interface_consistent"}


def test_schema_load_failure_marks_schema_dependent_checks_not_loadable(tmp_path):
    root = copy_fixture(tmp_path)
    bad_schema = root / "library" / "parts" / "good_entry" / "schema.py"
    bad_schema.write_text(
        'SCHEMA = {"schema_name": UNDEFINED_NAME, "units": "in", "document_name": "x"}\n',
        encoding="utf-8",
    )

    report = validate_code(entries_by_id(root)["good_entry"])
    checks = {check.name: check for check in report.checks}

    assert checks["schema_data_only"].passed is True
    for name in ("schema_required_fields", "unit_suffix_discipline", "param_admissibility"):
        assert checks[name].passed is False
        assert checks[name].detail == "schema not loadable"

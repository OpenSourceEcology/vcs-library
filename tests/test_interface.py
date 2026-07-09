from pathlib import Path
from shutil import copytree

from libtools.code_validator import validate_code
from libtools.export_json import export_entry
from libtools.registry import discover


FIXTURE_ROOT = Path(__file__).parent / "fixtures"


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "fixture"
    copytree(FIXTURE_ROOT / "library", root / "library")
    return root


def entries_by_id(root: Path):
    return {entry.id: entry for entry in discover(root)}


def interface_check(root: Path, entry_id: str = "good_entry"):
    report = validate_code(entries_by_id(root)[entry_id])
    return {check.name: check for check in report.checks}["interface_consistent"]


def append_interface(root: Path, lines: list[str]) -> None:
    meta_path = root / "library" / "parts" / "good_entry" / "meta.yaml"
    meta_path.write_text(
        meta_path.read_text(encoding="utf-8") + "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def valid_interface_lines() -> list[str]:
    return [
        "interface:",
        "  system: test_system",
        "  role: wall",
        "  width_in: 24.0",
        "  depth_in: 12.0",
        "  height_in: 1.5",
        "  exterior_face: -y",
    ]


def test_absent_interface_passes_with_no_interface_detail():
    check = interface_check(FIXTURE_ROOT)

    assert check.passed is True
    assert check.detail == "no interface"


def test_valid_interface_passes_on_tmp_fixture_copy(tmp_path):
    root = copy_fixture(tmp_path)
    append_interface(root, valid_interface_lines())

    check = interface_check(root)

    assert check.passed is True
    assert check.detail == ""


def test_bad_role_fails_with_field_name(tmp_path):
    root = copy_fixture(tmp_path)
    lines = valid_interface_lines()
    lines[2] = "  role: porch"
    append_interface(root, lines)

    check = interface_check(root)

    assert check.passed is False
    assert "role" in check.detail


def test_negative_width_fails_with_field_name(tmp_path):
    root = copy_fixture(tmp_path)
    lines = valid_interface_lines()
    lines[3] = "  width_in: -1.0"
    append_interface(root, lines)

    check = interface_check(root)

    assert check.passed is False
    assert "width_in" in check.detail


def test_bogus_exterior_face_fails_with_field_name(tmp_path):
    root = copy_fixture(tmp_path)
    lines = valid_interface_lines()
    lines[6] = "  exterior_face: front"
    append_interface(root, lines)

    check = interface_check(root)

    assert check.passed is False
    assert "exterior_face" in check.detail


def test_width_wildly_off_envelope_fails_with_field_name(tmp_path):
    root = copy_fixture(tmp_path)
    lines = valid_interface_lines()
    lines[3] = "  width_in: 240.0"
    append_interface(root, lines)

    check = interface_check(root)

    assert check.passed is False
    assert "width_in" in check.detail


def test_export_json_includes_interface_when_present_and_null_when_absent(tmp_path):
    root = copy_fixture(tmp_path)
    append_interface(root, valid_interface_lines())
    entry = entries_by_id(root)["good_entry"]
    absent_entry = entries_by_id(FIXTURE_ROOT)["good_entry"]

    present = export_entry(entry)
    absent = export_entry(absent_entry)

    assert present["interface"] == {
        "system": "test_system",
        "role": "wall",
        "width_in": 24.0,
        "depth_in": 12.0,
        "height_in": 1.5,
        "exterior_face": "-y",
    }
    assert absent["interface"] is None

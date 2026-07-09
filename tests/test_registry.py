from pathlib import Path
from shutil import copytree

import pytest

from libtools.registry import RegistryError, discover, load_schema


FIXTURE_ROOT = Path(__file__).parent / "fixtures"


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "fixture"
    copytree(FIXTURE_ROOT / "library", root / "library")
    return root


def test_discover_finds_good_fixture_entry():
    entries = discover(FIXTURE_ROOT)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.id == "good_entry"
    assert entry.layer == "part"
    assert entry.status == "active"
    assert entry.path == FIXTURE_ROOT / "library" / "parts" / "good_entry"
    assert entry.schema_path == entry.path / "schema.py"
    assert entry.compiler_path == entry.path / "compiler.py"


def test_discover_raises_when_meta_id_mismatches_dir_name(tmp_path):
    root = copy_fixture(tmp_path)
    meta_path = root / "library" / "parts" / "good_entry" / "meta.yaml"
    meta_path.write_text(
        meta_path.read_text().replace("id: good_entry", "id: wrong_entry"),
        encoding="utf-8",
    )

    with pytest.raises(RegistryError, match="good_entry"):
        discover(root)


def test_discover_raises_when_meta_yaml_missing(tmp_path):
    root = copy_fixture(tmp_path)
    (root / "library" / "parts" / "good_entry" / "meta.yaml").unlink()

    with pytest.raises(RegistryError, match="meta.yaml"):
        discover(root)


def test_discover_raises_on_invalid_status_value(tmp_path):
    root = copy_fixture(tmp_path)
    meta_path = root / "library" / "parts" / "good_entry" / "meta.yaml"
    meta_path.write_text(
        meta_path.read_text().replace("status: active", "status: retired"),
        encoding="utf-8",
    )

    with pytest.raises(RegistryError, match="status"):
        discover(root)


def test_load_schema_returns_schema_dict():
    entry = discover(FIXTURE_ROOT)[0]

    schema = load_schema(entry)

    assert schema["schema_name"] == "Good_Entry"


def test_load_schema_raises_when_schema_missing(tmp_path):
    root = copy_fixture(tmp_path)
    schema_path = root / "library" / "parts" / "good_entry" / "schema.py"
    schema_path.write_text("NAME = 'Good_Entry'\n", encoding="utf-8")
    entry = discover(root)[0]

    with pytest.raises(RegistryError, match="SCHEMA"):
        load_schema(entry)

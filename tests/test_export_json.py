import json
from pathlib import Path
from shutil import copytree

from libtools.cli import main
from libtools.export_json import export_entry
from libtools.registry import discover, load_schema


FIXTURE_ROOT = Path(__file__).parent / "fixtures"


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "fixture"
    copytree(FIXTURE_ROOT / "library", root / "library")
    return root


def test_export_entry_has_canonical_shape_and_schema_values():
    entry = next(entry for entry in discover(FIXTURE_ROOT) if entry.id == "good_entry")

    exported = export_entry(entry)

    assert list(exported) == [
        "id",
        "layer",
        "title",
        "owner",
        "version",
        "status",
        "units",
        "schema",
        "provenance",
    ]
    assert exported["id"] == "good_entry"
    assert exported["units"] == "in"
    assert exported["schema"] == load_schema(entry)
    assert exported["provenance"] == {"author": "Test"}


def test_export_entry_converts_schema_tuples_to_lists(tmp_path):
    root = tmp_path / "library_root"
    entry_dir = root / "library" / "parts" / "tuple_entry"
    entry_dir.mkdir(parents=True)
    (entry_dir / "schema.py").write_text(
        "\n".join(
            [
                "SCHEMA = {",
                "    'schema_name': 'Tuple_Entry',",
                "    'units': 'mm',",
                "    'coords': (1, 2),",
                "    'nested': {'points': ((3, 4), (5, 6))},",
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (entry_dir / "compiler.py").write_text("def compile(params):\n    return []\n", encoding="utf-8")
    (entry_dir / "expect.yaml").write_text("{}\n", encoding="utf-8")
    (entry_dir / "meta.yaml").write_text(
        "\n".join(
            [
                "id: tuple_entry",
                "layer: part",
                "title: Tuple Entry",
                "owner: Test Owner",
                'version: "0.1.0"',
                "status: active",
                "provenance:",
                "  author: Test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    entry = next(entry for entry in discover(root) if entry.id == "tuple_entry")

    exported = export_entry(entry)

    assert exported["schema"]["coords"] == [1, 2]
    assert exported["schema"]["nested"]["points"] == [[3, 4], [5, 6]]


def test_cli_export_json_all_writes_loadable_files(tmp_path):
    root = copy_fixture(tmp_path)

    code = main(["export-json", "--root", str(root), "--all"])

    assert code == 0
    out_dir = root / "exported"
    exported_paths = sorted(out_dir.glob("*.json"))
    assert [path.name for path in exported_paths] == ["bad_entry.json", "good_entry.json"]
    for path in exported_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "id" in data
        assert "schema" in data


def test_cli_export_json_unknown_id_is_usage_error(capsys):
    code = main(["export-json", "--root", str(FIXTURE_ROOT), "missing_entry"])

    captured = capsys.readouterr()
    assert code == 2
    assert "unknown id: missing_entry" in captured.err

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class RegistryError(Exception):
    pass


@dataclass
class Entry:
    id: str
    layer: str
    path: Path
    meta: dict
    expect: dict
    schema_path: Path
    compiler_path: Path
    status: str


LAYERS = ("parts", "modules", "assemblies", "structures")

_LAYER_NAMES = {
    "parts": "part",
    "modules": "module",
    "assemblies": "assembly",
    "structures": "structure",
}
_REQUIRED_FILES = ("schema.py", "compiler.py", "meta.yaml", "expect.yaml")
_STATUSES = ("active", "wip")


def discover(root: Path) -> list[Entry]:
    library = Path(root) / "library"
    entries = []

    for layer_dir_name in LAYERS:
        layer_dir = library / layer_dir_name
        if not layer_dir.is_dir():
            continue

        for entry_path in layer_dir.iterdir():
            if entry_path.name.startswith(".") or not entry_path.is_dir():
                continue
            entries.append(_load_entry(entry_path, _LAYER_NAMES[layer_dir_name]))

    return sorted(entries, key=lambda entry: (entry.layer, entry.id))


def load_schema(entry: Entry) -> dict:
    source = entry.schema_path.read_text(encoding="utf-8")
    namespace = {"__builtins__": {}}

    try:
        exec(source, namespace)
    except Exception as exc:
        raise RegistryError(f"{entry.path}: failed to load schema.py: {exc}") from exc

    schema = namespace.get("SCHEMA")
    if not isinstance(schema, dict):
        raise RegistryError(f"{entry.path}: schema.py must define SCHEMA as a dict")
    return schema


def _load_entry(entry_path: Path, expected_layer: str) -> Entry:
    missing = [name for name in _REQUIRED_FILES if not (entry_path / name).is_file()]
    if missing:
        raise RegistryError(f"{entry_path}: missing required files: {', '.join(missing)}")

    meta = _load_yaml(entry_path / "meta.yaml", required_mapping=True)
    expect = _load_yaml(entry_path / "expect.yaml", required_mapping=False)

    if meta.get("id") != entry_path.name:
        raise RegistryError(
            f"{entry_path}: meta id {meta.get('id')!r} does not match directory name {entry_path.name!r}"
        )
    if meta.get("layer") != expected_layer:
        raise RegistryError(
            f"{entry_path}: meta layer {meta.get('layer')!r} does not match {expected_layer!r}"
        )
    if meta.get("status") not in _STATUSES:
        raise RegistryError(f"{entry_path}: invalid status {meta.get('status')!r}")

    return Entry(
        id=meta["id"],
        layer=meta["layer"],
        path=entry_path,
        meta=meta,
        expect=expect,
        schema_path=entry_path / "schema.py",
        compiler_path=entry_path / "compiler.py",
        status=meta["status"],
    )


def _load_yaml(path: Path, *, required_mapping: bool) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RegistryError(f"{path.parent}: could not parse {path.name}: {exc}") from exc

    if data is None:
        data = {}
    if required_mapping and not isinstance(data, dict):
        raise RegistryError(f"{path.parent}: {path.name} must contain a mapping")
    if not isinstance(data, dict):
        raise RegistryError(f"{path.parent}: {path.name} must contain a mapping when present")
    return data

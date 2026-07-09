from __future__ import annotations

from libtools.registry import Entry, load_schema


def export_entry(entry: Entry) -> dict:
    schema = _json_ready(load_schema(entry))
    return {
        "id": entry.meta.get("id"),
        "layer": entry.meta.get("layer"),
        "title": entry.meta.get("title"),
        "owner": entry.meta.get("owner"),
        "version": entry.meta.get("version"),
        "status": entry.meta.get("status"),
        "units": schema.get("units"),
        "schema": schema,
        "provenance": entry.meta.get("provenance"),
        "interface": entry.meta.get("interface"),
    }


def _json_ready(value):
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value

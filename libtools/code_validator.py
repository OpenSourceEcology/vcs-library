from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from libtools.registry import Entry, RegistryError, load_schema
from libtools.report import Check, Report
from libtools.schema_check import check_schema_source


_DIMENSION_WORDS = (
    "width",
    "height",
    "depth",
    "length",
    "thickness",
    "spacing",
    "offset",
    "overhang",
    "radius",
    "diameter",
    "pitch",
    "elevation",
)
_EXACT_DIMENSION_KEYS = {"x", "y", "z"}
_EXEMPT_SUFFIXES = ("_count", "_plies", "_deg")
_EXEMPT_KEYS = {"stories", "version"}
_INTERFACE_SYSTEM_PATTERN = re.compile(r"[a-z0-9_]+")
_INTERFACE_ROLES = {"wall", "roof", "floor", "ceiling", "assembly"}
_EXTERIOR_FACES = {"+x", "-x", "+y", "-y"}
_INTERFACE_SPAN_TOLERANCE_IN = 2.0


def validate_code(entry: Entry) -> Report:
    checks: list[Check] = []

    source = entry.schema_path.read_text(encoding="utf-8")
    schema_violations = check_schema_source(source)
    checks.append(
        Check(
            "schema_data_only",
            not schema_violations,
            "; ".join(schema_violations),
        )
    )

    schema: dict[str, Any] | None
    try:
        schema = load_schema(entry)
    except RegistryError:
        schema = None

    if schema is None:
        checks.append(Check("schema_required_fields", False, "schema not loadable"))
        checks.append(Check("unit_suffix_discipline", False, "schema not loadable"))
        checks.append(Check("param_admissibility", False, "schema not loadable"))
    else:
        checks.append(_check_schema_required_fields(schema))
        checks.append(_check_unit_suffix_discipline(schema))
        checks.append(_check_param_admissibility(schema, entry.expect))

    checks.append(_check_compiler_contract(entry.compiler_path))
    checks.append(_check_meta_complete(entry.meta))
    checks.append(_check_interface_consistent(entry.meta, entry.expect))

    return Report(
        id=entry.id,
        layer=entry.layer,
        status=entry.status,
        tier="code",
        checks=checks,
    )


def _check_schema_required_fields(schema: dict[str, Any]) -> Check:
    missing = []
    if not _nonempty_str(schema.get("schema_name")):
        missing.append("schema_name")
    if schema.get("units") != "in":
        missing.append("units")
    if not _nonempty_str(schema.get("document_name")):
        missing.append("document_name")

    return Check("schema_required_fields", not missing, ", ".join(missing))


def _check_unit_suffix_discipline(schema: dict[str, Any]) -> Check:
    offenders: list[str] = []
    _collect_unit_suffix_offenders(schema, "", offenders)
    return Check("unit_suffix_discipline", not offenders, ", ".join(offenders))


def _collect_unit_suffix_offenders(value: Any, path: str, offenders: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if _is_unit_suffix_offender(key, child):
                offenders.append(child_path)
            _collect_unit_suffix_offenders(child, child_path, offenders)
        return

    if isinstance(value, list):
        for index, child in enumerate(value):
            _collect_unit_suffix_offenders(child, f"{path}[{index}]", offenders)


def _is_unit_suffix_offender(key: Any, value: Any) -> bool:
    if not isinstance(key, str):
        return False
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False

    lower_key = key.lower()
    if lower_key in _EXEMPT_KEYS or lower_key.endswith(_EXEMPT_SUFFIXES):
        return False
    requires_suffix = lower_key in _EXACT_DIMENSION_KEYS or any(
        word in lower_key for word in _DIMENSION_WORDS
    )
    if not requires_suffix:
        return False
    return not (lower_key.endswith("_in") or lower_key.endswith("_in3"))


def _check_param_admissibility(schema: dict[str, Any], expect: dict[str, Any]) -> Check:
    params = expect.get("params")
    if not params:
        return Check("param_admissibility", True, "no rules")

    failures = []
    if not isinstance(params, list):
        return Check("param_admissibility", False, "params must be a list")

    for rule in params:
        if not isinstance(rule, dict):
            failures.append("rule must be a mapping")
            continue
        key = rule.get("key")
        if key not in schema:
            failures.append(f"{key} missing")
            continue
        value = schema[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            failures.append(f"{key} not numeric")
            continue
        minimum = rule.get("min")
        maximum = rule.get("max")
        if minimum is not None and value < minimum:
            failures.append(f"{key} below min {minimum}")
        if maximum is not None and value > maximum:
            failures.append(f"{key} above max {maximum}")

    return Check("param_admissibility", not failures, "; ".join(failures))


def _check_compiler_contract(path: Path) -> Check:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        line = exc.lineno or "unknown"
        return Check("compiler_contract", False, f"syntax error on line {line}: {exc.msg}")

    failures = []
    compile_defs = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "compile"
    ]
    if not any(_has_compile_signature(node) for node in compile_defs):
        failures.append("missing top-level compile(schema, doc)")

    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            failures.append(f"top-level call on line {getattr(node, 'lineno', 'unknown')}")

    return Check("compiler_contract", not failures, "; ".join(failures))


def _has_compile_signature(node: ast.FunctionDef) -> bool:
    args = node.args
    return (
        len(args.posonlyargs) + len(args.args) == 2
        and not args.vararg
        and not args.kwonlyargs
        and not args.kwarg
    )


def _check_meta_complete(meta: dict[str, Any]) -> Check:
    missing = []
    for key in ("id", "layer", "title", "owner", "license", "version", "status"):
        if not _nonempty(meta.get(key)):
            missing.append(key)

    provenance = meta.get("provenance")
    if not isinstance(provenance, dict) or not _nonempty(provenance.get("author")):
        missing.append("provenance.author")

    if not isinstance(meta.get("slots"), dict):
        missing.append("slots")

    return Check("meta_complete", not missing, ", ".join(missing))


def _check_interface_consistent(meta: dict[str, Any], expect: dict[str, Any]) -> Check:
    interface = meta.get("interface")
    if interface is None:
        return Check("interface_consistent", True, "no interface")
    if not isinstance(interface, dict):
        return Check("interface_consistent", False, "interface must be a mapping")

    failures: list[str] = []

    system = interface.get("system")
    if not isinstance(system, str) or not _INTERFACE_SYSTEM_PATTERN.fullmatch(system):
        failures.append("system invalid")

    role = interface.get("role")
    if role not in _INTERFACE_ROLES:
        failures.append("role invalid")

    for field in ("width_in", "depth_in", "height_in"):
        value = interface.get(field)
        if not _positive_number(value):
            failures.append(f"{field} must be positive")

    exterior_face = interface.get("exterior_face")
    if exterior_face not in _EXTERIOR_FACES:
        failures.append("exterior_face invalid")

    if role == "wall" and isinstance(expect.get("envelope"), dict):
        bbox = expect["envelope"].get("bbox_in")
        if isinstance(bbox, dict):
            _check_interface_span(interface, bbox, "width_in", "x", failures)
            _check_interface_span(interface, bbox, "depth_in", "y", failures)
            _check_interface_span(interface, bbox, "height_in", "z", failures)

    return Check("interface_consistent", not failures, "; ".join(failures))


def _check_interface_span(
    interface: dict[str, Any],
    bbox: dict[str, Any],
    field: str,
    axis: str,
    failures: list[str],
) -> None:
    value = interface.get(field)
    if not _positive_number(value):
        return

    span = _bbox_axis_span(bbox.get(axis))
    if span is None:
        return
    if abs(value - span) > _INTERFACE_SPAN_TOLERANCE_IN:
        failures.append(f"{field} differs from envelope {axis} span {span:g}")


def _bbox_axis_span(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, list) or len(value) != 2:
        return None
    minimum, maximum = value
    if not _number(minimum) or not _number(maximum):
        return None
    return float(maximum) - float(minimum)


def _positive_number(value: Any) -> bool:
    return _number(value) and value > 0


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""

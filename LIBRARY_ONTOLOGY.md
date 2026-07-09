# Library Ontology

This is the canonical structure for this repository's part library and validator toolkit. It follows the Open Source Ecology [Schema Canon](https://wiki.opensourceecology.org/wiki/Schema_Canon) and the validation approach described in the July 8, 2026 entry of [Catarina Log](https://wiki.opensourceecology.org/wiki/Catarina_Log).

## Layers

- `parts`: Individual buildable pieces. Example: `sloped_rafter_raked`.
- `modules`: Reusable wall, ceiling, or similar building modules. Example: `extwall_window`.
- `assemblies`: Groups of modules and parts arranged into larger building sections. Example: `cabin_walls_floor_top_plate`.
- `structures`: Whole structures assembled from lower layers. This layer is declared as `library/structures/` and currently has no entries.

Entries are discovered under `library/parts/`, `library/modules/`, `library/assemblies/`, and `library/structures/`.

## Entry Contract

Each entry directory must contain four files:

- `schema.py`: Data for the entry. It defines `SCHEMA` as a Python dict.
- `compiler.py`: FreeCAD compiler code for the entry.
- `meta.yaml`: Identity, ownership, licensing, status, provenance, and declared Schema Canon slots.
- `expect.yaml`: Validation expectations for generated output and admissible schema parameters.

The entry id is the directory name and must match `meta.yaml` field `id`. The layer directory must match `meta.yaml` field `layer`. Entry ids use `snake_case`. Renames are breaking because command-line selection, reports, and generated artifact names use the id.

## Schema Discipline

`schema.py` is data-only. The `schema_data_only` check allows a leading docstring and assignments, requires exactly one `SCHEMA` assignment, and requires `SCHEMA` to be assigned a dict literal. It rejects top-level imports, functions, classes, loops, conditionals, calls, attributes, comprehensions, lambdas, f-strings, await, yield, and other executable constructs checked by `libtools/schema_check.py`.

The registry loads `schema.py` with an empty `__builtins__` namespace and reads `SCHEMA`. `SCHEMA` must be a dict.

Required schema fields checked by `schema_required_fields` are:

- `schema_name`: non-empty string.
- `units`: must be `in`.
- `document_name`: non-empty string.

## Compiler Contract

`compiler.py` must define a top-level function with this signature:

```python
def compile(schema, doc):
    ...
```

The `compiler_contract` check requires exactly two positional parameters and no varargs, keyword-only args, or kwargs. It also rejects top-level call expressions. Imports and helper functions are allowed.

Compilers create FreeCAD objects in `doc`. Current compilers return `list(doc.Objects)` at the end. The driver does not use the return value for validation; it recomputes the document and extracts shapes from `doc.Objects`.

Compilers convert inches to millimeters internally. Existing compilers use:

```python
IN = 25.4
```

## Meta Fields

`meta.yaml` is a mapping. The registry and validators use these fields:

- `id`: Entry id. Must match the directory name.
- `layer`: Singular layer name: `part`, `module`, `assembly`, or `structure`.
- `title`: Human-readable title.
- `owner`: Entry owner and maintainer.
- `license`: License label for the entry.
- `version`: Entry version.
- `status`: `active` or `wip`.
- `provenance`: Mapping for attribution and source tracing.
- `provenance.author`: Required by `meta_complete`.
- `provenance.drive_file_id`: Present on seeded entries from Catarina's source folder.
- `provenance.original_filename`: Source filename under `upstream/`.
- `provenance.source`: Source citation URL.
- `slots`: Mapping of Schema Canon slots.
- `slots.icon`: Declared slot for an icon, currently null in seeded entries.
- `slots.fab_drawing`: Declared slot for fabrication drawing, currently null in seeded entries.
- `slots.bom`: Declared slot for bill of materials, currently null in seeded entries.
- `slots.cheatsheet`: Declared slot for cheat sheet, currently null in seeded entries.

`meta_complete` requires non-empty `id`, `layer`, `title`, `owner`, `license`, `version`, and `status`; it also requires `provenance.author` and a `slots` mapping.

## Expect Fields

`expect.yaml` is a mapping. Missing sections default to empty mappings or no rules.

`envelope` describes the allowed bounding box for the union of output shapes:

- `envelope.bbox_in`: Optional mapping with axes `x`, `y`, and `z`. Each axis can be `[min, max]`. A numeric shorthand is normalized to `[0.0, value]`.
- `envelope.tolerance_in`: Optional tolerance added below the minimum and above the maximum. Default is `0.0`.

`solids` describes required output solids:

- `solids.min_count`: Optional minimum number of extracted shapes.
- `solids.roles`: Optional list of role rules.
- `solids.roles[].pattern`: `fnmatch` pattern matched against shape names.
- `solids.roles[].count`: Optional exact count. If omitted, the pattern must match at least one shape.

`overlap` describes allowed and disallowed solid intersections:

- `overlap.tolerance_in3`: Common-volume tolerance. Default is `0.001`.
- `overlap.allowed_contact`: Optional list of two-pattern pairs. If two shape names match a pair in either order, overlap above tolerance is allowed.

`params` describes admissible top-level schema values:

- `params`: Optional list. Empty or missing means no parameter rules.
- `params[].key`: Top-level schema key to check.
- `params[].min`: Optional numeric minimum.
- `params[].max`: Optional numeric maximum.

`param_admissibility` requires each listed key to exist in `SCHEMA`, be numeric and not boolean, and satisfy any min or max.

## Units And Names

Schemas use inches. Numeric keys that describe dimensions must use `_in` or `_in3` suffixes. The `unit_suffix_discipline` check applies to numeric keys containing these dimension words: `width`, `height`, `depth`, `length`, `thickness`, `spacing`, `offset`, `overhang`, `radius`, `diameter`, `pitch`, `elevation`, and exact keys `x`, `y`, `z`.

Exempt suffixes are `_count`, `_plies`, and `_deg`. Exempt exact keys are `stories` and `version`.

Compilers convert inches to millimeters before creating FreeCAD geometry. Geometry reports convert FreeCAD millimeter output back to inches and cubic inches.

## Validator Contract

Tier 1 is code validation. It runs without FreeCAD:

```bash
python -m libtools validate-code --root . --all
python -m libtools validate-code --root . extwall_window
```

Tier 1 checks are:

- `schema_data_only`: Enforces the data-only `schema.py` restrictions.
- `schema_required_fields`: Requires `schema_name`, `units: in`, and `document_name`.
- `unit_suffix_discipline`: Enforces `_in` and `_in3` suffixes on dimensional numeric schema keys, with implemented exemptions.
- `param_admissibility`: Checks `expect.yaml` parameter min and max rules against top-level schema values.
- `compiler_contract`: Requires `compile(schema, doc)` and rejects top-level calls.
- `meta_complete`: Requires identity, ownership, license, status, provenance author, and slots metadata.

Tier 2 is output validation. It needs `freecadcmd`:

```bash
python -m libtools validate-output --root . --all
python -m libtools validate-output --root . extwall_window
```

Tier 2 checks are:

- `compiles`: The compiler ran and produced a FreeCAD document without an exception.
- `completeness`: Every extracted shape is valid, closed, and has positive volume; also checks `solids.min_count` and `solids.roles`.
- `overlap`: Rejects unallowed common volume above `overlap.tolerance_in3`.
- `fit`: Checks the union bounding box against `envelope.bbox_in` with `envelope.tolerance_in`.

Both validators write reports to `reports/<id>.json` unless `--reports-dir` is supplied. Report JSON has this shape:

```json
{
  "id": "extwall_window",
  "layer": "module",
  "status": "active",
  "tier": "code",
  "checks": [
    {
      "name": "schema_data_only",
      "passed": true,
      "detail": ""
    }
  ],
  "passed": true
}
```

Exit codes are:

- `0`: All selected active entries pass. Failed `wip` entries are report-only and still exit `0`.
- `1`: One or more selected active entries fail validation.
- `2`: Command usage, bad root, unknown id, registry or OS error, or missing `freecadcmd` for output validation.

For `wip` entries, a failed validation prints `WIP-FAIL <id> (... report-only)` and does not fail the command.

## Generated Artifacts

Generated artifacts are not committed:

- `out/*.FCStd` from `compile` and `validate-output`.
- `reports/*.json` from validators.
- `exported/*.json` from `export-json`.

The repository `.gitignore` excludes `reports/`, `exported/`, `*.FCStd`, and `*.FCStd1`.

Schema Canon slots for `icon`, `fab_drawing`, `bom`, and `cheatsheet` are declared in `meta.yaml`. The seeded entries do not yet produce those artifacts.

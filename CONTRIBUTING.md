# Contributing

## Prerequisites

Use Python 3.11 or newer. A local virtual environment is recommended:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

FreeCAD is only needed for output validation and compiling `FCStd` files. CI runs output validation for library and toolkit changes. If `freecadcmd` is not on `PATH`, set `FREECADCMD`:

```bash
FREECADCMD=/path/to/freecadcmd .venv/bin/python -m libtools validate-output --root . extwall_window
```

## Add An Entry

Start from the closest existing entry in the same layer. For example, to add a window-like module, copy:

```bash
cp -R library/modules/extwall_window library/modules/my_new_module
```

Then edit the four entry files:

- `library/modules/my_new_module/schema.py`
- `library/modules/my_new_module/compiler.py`
- `library/modules/my_new_module/meta.yaml`
- `library/modules/my_new_module/expect.yaml`

Set `meta.yaml` field `id` to the new directory name and `layer` to the singular layer name. Use `snake_case` for the entry id.

Run code validation locally:

```bash
.venv/bin/python -m libtools validate-code --root . my_new_module
.venv/bin/python -m libtools validate-code --root . --all
```

Open a pull request. CI runs the toolkit tests, code validation for all entries, and output validation for library and toolkit changes. The entry owner reviews design changes.

## Design Changes

For an existing entry, check `meta.yaml` before changing the design:

```bash
sed -n '1,80p' library/modules/extwall_window/meta.yaml
```

The `owner` field names the maintainer for that entry. Design changes go through that owner.

## Validation Reports

Validators write reports to `reports/<id>.json` by default. You can choose another directory with `--reports-dir`.

Example code-validation report shape:

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
    },
    {
      "name": "schema_required_fields",
      "passed": true,
      "detail": ""
    }
  ],
  "passed": true
}
```

Read `checks[].detail` first when a check fails. A `wip` entry can fail and still let the command exit `0`; the CLI prints `WIP-FAIL <id> (... report-only)` for that case.

## Commands

Run all local tests:

```bash
.venv/bin/python -m pytest -q
```

Run tier-1 code validation:

```bash
.venv/bin/python -m libtools validate-code --root . --all
```

Run tier-2 output validation when FreeCAD is installed:

```bash
.venv/bin/python -m libtools validate-output --root . --all
```

Compile one entry to `out/<id>.FCStd`:

```bash
.venv/bin/python -m libtools compile --root . extwall_window
```

Export one entry's data to `exported/<id>.json`:

```bash
.venv/bin/python -m libtools export-json --root . extwall_window
```

Generated `reports/`, `out/`, and `exported/` files are not committed.

## Starting Another Library

Use [GOVERNANCE.md](GOVERNANCE.md) for ownership, provenance, licensing, and sibling-library guidance.

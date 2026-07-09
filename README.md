# Village Construction Set Library

This is the canonical part library for the Open Source Ecology Village Construction Set 12-foot modules, plus the validator toolkit that keeps entries checkable. The structure follows the OSE [Schema Canon](https://wiki.opensourceecology.org/wiki/Schema_Canon). Seeded design work is by Catarina and comes from the July 8, 2026 entry of [Catarina Log](https://wiki.opensourceecology.org/wiki/Catarina_Log).

## Layout

```text
library/
  parts/
  modules/
  assemblies/
  structures/
libtools/
tests/
upstream/catarina-2026-07-08/
```

The four library layers are:

- `parts`: Individual buildable pieces.
- `modules`: Reusable building modules.
- `assemblies`: Groups of modules and parts.
- `structures`: Whole structures. This layer is declared and currently empty.

Read the repository docs:

- [GOVERNANCE.md](GOVERNANCE.md)
- [LIBRARY_ONTOLOGY.md](LIBRARY_ONTOLOGY.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

## Quickstart

```bash
git clone <repo-url>
cd vcs-library
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m libtools validate-code --root . --all
```

Compiling entries and validating output geometry requires `freecadcmd`:

```bash
.venv/bin/python -m libtools validate-output --root . --all
```

If `freecadcmd` is not on `PATH`, set `FREECADCMD`:

```bash
FREECADCMD=/path/to/freecadcmd .venv/bin/python -m libtools validate-output --root . --all
```

## Current Contents

| Layer | ID | Status | Title |
| --- | --- | --- | --- |
| part | `sloped_rafter_flat_top_plate` | wip | Single sloped roof rafter with corrected birdsmouth cuts |
| part | `sloped_rafter_raked` | active | Single sloped roof rafter with raked-wall birdsmouth cuts |
| module | `ceiling_attic_storage` | active | Ceiling with limited attic storage |
| module | `extwall_front_rake` | active | Exterior wall front rake module |
| module | `extwall_side_rake` | active | Exterior wall side rake module |
| module | `extwall_single_door` | active | Exterior wall single door module |
| module | `extwall_standard` | active | Standard exterior wall module |
| module | `extwall_window` | active | Exterior wall window module |
| assembly | `cabin_walls_floor` | active | Cabin floor and walls assembly |
| assembly | `cabin_walls_floor_top_plate` | active | Cabin floor, walls, and single top plate assembly |
| assembly | `rake_wall_1` | active | Rake wall assembly parametric base Z |
| assembly | `rake_wall_2` | active | Rake wall assembly with side rake modules |

## Validation Status

Code validation is enforced in CI on every push and pull request. Output geometry validation is enforced in CI for changes under `library/`, `libtools/`, `pyproject.toml`, and the output-validation workflow.

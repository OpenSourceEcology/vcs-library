# Slot Generation Plan (fab drawings + BOM)

The [Schema Canon](https://wiki.opensourceecology.org/wiki/Schema_Canon)
requires each schema to produce, beyond CAD: fabrication drawings with QC
pointers, BOMs with sourcing and cost, build instructions, and cheatsheets.
`meta.yaml` declares these as `slots`; none are implemented. This plan
implements the two derivable ones — `fab_drawing` and `bom` — as generated
artifacts in the same pipeline that validates geometry. Build instructions
and cheatsheets remain authored (human) slots and are out of scope here.

Principles:

- Derived, never committed: slot outputs are CI artifacts (and local
  `slots/` output, gitignored), regenerated from the entry on every change —
  the same no-drift rule as FCStd outputs.
- Library-agnostic: generators live in `libtools`, driven only by the entry
  contract (schema, compiler, meta, expect). Nothing VCS-specific.
- Honest v0: outputs must be useful to a builder without overclaiming.
  No pricing until a pricing catalog exists; no QC text until authored.

## bom (v0)

`libtools/bom.py`, running inside the freecadcmd driver after a successful
compile (extend `compile_entry.py`):

- Inventory all solids: label, bbox dims (in), volume (in3).
- Group identical members: same sorted bbox dims within 1/32 in tolerance →
  one line with count. Sort lines by volume descending.
- Nominal-lumber inference: where two of the three dims match a standard
  nominal cross-section (1.5x3.5 → 2x4, 1.5x5.5 → 2x6, 1.5x7.25 → 2x8,
  1.5x9.25 → 2x10, 1.5x11.25 → 2x12, and 0.4375/0.5/0.75 sheet thicknesses
  → OSB/plywood sheet), emit the nominal and the cut length; otherwise emit
  raw dims. Inference table lives in one place with the tolerance.
- Output per entry: `slots/<id>.bom.csv` — columns: count, description
  (nominal or dims), cut_length_in, material_class (lumber|sheet|other),
  total_volume_in3. Plus a `sourcing` column left empty (Schema Canon wants
  3 sourcing links; authored later).
- `meta.yaml` slots stay declarations; a slot is "produced" when the
  generator emits it — `libtools generate-slots` prints a per-entry line and
  exits nonzero if an active entry's compile fails.

## fab_drawing (v0)

`libtools/fab_drawing.py`, also inside the driver (needs the compiled doc):

- TechDraw headless: one page per entry (template shipped in
  `libtools/templates/fab_page.svg`), front view (project along the
  exterior-face axis when `interface.exterior_face` exists, else -y) and one
  side view, auto-scaled to fit.
- Overall dimensions: width/height/depth annotations from the model bbox.
  Per-member dimensioning is v1; v0 ships overall dims + the BOM cut table
  rendered onto the page (TechDraw spreadsheet/annotation or an SVG
  post-pass — implementer's choice, whichever is robust headless).
- Output: `slots/<id>.fab.svg` (TechDraw SVG export; PDF optional if the
  headless export proves reliable in CI).
- If TechDraw proves unusable headless in the CI FreeCAD build, fallback:
  orthographic projection rendered directly from solid bboxes/edges to SVG
  (pure Python, no TechDraw) — same page layout, marked "projection" in a
  corner. The CLI and outputs stay identical either way; record which path
  shipped in this doc.

## CLI + CI

- `python -m libtools generate-slots [--root .] [--out-dir slots] (--all | ID...)`
  — spawns the freecadcmd driver per entry (same env contract as
  validate-output) with `LIBTOOLS_SLOTS=1`; wip entries generate but are
  report-only for exit codes, same semantics as validation.
- `output-validate.yml` gains a generate-slots step after validation and
  uploads `slots/` as a second artifact.
- Tests: bom grouping/inference logic is pure (list of (label, dims) in →
  lines out) — unit-tested without FreeCAD. Drawing layout math (view
  placement, scale fit) likewise factored pure and unit-tested. TechDraw
  interaction is CI-verified.

Done when: CI artifacts contain a `.bom.csv` and `.fab.svg` for all 12
entries; BOM lines for `extwall_standard` match a hand-count of its members;
the ontology doc's slots section links here and marks these two slots
generated.

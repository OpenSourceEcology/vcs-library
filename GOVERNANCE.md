# Governance

This repository is one library in a larger pattern: many small, owned libraries rather than one monolith. Anyone can start a library on the Open Source Ecology wiki or in a repository by following the same entry structure and validator contract.

This library covers the 12-foot modules of the Village Construction Set. The seeded entries are design work by Catarina and are derived from the sources listed in [upstream/catarina-2026-07-08/SOURCES.md](upstream/catarina-2026-07-08/SOURCES.md).

## Ownership

The author of an entry is its owner and maintainer. The owner is recorded in the entry's `meta.yaml` as `owner`. Design changes to an existing entry go through that owner.

All seeded entries currently list Catarina as `owner`, and their `provenance.author` is Catarina.

## Subsidiarity

A library should stay small enough to have clear ownership and useful review. If a design branch, local variant, or different construction set needs different assumptions, start a sibling library instead of forcing all work into one repository.

Future sibling libraries for other construction sets, including tractors, 3D printers, and vehicles, can reuse the same `libtools` package. The toolkit is deliberately not specific to the Village Construction Set.

## Forking And Provenance

Forking prior work into new libraries is encouraged. Provenance travels with the entry in `meta.yaml`, including the author, source file, and wiki citation. Original upstream files should be preserved under `upstream/` when a repository carries converted entries.

The purpose of provenance is attribution and traceability. It should make clear where a design came from and what file was converted.

## File Standards

Recommended source and output formats are:

- Python for schemas and compilers.
- FreeCAD native `FCStd` for generated CAD.
- IFC for model exchange.
- Inkscape `SVG` for vector drawings.
- SweetHome3D for home layout work.

FreeCAD native files are preferred over STEP for library-generated CAD because `FCStd` preserves full model information used by FreeCAD.

## Licensing

This library follows the OSE License for open source hardware documentation. Unless otherwise noted, content is available under CC-BY-SA-4.0. See [LICENSE.md](LICENSE.md).

## Iteration

Constant iteration is expected. Schemas, entries, compilers, and validators can be updated and forked freely. Validators are the quality gate that makes that safe: they keep data shape, metadata, compiler behavior, and generated geometry checkable as entries change.

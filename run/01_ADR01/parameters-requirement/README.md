# ADR01 parameter requirements

This directory holds ADR01 thermal-material and interface requirements.

`ADR01_material_parameters_baseline_v1.md` remains the frozen canonical
human-readable Baseline v1 specification. `material-map.yaml` is its concise
solver-facing derivative and may record an explicitly approved numerical
approximation without rewriting the frozen conceptual baseline.

The current finite-leakage bulk heat-switch proxy is an implementation decision,
not a change to Baseline v1 and not an ADR01 hardware value; see `../arch.md`.

Research notes, working sheets, and one-off task prompts do not belong here after
a baseline is frozen. `ADR01_papers_v4/` is the read-only evidence archive; do not
modify, move, rename, or delete it or its contents.

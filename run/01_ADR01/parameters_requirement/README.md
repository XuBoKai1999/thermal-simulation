# ADR01 parameters requirement

This directory maps each ADR01 geometry component to its thermal model and source-backed material parameters.

Core rule:

`geometry component ID` == `parameter component ID`

Target range for this research pass: **1–4 K**.

Files:
- `material-map.yaml`: component → material / property requirement mapping.
- `research-sources.md`: first-pass vetted source list and coverage notes.
- `CODEX_TASK.md`: ingestion / cleaning task for Codex.

Unknowns remain unknown. Do not convert unresolved material identity, RRR, orientation, magnetic field, or switch technology into silent numerical defaults.

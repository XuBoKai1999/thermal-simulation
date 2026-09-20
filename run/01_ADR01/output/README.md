# Generated ADR01 output

This directory contains generated run artifacts. The segmented production and
validation procedure is documented in [`../segmented-workflow.md`](../segmented-workflow.md).

New plan-driven runs use `output/<scenario>/` for one continuous physical
trajectory. It contains `plan.yaml`, `manifest.json`, logs, production-only
`summary.csv`, physical-time-named `dump/` and `checkpoint/` data, merged
`visualization/fields.pvd`, and interval evidence below `validation/`. Historical
segment directories retain their old layout and are not migrated or deleted.
`run.log` is the append-and-flush runtime event/progress stream;
`validation.log` remains the compact interval validation-state record.

Run summaries and P1 checkpoints use the lightweight `--summary-every` cadence;
`dump/` and `visualization/` use the independent heavy `--output-every` cadence.

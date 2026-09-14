# Generated ADR01 output

This directory contains generated run artifacts. The segmented production and
validation procedure is documented in [`../segmented-workflow.md`](../segmented-workflow.md).

Directory names identify from-zero references or continuation purpose, absolute
time interval, and timestep. Each validation result directory retains its own
`report.md`, CSV/JSON summaries, and comparison plot. Large dump/VTK files and
binary checkpoints are reproducible generated artifacts; repository retention
should be deliberate rather than automatic.

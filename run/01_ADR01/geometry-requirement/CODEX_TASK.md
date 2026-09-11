# Codex Geometry Task

Work inside the existing `thermal-simulation` repository and obey the parent and ADR01 `AGENTS.md`.

Read:

- `run/01_ADR01/geometry-requirement/README.md`
- `run/01_ADR01/geometry-requirement/draft-geometry.yaml`
- `run/01_ADR01/geometry-requirement/connections.yaml`

This is deliberately a soft requirement format, not a new DSL.

Your task is to interpret it using the geometry and Gmsh mechanisms already present in the repository.

First produce a recognizable 3D ADR draft geometry and an interactive inspection path.

Requirements:

- preserve every component ID and edge ID;
- do not invent missing engineering dimensions beyond the explicitly marked placeholder draft values;
- treat all current numeric dimensions as visualization placeholders;
- verify that every declared connection corresponds to an actual geometric contact;
- report gaps, overlaps, or ambiguous interpretation;
- report all assumptions;
- do not start the thermal solve yet;
- do not create a second framework inside ADR01;
- add generic parent-level geometry helpers only if the existing framework genuinely cannot express the required geometry;
- if you add generic functionality, validate it independently.

The first goal is simply:

    requirement -> 3D geometry -> interactive visual inspection

Do not proceed to material research or thermal solving in this task.

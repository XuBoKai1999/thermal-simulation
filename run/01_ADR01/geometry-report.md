# ADR01 Draft 0 Geometry Validation — Lateral-Offset Revision

## Result

The placeholder geometry was generated successfully as one conformal 3D assembly.
All 10 component IDs are dimension-3 physical groups. All 11 declared edge IDs are
dimension-2 physical groups on surfaces shared by exactly the declared component pair.

- Missing declared contacts: none
- Additional component contacts: none
- Split or overlapping component volumes: none detected by OCC fragmentation
- Mesh coherence errors: none
- Generated mesh: 2,506 nodes and 7,459 tagged elements

## Contact areas

| Edge | Area (mm²) |
|---|---:|
| `edge_hot_cylinder_1` | 19.634954 |
| `edge_cylinder_1_heat_switch` | 19.634954 |
| `edge_heat_switch_cylinder_2` | 19.634954 |
| `edge_cylinder_2_ggg` | 19.634954 |
| `edge_ggg_cylinder_3` | 19.634954 |
| `edge_cylinder_3_cold_stage` | 19.634954 |
| `edge_cold_stage_sample` | 36.000000 |
| `edge_hot_support_1` | 4.908739 |
| `edge_support_1_cold_stage` | 4.908739 |
| `edge_hot_support_2` | 4.908739 |
| `edge_support_2_cold_stage` | 4.908739 |

Areas are derived from the generated placeholder geometry, not separately entered
engineering data.

## Interpretations and assumptions

- Requirement millimetres are converted to metres in the generated mesh.
- Every cylinder is vertical along `+z` with `center_xy`, `z_min`, and `z_max` interpreted literally.
- `sample` is an axis-aligned box using the six stated bounds.
- The five coaxial ADR-chain components share `center_xy = (-5, 0) mm` and move as one chain.
- The sample is centred at approximately `(+5, 0) mm`; its placeholder footprint is `6 × 6 mm`.
- The two supports use `(0, -9) mm` and `(0, +9) mm`, avoiding the offset chain and sample while remaining on both plates.
- Exact shared boundary area is treated as geometric contact; touching solids are OCC-fragmented to create conformal topology.
- The 0.5 mm `heat_switch` remains a volumetric visual placeholder only.
- All dimensions and derived areas are visualization placeholders, not measured hardware values.
- No missing physical fact was inferred, and no superconducting magnet was added.

## Interactive inspection

From repository root in Windows PowerShell:

```powershell
.\scripts\wsl-run.ps1 "cd '/mnt/c/Users/User2/Documents/Works/03 thermal simulation' && python3 run/01_ADR01/geometry.py --view"
```

In Gmsh, use the physical groups to show/hide the 10 components and 11 interfaces,
then rotate, zoom, and inspect the left-offset chain, opposite-side sample, and two supports.
Human visual approval remains required before thermal work.

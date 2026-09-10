# 功能與文件 audit

## Feature inventory

| 功能 | 狀態 | 現行入口 / 限制 |
|---|---|---|
| Geometry creation | implemented | case `geometry.py` + Gmsh Python API；3D examples |
| Mesh generation/loading | implemented | `mesh.ensure_mesh`, `mesh.load_mesh`; `gdim=3` |
| Region/cell tags | implemented | Gmsh volume physical groups + `cell_tags`/`tags.json` |
| Facet/boundary tags | implemented | Gmsh surface physical groups + `facet_tags` |
| Case/config loading | implemented, narrow | `case.load_case`; steady multi-region；two fixed-T BC |
| Materials/properties | implemented, narrow | unified constant/table/Python `k/rho/cp`; no registry/database |
| Steady conduction | implemented | multi-region constant k 或 single-region table/Python k(T)；Q=0 |
| Transient conduction | implemented, narrow | multi-region constant properties；Backward Euler；loop lives in case runner |
| Initial condition | partial | x-split two-value DG0 only |
| Fixed-temperature BC | implemented | exactly two |
| Heat-flux/adiabatic/total-heat loads | absent as configurable features | untagged natural zero flux only |
| Volumetric heat source | absent | model source is hard-coded zero |
| Contact resistance | implemented, narrow | 3D mesh-resolved thin layer；Test 05 獨立 1D zero-thickness contact |
| Heat switch | absent | old docs only |
| Time stepping | partial | single-step model + case-specific loop |
| Solver configuration | partial | fixed PETSc preonly/LU; only prefix argument |
| Analysis | implemented, hard-coded | global T/q + hot_end/cold_end total heat |
| Region statistics | absent | despite old docs wording; only whole-domain summary |
| Heat flux calculation | implemented | cell $-k\nabla T$; DG0 IC special-cased zero |
| Dump writing/reading | implemented | v1 cell dump; serial ID mapping |
| Plotting/postprocessing | partial | x scatter CLI; low-level pcolormesh helper |
| Validation utilities | examples only | Test 01 inline；Test 02 與 Test 05 case-specific validators |
| MPI | partial | assembly/solve aware; dump mapping serial only |
| Mesh caching/reuse | implemented | geometry-file hash only |
| CLI/package entry point | absent | execute case `main.py` through WSL wrapper |
| External CAD | absent workflow | only mentioned as possible future path |
| Multi-material / region-dependent k | implemented | steady/transient constant scalar properties by cell tags |
| k(T) | implemented, narrow | steady single-region；table or local Python；UFL expression |
| rho(T), cp(T), anisotropic k | absent | transient properties remain constants |
| Nonlinear solve | implemented, narrow | steady $k(T)$；fixed PETSc SNES/Newton options |

## 舊文件與 source 的差異

Source code 與六個 working cases 是本手冊依據。已確認下列差異：

- `arch.md` 的 `loads`、`heat_switch` YAML 仍是示意/未來設計；`contacts` 目前只有
  `thin_layer_resistance` 已實作。
- `steps.md` Stage 7 baseline 與 `runs/baseline` 尚不存在。
- `arch.md` 說 analysis 有 region min/max/average；實作只有 whole-domain T summary。
- `arch.md`/`dump-format.md` 談真正 3D topology postprocess merge；現有 reader/plotter沒有
  讀 `mesh.msh` 或核對 `build.json`，只支援 dump centroid scatter。
- `arch.md` 提到 external STEP/BREP 可作方向，但沒有 repository API/case 證據。
- `arch.md` 示意 `resolved_case.yaml`、`run.log`；現有 examples 不產生這些檔案。
- `dump-format.md` 大致與 writer/reader一致。較精確地說，現行 `map_cell_ids` 回傳匹配到的
  Gmsh volume element tags；文件刻意要求 caller 不依賴其數值來源，這仍是合理契約。
- `dump-format.md` 說 3D postprocessor「必須」驗證 MESH_ID；規格正確，但目前尚無此類
  3D postprocessor implementation。
- 根目錄 `README.md` 現已提供專案定位、四個案例與 WSL2 執行入口。

Test 03 現已驗證 CSV table與 steady $k(T)$；Test 04 已驗證 multi-region constant
$k$ 與 thin-layer contact resistance；Test 05 驗證獨立 1D P1 nonlinear $k(T)$ 與
zero-thickness contact。Test 06驗證property loader與multi-region constant transient。
Temperature-dependent transient與通用3D zero-thickness contact仍不是現有功能。

## 讓文件化困難的現行 API 問題

- 沒有 package `__init__.py`、版本、安裝 metadata、single runner 或 stable facade；案例直接
  import modules。
- `build_model` 不依 `model.type` 分派；caller 必須知道要呼叫哪個 builder。
- case validation 使用歷史訊息 `Stage 2...`，且允許未知 keys，容易誤以為設定已生效。
- semantic tags 要由 caller另讀 JSON；`analyze` hard-code `hot_end`/`cold_end`。
- output schedule、summary serialization 與 transient stepping 重複留給 case `main.py`。
- PETSc options 不可由 caller mapping/config 調整；`solve.solve` prefix 綁定 steady-bar 名稱。
- nonlinear SNES options 同樣固定在 `solve.solve_nonlinear`，尚無 YAML/caller options。
- `write_dump` 所稱「unknown field」其實只檢查 data 是否有 key，並非限制於標準 fields。
- reader metadata types 不一致（大多 string，bounds/regions 結構化，IDs data 為 float）。

這些是未來可改善項目；本次沒有為了手冊而重構 API 或 solver。

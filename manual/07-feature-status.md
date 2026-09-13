# 功能與文件 audit

## Feature inventory

| 功能 | 狀態 | 現行入口 / 限制 |
|---|---|---|
| Geometry creation | implemented | case `geometry.py` + Gmsh Python API；3D examples |
| Mesh generation/loading | implemented | `mesh.ensure_mesh`, `mesh.load_mesh`; `gdim=3` |
| Region/cell tags | implemented | Gmsh volume physical groups + `cell_tags`/`tags.json` |
| Facet/boundary tags | implemented | Gmsh surface physical groups + `facet_tags` |
| Case/config loading | implemented, narrow | `case.load_case`; multi-region；one or more fixed-T BCs |
| Materials/properties | implemented, narrow | case-local constant/table/Python `k/rho/cp`; source-preserving NIST database與listing CLI已完成，但尚未solver-integrated |
| Steady conduction | implemented | multi-region constant k 或 single-region table/Python k(T)；Q=0 |
| Transient conduction | implemented, narrow | multi-region constant或temperature-dependent properties；Backward Euler；loop lives in case runner |
| Initial condition | implemented, narrow | `uniform`, backward-compatible `split_x`, or semantic `by_region` |
| Fixed-temperature BC | implemented | one or more semantic surfaces |
| Heat-flux/adiabatic/total-heat loads | absent as configurable features | untagged natural zero flux only |
| Volumetric heat source | absent | model source is hard-coded zero |
| Contact resistance | reference/proxy paths only | mesh-resolved thin layer and Test 05's independent 1D solver; no generic 3D interface law |
| Heat switch | implemented as case proxy | ADR01 OFF state uses an approved finite-leakage thin bulk proxy; no generic switch model or ON state |
| Time stepping | partial | single-step model + case-specific loop |
| Solver configuration | partial | fixed PETSc preonly/LU; only prefix argument |
| Analysis | implemented | global T/q + caller-selected tagged-surface total heat |
| Region statistics | implemented | per-volume-region T min/max/volume average |
| Heat flux calculation | implemented | cell $-k\nabla T$; DG0 IC special-cased zero |
| Dump writing/reading | implemented | v2 cell dump with v1 reader compatibility; serial ID mapping |
| Plotting/postprocessing | partial | x scatter CLI; low-level pcolormesh helper |
| Validation utilities | examples only | Test 01 inline；Test 02 與 Test 05 case-specific validators |
| MPI | partial | assembly/solve aware; dump mapping serial only |
| Mesh caching/reuse | implemented | geometry-file hash only |
| CLI/package entry point | absent | execute case `main.py` through WSL wrapper |
| External CAD | absent workflow | only mentioned as possible future path |
| Multi-material / region-dependent k | implemented | steady constant與transient constant/table/Python properties by cell tags |
| k(T) | implemented, narrow | steady single-region；table or local Python；UFL expression |
| rho(T), cp(T) | implemented | multi-region nonlinear transient via table/Python evaluator and SNES |
| anisotropic k | absent | scalar isotropic conductivity only |
| Nonlinear solve | implemented, narrow | steady/transient temperature-dependent properties; PETSc SNES/Newton and table-domain-derived VI bounds |

## Contact capability matrix

| Contact representation | Status | Meaning |
|---|---|---|
| Perfect shared-mesh contact | **SUPPORTED** | Conformal shared topology；continuous P1 temperature |
| Mesh-resolved finite thin layer | **SUPPORTED** | 3D steady only；layer thickness must match geometry |
| 1D zero-thickness contact solver | **REFERENCE ONLY** | `lib/contact.py` + Test 05；不是 generic model path |
| General 3D zero-thickness contact | **NOT SUPPORTED** | 無 DG/Nitsche/mortar/interface-law implementation |
| Transient contact resistance | **NOT SUPPORTED** | generic transient loader 明確拒絕 `contacts` |

## Known limitations checklist

目前不能在 `case.yaml` 中使用：prescribed heat flux/total heat、convection、radiation、
volumetric heat generation、time-dependent BC、generic heat-switch model、anisotropic
conductivity、arbitrary coordinate-dependent/expression-based initial field、general 3D
zero-thickness contact 或 transient contact resistance。Semantic constant `by_region` IC已支援；
ADR01另有case-specific finite-leakage bulk proxy表示heat-switch OFF state。
此外，沒有 automatic generic runner、NIST database → `case.yaml` integration、automatic
external CAD/helper dependency tracking、topology-aware 3D postprocessor，且 MPI dump/cell-ID
mapping 未實作。

### Region-wise initial-condition representation

Semantic constant `by_region` initial conditions are supported. However, the
transient temperature solution currently uses a continuous P1 space, so a
piecewise-discontinuous temperature jump between touching regions cannot be
represented exactly on a conformal shared interface. The shared-interface values
must belong to one continuous FE field. Consequently, a discontinuous `by_region`
IC may show interface smoothing and mesh-dependent initial gradients or heat-flux
diagnostics.

This is a numerical representation limitation, not material or contact physics,
and does not mean that `by_region` or ordinary perfect-contact transient solving
is broken. The final treatment has not been selected; possible approaches require
future numerical investigation rather than being prescribed here.

NIST ingestion 現況：43 個index entries（42 material pages + 1 regenerator dataset）、
38 fully normalized、1 partially normalized、3 manual-required、129 derived CSVs。Derived
tables只覆蓋各series的`equation_range_K`；資料庫沒有補入外部density，也不替使用者在
RRR、direction等variants間自動選擇。

## 舊文件與 source 的差異

Source code 與七個 working cases 是本手冊依據。已確認下列差異：

- `arch.md` 的 `loads`、`heat_switch` YAML 仍是示意/未來設計；`contacts` 目前只有
  `thin_layer_resistance` 已實作。
- `steps.md` 的 ADR01 baseline 尚未開始；實際 planning directory 是 `run/01_ADR01/`。
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
zero-thickness contact。Test 06驗證property loader、multi-region constant transient與
temperature-dependent nonlinear transient。Test 07驗證一般3D multi-region transient、
uniform IC、semantic surfaces、region statistics與conformal interface。通用3D
zero-thickness contact仍不是現有功能。

## 讓文件化困難的現行 API 問題

- 沒有 package `__init__.py`、版本、安裝 metadata、single runner 或 stable facade；案例直接
  import modules。
- `build_model` 不依 `model.type` 分派；caller 必須知道要呼叫哪個 builder。
- case validation仍允許未知 keys，容易誤以為設定已生效。
- semantic tags 要由 caller另讀 JSON。
- output schedule、summary serialization 與 transient stepping 重複留給 case `main.py`。
- PETSc options 不可由 caller mapping/config 調整；`solve.solve` prefix 綁定 steady-bar 名稱。
- nonlinear SNES options 同樣固定在 `solve.solve_nonlinear`，尚無 YAML/caller options。
- `write_dump` 所稱「unknown field」其實只檢查 data 是否有 key，並非限制於標準 fields。
- reader metadata types 不一致（大多 string，bounds/regions 結構化，IDs data 為 float）。

這些是未來可改善項目；本次沒有為了手冊而重構 API 或 solver。

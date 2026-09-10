# thermal-simulation 使用者手冊

本手冊是 thermal-simulation 的 **repository operation manual + agent handoff manual**。
它以目前 source 與 Test 01–07 為準，不是未來設計藍圖，也不是熱傳教科書。完全沒有
專案前文的 Agent 應先讀本頁，再依下列順序閱讀整個 `manual/`；開始工作不需要先讀
根目錄的舊 architecture 或 construction notes。

## 30 秒理解 framework

thermal-simulation 是 lightweight、case-driven、Python-based 的 3D thermal simulation
framework，使用 Gmsh 建網格、FEniCSx 0.10 API 建立 FEM、PETSc 解線性或非線性系統，
並輸出 LAMMPS-like cell dump。核心分工是：

```text
<case>/geometry.py  → 幾何、mesh size、semantic volume/surface tags
<case>/case.yaml    → model、材料、initial condition、BC、time settings
<case>/main.py      → 本 case 的 workflow、time loop、output 與 verification orchestration
lib/                → 可重用的 FEM、material、analysis、mesh、dump implementation
<case>/build/       → mesh topology、semantic tags、mesh identity/cache manifest
<case>/output/      → dump 與 case-specific summaries/plots
```

`main.py` 是 case orchestration，不是放新 weak form 或複製 solver implementation 的地方。
新 case 應先找最接近的 Test 01–07，重用 `lib/`，再只調整案例資料與 workflow。

## 建議閱讀順序

1. [Quickstart](01-quickstart.md)：在 WSL2 跑第一個穩態案例。
2. [工作流程、geometry、mesh 與 case](02-workflow-geometry-mesh-case.md)：建立自己的案例。
3. [物理模型、邊界條件與 solver](03-physics-and-solver.md)：理解目前方程式與限制。
4. [輸出與後處理](04-output-and-postprocessing.md)：讀 dump、畫圖與取得 summary。
5. [範例](05-examples.md)：已驗證的直棒與 material-property 案例。
6. [Verification 與 troubleshooting](06-verification-and-troubleshooting.md)。
7. [功能盤點與舊文件差異](07-feature-status.md)。
8. [Public API reference](08-api-reference.md)。

## 一句話定位

目前版本是小型、case-driven 的 3D FEniCSx 熱傳框架：使用者以 Python/Gmsh 建立
geometry，以 YAML 指定 region、material、`k/rho/cp` properties 與一個以上固定溫度邊界，再由案例自己的 `main.py`
串接 mesh、model、solve、analysis 與 dump。它不是具有統一 CLI、通用 case runner、
材料資料庫或多物理 DSL 的成熟套件。

## Environment 與執行邊界

Codex 與開發 shell 位於 Windows PowerShell；所有 Python simulation、FEniCSx、Gmsh、
PETSc 與 MPI 命令必須送進 WSL2 Ubuntu：

```text
Windows PowerShell → scripts/wsl-run.ps1 → WSL2 Ubuntu → Python/FEniCSx/PETSc/MPI/Gmsh
```

```powershell
.\scripts\wsl-run.ps1 "python3 test/01_steady_bar/main.py"
.\scripts\wsl-run.ps1 "python3 -m pytest test/06_material_properties/test_properties.py"
```

若 execution policy 阻擋 helper，使用 `01-quickstart.md` 的 Bypass 形式。不要用 Windows
Python 執行 simulation，也不要混用 Windows/WSL packages。code 使用 FEniCSx 0.10 API；
repository 沒有 dependency lockfile，因此 Gmsh、PETSc、MPI 的確切 patch versions 不是契約。
完整 end-to-end dump workflow 目前只支援 serial。

## Repository layout

```text
lib/          generic mesh, case, material, FEM, solve, analysis and dump modules
materials/    NOT PRESENT as a shared material database; case-local files are supported
scripts/      Windows PowerShell → WSL helper
postprocess/  simple dump plotting CLI
test/         Test 01–07 verification cases
run/          real project cases; framework manual 不收錄個別專案物理
manual/       本 operation knowledge base
```

`lib/` 的 callable-level 責任與 signatures 見 `08-api-reference.md`。不要假設存在 generic
runner、installed package、shared materials registry、external CAD dependency manager 或 CLI。

## 目前能做什麼

- 3D Gmsh geometry、physical volume/facet tags 與 `.msh` cache。
- `k`、`rho`、`cp` 可來自 scalar/explicit constant、CSV table 或 local Python callable。
- steady 可使用一個或多個 constant、isotropic-$k$ regions；single-region steady `k(T)`
  可使用 table 或 Python source。
- 暫態可使用多個 regions；constant properties走linear solver，任一 relevant property
  為table/Python `p(T)`時走nonlinear SNES solver。
- 穩態、零體積熱源 conduction。
- Backward Euler 暫態、零體積熱源 conduction。
- 一個以上 fixed-temperature Dirichlet boundaries。
- Uniform或legacy split-x兩值暫態 initial condition。
- P1 temperature、cell-centroid temperature/heat-flux dump、全域 summary 與兩端總熱流。
- Per-region temperature min/max/average與caller-selected tagged-surface total heat flow。
- 讀取單一 dump 或同 mesh dump series，以及簡單的 x-profile 圖。
- steady case 可由 table 或案例自己的 Python file 提供 UFL-compatible $k(T)$，並以
  PETSc SNES/Newton 求解。
- steady case 可使用多個 constant-$k$ regions，並以 mesh-resolved thin layer 表示
  面積比接觸熱阻。

重要限制請先看[功能盤點](07-feature-status.md)。尤其目前不支援 heat load、heat flux
BC、零厚度 interface contact、heat switch、convection、radiation或temperature dependence
於`T`以外的state variable。

## Material syntax

Backward-compatible constant：

```yaml
regions:
  bar: {k: 10.0, rho: 1000.0, cp: 100.0}
```

Named materials 可混用 explicit constant、table 與 Python：

```yaml
materials:
  copper:
    rho: {type: constant, value: 8960}
    cp: {type: table, file: materials/copper_cp.csv, x: T_K, y: cp_J_kgK}
    k: {type: python, file: materials/copper.py, function: k}
regions:
  upper_plate: {material: copper}
  cold_stage: {material: copper}
```

CSV 使用 linear interpolation，temperature欄必須唯一且資料 finite/positive；domain 外
evaluation 是 error。Python function 必須存在並回傳 finite、positive value；local Python
是使用者主動提供的 extension code，不是 sandbox。`test/06_material_properties/case.yaml`
是 multi-region constant transient 的可執行範例。

## 如果你現在要開始一個新的 thermal case

1. 讀完 `manual/`，從 Test 01–07 找最接近的 case；一般 3D transient 首選 Test 07。
2. 在 `run/<case>/` 建 `geometry.py`、`case.yaml`、`main.py`；不要修改既有 test 當 real case。
3. 建 semantic volume/surface tags，確認 perfect contact solids 是 shared/conformal topology。
4. 在 YAML 定義 materials/regions、fixed-temperature BC，以及 transient IC 與 time settings。
5. 從相近 test 複製 orchestration，重用 `lib/` 建 mesh、model、solve、analyze 與 dump。
6. 透過 WSL helper 做 serial smoke run，檢查 tags、物性、solver 與輸出。
7. 核對 region temperature、selected-surface heat flow、sign 與 energy balance。
8. 做 coarse/medium/fine mesh 與 `dt`, `dt/2`, `dt/4` convergence，比較 observables。
9. 若需要新 physics，先建立 minimal verification test，再改 generic `lib/` 並跑 regressions。

## Rules for Agents

1. 如無必要，勿增實體；先使用現有 module、case pattern 與文件結構。
2. 優先 reuse `lib/`；`main.py` 是 orchestration，不是新的 solver。
3. 不要把 test-specific geometry、tag name、BC 或 verification 假設放進 generic `lib/`。
4. 新 physics 先做 minimal、可解析或可獨立核對的 test，再回 real case。
5. 不要宣稱 planned、reference-only 或未支援功能已受 framework 支援。
6. 材料 table 超出有效溫度範圍必須報錯；禁止 silent extrapolation。
7. 幾何上看似接觸不等於 FEM topology 相連；perfect contact 必須驗證 shared/conformal topology。
8. 修改 framework 後必須跑與風險相符的 Test 01–07 regressions。
9. 行為、schema、output 或限制改變時，同步更新 `manual/`。
10. ADR 等 real-case 需求留在各自 `run/` 文件；不要污染 framework manual。

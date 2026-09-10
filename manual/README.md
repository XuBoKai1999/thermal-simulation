# thermal-simulation 使用者手冊

本手冊描述 repository **目前程式碼實際提供**的功能。它不是未來設計藍圖，也不是
通用熱傳套件的承諾。目前有六個已驗證入口：Test 01 constant-$k$ steady、Test 02
transient、Test 03 CSV table $k(T)$ nonlinear solve、Test 04 multi-region
thin-layer contact resistance，以及 Test 05 獨立 1D P1 zero-thickness nonlinear contact、
長時間 transient 與固定 0.125 s 的 `dx × dt` numerical-reference benchmark；Test 06則驗證
統一constant/table/Python property loader與multi-region constant-property transient。

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
geometry，以 YAML 指定 region、material、`k/rho/cp` properties 與兩個固定溫度邊界，再由案例自己的 `main.py`
串接 mesh、model、solve、analysis 與 dump。它不是具有統一 CLI、通用 case runner、
材料資料庫或多物理 DSL 的成熟套件。

## 目前能做什麼

- 3D Gmsh geometry、physical volume/facet tags 與 `.msh` cache。
- `k`、`rho`、`cp` 可來自 scalar/explicit constant、CSV table 或 local Python callable。
- steady 可使用一個或多個 constant、isotropic-$k$ regions；single-region steady `k(T)`
  可使用 table 或 Python source。
- 暫態可使用多個 regions；constant properties走linear solver，任一 relevant property
  為table/Python `p(T)`時走nonlinear SNES solver。
- 穩態、零體積熱源 conduction。
- Backward Euler 暫態、零體積熱源 conduction。
- 恰好兩個 fixed-temperature Dirichlet boundaries。
- 分段於 x 座標的兩值暫態 initial condition。
- P1 temperature、cell-centroid temperature/heat-flux dump、全域 summary 與兩端總熱流。
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

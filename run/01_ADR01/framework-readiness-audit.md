# Thermal Simulation Framework Readiness Audit for ADR01

## 1. Executive summary

目前 repository 是一個「case-driven、由案例自行編排 workflow」的精簡 thermal FEM framework，不是通用模擬器或統一 CLI。

實際已驗證的核心能力：

- Gmsh 建立與載入 3D mesh。
- FEniCSx P1 穩態熱傳。
- 穩態多 region、各 region 常數 isotropic `k`。
- 單一 region、常數 `k`、`rho`、`cp` 的 transient Backward Euler。
- 單一 region steady `k(T)` 與 PETSc SNES/Newton。
- 3D mesh-resolved thin-layer contact resistance。
- 獨立的 1D zero-thickness nonlinear contact benchmark。
- Cell-centroid dump、dump series reader、全域 summary 與兩個固定名稱端面的總熱流。

主要限制：

- 通用 3D transient 只允許一個 material region。
- 通用 transient 不支援 `k(T)`、`rho(T)`、`cp(T)`。
- 只能設定恰好兩個固定溫度邊界。
- Heat load、specified heat flux、convection、radiation、heat switch 都未實作。
- 3D zero-thickness contact 尚未實作。
- Transient loop、輸出排程及 summary 寫出都由各案例 `main.py` 自行處理。
- Dump cell-ID mapping 只支援 serial execution。

因此可以開始 ADR01 的幾何、semantic tagging、材料輸入整理及「高度簡化」的首版 transient case，但目前不能直接表達一般多材料、有熱負載或複雜熱邊界的 ADR assembly。

稽核執行期間沒有修改 repository；所有會產生輸出的測試均在 WSL `/tmp` 隔離副本中執行。

## 2. Repository data flow

### 實際資料流

```text
case main.py
  -> import geometry.py
  -> mesh.ensure_mesh()
      -> geometry.build_geometry()
      -> build/mesh.msh
      -> build/tags.json
      -> build/build.json
  -> case.load_case(case.yaml)
  -> main.py 自行讀 tags.json
  -> mesh.load_mesh()
  -> model.build_model()
       或 build_transient_model()
       或 build_nonlinear_model()
  -> solve.solve()/make_solver()/solve_nonlinear()
  -> analyze.analyze()
  -> mesh.map_cell_ids()
  -> dump.write_dump()
  -> main.py 自行寫 summary.csv 或其他案例 CSV
```

這和文件描述的高層流程大致一致，但下列部分只是文件願景或描述得比實作廣：

- 沒有統一 case runner。
- 沒有自動 transient loop。
- 沒有通用 summary writer。
- 沒有 `resolved_case.yaml` 或 `run.log` writer。
- 沒有 per-region temperature statistics。
- 沒有通用 3D mesh/dump merge visualizer。
- `loads`、`heat_switch` YAML 是未來示意，loader 不接受也不使用它們。
- STEP/BREP CAD import workflow 尚未建立作為 framework API。

### 主要 `lib/*.py` 實際責任

| 檔案 | 實際責任 |
|---|---|
| `case.py` | 載入及狹義驗證 `case.yaml`；另有 Test 01 型式的 `expected.yaml` validator。 |
| `mesh.py` | 依 geometry source hash/cache key 建立或重用 Gmsh mesh；載入 FEniCSx mesh；serial-only Gmsh/FEniCSx cell-ID 對應。 |
| `materials.py` | 驗證 local material callable；依 cell tags 建立 DG0 constant conductivity field；薄層以 `k = thickness / resistance` 轉換。 |
| `model.py` | 建立 steady linear、steady nonlinear `k(T)`、single-region transient weak form；建立兩個 fixed-T Dirichlet BC。 |
| `solve.py` | PETSc preonly/LU linear solve；固定選項的 SNES/Newton nonlinear solve。 |
| `analyze.py` | 計算 cell-centroid `T`、`q = -k grad(T)`、全域 min/max/average、平均熱流及 hard-coded `hot_end`/`cold_end` surface heat flow。 |
| `dump.py` | 驗證並序列化 caller 已準備好的 cell fields；建立 dump 目錄及 `<timestep>.dump`。 |
| `dump_reader.py` | 讀單一 dump；按 TIME 排序並驗證相同 MESH_ID 的 dump series。 |
| `contact.py` | 獨立 NumPy 1D P1、兩個不共享 interface nodes 的 steady/transient nonlinear zero-thickness contact solver；不是通用 FEniCSx 3D contact。 |
| `plotting.py` | 一個簡單 `pcolormesh` helper；不讀 dump、不做 mesh reconstruction。 |

### 新 case 最少檔案

必要：

```text
main.py
geometry.py
case.yaml
```

視需求增加：

- `material.py`：只用於 steady、單一 region 的 local `k(T)`。
- `expected.yaml`、`validate.py`：驗證案例需要，實際 simulation case 非必要。
- `build/`、`output/`：由 runner 執行時產生。

### `geometry.py` 實際 contract

最少要提供：

```python
def build_geometry(mesh_path):
    ...
    return semantic_tags
```

它需要：

- 使用 Gmsh 建立 geometry 和 mesh。
- 建立所有材料 volume 的 Physical Groups。
- 建立 BC surface 的 Physical Groups。
- 寫出指定的 `mesh_path`。
- 回傳 semantic name、dimension 與 physical tag mapping。

所有 cell 必須被 `case.yaml.regions` 對應的 volume tag 覆蓋。BC 名稱也必須與 YAML 相符。

### `case.yaml` 實際接受內容

通用 loader 真正接受：

- `model.type`
  - `steady_conduction`
  - `transient_conduction`
- `regions`
  - steady constant material：正值 scalar `k`
  - steady nonlinear：唯一 region 設 `material: local`
  - transient：唯一 region 必須有正值 scalar `k`、`rho`、`cp`
- `contacts`
  - 只接受 `thin_layer_resistance`
  - 必須指定已有 volume region
  - 正值 `resistance_m2K_W`
  - 正值 `thickness_m`
- `boundary_conditions`
  - 必須恰好兩個
  - 每個必須是 `fixed_temperature`
  - numeric `value_K`
- transient `time`
  - 正值 `dt_s`、`end_s`
  - `initial_condition.split_x_m`
  - `left_T_K`、`right_T_K`

Test 05 的 YAML 沒有經過 `case.load_case()`，而是由 runner 直接 `yaml.safe_load()`；不能把它視為通用 case schema。

### `main.py` 需要自行串接

- 路徑及 project import。
- Mesh cache/build。
- Case loading。
- Tags/manifest JSON loading。
- Model 選擇。
- Transient loop與 previous-state update。
- Solver options/prefix。
- Dump time schedule。
- Analyze、cell-ID mapping、dump。
- Summary/validation CSV。
- Local material import。

### `build/` 實際產物

通常是：

- `mesh.msh`
- `tags.json`
- `build.json`
  - `geometry_sha256`
  - 隨 mesh rebuild 產生的 `mesh_id`

收斂案例可以在其下使用多個 `dx_*` 子目錄。

Cache fingerprint 只包含 geometry source bytes 加 caller 的 `cache_key`；不會自動追蹤所有外部 CAD、imported helper 或 Gmsh option dependency。

### `output/` 實際產物

依 `main.py` 而異：

- `dump/<timestep>.dump`
- steady cases 的 `summary.csv`
- transient convergence 的 `runs.csv` 與多層 dump 目錄
- Test 05 的 convergence/transient summary CSV

目前沒有 library 保證產生：

- `resolved_case.yaml`
- `run.log`
- 統一格式的 transient summary
- 通用 per-region summary

### 已存在的主要 API

- `case.load_case`, `case.load_expected`
- `mesh.ensure_mesh`, `mesh.load_mesh`, `mesh.map_cell_ids`
- `materials.validate`, `materials.conductivity_field`
- `model.build_model`, `build_nonlinear_model`, `build_transient_model`
- `model.build_boundary_conditions`
- `solve.solve`, `solve.make_solver`, `solve.solve_nonlinear`
- `analyze.analyze`
- `dump.write_dump`
- `dump_reader.read_dump`, `read_dump_series`
- `contact.solve_steady_rod`, `advance_transient_rod`
- `plotting.plot_heatmap`

## 3. Capability matrix

| 能力 | 狀態 | 實際證據／限制 |
|---|---|---|
| 3D geometry | WORKING | `test/01-04/geometry.py` 均建立 3D box/tetrahedral mesh；`mesh.load_mesh(..., gdim=3)`。 |
| Multiple material regions | LIMITED | Test 04 驗證 3D steady 三 region；`materials.conductivity_field()` 依 cell tags 指派。Transient loader 明確禁止多 region。 |
| Transient conduction | LIMITED | `model.build_transient_model()`、Test 02 通過；Backward Euler，但單一 region、constant properties、loop 在 case runner。 |
| `rho` | LIMITED | Test 02 transient 使用 constant positive scalar；只允許單一 region。 |
| `cp` | LIMITED | 同上。 |
| Constant `k` | WORKING | Test 01 steady、Test 02 transient、Test 04 multi-region 均通過。 |
| Temperature-dependent `k(T)` | LIMITED | Test 03 steady 3D single-region SNES 通過；Test 05 1D solver也使用 `k(T)`。通用 transient 不支援。 |
| Multiple temperature-dependent materials | NOT IMPLEMENTED | `case.load_case()` 要求 local material只能是唯一 region且不可有 contacts。 |
| Fixed-temperature BC | LIMITED | Test 01-04 通過；loader 強制恰好兩個 constant `fixed_temperature`。 |
| Arbitrary initial temperature | LIMITED | 通用 transient只接受 x-direction split、左右兩個溫度；不是 callable、field file或 region mapping。 |
| Contact resistance | LIMITED | 3D finite-thickness steady layer及獨立1D zero-thickness solver；沒有通用3D interface contact。 |
| Zero-thickness contact resistance | LIMITED | Test 05 steady/transient 1D benchmark通過；`lib/contact.py`，不是FEniCSx 3D framework model。 |
| Thin-layer contact resistance | LIMITED | Test 04 3D steady通過；需要實際 meshed volume，`k = thickness / resistance`。Transient case禁止 contacts。 |
| Time-dependent BC | NOT IMPLEMENTED | `value_K` 直接轉成 PETSc scalar constant；沒有 time callback/update schema。 |
| Heat flux / heat load | NOT IMPLEMENTED | Weak form source固定為零；case loader只接受 fixed temperature。未標記表面只有自然零法向熱流。 |
| Convection | NOT IMPLEMENTED | 沒有 Robin boundary weak form或 YAML schema。 |
| Radiation | NOT IMPLEMENTED | 沒有 `T^4` surface term或 nonlinear radiation model。 |
| Heat switch | NOT IMPLEMENTED | 只在 architecture 示例中出現；loader/model均未使用。 |
| Dump output | WORKING | `dump.py`、Test 01-05 dumps、reader及兩個 validator均通過；cell mapping只限 serial。 |
| Summary output | LIMITED | `analyze()` 回傳全域 summary；Test 01/03/04由 `main.py` 寫 CSV。無通用 writer、per-region summary或通用 transient summary。 |

## 4. Regression test results

為避免 runner 重寫 repository 內既有 `build/` 和 `output/`，測試全部在 WSL `/tmp/thermal-audit-20260909-e` 的隔離副本執行。

### Environment

經由 `scripts/wsl-run.ps1`：

| 元件 | 結果 |
|---|---|
| WSL2 Ubuntu | WORKING |
| Python 3 | WORKING |
| FEniCSx/dolfinx | `0.10.0.post5` |
| Gmsh Python | `4.14.0` |
| petsc4py | `3.24.4` |
| mpi4py | `4.1.1` |

### Cases

| 命令 | 結果 |
|---|---|
| `python3 test/01_steady_bar/main.py` | PASS |
| `python3 test/02_transient_bar/main.py` | PASS |
| `python3 test/02_transient_bar/validate.py` | PASS |
| `python3 test/03_temperature_dependent_bar/main.py` | PASS |
| `python3 test/04_contact_resistance_bar/main.py` | PASS |
| `python3 test/05_steady_nonlinear_contact_bar/main.py` | PASS |
| `python3 test/05_steady_nonlinear_contact_bar/validate.py` | PASS |

重要數值：

- Test 01：midpoint `T` error `5.33e-15 K`；heat flux PASS。
- Test 03：Newton 4 iterations；max `T` error `5.65e-4 K`。
- Test 04：thin-layer contact `k = 0.5 W/(m K)`；contact test PASS。
- Test 05：
  - `T_left = 3 K`、`T_right = 2 K`。
  - Mean `qx = 249.9975 W/m^2`。
  - Zero-thickness contact PASS。
  - 16 組 fixed-time `dx` x `dt` transient slice 完成。
  - 0-500 s transient reference 完成。

所有實際 regression/validation 均無 failure。

## 5. ADR01 minimum required inputs

### 1. 必須現在知道

- Geometry：
  - ADR solid parts 的 3D 尺寸或可重建的簡化幾何。
  - 各部件是否實際相接、重疊、留有間隙。
  - 首版是否能簡化成單一等效 solid region。
- Semantic regions：
  - 每個 volume 的穩定名稱。
  - 固定溫度邊界對應的兩個 surface 名稱。
- Material assignment：
  - 每個 volume 對應材料。
  - 若要使用現有通用 transient，必須決定如何把 ADR 簡化成單一等效材料 region。
- Constant properties：
  - `k` [W/(m K)]
  - `rho` [kg/m^3]
  - `cp` [J/(kg K)]
  - 適用溫度範圍與資料來源。
- Initial temperature：
  - 首版能否用均勻溫度。
  - 目前 schema 沒有直接 uniform initial temperature；現行方式可令左右值相同，但仍依賴 `split_x_m`。
- Thermal BC：
  - 兩個 fixed-temperature surfaces。
  - 各自溫度值。
- Time：
  - total simulation time。
  - 至少一個有物理依據的初始 `dt`。
- Mesh：
  - 全域初始 mesh size。
  - 最小幾何尺寸與預期溫度梯度區域。
- Outputs：
  - 至少指定需要的 dump times。
  - 要觀察的 `T_min`、`T_max`、`T_avg`、cell `T`、`q`。
  - 是否真的需要特定 ADR component/region 的統計；目前 framework沒有直接提供。

### 2. 可以先合理假設

- 所有材料 isotropic。
- `k`、`rho`、`cp` 在首版溫度範圍內為常數。
- 初始溫度均勻。
- 未指定的外表面為 adiabatic，即自然零法向熱流。
- 所有連續相接 solid 具有 perfect thermal contact。
- 暫時使用單一等效 material region。
- 首版使用全域 mesh size，再做至少一輪 mesh/time-step sensitivity。
- `dt` 可先由熱擴散率和最小特徵長度估算，再以時間收斂修正。

這些假設必須在 ADR01 結果中明確標示，不能被解讀為真實裝置條件。

### 3. 第一版可以忽略

在問題目標允許「最小可執行 baseline」的前提下：

- Contact resistance。
- Radiation。
- Convection。
- Temperature-dependent properties。
- Anisotropic conductivity。
- Bolts、threads、微小倒角和非熱關鍵細節。
- 材料資料庫及 reusable config infrastructure。
- MPI parallel dump。
- 通用 3D visualization。
- Per-region automated summary。

### 4. Framework 目前不支援，ADR 真需要時才處理

- 通用多-region transient。
- Transient `k(T)`、`rho(T)`、`cp(T)`。
- Multiple temperature-dependent materials。
- Volumetric heat generation。
- Prescribed surface heat flux或 total heat load。
- Time-dependent temperature/load。
- Convection。
- Radiation。
- Heat switch。
- 通用 3D zero-thickness contact。
- Pressure-/temperature-dependent contact conductance。
- 任意 initial field、region-based IC或從實驗場匯入。
- 超過或少於兩個 fixed-temperature BC 的通用 case validation。

## 6. Contact resistance status

### 現有 representations

#### 3D mesh-resolved thin layer

```text
k_contact = thickness / resistance_m2K_W
```

- Contact 是一個有實際厚度、需要 mesh 的 volume region。
- 使用連續 P1 temperature。
- 只整合在 steady multi-region framework。
- Test 04 已以解析串聯熱阻驗證。

#### 1D zero-thickness interface

```text
q = h_c (T_left - T_right)
h_c = 1 / R_c
```

- 使用兩個空間位置相同但互不共享的 interface nodes。
- 可產生真正溫度 jump。
- Test 05 已驗證 steady nonlinear與數值 transient。
- 只存在於 `lib/contact.py` 的獨立1D NumPy solver。

### 對真正 ADR assembly 是否足夠

目前不足以一般化處理真正 3D ADR assembly：

- Thin layer可作為工程近似，但會引入人工幾何厚度和 mesh要求。
- 1D zero-thickness模型不能直接套用至任意3D接觸面。
- 尚無 nonmatching interface、surface pairing、Nitsche/mortar/DG coupling。
- 尚無 contact pressure、surface roughness、temperature-dependent conductance。

### 忽略 contact resistance 的物理假設

若相鄰 solids 使用 conforming、共享 nodes 的 mesh而不加入 contact resistance，等價於：

- Perfect thermal contact。
- Interface temperature連續：`T1 = T2`。
- Contact resistance：`R_c = 0`。
- Contact conductance：`h_c -> infinity`。
- 不存在額外 interface temperature jump。

這通常會高估跨接觸面的熱耦合、低估溫差。

### 未來最少需要的 contact input

- 面積比接觸熱阻 `R_c` [m^2 K/W]，或等價 conductance `h_c` [W/(m^2 K)]。
- 接觸材料配對。
- 適用溫度範圍。
- 接觸壓力或 bolt preload，如果資料顯示相關。
- 表面處理、粗糙度、氧化層/鍍層。
- 是否使用 thermal grease、indium、epoxy等 interstitial layer。
- 真實有效接觸面積。
- 若採薄層近似：模型厚度及如何保持指定面積比熱阻。

最佳資料是同類材料、表面處理、溫度和 preload 下的實測值；其次才是有相同條件的文獻範圍。

## 7. `run/` vs `runs/` finding

- `arch.md` 和 `steps.md` 的正式架構主要使用 `runs/<name>/`，並提到未來 `runs/baseline/`。
- 本機實際存在 `run/01_ADR01/`。
- Repository root 沒有 `runs/`。
- `lib/` 沒有對 `run/` 或 `runs/` 的 hard-coded dependency。
- Case path全部由各案例 `main.py` 的 `Path(__file__).resolve().parent` 決定，因此任一名稱技術上都可運作。
- 文件內「run/test」有時是一般語意，不是固定目錄 API。

結論：這是 documentation/layout 命名差異，不是現有 runtime blocker。本輪不應 rename。

## 8. Blocking issues before ADR01

對「可以開始整理 ADR01」沒有環境 blocker；對「建立具物理代表性的完整 ADR transient model」則有下列 blockers：

1. 真實 ADR geometry、semantic part list及材料對應尚需輸入。
2. 現行通用 transient只支援單一 region；真正 assembly通常是多材料。
3. 只有兩個常數 fixed-temperature BC。
4. 若 ADR 是由 internal heat load驅動，現行 framework無法表示。
5. 若主要散熱機制是 convection/radiation，現行 framework無法表示。
6. 若冷端或 heater隨時間改變，現行 framework無法表示。
7. 若 interface熱阻對結果重要，現行通用3D transient沒有可直接使用的 contact model。
8. `analyze()` hard-code `hot_end`、`cold_end`，ADR geometry必須暫時沿用這兩個名稱，否則需要未來再改 implementation。
9. Arbitrary initial field未實作。
10. Dump end-to-end只適合 serial。

因此，在不擴充 framework 的情況下，ADR01 首版必須限定為：

```text
3D geometry
+ 單一等效 material
+ constant k/rho/cp
+ 兩個 constant fixed-temperature boundaries
+ 其餘表面 adiabatic
+ perfect internal thermal contact
+ no heat source/load
```

若這個模型無法代表 ADR 的主要加熱與散熱機制，就不應把它當成預測模型，只能當 geometry/mesh/transient pipeline smoke test。

## 9. Recommended next action

下一步先不要改 framework。先取得並確認一份最小 ADR01 input sheet：

- 簡化幾何與尺寸。
- 哪些 parts 必須保留。
- 材料對應及 `k`、`rho`、`cp`。
- 初始溫度。
- 兩個可合理視為固定溫度的表面及溫度。
- 是否存在不可忽略的 heater/heat load。
- 是否存在不可忽略的 convection/radiation。
- 目標 transient duration及關注時間尺度。
- 預期輸出時間與關注位置。

接著先判斷「單一等效材料＋兩個 fixed-T BC＋adiabatic其餘表面」是否仍能回答第一版 ADR 問題：

- 若可以，直接以現有 Test 02 pattern建立最小 ADR01。
- 若不可以，先只實作第一個真正必要的 framework gap。最可能是 multi-region transient 或 heat load；不要同時建立完整 config/material/contact infrastructure。

**READY FOR ADR01: YES WITH LIMITATIONS**

理由：環境、3D mesh、FEniCSx transient solver、dump pipeline及現有 regressions都正常，可開始一個高度簡化的 ADR01 baseline；但真正多材料、有熱負載、複雜邊界或3D contact的 ADR transient assembly 尚超出目前 framework 能力。

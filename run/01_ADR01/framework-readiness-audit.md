# Thermal Simulation Framework Readiness Audit for ADR01

> 更新（2026-09-10）：material-property extension 已完成。現在支援統一
> constant/table/Python property representation，以及 multi-region constant-property
> transient。本文件下列結論已同步到目前 implementation；temperature-dependent
> transient 已由Test 06 nonlinear regression實作並驗證。

## 1. Executive summary

目前 repository 是一個「case-driven、由案例自行編排 workflow」的精簡 thermal FEM framework，不是通用模擬器或統一 CLI。

實際已驗證的核心能力：

- Gmsh 建立與載入 3D mesh。
- FEniCSx P1 穩態熱傳。
- 穩態多 region、各 region 常數 isotropic `k`。
- 多 region、各 region 常數 `k`、`rho`、`cp` 的 transient Backward Euler。
- 單一 region steady `k(T)` 與 PETSc SNES/Newton。
- 3D mesh-resolved thin-layer contact resistance。
- 獨立的 1D zero-thickness nonlinear contact benchmark。
- Cell-centroid dump、dump series reader、全域/per-region summary 與selected-surface總熱流。

主要限制：

- Transient支援constant或temperature-dependent `k/rho/cp`，但runner仍需明確選builder。
- 只支援fixed-temperature boundary type，但可設定一個以上semantic surfaces。
- Heat load、specified heat flux、convection、radiation、heat switch 都未實作。
- 3D zero-thickness contact 尚未實作。
- Transient loop、輸出排程及 summary 寫出都由各案例 `main.py` 自行處理。
- Dump cell-ID mapping 只支援 serial execution。

因此可以開始 ADR01 的幾何、semantic tagging、multi-region材料輸入整理及constant-property
transient baseline，並可使用temperature-dependent `k/rho/cp`；但目前仍不能直接表達
有熱負載或複雜熱邊界的 ADR assembly。

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
- 沒有通用 3D mesh/dump merge visualizer。
- `loads`、`heat_switch` YAML 是未來示意，loader 不接受也不使用它們。
- STEP/BREP CAD import workflow 尚未建立作為 framework API。

### 主要 `lib/*.py` 實際責任

| 檔案 | 實際責任 |
|---|---|
| `case.py` | 載入及狹義驗證 `case.yaml`；另有 Test 01 型式的 `expected.yaml` validator。 |
| `mesh.py` | 依 geometry source hash/cache key 建立或重用 Gmsh mesh；載入 FEniCSx mesh；serial-only Gmsh/FEniCSx cell-ID 對應。 |
| `materials.py` | 載入並統一 constant、CSV/table、Python callable property evaluator；依 cell tags 建立 `k/rho/cp` DG0 constant fields；薄層以 `k = thickness / resistance` 轉換。 |
| `model.py` | 建立steady linear/nonlinear與multi-region linear/nonlinear transient weak forms；建立一個以上fixed-T Dirichlet BC。 |
| `solve.py` | PETSc preonly/LU linear solve；固定選項的 SNES/Newton nonlinear solve。 |
| `analyze.py` | 計算cell-centroid `T`、`q = -k grad(T)`、全域/per-region temperature statistics、平均熱流與caller-selected surface heat flow。 |
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

- CSV或Python property file：用於steady、單一region的`k(T)`；constant case不需要額外檔案。
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
  - transient：每個region必須有positive `k`、`rho`、`cp` properties
- `contacts`
  - 只接受 `thin_layer_resistance`
  - 必須指定已有 volume region
  - 正值 `resistance_m2K_W`
  - 正值 `thickness_m`
- `boundary_conditions`
  - 至少一個
  - 每個必須是 `fixed_temperature`
  - numeric `value_K`
- transient `time`
  - 正值 `dt_s`、`end_s`
  - `initial_condition.type: uniform`與`value_K`，或legacy `split_x`欄位

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
| Multiple material regions | WORKING | Test 04驗證3D steady；Test 06驗證multi-region constant-property transient；property fields依cell tags指派。 |
| Transient conduction | WORKING | Test 02及Test 06通過；Backward Euler支援multi-region constant與temperature-dependent properties，loop仍在case runner。 |
| `rho` | WORKING | Multi-region constant與transient `rho(T)`由Test 06驗證。 |
| `cp` | WORKING | Multi-region constant與transient `cp(T)`由Test 06驗證。 |
| Constant `k` | WORKING | Test 01 steady、Test 02 transient、Test 04 multi-region 均通過。 |
| Temperature-dependent `k(T)` | WORKING | Test 03 steady與Test 06 multi-region transient SNES通過。 |
| Multiple temperature-dependent materials | WORKING | Test 06 nonlinear transient使用multi-region property expressions。 |
| Fixed-temperature BC | LIMITED | Test 01-04及07通過；一個以上constant fixed-temperature surfaces，其他type未實作。 |
| Arbitrary initial temperature | LIMITED | 支援uniform與legacy split-x；不是callable、field file或region mapping。 |
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
  - 首版需要保留哪些獨立material regions。
- Semantic regions：
  - 每個 volume 的穩定名稱。
  - 固定溫度邊界對應的兩個 surface 名稱。
- Material assignment：
  - 每個 volume 對應材料。
  - 每個semantic region對應哪一個named material。
- Constant properties：
  - `k` [W/(m K)]
  - `rho` [kg/m^3]
  - `cp` [J/(kg K)]
  - 適用溫度範圍與資料來源。
- Initial temperature：
  - 首版能否用均勻溫度。
  - 使用`type: uniform`與`value_K`。
- Thermal BC：
  - 一個以上 fixed-temperature surfaces。
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
  - 需要哪些ADR component/region statistics與surface heat flows。

### 2. 可以先合理假設

- 所有材料 isotropic。
- `k`、`rho`、`cp` 在首版溫度範圍內為常數。
- 初始溫度均勻。
- 未指定的外表面為 adiabatic，即自然零法向熱流。
- 所有連續相接 solid 具有 perfect thermal contact。
- 各region首版使用constant `k/rho/cp`，即使property資料來源已有table/Python版本。
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

### 4. Framework 目前不支援，ADR 真需要時才處理

- Volumetric heat generation。
- Prescribed surface heat flux或 total heat load。
- Time-dependent temperature/load。
- Convection。
- Radiation。
- Heat switch。
- 通用 3D zero-thickness contact。
- Pressure-/temperature-dependent contact conductance。
- 任意 initial field、region-based IC或從實驗場匯入。

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

## 7. `run/` directory decision

- 實際 real-case 目錄採 `run/<name>/`；目前只有 `run/01_ADR01/` planning documents。
- `arch.md`、`steps.md` 與 manual 已同步採用 `run/`。
- `lib/` 沒有對該目錄名稱的 hard-coded dependency；case path仍由各案例 `main.py` 決定。

## 8. Blocking issues before ADR01

對「可以開始整理 ADR01」沒有環境 blocker；對「建立具物理代表性的完整 ADR transient model」則有下列 blockers：

1. 真實 ADR geometry、semantic part list及材料對應尚需輸入。
2. ADR material table必須涵蓋完整預期溫度範圍，否則nonlinear solve會因domain validation失敗。
3. 只能使用constant fixed-temperature BC，但數量可為一個以上。
4. 若 ADR 是由 internal heat load驅動，現行 framework無法表示。
5. 若主要散熱機制是 convection/radiation，現行 framework無法表示。
6. 若冷端或 heater隨時間改變，現行 framework無法表示。
7. 若 interface熱阻對結果重要，現行通用3D transient沒有可直接使用的 contact model。
8. Callable/region-mapped arbitrary initial field未實作；uniform baseline已支援。
9. Dump end-to-end只適合 serial。

因此，在不擴充 framework 的情況下，ADR01 首版必須限定為：

```text
3D geometry
+ 一個或多個material regions
+ 各region constant k/rho/cp
+ 一個以上 constant fixed-temperature boundaries
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
- 一個以上可合理視為固定溫度的表面及溫度。
- 是否存在不可忽略的 heater/heat load。
- 是否存在不可忽略的 convection/radiation。
- 目標 transient duration及關注時間尺度。
- 預期輸出時間與關注位置。

接著先判斷「multi-region constant properties＋一個以上fixed-T BC＋adiabatic其餘表面」是否仍能回答第一版 ADR 問題：

- 若可以，直接以 Test 07 pattern建立最小 ADR01。
- 若需要internal heat load或更複雜BC，再將第一個真正必要的物理缺口獨立處理；
  不要同時加入contact或其他物理。

**READY FOR ADR01: YES WITH LIMITATIONS**

理由：環境、3D mesh、multi-region constant-property transient、統一material properties、
dump pipeline、temperature-dependent transient及現有regressions都正常；但有熱負載、
複雜邊界或3D contact的 ADR assembly 尚超出目前framework能力。

# ADR Thermal Simulation Architecture

> 原則：**如無必要勿增實體**。  
> 目標不是做通用 FEM 平台，而是做一套夠用、可驗證、可延伸的 ADR 熱傳模擬工具。

---

## 1. 核心概念

整套專案分成兩層：

```text
lib/              = simulation engine
runs/<name>/      = 一次實際模擬
test/<name>/      = 一次驗證模擬
```

可類比 LAMMPS：

```text
lib/                    ≈ LAMMPS src/
run/test 裡的 main.py   ≈ LAMMPS infile
```

也就是：

- `lib/`：負責「怎麼算」
- `main.py`：負責「這次要做什麼、依什麼順序做」
- `geometry.py`：負責「系統長什麼樣」
- `case.yaml`：負責「這次物理參數是什麼」

---

## 2. 專案結構

```text
adr-thermal/
├─ arch.md
├─ steps.md
├─ dump-format.md
│
├─ lib/
│  ├─ case.py
│  ├─ mesh.py
│  ├─ model.py
│  ├─ solve.py
│  ├─ analyze.py
│  ├─ dump.py
│  ├─ dump_reader.py
│  └─ plotting.py
│
├─ postprocess/
│  └─ plot_dump.py
│
├─ runs/
│  └─ baseline/
│     ├─ main.py
│     ├─ geometry.py
│     ├─ case.yaml
│     ├─ build/
│     └─ output/
│
└─ test/
   ├─ 01_steady_bar/
      ├─ main.py
      ├─ geometry.py
      ├─ case.yaml
      ├─ expected.yaml
      ├─ build/
      └─ output/
   └─ 02_transient_bar/
      ├─ main.py
      ├─ geometry.py
      ├─ case.yaml
      ├─ validate.py
      ├─ build/
      ├─ output/dump/
      └─ validation/
```

目前不要新增：

```text
interfaces/
tools/
utils/
config/
core/
manager/
registry/
factory/
physics/
```

除非之後真的出現明確需求。

---

## 3. 一個 run / test 的資料流

```text
main.py
  → geometry.py / lib/mesh.py
  → lib/case.py
  → lib/model.py
  → lib/solve.py
  → lib/analyze.py
  → lib/dump.py
  → output/dump/

output/dump/
  → lib/dump_reader.py
  → postprocess/plot_dump.py 或案例自己的 validate.py
```

`main.py` 只負責串接流程，不負責重新實作 FEM。

不同 run / test 可以有不同 `main.py`。

---

## 4. 每次新模擬通常改什麼

一般情況下：

```text
main.py
geometry.py
case.yaml
```

其中：

- workflow 不變時，`main.py` 通常可以直接沿用
- geometry 不變時，只改 `case.yaml` 即可
- case 改變時，不應重新 mesh

核心規則：

```text
geometry 改變  → rebuild mesh
case 改變      → reuse mesh，重新 model + solve
```

---

## 5. `build/` 與 `output/`

### `build/`

存 geometry / mesh 的可重用產物，例如：

```text
mesh.msh
tags.json
build.json
```

只在 geometry 或 mesh 設定改變時重建。`build.json` 保存對應的 `MESH_ID`，供 dump 與後處理核對：cache reuse 沿用同一 ID，mesh rebuild 產生新 ID。

責任分工：

```text
build/mesh.msh
  = mesh topology
  = vertices / coordinates
  = element type / cell connectivity
  = physical / region tags

output/dump/<timestep>.dump
  = 該 mesh 上的物理場 snapshot
  = cell_ID / region_ID
  = sampling x y z
  = T / qx / qy / qz / qmag
```

dump 不重複保存 topology。dump 中的 `x y z` 只是 sampling location，例如 cell centroid，不能描述 cell 形狀。

### `output/`

存物理解題結果，例如：

```text
resolved_case.yaml
dump/
  ├─ 0.dump
  ├─ 1.dump
  └─ ...
summary.csv
run.log
```

場資料採用類似 LAMMPS custom dump 的文字格式。每個 dump 是一個 timestep 的空間快照，例如：

```text
ITEM: TIMESTEP
0
ITEM: TIME
0.0
ITEM: MESH_ID
287b3fe991f40c0a2526069ce8487657652e2237323ebc118b28d6f83db9b89f
ITEM: NUMBER OF CELLS
209
ITEM: FIELDS cell_ID region_ID x y z T qx qy qz qmag
0 1 0.0025 0.005 0.005 3.925 300.0 0.0 0.0 300.0
...
```

規則：

- `cell_ID` 是同一 `MESH_ID` 下跨 timestep 穩定的 finite-element cell 編號。
- `x y z` 是該點座標。
- `region_ID` 識別 semantic geometry region；材料指定仍來自 `case.yaml`。
- `T` 是溫度，`qx qy qz` 是熱流向量分量，`qmag` 是熱流大小。
- 欄位順序由 `main.py` 指定；`analyze.py` 準備物理資料，`dump.py` 只寫出指定欄位。
- 穩態只寫一份 `0.dump`；暫態依輸出頻率寫 `{timestep}.dump`。
- timestep 是整數步數；物理時間由 `time = timestep * dt` 得到並寫入 header。
- dump 目錄、輸出頻率與欄位由各 run/test 的 `main.py` 設定，不放入 physics `case.yaml`。

第一版只支援 cell dump。座標為 cell centroid，`T` 在 centroid 評估，熱流由 `analyze.py` 在 cell 上計算。nodes 等出現明確需求後再加入。

`cell_ID` 由 mesh pipeline 建立並維持。不得假定它天然等於 Gmsh element tag 或 FEniCSx local cell index，因為 mesh import 可能重新排序。它的唯一契約是能可靠解析回同一 `MESH_ID` 的 `mesh.msh` 中某一實際 cell；第一版採能通過 Test 01 mapping 驗證的最簡方法，不建立通用 ID manager 或 mapping framework。

cell 的 element type、vertex coordinates 與 connectivity 由對應的 `mesh.msh` 定義；dump 不假設 cell 是四面體、六面體或其他特定形狀。後處理若要畫真正的 3D mesh、surface 或 slice，必須同時讀取 `build/mesh.msh` 與 dump，先驗證兩者 `MESH_ID` 相同，再依 `cell_ID` 對應 field values。

完整 header、欄位定義、單位與檔名規則以 [`dump-format.md`](dump-format.md) 為唯一規格。

`summary.csv` 只保存區域統計與總熱流等彙總量，不取代逐 cell dump。第一版由 `main.py` 使用 Python 標準庫 `csv` 將 `analyze.py` 回傳的 summary data 寫出，不為此新增另一層 abstraction。XDMF/HDF5 可作為選配輸出，不是 dump 的必要部分。

---

## 6. `lib/` 各檔案責任

### `case.py`

讀取與檢查 `case.yaml`。

### `mesh.py`

建立或載入 mesh，並提供 semantic region / facet tags。

### `model.py`

定義 PDE 與 weak form。

目前實作：

```yaml
model:
  type: steady_conduction | transient_conduction
```

steady conduction：

$$
\nabla\cdot(k\nabla T)+Q=0
$$

transient conduction 使用 backward Euler：

$$
\rho c_p\frac{T^{n+1}-T^n}{\Delta t}
=\nabla\cdot(k\nabla T^{n+1}).
$$

### `solve.py`

只負責解已建立好的 FEM problem。

### `analyze.py`

計算衍生物理量，例如：

- $T(\mathbf x)$
- $\mathbf q=-k\nabla T$
- region 平均 / 最大 / 最小溫度
- tagged surface 的 total heat flow
- region 統計資料

$$
\dot Q_S=
\int_S \mathbf q\cdot\mathbf n\,dA
$$

### `dump.py`

只負責把 `analyze.py` 已準備好的資料依指定 fields 序列化成 `{timestep}.dump`。不計算 Fourier law、surface integral 或其他物理量，也不負責畫圖。

示意：

```python
dump = {
    "directory": case_dir / "output" / "dump",
    "every": 10,
    "fields": ["cell_ID", "region_ID", "x", "y", "z", "T", "qx", "qy", "qz", "qmag"],
}
```

### `dump_reader.py`

獨立解析 LAMMPS-like dump header、metadata 與欄位資料，並讀取依 `TIME`
排序、具有相同 `MESH_ID` 的 dump series。它不依賴 FEM solver。

### `plotting.py`

保存已實際重用的後處理繪圖小工具。目前只有通用 scalar-field heatmap；不預先
建立尚未使用的 vector-field framework。

### `postprocess/plot_dump.py`

獨立讀取既有 dump，再用 Python 產生圖片或衍生 CSV。需要 mesh topology 的圖形時，同時讀取對應的 `build/mesh.msh`，驗證 `MESH_ID` 後依 `cell_ID` 合併資料。模擬本身不自動畫圖；重畫圖片不應重新求解 FEM。

---

## 7. `case.yaml`

`case.yaml` 描述 physics，不描述 CAD。

示意：

```yaml
model:
  type: steady_conduction

regions:
  hot_plate:
    k: 500.0

  support_1:
    k: 0.2

boundary_conditions:
  hot_plate_fixed_T:
    type: fixed_temperature
    value_K: 4.0

loads:
  sample_load_surface:
    type: total_heat
    value_W: 0.001

contacts:
  bus_to_cold_stage:
    type: contact_conductance
    h_W_m2K: 500.0

heat_switch:
  state: off
  G_on_W_K: 0.1
  G_off_W_K: 1.0e-4
```

目前：

- contact 直接放在 case
- heat switch 直接放在 case
- 不建立 interface database

---

## 8. 材料資料

只存真正需要跨 run 重用的材料資料。

第一版 constant-$k$ 模型可以完全不需要材料檔。

未來需要跨 run 重用的 $k(T)$ 或 $c_p(T)$ 時，才建立例如：

```text
lib/materials/
└─ copper/
   ├─ k.csv
   └─ sources.md
```

不要先建立中央 materials registry。

---

## 9. Geometry 與 mesh cache

第一版可使用：

```text
geometry.py
```

配合 Gmsh Python API。

未來若取得複雜 CAD，也可直接改用：

```text
geometry.step
geometry.brep
```

不必用 Python 重畫。

geometry 必須建立 semantic tags，例如：

```text
hot_plate
magnet
ggg
thermal_bus
cold_stage
support_1
hot_plate_fixed_T
support_1_heatflow
```

`mesh.py` 應提供最小功能：

```python
ensure_mesh(...)
```

邏輯：

```text
cache 有效   → load mesh
cache 無效   → rebuild mesh
```

---

## 10. 未來擴展

只有真正需要時才加入。

### Transient（已由 Test 02 驗證最小版本）

$$
\rho c_p\frac{\partial T}{\partial t}
=
\nabla\cdot(k\nabla T)+Q
$$

目前 `test/02_transient_bar` 已驗證 constant-property transient conduction、分段初始
溫度、固定溫度邊界與多 timestep dump。輸出時點由案例 `main.py` 決定，可採固定
間隔，也可像 Test 02 一樣在早期密集輸出並另存最終狀態。

`validate.py` 只讀 dumps，將 3D cell samples 沿橫截面平均後，與獨立的一維 Fourier
解析解比較並畫出 $T(x,t)$ 與 $q_x(x,t)$；修改繪圖不會重新求解 FEM。

### Fluid

真的加入流體、而且 `model.py` 已經明顯過大時，再考慮拆成：

```text
lib/physics/
├─ thermal.py
├─ fluid.py
└─ coupled.py
```

現在不要先建立。

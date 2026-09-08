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
│
├─ lib/
│  ├─ case.py
│  ├─ mesh.py
│  ├─ model.py
│  ├─ solve.py
│  ├─ analyze.py
│  └─ materials/
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
   └─ 01_steady_bar/
      ├─ main.py
      ├─ geometry.py
      ├─ case.yaml
      ├─ expected.yaml
      ├─ build/
      └─ output/
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
  │
  ├─ geometry.py
  │      ↓
  │   lib/mesh.py
  │      ↓
  │    build/
  │
  ├─ case.yaml
  │      ↓
  │   lib/case.py
  │
  ├─ lib/model.py
  │      ↓
  │   weak form
  │
  ├─ lib/solve.py
  │      ↓
  │   FEM solution
  │
  └─ lib/analyze.py
         ↓
      output/
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

只在 geometry 或 mesh 設定改變時重建。

### `output/`

存物理解題結果，例如：

```text
resolved_case.yaml
temperature.*
heat_flux.*
summary.csv
run.log
```

---

## 6. `lib/` 各檔案責任

### `case.py`

讀取與檢查 `case.yaml`。

### `mesh.py`

建立或載入 mesh，並提供 semantic region / facet tags。

### `model.py`

定義 PDE 與 weak form。

目前只實作：

```yaml
model:
  type: steady_conduction
```

steady conduction：

$$
\nabla\cdot(k\nabla T)+Q=0
$$

### `solve.py`

只負責解已建立好的 FEM problem。

### `analyze.py`

固定後處理，例如：

- $T(\mathbf x)$
- $\mathbf q=-k\nabla T$
- region 平均 / 最大 / 最小溫度
- tagged surface 的 total heat flow

$$
\dot Q_S=
\int_S \mathbf q\cdot\mathbf n\,dA
$$

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

## 8. `materials/`

只存真正需要跨 run 重用的材料資料。

第一版 constant-$k$ 模型可以完全不需要材料檔。

未來需要 $k(T)$ 時再加入，例如：

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

### Transient

$$
\rho c_p\frac{\partial T}{\partial t}
=
\nabla\cdot(k\nabla T)+Q
$$

屆時修改 `model.py` / `solve.py`。

### Fluid

真的加入流體、而且 `model.py` 已經明顯過大時，再考慮拆成：

```text
lib/physics/
├─ thermal.py
├─ fluid.py
└─ coupled.py
```

現在不要先建立。

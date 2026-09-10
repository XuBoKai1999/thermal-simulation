# ADR01 Architecture

> 原則：如無必要勿增實體。  
> `run/01_ADR01` 是一個具體 ADR 熱傳案例，不是新的 thermal framework。  
> 通用能力留在 repo root；ADR01 只描述本案 geometry、physics、workflow 與 validation。

## 1. 目標

ADR01 的第一個可交付版本只做 3D transient heat conduction：

$$
\rho(T)c_p(T)\frac{\partial T}{\partial t}
=
\nabla\cdot\left(k(T)\nabla T\right)
$$

第一版允許先使用 constant properties，再逐步換成可信的 $k(T)$、$c_p(T)$。

Baseline 暫定：

- 初始溫度：整體 $T_0=4\ \mathrm{K}$
- 4 K platform：fixed temperature
- ADR cold boundary：fixed temperature，第一版可先設 $1\ \mathrm{K}$
- 多材料、多 region、3D geometry
- 零體積熱源
- 未指定外表面：adiabatic / zero normal heat flux
- region 間第一版視為 perfect thermal contact

第一版不處理：

- contact resistance
- heat switch $G_{\rm on}/G_{\rm off}$
- radiation
- convection
- prescribed heat load / heat-flux BC
- time-dependent BC
- magnetic refrigeration / MCE 本體
- anisotropic conductivity

上述項目只有在 baseline 跑通且實際需求成立後才加入。

---

## 2. 專案分層

```text
thermal-simulation/
├─ lib/                         # 通用 simulation engine
├─ materials/                   # 全 repo 共用材料庫
├─ scripts/
│  └─ list-materials.py         # 列出可用材料
├─ test/                        # framework regression
└─ run/
   └─ 01_ADR01/
      ├─ arch.md
      ├─ steps.md
      ├─ framework-readiness-audit.md
      ├─ geometry.py
      ├─ case.yaml
      ├─ main.py
      ├─ build/
      └─ output/
```

`run/01_ADR01` 不自行建立材料資料庫，也不複製 `lib/`。

若之後需要專門的 convergence / validation script，等 baseline 能跑後再增加：

```text
validate.py
```

目前不要預先建立。

---

## 3. ADR01 每個檔案的責任

### `geometry.py`

只負責：

- ADR01 的 3D geometry
- geometric parameters
- Gmsh volumes
- physical volume tags
- physical surface tags
- conformal interfaces
- mesh size

不負責：

- 材料數值
- boundary temperature
- time step
- solver
- heat-transfer equations

每個可區分的 thermal body 應有 semantic region name，例如：

```text
upper_plate
cold_stage
support_1
support_2
shield
...
```

實際名稱由真實 ADR 結構決定；沒有必要的零件不要虛構。

預期 perfect-contact 的相鄰 solid 必須使用 shared/conformal topology，不得只是 coincident surfaces。

---

### `case.yaml`

只負責本次物理 case：

- model type
- material assignment
- boundary conditions
- initial condition
- time step
- end time

概念上：

```yaml
model:
  type: transient_conduction

materials:
  copper:
    file: ../../materials/nist/copper_ofhc_rrr100/material.yaml

regions:
  upper_plate:
    material: copper

boundary_conditions:
  platform_4K:
    type: fixed_temperature
    value_K: 4.0

  adr_1K:
    type: fixed_temperature
    value_K: 1.0

time:
  initial_condition:
    type: uniform
    value_K: 4.0

  dt_s: ...
  end_s: ...
```

`file:` external material reference 是本案希望加入的最小 shared-material 功能；若 framework 尚未支援，由前置步驟補上。

---

### `main.py`

ADR01 的 executable workflow，類似 LAMMPS infile。

只串接：

```text
load case
→ ensure/load mesh
→ build model
→ solve transient
→ analyze
→ dump
→ summary
```

不得在 `main.py` 重新實作：

- FEM weak form
- material interpolation
- dump format
- mesh parser
- generic analysis

需要通用能力時，先判斷是否真的是 framework 缺陷；只有必要時才改 `lib/`。

---

### `build/`

geometry / mesh cache：

```text
mesh.msh
tags.json
build.json
```

geometry 改變才 rebuild。

若未來 `geometry.py` 讀取外部 CAD/STEP，外部檔案版本必須納入 mesh cache key。

---

### `output/`

只放 run result：

```text
resolved_case.yaml
dump/
summary.csv
run.log
```

後續 convergence / validation 結果可再加入，但不要先建立多餘層級。

---

## 4. 共用 `materials/`

材料不屬於 ADR01，而屬於整個 thermal-simulation repo。

建議最小結構：

```text
materials/
└─ nist/
   ├─ copper_ofhc_rrr100/
   │  ├─ material.yaml
   │  ├─ k.csv
   │  └─ cp.csv
   ├─ stainless_304/
   │  ├─ material.yaml
   │  ├─ k.csv
   │  └─ cp.csv
   ├─ aluminum_6061_t6/
   │  ├─ material.yaml
   │  ├─ k.csv
   │  └─ cp.csv
   └─ g10_cr/
      ├─ material.yaml
      ├─ k.csv
      └─ cp.csv
```

沒有另外建立 registry database。

每個 `material.yaml` 就是該材料的 source of truth；`scripts/list-materials.py` 直接掃描 `materials/**/material.yaml`。

### `material.yaml` 至少保存

```yaml
name: Copper OFHC RRR100
source: NIST
reference: ...
validity:
  k_K: [4, 300]
  cp_K: [4, 300]

rho:
  type: constant
  value: ...

k:
  type: table
  file: k.csv
  x: T_K
  y: k_W_mK

cp:
  type: table
  file: cp.csv
  x: T_K
  y: cp_J_kgK
```

source metadata 與 numerical data 必須可追溯。

### NIST fit 的處理

NIST 網頁常提供 curve-fit coefficients，而不是原始 CSV。

第一版材料匯入可：

```text
NIST published fit
→ 依其有效範圍產生足夠密的 table
→ 保存為 CSV
→ framework 使用既有 table interpolation
```

不要默默外插超過來源有效範圍。

尤其 ADR 目標到 $1\ \mathrm{K}$；若 NIST property 只保證到 $4\ \mathrm{K}$ 或更高，該材料必須標記為資料缺口，另找可靠的 1–4 K 來源。

---

## 5. Material discovery

增加：

```text
scripts/list-materials.py
```

執行：

```powershell
.\scripts\wsl-run.ps1 "python3 scripts/list-materials.py"
```

輸出至少包含：

```text
material
source
k range
cp range
rho available
path
```

例如：

```text
Copper OFHC RRR100 | NIST | k: 4-300 K | cp: 4-300 K | rho: yes | materials/nist/...
```

這支程式只掃描 metadata，不建立 registry、不 import FEniCSx、不修改材料。

---

## 6. Data flow

```text
materials/
    ↓
case.yaml
    ↓
geometry.py ─→ mesh cache
    ↓
lib/case.py
    ↓
lib/materials.py
    ↓
lib/model.py
    ↓
lib/solve.py
    ↓
lib/analyze.py
    ↓
dump + summary
```

ADR01 應優先 reuse 已驗證 framework。

---

## 7. Baseline verification

ADR01 至少必須檢查：

### Geometry

- 所有 intended regions 都存在
- semantic tags 正確
- perfect-contact interfaces conformal/shared
- mesh 沒有 disconnected coincident bodies

### Numerical

至少做：

$$
dx\text{-convergence}
$$

與

$$
dt\text{-convergence}
$$

並觀察主要 region：

$$
T_{\min},\quad T_{\max},\quad T_{\rm avg}
$$

以及重要 surface：

$$
\dot Q=\int_S\mathbf q\cdot\mathbf n\,dA
$$

### Energy sanity

暫態應檢查：

$$
\Delta U
\approx
-\int\sum_S \dot Q_S\,dt
$$

constant property 時：

$$
U=\int_\Omega \rho c_p T\,dV
$$

temperature-dependent $c_p(T)$ 時不可直接沿用 constant-$c_p$ 形式，需使用一致的內能定義。

---

## 8. ADR01 完成定義

ADR01 baseline 完成必須同時滿足：

1. 真實簡化 ADR geometry 已建立。
2. region/material mapping 可追溯。
3. mesh interface topology 正確。
4. transient 4 K → 1 K simulation 可完整執行。
5. $T(\mathbf x,t)$ 與 $\mathbf q(\mathbf x,t)$ 可輸出。
6. region statistics 與重要 surface heat flow 可取得。
7. mesh/time-step convergence 無明顯異常。
8. energy balance 無明顯非物理失衡。
9. 所有使用的材料數據來源與有效溫區有紀錄。

完成 baseline 前，不增加第二階段物理。

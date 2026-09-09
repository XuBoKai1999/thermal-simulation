# ADR Thermal Simulation Construction Steps

> 原則：**如無必要勿增實體**。  
> 每個 Stage 只完成目前需要的一件事。  
> 每完成一個 Stage 就停止，先讓人用肉眼檢查，再進下一階段。

目前狀態：Stage 0–6 已由 Test 01 完成；另已完成 Test 02 暫態棒、Test 03
temperature-dependent material、Test 04 thin-layer contact resistance，以及 Test 05
一維 nonlinear zero-thickness contact 驗證。尚未進入
Stage 7 ADR baseline。

---

# Stage 0 — 建立最小骨架

## 要做什麼

建立：

```text
adr-thermal/
├─ arch.md
├─ steps.md
├─ lib/
│  ├─ case.py
│  ├─ mesh.py
│  ├─ model.py
│  ├─ solve.py
│  └─ analyze.py
└─ test/
   └─ 01_steady_bar/
      ├─ main.py
      ├─ geometry.py
      ├─ case.yaml
      ├─ expected.yaml
      ├─ build/
      └─ output/
```

目前不要建立 `runs/baseline/`。

也不要新增：

```text
utils/
config/
core/
manager/
registry/
factory/
```

## 成功條件

- Python 能 import `dolfinx`
- Python 能 import `gmsh`
- `test/01_steady_bar/main.py` 能 import `lib/` 中各模組
- 尚未真正解 PDE

## 肉眼檢查

執行：

```text
python main.py
```

terminal 應明確顯示：

```text
dolfinx: OK
gmsh: OK
project imports: OK
```

並直接查看目錄樹，確認沒有多出不需要的檔案或資料夾。

---

# Stage 1 — 建立 Test 01 geometry 與 mesh

## 要做什麼

只完成：

```text
test/01_steady_bar/geometry.py
lib/mesh.py
test/01_steady_bar/main.py
```

建立一根最簡單的 3D 長方柱。

至少標記：

```text
bar
hot_end
cold_end
```

其中：

- `bar`：volume
- `hot_end`：一端面
- `cold_end`：另一端面

`main.py` 目前只負責：

```text
geometry.py
→ lib/mesh.py
→ build/
```

不要讀 case，不要解 PDE。

## 成功條件

第一次執行：

```text
python main.py
```

應建立：

```text
build/mesh.msh
build/tags.json
```

第二次執行時，geometry 未變：

```text
mesh cache valid, reuse existing mesh
```

不重新 mesh。

## 肉眼檢查

### 1. 用 Gmsh 開 `build/mesh.msh`

應看到：

- 一根乾淨直棒
- mesh 正常
- hot / cold 兩端位置正確

### 2. terminal 列出 semantic tags

應看到：

```text
bar
hot_end
cold_end
```

不接受只有數字 tag。

### 3. Cache 測試

連跑兩次。

第二次不應重新執行 Gmsh meshing。

---

# Stage 2 — 加入 case 與 steady conduction

## 要做什麼

現在才加入：

```text
lib/case.py
lib/model.py
lib/solve.py
```

並擴充：

```text
test/01_steady_bar/main.py
```

使流程變成：

```text
ensure mesh
→ load case
→ build model
→ solve
```

`case.yaml`：

```yaml
model:
  type: steady_conduction

regions:
  bar:
    k: 10.0

boundary_conditions:
  hot_end:
    type: fixed_temperature
    value_K: 4.0

  cold_end:
    type: fixed_temperature
    value_K: 1.0
```

目前只支援：

$$
\nabla\cdot(k\nabla T)=0
$$

不要加入：

- transient
- radiation
- convection
- nonlinear material
- fluid

## 成功條件

`python main.py` 能解出溫度場，並在 terminal 顯示 hot end、midpoint、cold end 的代表性溫度值。

## 檢查

Stage 2 只確認求解成功，不正式 dump。終端 sample 應能確認：

- hot end = 4 K
- cold end = 1 K
- 沿長度方向單調下降
- 垂直棒長的每個截面基本等溫

若出現局部 hot spot、橫向溫差或非單調變化，先停止查錯。

### Case / mesh 分離測試

將 cold end 改成：

```yaml
value_K: 2.0
```

再跑一次。

應：

```text
reuse mesh
→ rebuild model
→ solve again
```

新的溫度場應變成 4 K → 2 K。

---

# Stage 3 — 驗證解析解

## 要做什麼

在：

```text
test/01_steady_bar/main.py
```

加入解析解比較。

解析解：

$$
T(x)=T_1+\frac{T_2-T_1}{L}x
$$

`expected.yaml` 只保存 tolerance 等測試資訊。

## 成功條件

terminal 最後明確顯示：

```text
Temperature profile: PASS
```

並列出誤差。

## 肉眼檢查

輸出一張簡單表格：

```text
quantity              FEM          analytic      error
T(midpoint)            ...          ...           ...
```

FEM 與 analytic 應肉眼看起來一致。

Test 01 未通過前，不建立 ADR baseline。

---

# Stage 4 — 衍生物理量與守恆

## 要做什麼

實作：

```text
lib/analyze.py
```

並讓 Test 01 的 `main.py` 呼叫它。

最小功能：

```text
temperature field
heat-flux vector
|q|
surface total heat flow
region average/min/max temperature
```

$$
\mathbf q=-k\nabla T
$$

$$
\dot Q_S=
\int_S \mathbf q\cdot\mathbf n\,dA
$$

## 成功條件

比較 FEM 與解析解：

$$
q_x=-k\frac{T_2-T_1}{L}
$$

$$
\dot Q=-kA\frac{T_2-T_1}{L}
$$

terminal 明確顯示：

```text
Heat flux: PASS
Hot-end total heat flow: PASS
Cold-end total heat flow: PASS
Heat-flow conservation: PASS
```

`analyze.py` 回傳已準備好的 cell fields 與 summary data，但不寫 dump、不決定檔案格式。

## 檢查

- `q_x` 方向與大小符合解析解。
- 直接在既有 `hot_end` 與 `cold_end` 積分，不建立 internal `heatflow_section`。
- 兩端 outward-normal heat flow 符號相反、絕對值相同：

$$
|\dot Q_\mathrm{hot}|\approx|\dot Q_\mathrm{cold}|.
$$

---

# Stage 5 — LAMMPS-like cell dump

## 要做什麼

實作：

```text
lib/dump.py
```

`analyze.py` 準備 fields；`dump.py` 只驗證並序列化資料，不計算 $T$、$\mathbf q$ 或 $\dot Q$。
`summary.csv` 與 dump 分開；第一版由 `main.py` 使用 Python 標準庫 `csv` 寫出 `analyze.py` 回傳的 summary data。

由 `main.py` 指定：

```python
dump = {
    "directory": case_dir / "output" / "dump",
    "every": 1,
    "fields": ["cell_ID", "region_ID", "x", "y", "z", "T", "qx", "qy", "qz", "qmag"],
}
```

v1 只支援 cell dump，格式遵守 [`dump-format.md`](dump-format.md)。`region_ID` 是 semantic geometry region，不是 material ID。

## 成功條件

產生：

```text
output/dump/0.dump
output/summary.csv
```

並確認：

- dump 的 `MESH_ID` 與 `build/mesh.msh` / `build.json` 一致。
- `cell_ID` 在同一 `MESH_ID` 的不同 timestep 間穩定。
- 不假定 `cell_ID` 等於 Gmsh element tag 或 FEniCSx local cell index。
- 對每個 dumped `cell_ID`，解析回 `mesh.msh` 的實際 cell，重新計算 centroid，並在 tolerance 內與 dump 的 `x y z` 一致。
- `NUMBER OF CELLS` 等於實際資料列數。
- 每列欄位與 `FIELDS` 完全一致。
- 改變 `main.py` 的 fields 後，只輸出指定欄位。
- 未知欄位或非有限值會明確失敗。

不要求改變 MPI process 數後仍產生完全相同的 ID；此需求延後。
不得為此建立通用 ID manager、mapping framework 或 registry；只實作 serial Test 01 所需的最小可靠 mapping。

---

# Stage 6 — 獨立 Python 後處理

## 要做什麼

實作：

```text
postprocess/plot_dump.py
```

它不重新求解 PDE。簡單曲線可只讀 dump；真正的 3D mesh、surface 或 slice 必須同時讀取既有 `build/mesh.msh`、`build/build.json` 與 dump，驗證 `MESH_ID` 後依 `cell_ID` 合併 topology 與 field values。

第一版只需能從 `0.dump` 產生：

```text
T(x)
qmag(x)
```

輸出路徑由後處理命令指定。後續有明確需求時再加入 slice、scatter、heatmap、animation、time series 或 CSV conversion。

## 成功條件

- 改變配色、圖尺寸或輸出路徑，不會觸發 FEM。
- 刪除或暫時移開 FEM environment 後，只要 Python 繪圖相依套件仍在，便可讀 dump 畫圖。
- 圖上的直棒溫度為線性變化，`qmag` 近似常數。

---

# Test 05 補充驗證 — nonlinear zero-thickness contact

Test 05 分成三個彼此不可混稱的結果：

1. steady closed-form benchmark：驗證 $T_L=3$ K、$T_R=2$ K、$q_x=250$ W/m²。
2. finest-resolution transient：`dx=0.00125 m, dt=0.125 s`，觀察 0–500 s 趨向
   steady exact endpoint；它不是 transient analytic solution。
3. fixed-time convergence slice：固定 `t=0.125 s`，計算四組 dx 與四組 dt。最細
   `dx=0.00125 m, dt=0.015625 s` 只作 numerical reference，其餘 15 組與它比較。

固定時間切片必須輸出全部 16 組疊合的 T 與 qx profiles，以及
`errors_vs_finest.csv`。不要將最細 numerical reference 標成 analytic/exact solution。

# Stage 7 — 建立第一版 ADR baseline

## 前提

Stage 1–6 全部通過。

目前暫停於此 Stage 之前；Test 02 不是 ADR baseline。

Test 03 也不是 ADR baseline。它驗證案例本地：

```text
material.py → k(T) → nonlinear weak form → SNES/Newton → analyze → dump
```

其解析 benchmark 使用 $k(T)=10(1+0.1T)$，並以 Kirchhoff transform 比較溫度與
heat flux。現行結果為 Newton 4 iterations、最大溫度誤差約
$5.65\times10^{-4}\ \mathrm K$，測試 PASS。

Test 04 驗證三個 steady regions 與 mesh-resolved contact layer：

$$
k_\mathrm{contact}=\frac{\delta}{R_c''},\qquad
R''_\mathrm{total}=\frac{L_1}{k_1}+R_c''+\frac{L_2}{k_2}.
$$

現行 benchmark 使用 $k_1=10$、$k_2=20\ \mathrm{W/(mK)}$、
$R_c''=0.002\ \mathrm{m^2K/W}$、$\delta=0.001\ \mathrm m$，得到
$q_x=318.302\ \mathrm{W/m^2}$、接觸層溫降 $0.636605\ \mathrm K$，PASS。

## 要做什麼

現在才建立：

```text
runs/
└─ baseline/
   ├─ main.py
   ├─ geometry.py
   ├─ case.yaml
   ├─ build/
   └─ output/
```

`runs/baseline/main.py` 是這次 ADR 模擬自己的 workflow。

它呼叫既有 `lib/`，不要複製 FEM 實作。

第一版 geometry 只放必要的簡化部件：

```text
4 K plate
magnet
GGG
thermal bus
cold stage
low-k supports
dummy sample
```

材料先用 constant $k$。

仍然只做：

```yaml
model:
  type: steady_conduction
```

## 成功條件

能完整執行：

```text
main.py
  ↓
geometry / cached mesh
  ↓
case
  ↓
model
  ↓
solve
  ↓
analyze
  ↓
dump
  ↓
output
```

## 肉眼檢查

### 1. Gmsh

先看 geometry / mesh：

- 各零件位置合理
- 沒有明顯互相穿透
- support 接在正確位置
- semantic tags 齊全

### 2. 檢查 dump 中的 `T`

確認：

- 4 K boundary 確實為 4 K
- 溫度場連續
- 沒有明顯數值異常點

### 3. 檢查 dump 中的 `q`

確認熱流方向大致由高溫往低溫。

### 4. `summary.csv`

至少能直接看到：

```text
cold_stage_T_avg
cold_stage_T_min
cold_stage_T_max
magnet_T_avg
magnet_T_max
```

以及主要 heat-leak path 的：

```text
Q_dot
```

---

# 後續 — 加入新的物理，一次只加一項

Stage 7 成功後，才依需求逐項加入例如：

```text
heat switch G_on / G_off
sample heat load
radiation
fluid
```

一次只加一項。

每加入一項：

```text
先做最小 test
→ test 通過
→ 再放進 ADR run
```

不要一次加入多個新物理。

已完成的最小 transient 驗證案例為：

```text
test/02_transient_bar/
```

其條件為：

$$
T(0,t)=4\ \mathrm K,\qquad T(L,t)=1\ \mathrm K,
$$

$$
T(x,0)=
\begin{cases}
4\ \mathrm K, & x<L/2,\\
1\ \mathrm K, & x\ge L/2.
\end{cases}
$$

網格在 $x=L/2$ 貼合初始溫度跳躍面。`0.dump` 是未做時間步進的初始 cell
field；為觀察快速暫態，現行輸出為：

```text
output/dump/0.dump
output/dump/1.dump
...
output/dump/20.dump
output/dump/500.dump
```

每份檔案保存該 timestep 與 `time = timestep * dt`，並在相同 `MESH_ID` 下維持相同 `cell_ID` 對應同一 finite-element cell。

`test/02_transient_bar/validate.py` 獨立讀取 dumps，比較一維 Fourier 解析解，並
輸出溫度與 $q_x$ 的空間分布圖。它不得匯入或重跑 FEM solver。執行方式：

```powershell
.\scripts\wsl-run.ps1 "python3 test/02_transient_bar/main.py"
.\scripts\wsl-run.ps1 "python3 test/02_transient_bar/validate.py"
```

因本案例 $\alpha=10^{-4}\ \mathrm{m^2/s}$、$L=0.1\ \mathrm m$，50 s 已達
$\tau=\alpha t/L^2=0.5$，所以早期逐步 dumps 是觀察暫態所必需。

---

# 施工規則

每個 Stage 完成後就停止。

不要自動開始下一 Stage。

每個 Stage 都必須留下能直接檢查的東西：

```text
Gmsh geometry
指定欄位的 dump
terminal PASS / FAIL
summary.csv
```

整個順序：

```text
看得見 geometry
    ↓
看得見 mesh
    ↓
看得見 T
    ↓
T 對得上解析解
    ↓
derive q
    ↓
q、Q_dot 與守恆驗證
    ↓
dump 指定 fields
    ↓
獨立讀 dump 畫圖
    ↓
再進 ADR
```

若一個新檔案、新 class 或新 abstraction 對目前 Stage 沒有直接用途，就不要建立。

# ADR Thermal Simulation Construction Steps

> 原則：**如無必要勿增實體**。  
> 每個 Stage 只完成目前需要的一件事。  
> 每完成一個 Stage 就停止，先讓人用肉眼檢查，再進下一階段。

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
│  ├─ analyze.py
│  └─ materials/
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
heatflow_section
```

其中：

- `bar`：volume
- `hot_end`：一端面
- `cold_end`：另一端面
- `heatflow_section`：量 total heat flow 的截面

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
heatflow_section
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

`python main.py` 能解出溫度場並寫入：

```text
output/
```

## 肉眼檢查

### ParaView 看溫度

應看到：

- hot end = 4 K
- cold end = 1 K
- 沿長度方向單調下降
- 垂直棒長的每個截面基本等溫

視覺上應是一條乾淨的線性漸層。

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

$$
q_x=-k\frac{T_2-T_1}{L}
$$

$$
\dot Q=-kA\frac{T_2-T_1}{L}
$$

`expected.yaml` 只保存 tolerance 等測試資訊。

## 成功條件

terminal 最後明確顯示：

```text
Temperature profile: PASS
Heat flux: PASS
Total heat flow: PASS
```

並列出誤差。

## 肉眼檢查

輸出一張簡單表格：

```text
quantity              FEM          analytic      error
T(midpoint)            ...          ...           ...
q_x                    ...          ...           ...
Q_dot                  ...          ...           ...
```

FEM 與 analytic 應肉眼看起來一致。

Test 01 未通過前，不建立 ADR baseline。

---

# Stage 4 — 完成固定後處理

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

`output/` 至少有：

```text
temperature.*
heat_flux.*
summary.csv
```

`summary.csv` 至少包含：

```text
T_min
T_max
T_avg
Q_dot_heatflow_section
```

## 肉眼檢查

### ParaView

看：

1. `T`
2. `|q|`
3. `q` vector

對直棒而言：

- `T`：線性變化
- `|q|`：整根棒幾乎為常數
- `q`：全部朝同一方向

### 守恆

不同截面量到的 total heat flow 應近似相同：

$$
\dot Q_{S_1}\approx\dot Q_{S_2}
$$

---

# Stage 5 — 建立第一版 ADR baseline

## 前提

Stage 1–4 全部通過。

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
output
```

## 肉眼檢查

### 1. Gmsh

先看 geometry / mesh：

- 各零件位置合理
- 沒有明顯互相穿透
- support 接在正確位置
- semantic tags 齊全

### 2. ParaView 看 `T`

確認：

- 4 K boundary 確實為 4 K
- 溫度場連續
- 沒有明顯數值異常點

### 3. ParaView 看 `q`

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

# Stage 6 — 加入新的物理，一次只加一項

Stage 5 成功後，才依需求逐項加入，例如：

```text
contact conductance
heat switch G_on / G_off
k(T)
sample heat load
transient
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

---

# 施工規則

每個 Stage 完成後就停止。

不要自動開始下一 Stage。

每個 Stage 都必須留下能直接檢查的東西：

```text
Gmsh geometry
ParaView field
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
對得上解析解
    ↓
看得見 q
    ↓
算得對 Q_dot
    ↓
再進 ADR
```

若一個新檔案、新 class 或新 abstraction 對目前 Stage 沒有直接用途，就不要建立。

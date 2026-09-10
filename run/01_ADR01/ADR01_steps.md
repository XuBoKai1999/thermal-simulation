# ADR01 Steps

> 按順序施工。  
> 每一步完成後再進下一步。  
> `我們` = 使用者 + ChatGPT 做物理判斷、資料判讀與設計決策。  
> `Codex` = 實作、修改 repository、執行 regression。  
> `共同` = 我們先定義需求，再交 Codex 實作並回來 review。

## Stage 0 — Repository gate

**Owner：Codex / review**

1. 確認 local `main` 已包含 framework-hardening commit。
2. 確認 Test 07、uniform IC、general BC、region statistics、selected heat-flow analysis 都在同一個可執行 snapshot。
3. 跑 Test 07。
4. 若 PASS，framework freeze。

完成條件：

```text
READY FOR ADR BASELINE
```

之後除非 ADR 實際撞到 framework bug，否則不要主動重構 `lib/`。

---

## Stage 1 — 建立 shared materials library

**Owner：共同**

### 1.1 先做最小 external material reference

讓 `case.yaml` 可以引用 repo 共用材料，例如：

```yaml
materials:
  copper:
    file: ../../materials/nist/copper_ofhc_rrr100/material.yaml
```

要求：

- material file 可定義 `k/rho/cp`
- table path 以 `material.yaml` 所在目錄為基準
- 不破壞既有 inline material syntax
- 不做 registry class / database / plugin system

**交給 Codex。**

### 1.2 建立 material listing script

增加：

```text
scripts/list-materials.py
```

直接掃：

```text
materials/**/material.yaml
```

執行：

```powershell
.\scripts\wsl-run.ps1 "python3 scripts/list-materials.py"
```

列出：

- name
- source
- k validity
- cp validity
- rho availability
- material path

**交給 Codex。**

### Gate

增加一個很小的 regression：

```text
shared external material
→ case loader
→ k/rho/cp evaluate
```

不要建立新的大型 simulation test。

---

## Stage 2 — 第一批 NIST material ingestion

**Owner：我們蒐集 / Codex 整理**

先從 cryogenic hardware 常見材料開始，不一次下載整個 NIST database。

第一批候選：

1. OFHC Copper
2. Stainless Steel 304
3. Aluminum 6061-T6
4. G-10 CR Fiberglass Epoxy

NIST 是主要 provenance source。

### 2.1 每一種材料確認

- exact material grade
- property
- units
- equation
- equation validity range
- data range
- fit error
- source/reference

### 2.2 轉成 framework 可讀資料

若 NIST 提供 curve-fit coefficients：

```text
published coefficients
→ sampling
→ CSV
```

CSV 至少：

```text
T_K,k_W_mK
```

或：

```text
T_K,cp_J_kgK
```

`material.yaml` 保存 provenance 與 validity range。

### 2.3 不允許 silent extrapolation

ADR 會碰到約 1–4 K。

NIST property 若只到 4 K、10 K 或 12 K：

```text
標成 DATA GAP
```

不能自行把 fit 向 1 K 外推後當作可信資料。

### Gate

執行：

```powershell
.\scripts\wsl-run.ps1 "python3 scripts/list-materials.py"
```

確認第一批材料都可被列出，且 validity range 清楚。

---

## Stage 3 — ADR physical inventory

**Owner：我們**

此時才正式決定 ADR01 到底模擬什麼。

根據葛博提供的圖、CAD、簡報或尺寸資料，逐件列出：

| Region | Geometry | Material | Contact | 備註 |
|---|---|---|---|---|
| ... | ... | ... | perfect / unknown | ... |

只保留熱路徑上真的必要的實體。

需要確認：

- overall dimensions
- plate thickness / radius
- support geometry
- ADR / cold-stage location
- 4 K platform interface
- holes 是否第一版需要
- 各 component 材料
- 哪些 interface 第一版假設 perfect

### Gate

必須能回答：

```text
系統有哪些 thermal regions？
每個 region 是什麼材料？
4 K BC 在哪？
1 K BC 在哪？
```

回答不了就不進 geometry implementation。

---

## Stage 4 — 定義 ADR01 baseline abstraction

**Owner：我們**

先明確寫死第一版假設：

\[
T(\mathbf x,0)=4\ \mathrm K
\]

\[
T_{\rm platform}=4\ \mathrm K
\]

\[
T_{\rm ADR}=1\ \mathrm K
\]

其餘外表面：

\[
\mathbf q\cdot\mathbf n=0
\]

region interface：

\[
R_c=0
\]

第一版不加入：

```text
radiation
convection
heat switch
contact resistance
heat load
MCE
```

### Material strategy

分兩輪：

**Run A — engineering baseline**

使用可信的 representative constant properties，先驗證 geometry + thermal path。

**Run B — material-dependent baseline**

換成已驗證的 \(k(T),c_p(T)\)。

若 1–4 K property 尚缺，不得假裝 NIST 資料已足夠；先補文獻資料。

---

## Stage 5 — 實作 `geometry.py`

**Owner：Codex**

依 Stage 3 已確認尺寸建立：

```text
run/01_ADR01/geometry.py
```

要求：

- 只用必要 geometry
- semantic volume tags
- semantic surface tags
- intended perfect-contact interface 使用 OCC fragment / conformal topology
- mesh size 可參數化
- 不在 geometry.py 放材料或溫度

### Gate

先只 build mesh，不 solve。

檢查：

- ParaView / Gmsh 外形
- physical regions
- boundary surfaces
- interface topology
- mesh quality / element count

由我們 review 圖與 tags。

---

## Stage 6 — 建立 `case.yaml`

**Owner：共同**

由我們決定：

- region → material
- BC
- initial temperature
- initial \(\Delta t\)
- initial end time

Codex 寫入：

```text
run/01_ADR01/case.yaml
```

第一輪優先使用 shared `materials/`；不要在 ADR01 複製 NIST data。

### Gate

case loader 必須能：

```text
load
resolve external materials
validate T domain
```

若要求 1 K 但 material table domain 從 4 K 起，必須直接失敗，而不是外插。

---

## Stage 7 — 建立最小 `main.py`

**Owner：Codex**

從已驗證 general 3D transient workflow reuse。

流程只需：

```text
load case
mesh
build transient model
solve
analyze
dump
summary
```

輸出至少：

- T
- qx, qy, qz, qmag
- per-region Tmin/Tavg/Tmax
- 4 K boundary heat flow
- cold boundary heat flow

不要在這一步建立通用 runner。

---

## Stage 8 — 第一次 ADR smoke run

**Owner：Codex 執行 / 我們判讀**

先使用粗 mesh、保守 timestep。

目的不是得到最終數字，而是檢查：

1. solver 能跑
2. 溫度範圍合理
3. 熱由 4 K 端往 cold side 傳
4. 無 disconnected region
5. 無 NaN / negative material property
6. dump 可讀

### Gate

必須看到合理的：

\[
T(\mathbf x,t)
\]

與：

\[
\mathbf q(\mathbf x,t)
\]

若失敗，只修實際問題，不趁機重構。

---

## Stage 9 — Visualization / thermal-path review

**Owner：我們**

用 ParaView / postprocess 看：

- temperature field
- heat-flux magnitude
- heat-flow direction
- hottest/coldest regions
- thermal bottleneck
- 是否有不應存在的 thermal isolation

這一步主要檢查模型是否符合實際結構直覺。

若 geometry / material assignment 錯，回 Stage 3–6。

---

## Stage 10 — Mesh convergence

**Owner：Codex 執行 / 我們判讀**

至少三個 mesh level：

```text
coarse
medium
fine
```

比較主要 observables：

- cold-stage \(T_{\rm avg}(t)\)
- selected region \(T_{\rm avg}(t)\)
- 主要 boundary \(\dot Q(t)\)

不要求所有 cell field pointwise identical。

### Gate

選定 production mesh。

---

## Stage 11 — Time-step convergence

**Owner：Codex 執行 / 我們判讀**

固定 production mesh，至少三個 timestep：

```text
dt
dt/2
dt/4
```

比較：

- selected \(T(t)\)
- selected \(\dot Q(t)\)
- characteristic cooling time

### Gate

選定 production timestep。

---

## Stage 12 — Energy balance sanity check

**Owner：共同**

constant-property baseline：

\[
U=\int_\Omega \rho c_pT\,dV
\]

檢查：

\[
\Delta U
\approx
-\int_{t_n}^{t_{n+1}}
\sum_S\dot Q_S\,dt
\]

允許離散誤差，但不能有量級上的不守恆。

若使用 \(c_p(T)\)，先定義一致的：

\[
u(T)=\int c_p(T)\,dT
\]

再做 energy check。

必要時此階段才新增 ADR-specific `validate.py`。

---

## Stage 13 — 補齊 1–4 K material data

**Owner：我們**

這一步是 final physical model 的必要 gate。

逐一檢查 ADR01 真正使用的材料：

| Material | \(k\) 1–4 K | \(c_p\) 1–4 K | \(\rho\) | Status |
|---|---|---|---|---|
| ... | ... | ... | ... | OK / GAP |

NIST 不足的部分再查：

- NIST/NBS monographs
- peer-reviewed low-temperature measurements
- manufacturer cryogenic data（若適用）
- 其他可追溯 primary/technical sources

禁止：

```text
把 4 K 以上 fit 直接外插到 1 K，然後當成 final result
```

---

## Stage 14 — Temperature-dependent production baseline

**Owner：Codex 執行 / 我們判讀**

把 constant \(k,\rho,c_p\) 換成 shared materials library 中可信的：

\[
k(T),\quad c_p(T)
\]

\(\rho\) 若熱收縮效應可忽略，可先 constant。

重新做：

- smoke run
- mesh sanity
- dt convergence
- energy sanity

得到 ADR01 第一個正式 baseline result。

---

## Stage 15 — Baseline report

**Owner：我們**

整理：

- geometry assumptions
- material sources
- BC / IC
- mesh
- timestep
- temperature field
- heat-flux field
- region temperatures
- heat leak / boundary heat flow
- convergence
- limitations

此時才稱：

```text
ADR01 BASELINE COMPLETE
```

---

## Stage 16 — 決定第二階段 physics

**Owner：我們**

baseline 完成後才依 sensitivity / 實際需求決定是否加入：

1. contact resistance
2. prescribed heat load
3. time-dependent ADR boundary
4. heat switch \(G_{\rm on}/G_{\rm off}\)
5. radiation
6. anisotropic \(k\)
7. MCE / \(C(T,B)\)

每次只加入一個新物理，先建立可驗證的最小 test，再回 ADR。

不要一次全部塞進 ADR01。

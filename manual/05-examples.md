# 已驗證範例

## 01 steady bar

目的：以一維解析解驗證 3D P1 steady conduction、Fourier flux、兩端 surface integral、
energy conservation、cell-ID mapping 與 dump writer。

- Geometry：長 0.1 m，方形截面 0.01 m × 0.01 m，mesh size 0.005 m。
- Region：`bar`, `k = 10 W/(m K)`。
- BC：`hot_end = 4 K`, `cold_end = 1 K`。
- Source/IC：沒有 source；steady 無 IC。
- Solver：PETSc preonly + LU。

執行：

```powershell
.\scripts\wsl-run.ps1 "python3 test/01_steady_bar/main.py"
```

預期：$T(0.05\,m)=2.5\,K$、$q_x=300\,W/m^2$、截面熱流大小 0.03 W，並顯示六個
PASS（temperature、flux、兩端 total heat、conservation、cell mapping）。結果在
`test/01_steady_bar/output/`。

## 02 transient bar

目的：驗證 constant-property Backward Euler early transient、piecewise DG0 initial state、
固定溫度邊界，以及初始跳躍附近的 `dt × dx` 敏感性。

- Geometry：尺寸/mesh size 同 Test 01，但在 `x=0.05 m` 將 volumes fragment，使 mesh
  對齊 IC jump。
- Material：`k=10 W/(m K)`, `rho=1000 kg/m³`, `cp=100 J/(kg K)`。
- BC：兩端 4 K 與 1 K。
- IC：`x < 0.05 m` 為 4 K，其餘為 1 K。
- Convergence mesh sizes：`dx=0.01, 0.005, 0.0025 m`。
- Convergence time steps：`dt=0.0625, 0.03125, 0.015625 s`。
- Early-transient dumps：每組皆輸出物理時間 `0, 0.0625, 0.125, 0.25, 0.5 s`。
- 本測試刻意只保留初始跳躍最明顯的時間窗，不計算 late-time 或 steady state。

執行 solver：

```powershell
.\scripts\wsl-run.ps1 "python3 test/02_transient_bar/main.py"
```

成功訊息：

```text
mesh sizes: 0.01, 0.005, 0.0025 m
time steps: 0.0625, 0.03125, 0.015625 s
comparison times: 0, 0.0625, 0.125, 0.25, 0.5 s
Early-transient space-time runs: PASS
```

各時間步長的 dump 分開存於
`test/02_transient_bar/output/convergence/dx_*/dt_*/dump/`；物理時間以 dump header 的
`TIME` 為準。案例特定 post-validation 命令是：

```powershell
.\scripts\wsl-run.ps1 "python3 test/02_transient_bar/validate.py"
```

它只讀 dumps，比較 1D Fourier series，理論上產生 validation 下兩張 profile 圖。在目前
Windows `/mnt/c` 掛載環境，若目的 PNG 已存在，Pillow 可能在覆寫時回報
`OSError: [Errno 22] Invalid argument`；這是已觀察到的輸出檔覆寫問題，不表示 FEM 或
dump reader 驗證失敗。可先將既有 validation PNG 移到別處後再執行。

本案例的 thermal diffusivity：

$$
\alpha=\frac{k}{\rho c_p}=10^{-4}\,\mathrm{m^2/s},
\qquad t_\mathrm{diff}\sim\frac{L^2}{\alpha}=100\,s.
$$

驗證程式在固定最細 `dx` 時比較不同 `dt`，並在固定最細 `dt` 時比較不同 `dx`；
溫度與熱流各自輸出兩張 profiles 圖，完整誤差存入 `convergence_errors.csv`。

## 03 temperature-dependent material bar

目的：驗證案例本地 `material.py`、$k(T)$ nonlinear weak form、SNES/Newton、解析解與
dump pipeline。

- Geometry/BC：同 Test 01。
- Case：`regions.bar.material: local`，不把專案材料塞進 `lib/`。
- Material：$k(T)=10(1+0.1T)\ \mathrm{W/(m\,K)}$。
- Solver：PETSc SNES `newtonls`；Newton linearization 使用 LU。
- Verification：使用 Kirchhoff transform
  $\Phi(T)=\int k(T)\,dT$ 建立一維解析解。

執行：

```powershell
.\scripts\wsl-run.ps1 "python3 test/03_temperature_dependent_bar/main.py"
```

目前驗證結果：4 Newton iterations，cell-centroid 最大溫度誤差約
$5.65\times10^{-4}\ \mathrm K$，平均 $q_x$ 誤差約
$1.71\times10^{-13}\ \mathrm{W/m^2}$，PASS。輸出位於
`test/03_temperature_dependent_bar/output/`。

## 04 contact resistance bar

目的：驗證三個 steady regions、thin-layer contact resistance、cell-tag conductivity field、
解析串聯熱阻與 dump。

- 左棒：$L_1=0.0495\ \mathrm m$、$k_1=10\ \mathrm{W/(mK)}$。
- 接觸層：$\delta=0.001\ \mathrm m$、$R_c''=0.002\ \mathrm{m^2K/W}$，所以
  $k_\mathrm{contact}=0.5\ \mathrm{W/(mK)}$。
- 右棒：$L_2=0.0495\ \mathrm m$、$k_2=20\ \mathrm{W/(mK)}$。
- BC：4 K 與 1 K；其餘外表面自然絕熱。

執行：

```powershell
.\scripts\wsl-run.ps1 "python3 test/04_contact_resistance_bar/main.py"
```

## 05 steady nonlinear zero-thickness contact bar

這是獨立的 1D P1 benchmark，同時驗證 nonlinear $k(T)$、兩個不共享的介面溫度
DOFs，以及 $q=h_c(T_L-T_R)$。它不是 Test 04 的薄層近似，也不代表通用 3D contact。

```text
k(T) = 10 [1 + 3/13 (T - 2.5)^2] W/(m K)
R''c = 0.004 m² K/W
T_left = 3 K, T_right = 2 K, qx = 250 W/m²
dx = 0.01, 0.005, 0.0025, 0.00125 m
```

```powershell
.\scripts\wsl-run.ps1 "python3 test/05_steady_nonlinear_contact_bar/main.py"
.\scripts\wsl-run.ps1 "python3 test/05_steady_nonlinear_contact_bar/validate.py"
```

每個 `dx` 有獨立 `mesh.msh` 與 `0.dump`。驗證輸出包含 temperature/contact jump、
constant heat flux、Kirchhoff transform 及 mesh-convergence 圖。

另以 `dx=0.00125 m`、`dt=0.125 s`、`rho=1000 kg/m³`、`cp=100 J/(kg K)` 計算
0–500 s transient reference。初始左右半棒分別為 4 K 與 1 K；dump 時間為
0、0.125、0.5、2、10、50、100、200、500 s。此數值暫態用來觀察解趨向已知 steady
endpoint，不宣稱為 transient analytic solution。

解析與 FEM 均得到 $q_x=318.302\ \mathrm{W/m^2}$，接觸層溫降
$0.636605\ \mathrm K$；溫度最大誤差約 $2.66\times10^{-14}\ \mathrm K$，PASS。

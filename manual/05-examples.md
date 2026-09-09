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

目的：驗證 constant-property Backward Euler transient、piecewise DG0 initial state、固定
溫度邊界、多 timestep dump 與接近 steady solution。

- Geometry：尺寸/mesh size 同 Test 01，但在 `x=0.05 m` 將 volumes fragment，使 mesh
  對齊 IC jump。
- Material：`k=10 W/(m K)`, `rho=1000 kg/m³`, `cp=100 J/(kg K)`。
- BC：兩端 4 K 與 1 K。
- IC：`x < 0.05 m` 為 4 K，其餘為 1 K。
- Time：`dt=1 s`, `end=500 s`, 500 steps。
- Dumps：0–20 steps 每步輸出，另輸出 500，共 22 files。

執行 solver：

```powershell
.\scripts\wsl-run.ps1 "python3 test/02_transient_bar/main.py"
```

成功訊息：

```text
dump files: 22
final timestep: 500, time: 500 s
Final dump near steady: PASS
```

輸出在 `test/02_transient_bar/output/`。案例特定 post-validation 命令是：

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

因此 0–20 s 的密集輸出用於觀察 early transient，500 s 結果接近 steady state。


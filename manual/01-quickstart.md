# Quickstart

以下命令已以 repository 目前內容驗證。所有 FEniCSx、Gmsh、PETSc 與 Python simulation
都必須透過 WSL2 Ubuntu；不要使用 Windows Python。

## 1. 從 repository root 執行

在 Windows PowerShell 進入：

```text
C:\Users\User2\Documents\Works\03 thermal simulation
```

執行穩態直棒驗證：

```powershell
.\scripts\wsl-run.ps1 "python3 test/01_steady_bar/main.py"
```

若 PowerShell execution policy 阻止 `.ps1`，可對這次呼叫使用：

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\scripts\wsl-run.ps1 "python3 test/01_steady_bar/main.py"
```

## 2. 案例輸入在哪裡

- `test/01_steady_bar/geometry.py`：0.1 m × 0.01 m × 0.01 m 的直棒、0.005 m mesh size，
  以及 `bar`、`hot_end`、`cold_end` physical groups。
- `test/01_steady_bar/case.yaml`：`k = 10 W/(m K)`，hot/cold ends 分別為 4 K、1 K。
- `test/01_steady_bar/main.py`：真正的 runner，串接 framework API、驗證解析解並寫輸出。
- `test/01_steady_bar/expected.yaml`：僅供本驗證案例使用的誤差容許值，不是一般 case schema。

## 3. 成功時會看到什麼

terminal 應包含：

```text
Temperature profile: PASS
Heat flux: PASS
Hot-end total heat flow: PASS
Cold-end total heat flow: PASS
Heat-flow conservation: PASS
cell_ID mapping: PASS
```

第一次執行可能建立 mesh；geometry 沒變時會看到：

```text
mesh cache valid, reuse existing mesh
```

輸出位置：

- mesh/topology：`test/01_steady_bar/build/mesh.msh`
- semantic tags：`test/01_steady_bar/build/tags.json`
- mesh identity/cache manifest：`test/01_steady_bar/build/build.json`
- cell fields：`test/01_steady_bar/output/dump/0.dump`
- scalar summary：`test/01_steady_bar/output/summary.csv`

## 4. 不重新求解，直接畫既有 dump

```powershell
.\scripts\wsl-run.ps1 "python3 postprocess/plot_dump.py test/01_steady_bar/output/dump/0.dump -o test/01_steady_bar/output/plots"
```

產生：

```text
test/01_steady_bar/output/plots/temperature.png
test/01_steady_bar/output/plots/heat_flux_magnitude.png
```

這個 postprocess command 只讀 dump，不會呼叫 FEM solver。

## 5. 下一步

不要直接修改 `lib/` 來建立新案例。先複製一個已驗證案例成新的 case directory，修改
`geometry.py`、`case.yaml`，必要時才調整 `main.py` 的輸出與案例特定驗證。新 geometry
必須仍符合目前框架的單一 volume region、兩個 fixed-temperature facet tags 限制。


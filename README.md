# Thermal Simulation

小型、case-driven 的 3D FEniCSx 熱傳模擬專案。`lib/` 提供 mesh、model、solve、
analysis 與 LAMMPS-like dump I/O；每個 `test/<name>/main.py` 則像 LAMMPS infile，
明確串接一次模擬。所有 Python simulation 必須依 `AGENTS.md` 經 WSL2 執行。

## 已驗證案例

| 案例 | 功能 |
|---|---|
| `01_steady_bar` | 單一 constant-$k$ region 的穩態解析驗證 |
| `02_transient_bar` | Early transient Backward Euler `dt × dx` 收斂與解析解 profiles 比較 |
| `03_temperature_dependent_bar` | 案例本地 $k(T)$ 與 SNES/Newton nonlinear solve |
| `04_contact_resistance_bar` | steady multi-region 與 mesh-resolved thin-layer contact resistance |
| `05_steady_nonlinear_contact_bar` | 1D P1 nonlinear $k(T)$、零厚度接觸、steady exact、transient 與 0.125 s `dx × dt` slice |

執行範例：

```powershell
.\scripts\wsl-run.ps1 "python3 test/04_contact_resistance_bar/main.py"
```

使用說明見 [`manual/README.md`](manual/README.md)，架構、施工狀態與 dump 規格分別見
[`arch.md`](arch.md)、[`steps.md`](steps.md)、[`dump-format.md`](dump-format.md)。

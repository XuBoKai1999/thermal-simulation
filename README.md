# Thermal Simulation

小型、case-driven 的 3D FEniCSx 熱傳模擬專案。`lib/` 提供 mesh、model、solve、
analysis 與 LAMMPS-like dump I/O；每個 `test/<name>/main.py` 則像 LAMMPS infile，
明確串接一次模擬。所有 Python simulation 必須依 `AGENTS.md` 經 WSL2 執行。

## 已驗證案例

| 案例 | 功能 |
|---|---|
| `01_steady_bar` | 單一 constant-$k$ region 的穩態解析驗證 |
| `02_transient_bar` | Early transient Backward Euler `dt × dx` 收斂與解析解 profiles 比較 |
| `03_temperature_dependent_bar` | CSV table $k(T)$ 與 SNES/Newton nonlinear solve |
| `04_contact_resistance_bar` | steady multi-region 與 mesh-resolved thin-layer contact resistance |
| `05_steady_nonlinear_contact_bar` | 1D P1 nonlinear $k(T)$、零厚度接觸、steady exact、transient 與 0.125 s `dx × dt` slice |
| `06_material_properties` | constant/table/Python property loader 與 multi-region constant-property transient regression |
| `06_material_properties/nonlinear_transient.py` | multi-region temperature-dependent `k/rho/cp` transient 與 SNES regression |
| `07_3d_multiregion_transient` | uniform/semantic `by_region` IC、一般 semantic surfaces、region statistics、selected heat flow 與 conformal interface |

## Material properties

`k`、`rho`、`cp` 使用同一種 property representation。既有 scalar YAML 仍等價於
constant property；新案例也可用 `type: constant`、CSV `type: table` 或案例本地
`type: python`。Region 可直接保存舊式 properties，或以 `material: <name>` 指向頂層
`materials` block。相對檔案路徑以 `case.yaml` 所在目錄為基準。

- Steady linear：一個或多個 constant-property regions。
- Steady nonlinear：單一 region 的 table/Python `k(T)`，使用 SNES/Newton。
- Transient linear：一個或多個 regions，且 relevant `k/rho/cp` 全為 constant。
- Transient nonlinear：一個或多個 regions 的 table/Python `k(T)`、`rho(T)`、`cp(T)`，使用 SNES/Newton。
- Initial condition：`uniform`、backward-compatible `split_x`，或 semantic `by_region`。
- 一個以上 fixed-temperature semantic surfaces；analysis 可指定任意 tagged surfaces 並回傳 per-region temperature statistics。

執行範例：

```powershell
.\scripts\wsl-run.ps1 "python3 test/04_contact_resistance_bar/main.py"
```

使用說明見 [`manual/README.md`](manual/README.md)，架構、施工狀態與 dump 規格分別見
[`arch.md`](arch.md)、[`steps.md`](steps.md)、[`dump-format.md`](dump-format.md)。

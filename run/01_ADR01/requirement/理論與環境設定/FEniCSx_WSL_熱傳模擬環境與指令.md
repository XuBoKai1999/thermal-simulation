# FEniCSx / WSL 熱傳模擬環境與指令整理

## 1. 目前採用的架構

本專案採用：

```text
Windows
│
├─ PowerShell
├─ Codex
├─ VS Code
├─ Git
│
└─ 專案檔案
      │
      │ wsl.exe
      ▼
WSL2 Ubuntu 26.04
│
├─ Python 3.14.4
├─ FEniCSx 0.10
│  ├─ DOLFINx
│  ├─ UFL
│  ├─ Basix
│  └─ FFCx
├─ PETSc
├─ Open MPI
├─ mpi4py
└─ Gmsh 4.14
```

核心原則：

- Windows：負責編輯、Codex、Git、PowerShell。
- WSL：負責 FEniCSx、PETSc、MPI、Gmsh 與實際數值計算。
- Windows Python 不參與本專案的 FEM 計算。
- Codex 可以繼續在 PowerShell 中運作，但模擬指令一律送進 WSL。

---

## 2. 安裝方式

WSL 原本已有：

```text
Ubuntu 26.04 LTS
Python 3.14.4
```

Ubuntu 26.04 repository 已提供 FEniCSx 套件，因此沒有使用 Conda，也沒有自行編譯 PETSc。

在 PowerShell 中執行：

```powershell
wsl -d Ubuntu -u root -- apt update
```

接著：

```powershell
wsl -d Ubuntu -u root -- apt install -y fenicsx gmsh python3-gmsh
```

APT 自動補齊相關相依套件，包括 DOLFINx、PETSc、MPI 等。

---

## 3. 已確認版本

| 元件 | 版本 |
|---|---|
| Ubuntu | 26.04 LTS |
| Python | 3.14.4 |
| FEniCSx / DOLFINx | 0.10.0.post5 |
| UFL | 2025.2.1 |
| Basix | 0.10.0 |
| FFCx | 0.10.1.post0 |
| PETSc / petsc4py | 3.24.4 |
| Open MPI | 5.0.10 |
| Gmsh CLI | 4.14.0 |
| Gmsh Python API | 4.14.0 |

---

## 4. WSL 中最重要的熱傳 / FEM 指令

實際日常需要記住的 CLI 主要只有三類：

| 指令 | 功能 | 用途 |
|---|---|---|
| `python3` | WSL Python interpreter | 執行 FEniCSx 模擬 |
| `mpirun` | Open MPI launcher | 平行執行 FEniCSx |
| `gmsh` | Gmsh CLI | 建立幾何、產生 mesh |

另外：

| 指令 | 功能 |
|---|---|
| `apt` | Ubuntu 套件管理 |
| `dpkg` | 查詢已安裝套件 |

---

## 5. FEniCSx 不是獨立 CLI

FEniCSx 的主要使用方式不是：

```bash
fenicsx main.py
```

而是：

```bash
python3 main.py
```

因為 FEniCSx 是 Python library。

程式中通常會寫：

```python
from dolfinx import mesh, fem
import ufl
from petsc4py import PETSc
from mpi4py import MPI
```

以下名稱主要都是 Python module / library，而不是日常直接執行的 CLI：

```text
dolfinx
ufl
basix
ffcx
petsc4py
mpi4py
```

---

## 6. `python3`：執行 FEniCSx

普通執行：

```bash
python3 main.py
```

檢查 DOLFINx：

```bash
python3 -c "import dolfinx; print(dolfinx.__version__)"
```

目前應輸出：

```text
0.10.0.post5
```

檢查 PETSc：

```bash
python3 -c "import petsc4py; from petsc4py import PETSc; print(petsc4py.__version__); print(PETSc.Sys.getVersion())"
```

---

## 7. `mpirun`：平行 FEM

兩個 MPI process：

```bash
mpirun -np 2 python3 main.py
```

四個：

```bash
mpirun -np 4 python3 main.py
```

其中：

```text
-np 4
```

表示啟動 4 個 MPI process。

已實際測試：

```powershell
wsl -d Ubuntu -- mpirun -np 2 python3 -c "from mpi4py import MPI; print('rank', MPI.COMM_WORLD.rank, 'of', MPI.COMM_WORLD.size)"
```

得到：

```text
rank 0 of 2
rank 1 of 2
```

也已測試 FEniCSx mesh partition：

```python
mesh.create_unit_square(MPI.COMM_WORLD, 8, 8)
```

結果：

```text
rank 0 cells 64
rank 1 cells 64
```

因此已確認：

```text
PowerShell
→ WSL2
→ Open MPI
→ Python
→ FEniCSx
```

整條鏈可以正常運作。

---

## 8. `gmsh`：幾何與 Mesh

查看版本：

```bash
gmsh --version
```

目前版本：

```text
4.14.0
```

產生 2D mesh：

```bash
gmsh geometry.geo -2
```

產生 3D mesh：

```bash
gmsh geometry.geo -3
```

Gmsh 也有 Python API：

```python
import gmsh
```

所以之後幾何 / mesh 可以選擇：

```text
.geo + gmsh CLI
```

或：

```text
Python + gmsh API
```

---

## 9. PowerShell → WSL 執行橋接

為避免每次都手寫：

```powershell
wsl -d Ubuntu -- ...
```

專案內建立：

```text
scripts/
└─ wsl-run.ps1
```

用途：

1. 從 PowerShell 接收 Linux command。
2. 將目前 Windows 專案路徑轉成 WSL 路徑。
3. 切換到相同專案目錄。
4. 在 WSL 中執行指令。

目前已測試成功：

```powershell
.\scripts\wsl-run.ps1 "python3 -c 'import dolfinx; print(dolfinx.__version__)'"
```

輸出：

```text
0.10.0.post5
```

---

## 10. 日常標準操作

### 普通 FEniCSx 模擬

```powershell
.\scripts\wsl-run.ps1 "python3 main.py"
```

### MPI FEniCSx 模擬

```powershell
.\scripts\wsl-run.ps1 "mpirun -np 4 python3 main.py"
```

### Gmsh 2D mesh

```powershell
.\scripts\wsl-run.ps1 "gmsh model.geo -2"
```

### Gmsh 3D mesh

```powershell
.\scripts\wsl-run.ps1 "gmsh model.geo -3"
```

這四條可以視為目前專案的核心日常指令。

---

## 11. 哪些是 CLI，哪些不是

| 名稱 | CLI？ | 本質 |
|---|---:|---|
| `python3` | 是 | Python interpreter |
| `mpirun` | 是 | MPI launcher |
| `gmsh` | 是 | mesh / geometry 工具 |
| `dolfinx` | 否 | Python module |
| `fenicsx` | 通常不直接執行 | Ubuntu meta-package / 軟體套件名 |
| `ufl` | 否 | Python module |
| `basix` | 否 | Python module |
| `ffcx` | 通常不手動執行 | form compiler |
| `petsc4py` | 否 | Python module |
| `mpi4py` | 否 | Python module |
| PETSc | 通常不直接操作 CLI | 底層 linear / nonlinear solver library |

---

## 12. 最小心智模型

目前可以把整套 Pipeline 記成：

```text
PowerShell
    │
    ▼
wsl-run.ps1
    │
    ▼
WSL Ubuntu
    │
    ├── gmsh
    │     └── geometry / mesh
    │
    └── python3
          └── FEniCSx
               ├── UFL
               ├── PETSc
               └── MPI
```

最簡化：

```text
gmsh → python3 / FEniCSx → result
```

模型較大時：

```text
gmsh → mpirun python3 / FEniCSx → result
```

也就是：

- `gmsh` 管幾何與 mesh。
- `python3` 執行 FEM。
- `mpirun` 管平行。
- FEniCSx / PETSc / UFL 等由 Python 程式內部呼叫。

---

## 13. 後續熱傳模擬主線

第一個最小可驗證模型：

$$
-\nabla\cdot(k\nabla T)=0
$$

例如：

$$
T(x=0)=4\ \mathrm{K},
\qquad
T(x=L)=1\ \mathrm{K}
$$

若 $k$ 為常數且問題為一維，解析解為：

$$
T(x)=4-\frac{3x}{L}
$$

可用此案例驗證：

```text
mesh
→ boundary condition
→ weak form
→ PETSc solver
→ numerical solution
→ analytical comparison
```

確認整條 FEM Pipeline 正常後，再逐步加入：

```text
3D geometry
→ 多材料
→ thermal conductivity k(T)
→ heat capacity c_p(T)
→ transient heat conduction
→ ADR geometry
→ low-temperature material model
```

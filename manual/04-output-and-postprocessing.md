# 輸出、dump 與後處理

## Analysis output

```python
derived = analyze.analyze(
    temperature, mesh_data, case_data, semantic_tags,
    heatflow_surfaces=["plate_4K", "cold_stage"],
)
# local k(T): analyze.analyze(..., material=material)
```

回傳：

- `cell_data`：`region_ID`, centroid `x/y/z`, `T`, `qx/qy/qz`, `qmag`。
- `bounds`：3×2 array，domain x/y/z min/max，單位 m。
- `characteristic_cell_size`：all-cell median
  `cell_measure^(1/topological_dimension)`；3D tetrahedra即median $V_K^{1/3}$。
- `summary`：全域 `T_min`, `T_max`, volume-average `T_avg`, volume-average vector
  `q_avg`、每個volume region的`T_min_K/T_max_K/T_avg_K`，以及所選surface的
  `Q_dot_<semantic_name>`。

Fourier heat flux：

$$
\mathbf q=-k\nabla T \quad [\mathrm{W/m^2}].
$$

constant multi-region/contact case 的 $k$ 是依 cell tags 建立的 DG0 conductivity field；
接觸層 cell 使用 `thickness_m / resistance_m2K_W`。

`Q_dot_*` 是 $\int_\Gamma \mathbf q\cdot\mathbf n\,dA$，單位 W，符號採 outward normal。
`heatflow_surfaces`由caller指定；省略時使用case中的fixed-temperature boundary names，
因此既有`Q_dot_hot_end`/`Q_dot_cold_end`輸出保持相容。

對 degree-0 initial state，`analyze` 將 heat flux 設為零。因此 Test 02 的 `0.dump` q fields
為零，不能解讀為 discontinuous IC 的物理界面熱流。

對 Test 03 類型的 nonlinear steady case，必須把同一個 local material module 傳給
`analyze`，使 dump heat flux 使用 $-k(T)\nabla T$；未傳入時函式會尋找 YAML constant
`k`，local-material case 因此會失敗，而不是靜默使用錯誤物性。

`summary.csv` 不是 library writer；兩個案例由自己的 `main.py` 用 `csv.writer` 寫出。

## Dump v2

`dump.write_dump` 一個 timestep 寫一個 UTF-8、LF、whitespace-separated text file。header
實際順序為：

```text
ITEM: FORMAT_VERSION
ITEM: TIMESTEP
ITEM: TIME
ITEM: SOLVER_DT
ITEM: CHARACTERISTIC_CELL_SIZE
ITEM: MESH_ID
ITEM: NUMBER OF CELLS
ITEM: BOX BOUNDS
ITEM: REGIONS          # fields 包含 region_ID 時
ITEM: UNITS
ITEM: FIELDS ...
```

`REGIONS` 是 conditional；其餘均由現行 writer 寫出。filename 是
`<timestep>.dump`。穩態預設 timestep 0/time 0.0；暫態 caller 明確傳入。
`BOX BOUNDS`來自actual mesh coordinates。`CHARACTERISTIC_CELL_SIZE`是rough scale，
不是global `dx`；定義為all-cell median `cell_measure^(1/topological_dimension)`，對3D
tetrahedra即median $V_K^{1/3}$。`SOLVER_DT`在caller知道時記錄數值，否則為`unknown`。
Reader仍接受v1的`BOUNDS`，並為新舊名稱提供metadata alias。

Transient cases may set `output.every_time_s` independently from `time.dt_s`.
`case.output_timesteps` maps each uniform requested physical time to the nearest
actual solver step, resolves half-step ties toward the later step, and removes
duplicates. Dumps record the actual step time; the solver does not interpolate.

| field | type | unit | meaning / sampling |
|---|---|---|---|
| `cell_ID` | integer | — | 對應 `mesh.msh` 的 Gmsh volume element tag；writer 必要，排序 key |
| `region_ID` | integer | — | semantic volume physical tag，不是 material ID；optional |
| `x`, `y`, `z` | float | m | finite-element cell vertex coordinates 的平均，即 cell centroid；optional |
| `T` | float | K | P1 temperature interpolate 到 DG0 interpolation point；linear tetrahedra 中為 centroid value；optional |
| `qx`,`qy`,`qz` | float | W/m² | $-k\nabla T$ 的 DG0 cell values；optional |
| `qmag` | float | W/m² | 三個 flux components 的 Euclidean norm；optional |

這些是 `analyze` 目前真正提供的 fields。`write_dump` 可接受 caller data 中的其他欄位，
但沒有 unit mapping，也沒有任何 framework semantics；一般使用者應使用上表。

Dump 不含 vertex、element type 或 connectivity，不能由 centroid points 重建完整 mesh。
真正 3D topology 必須讀同一 cache 的 `build/mesh.msh`；以 dump `MESH_ID` 與
`build/build.json` 核對。現有簡單 plotter只畫 centroid scatter，沒有實作 topology merge。

`cell_ID` mapping 目前在 serial 下用 cell primary-node coordinates matching，輸出 Gmsh
element tag。雖數值通常就是 Gmsh tag，API 契約應視為「同一 MESH_ID 下可解析且穩定」，
不可當作 FEniCSx local cell index。

## Read dump

```python
from lib.dump_reader import read_dump, read_dump_series

metadata, data = read_dump("test/01_steady_bar/output/dump/0.dump")
temperature = data["T"]
x = data["x"]
qx = data["qx"]

frames = read_dump_series(
    "test/02_transient_bar/output/convergence/dx_0p0025/dt_0p25/dump"
)
metadata_10, data_10 = next(
    frame for frame in frames if float(frame[0]["TIME"]) == 10.0
)

# Test 05：固定 0.125 s、指定 dx/dt 的單一切片
metadata, data = read_dump(
    "test/05_steady_nonlinear_contact_bar/output/slice_0p125/"
    "dx_0p00125/dt_0p015625/dump/8.dump"
)
```

Reader 將 scalar metadata（含 `TIME`, `TIMESTEP`, `NUMBER OF CELLS`）保留為 string；
`BOUNDS` 是 float ndarray、`REGIONS` 是 `{int: str}`、所有 field arrays 是 float ndarray
（因此 ID arrays 也會是 float）。series 依 `float(TIME)` 排序並要求單一 `MESH_ID`。

## Plotting

現有 CLI：

```powershell
.\scripts\wsl-run.ps1 "python3 postprocess/plot_dump.py test/01_steady_bar/output/dump/0.dump -o test/01_steady_bar/output/plots"
```

它需要 `x`, `T`, `qmag`，輸出兩張 centroid scatter x-profile。這不是截面平均、2D heatmap
或真正 mesh rendering；3D bar 在相同 x 會有多個 cell samples。

`lib.plotting.plot_heatmap` 可畫 caller 已整理成 `pcolormesh` compatible arrays 的 scalar
heatmap：

```python
from lib.plotting import plot_heatmap
plot_heatmap(x_grid, y_grid, values, "T.png",
             ylabel="y/W", color_label="T [K]")
```

它不會從 scattered dump data 插值成 grid，也不會讀 dump。repository 沒有通用 heat-flux
profile、region statistics、slice、animation 或 3D viewer。Test 02 的 `validate.py` 是案例特定
的 cross-section bin average 與解析解 plot，不是 public plotting API。

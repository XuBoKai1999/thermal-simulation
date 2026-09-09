# Public API reference

這裡只列案例與 postprocess 真正使用的 callable。所有 simulation API 都應在 WSL2 的
FEniCSx environment 中使用；`dump_reader` 與 plotting 只需其 Python dependencies。

## `lib.case`

### `load_case(path)`

| name | type | unit | required/default | description |
|---|---|---|---|---|
| `path` | path-like | — | required | YAML case path |

回傳 validated `dict`。schema 見工作流程章。無 defaults；不拒絕未知 top-level keys。

```python
from lib import case
case_data = case.load_case(case_dir / "case.yaml")
```

### `load_expected(path)`

讀 Test 01 格式的 `expected.yaml`，要求 `tolerances` keys 恰為 `temperature_K`,
`heat_flux_W_m2`, `total_heat_W` 且皆為正數。回傳 dict。這是 verification helper，不是
simulation case 必要 API。

## `lib.mesh`

### `ensure_mesh(build_dir, geometry_file, build_geometry)`

| name | type | unit | required/default | description |
|---|---|---|---|---|
| `build_dir` | path-like | — | required | cache/output directory |
| `geometry_file` | path-like | — | required | hash fingerprint 的 Python file |
| `build_geometry` | callable | — | required | 接收 mesh path、寫 `.msh` 並回傳 tags dict |

回傳 `Path` 到 `mesh.msh`。cache valid 時不呼叫 builder。

### `load_mesh(mesh_path)`

以 `MPI.COMM_WORLD`, rank 0, `gdim=3` 讀 Gmsh mesh。回傳物件含 `.mesh`, `.cell_tags`,
`.facet_tags`。

### `map_cell_ids(mesh_path, domain)`

serial only。回傳 `(cell_ids, mesh_centroids)`；前者順序對齊 local FEniCSx cells，後者為
`{cell_ID: centroid_xyz}`。若 MPI size 非 1、mapping 缺失或 ID 不唯一則失敗。

## `lib.model`

### `build_model(mesh_data, case_data, semantic_tags)`

建立 steady weak form，回傳 `(a, linear, boundary_conditions, space)`。`space` 為 P1；
`linear` source 固定為零。只使用第一個 region 的 `k`。

```python
a, L, bcs, V = model.build_model(mesh_data, case_data, semantic_tags)
```

### `build_transient_model(mesh_data, case_data, semantic_tags, previous=None)`

| name | type | unit | required/default | description |
|---|---|---|---|---|
| `mesh_data` | FEniCSx mesh data | — | required | mesh + tags |
| `case_data` | dict | SI schema | required | validated transient case |
| `semantic_tags` | dict | — | required | name → dimension/tag |
| `previous` | `fem.Function` or `None` | K | default `None` | previous state；None 時由 x-split IC 建 DG0 function |

回傳 `(a, linear, boundary_conditions, space, previous)`。只建單一 Backward Euler step。

### `build_boundary_conditions(space, facet_tags, case_data, semantic_tags)`

回傳 Dirichlet BC list。所有 case BC 均按 fixed `value_K` 建立；facet global count 為零時
丟出 `ValueError`。

## `lib.solve`

### `solve(a, linear, boundary_conditions)`

以固定 preonly/LU 解一次，回傳名為 `temperature` 的 `fem.Function`。PETSc prefix 固定為
`steady_bar_`。

### `make_solver(a, linear, boundary_conditions, prefix)`

回傳 `dolfinx.fem.petsc.LinearProblem`。四個 arguments 都 required；`prefix` 應是 PETSc
options prefix string。solver options 固定，沒有其他 arguments/defaults。

## `lib.analyze`

### `analyze(temperature, mesh_data, case_data, semantic_tags)`

四個 arguments 均 required。`temperature` 單位 K；material `k` 取自 case。回傳：

```python
{
    "cell_data": {"region_ID": ..., "x": ..., "y": ..., "z": ...,
                  "T": ..., "qx": ..., "qy": ..., "qz": ..., "qmag": ...},
    "bounds": ...,
    "summary": {"T_min": ..., "T_max": ..., "T_avg": ..., "q_avg": ...,
                "Q_dot_hot_end": ..., "Q_dot_cold_end": ...},
}
```

需要 semantic tags `hot_end`、`cold_end`。summary 是全 domain，不是 per-region。

## `lib.dump`

### `write_dump(data, directory, fields, mesh_id, bounds, regions, timestep=0, time=0.0)`

| name | type | unit | required/default | description |
|---|---|---|---|---|
| `data` | mapping of 1D arrays | field-specific | required | prepared cell arrays |
| `directory` | path-like | — | required | output directory，自動建立 |
| `fields` | sequence[str] | — | required | output order；必須含 `cell_ID` |
| `mesh_id` | str | — | required | cache manifest ID |
| `bounds` | shape `(3,2)` | m | required | xyz low/high |
| `regions` | mapping[int,str] | — | required | region legend；僅 region_ID selected 時寫出 |
| `timestep` | int-like | — | default `0` | filename/header step |
| `time` | number | s | default `0.0` | physical time |

驗證 fields 存在、等長且 finite，按 cell_ID 排序，回傳 output `Path`。不計算物理量。

## `lib.dump_reader`

### `read_dump(path)`

讀單檔並驗證 row/field count，回傳 `(metadata, data)`。`path` required，無 defaults。

### `read_dump_series(directory)`

讀 `directory/*.dump`，按 TIME 排序，要求至少一個 frame 且所有 `MESH_ID` 相同。回傳
`[(metadata, data), ...]`。

## `lib.plotting`

### `plot_heatmap(x, y, values, path, *, ylabel, color_label, vmin=None, vmax=None, cmap="viridis")`

`x`, `y`, `values` 必須已可直接交給 Matplotlib `pcolormesh(shading="nearest")`；`path`
為輸出圖片。keyword-only `ylabel` 與 `color_label` required；`vmin/vmax` 預設自動，cmap
預設 `viridis`。無回傳值。此函式不讀 dump、不建 grid。

## CLI entry point

唯一通用 CLI-like entry 是：

```text
python3 postprocess/plot_dump.py DUMP [-o OUTPUT_DIR]
```

simulation 沒有通用 CLI；請執行某個 case 的 `main.py`。

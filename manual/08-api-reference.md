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

### `output_timesteps(case_data)`

For optional positive `output.every_time_s`, return sorted solver-step indices
nearest to the requested uniform physical times through `time.end_s`. Half-step
ties select the later step, duplicate mapped steps are removed, and no temporal
interpolation is performed. Returns an empty list when the option is absent.

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
`linear` source 固定為零。conductivity 是由 `materials.conductivity_field` 依 semantic cell
tags 建立的 DG0 field，可包含多個 constant-$k$ regions 與 thin contact layer。

```python
a, L, bcs, V = model.build_model(mesh_data, case_data, semantic_tags)
```

### `build_nonlinear_model(mesh_data, case_data, semantic_tags, material=None)`

建立 steady $\nabla\cdot(k(T)\nabla T)=0$ residual、自動 Jacobian 與 P1 unknown，回傳
`(residual, temperature, boundary_conditions, jacobian)`。預設使用case已解析的single-region
table/Python `k(T)`；optional `material.k(T)`保留legacy runner相容性。初始 guess 是兩個 fixed boundary temperatures 的平均值，boundary DOFs 再套用
Dirichlet values。

### `build_transient_model(mesh_data, case_data, semantic_tags, previous=None)`

| name | type | unit | required/default | description |
|---|---|---|---|---|
| `mesh_data` | FEniCSx mesh data | — | required | mesh + tags |
| `case_data` | dict | SI schema | required | validated transient case |
| `semantic_tags` | dict | — | required | name → dimension/tag |
| `previous` | `fem.Function` or `None` | K | default `None` | previous state；None時依case IC schema建立initial DG0/P1 state，支援`uniform`、`split_x`與semantic constant `by_region` |

回傳 `(a, linear, boundary_conditions, space, previous)`。只建單一 Backward Euler step；
constant `k/rho/cp`均由semantic cell tags建立DG0 fields，可有多個regions。

### `build_nonlinear_transient_model(mesh_data, case_data, semantic_tags, previous=None)`

建立multi-region `k(T)/rho(T)/cp(T)` Backward Euler residual、Jacobian、unknown與previous
temperature。Caller於每步使用`solve_nonlinear`，成功後將solution複製回previous。

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

### `solve_nonlinear(residual, temperature, boundary_conditions, jacobian, prefix)`

When the model attaches common table-property bounds to `temperature`, this
function switches to PETSc VI solving and applies those bounds. This is a
numerical safeguard, not physical validation; an explicit unbounded diagnostic
mode is not yet part of this API.

建立並執行 FEniCSx `NonlinearProblem`，使用固定 SNES/Newton + LU options。回傳
`(solution, newton_iterations)`；SNES/KSP 未收斂時直接 raise PETSc error。

## `lib.analyze`

### `analyze(temperature, mesh_data, case_data, semantic_tags, material=None, heatflow_surfaces=None)`

四個 arguments 均 required。`temperature` 單位 K；material `k` 取自 case。回傳：

```python
{
    "cell_data": {"region_ID": ..., "x": ..., "y": ..., "z": ...,
                  "T": ..., "qx": ..., "qy": ..., "qz": ..., "qmag": ...},
    "bounds": ...,
    "characteristic_cell_size": ...,
    "summary": {"T_min": ..., "T_max": ..., "T_avg": ..., "q_avg": ...,
                "regions": {"region_name": {"T_min_K": ..., "T_max_K": ...,
                                                "T_avg_K": ...}},
                "Q_dot_<surface_name>": ...},
}
```

`heatflow_surfaces`指定要積分的semantic facet names；省略時使用case BC names。
summary同時包含whole-domain與per-region statistics。
`material=None` 時使用case解析後的constant conductivity field或single-region `k(T)` property；
legacy local-material case仍可傳入具有`k(T)`的module。

## `lib.materials`

### `load_property(definition, base_dir, name="property")`

For `type: table`, optional positive `scale` multiplies all tabulated property
values. Optional `domain_K: [lo, hi]` restricts the usable interpolation domain
to a subrange of the CSV table; evaluation outside it fails rather than
extrapolating.

將scalar或`type: constant/table/python`mapping載入為`Property`。`Property.evaluate(T, **state)`
驗證numeric result finite且positive；table的`domain`明確保存上下界，domain外numeric evaluation
失敗。相對CSV/Python路徑以`base_dir`解析。

### `load_region_properties(case_data, base_dir)`

解析`region -> material -> k/rho/cp`並回傳region property mapping；`case.load_case`將結果保存
於內部`_region_properties`。

### `validate(material, names)`

確認 `material` object/module 對每個 `names` 項目都有 callable，否則丟出 `ValueError`。
`build_nonlinear_model` 會以 `("k",)` 呼叫它。它不載入 module、不建立 registry，也不
檢查 symbolic function 在整個溫度範圍的 positivity。

### `property_field(mesh_data, case_data, semantic_tags, name)`

依semantic cell tags為constant property建立DG0 field；`name`目前可為`k/rho/cp`。

### `property_expression(mesh_data, case_data, semantic_tags, name, temperature)`

依semantic cell tags組合region-wise `Property.evaluate(temperature)` UFL expression，供
nonlinear transient model與analysis使用。

### `conductivity_field(mesh_data, case_data, semantic_tags)`

`property_field(..., "k")`的相容wrapper。一般 region 使用解析後的material property；被 contact 指向的
region 使用 `thickness_m / resistance_m2K_W`。每個 owned mesh cell 都必須取得有限值，
否則丟出 `ValueError`。回傳 function 單位 W/(m K)。

## `lib.dump`

### `write_dump(data, directory, fields, mesh_id, bounds, regions, timestep=0, time=0.0, solver_dt=None, characteristic_cell_size=None)`

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
| `solver_dt` | positive number or `None` | s | default `None` | solver timestep；未知時header為`unknown` |
| `characteristic_cell_size` | positive number or `None` | m | default `None` | approximate cell scale；未知時header為`unknown` |

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

# 工作流程、geometry、mesh 與 case

## 真正的 simulation workflow

repository 沒有統一 CLI 或 runner。一場 simulation 由案例的 `main.py` 明確串接：

```text
geometry.py
  → mesh.ensure_mesh()
  → case.load_case()
  → 讀 build/tags.json
  → mesh.load_mesh()
  → model.build_model() 或 build_transient_model()
  → solve.solve() 或 make_solver().solve()
  → analyze.analyze()
  → mesh.map_cell_ids()
  → dump.write_dump()
  → main.py 自行寫 summary.csv
```

暫態的 timestep loop、previous-state 更新、dump schedule 與 final-time 檢查都寫在
`test/02_transient_bar/main.py`，目前不是 `lib` 的通用功能。

## 案例與 framework 的分工

| 位置 | 責任 | 一般使用者是否修改 |
|---|---|---|
| `lib/` | mesh import、weak form、solve、analysis、dump I/O | 通常不改 |
| `scripts/wsl-run.ps1` | 將命令送入 WSL2 Ubuntu | 通常不改 |
| `<case>/geometry.py` | CAD、mesh size、physical groups | geometry 改變時修改 |
| `<case>/case.yaml` | model、材料、BC、time | 每個 case 通常修改 |
| `<case>/main.py` | 串接流程、time loop、輸出策略、case-specific checks | 可從相近案例複製後調整 |
| `<case>/expected.yaml` / `validate.py` | 案例特定 verification | 建議為驗證案例建立 |
| `<case>/build/` | 可重用 mesh artifact | 不手改 |
| `<case>/output/` | simulation result | 不作為輸入手改 |

## Geometry API 契約

現有案例使用 Gmsh Python API：

```python
def build_geometry(mesh_path):
    ...
    gmsh.write(str(mesh_path))
    return tags
```

`build_geometry` 必須自行 `gmsh.initialize()` / `gmsh.finalize()`、產生 3D mesh、寫入傳入的
`mesh_path`，並回傳：

```python
{
    "bar": {"dimension": 3, "tag": 1},
    "hot_end": {"dimension": 2, "tag": 2},
    "cold_end": {"dimension": 2, "tag": 3},
}
```

實際 tag 數字由 Gmsh 決定；字串名稱才是 case 與 geometry 的語意介面。volume physical
group 對應 `regions` key，surface physical groups 對應 `boundary_conditions` key。

現有 geometry 以：

```python
gmsh.option.setNumber("Mesh.MeshSizeMin", MESH_SIZE)
gmsh.option.setNumber("Mesh.MeshSizeMax", MESH_SIZE)
```

控制全域 mesh resolution。framework 沒有 YAML mesh setting，也沒有 local refinement helper。

### 外部 CAD

Gmsh 本身可以匯入 CAD，但 repository 沒有已實作、已測試的 STEP/BREP loader workflow。
`arch.md` 的外部 CAD 描述是未來可能性，不是現行 public API。

## Mesh 與 tags

```python
mesh_path = mesh.ensure_mesh(build_dir, geometry.__file__, geometry.build_geometry)
mesh_data = mesh.load_mesh(mesh_path)
```

`load_mesh` 固定以 `gdim=3` 呼叫 FEniCSx `read_from_msh`，回傳 FEniCSx 的
`MeshData`-like object。現有程式使用：

- `mesh_data.mesh`：FEniCSx domain/topology/geometry。
- `mesh_data.cell_tags`：volume cell → Gmsh physical tag。
- `mesh_data.facet_tags`：boundary facet → Gmsh physical tag。

`tags.json` 保存 semantic name → dimension/tag；它不由 `load_mesh` 自動回傳，案例目前
自行用 `json.loads` 讀取。

## Mesh cache 行為

`ensure_mesh` 只對 **`geometry.py` 檔案 bytes 的 SHA-256** 做 fingerprint，並要求以下三檔
同時存在：

```text
build/mesh.msh
build/tags.json
build/build.json
```

hash 相同且 `build.json` 有 `mesh_id` 就 reuse；否則呼叫 `build_geometry` 並產生新 UUID
`mesh_id`。

- 修改 `geometry.py`（含 `MESH_SIZE`）會 rebuild。
- 只改 `case.yaml` 不會 rebuild，可 reuse mesh 後重建 model/solve。
- geometry 若依賴另一個檔案或環境值，該依賴**不在 fingerprint 內**；這時應修改
  `geometry.py` 或明確移走該案例的三個 build artifacts 後重跑。
- cache 不檢查 Gmsh/FEniCSx 版本，也不檢查 mesh file 是否損壞。

## 目前 case.yaml schema

### 穩態

```yaml
model:
  type: steady_conduction

regions:
  bar:
    k: 10.0

boundary_conditions:
  hot_end:
    type: fixed_temperature
    value_K: 4.0
  cold_end:
    type: fixed_temperature
    value_K: 1.0
```

### 暫態

```yaml
model:
  type: transient_conduction

regions:
  bar:
    k: 10.0
    rho: 1000.0
    cp: 100.0

boundary_conditions:
  hot_end:
    type: fixed_temperature
    value_K: 4.0
  cold_end:
    type: fixed_temperature
    value_K: 1.0

time:
  initial_condition:
    split_x_m: 0.05
    left_T_K: 4.0
    right_T_K: 1.0
  dt_s: 1.0
  end_s: 500.0
```

| path | type | SI unit | requirement |
|---|---|---|---|
| `model.type` | string | — | `steady_conduction` 或 `transient_conduction` |
| `regions` | mapping | — | **恰好一個** entry |
| `regions.<name>.k` | positive number | W/(m K) | steady/transient 必要 |
| `regions.<name>.rho` | positive number | kg/m³ | transient 必要 |
| `regions.<name>.cp` | positive number | J/(kg K) | transient 必要 |
| `boundary_conditions` | mapping | — | **恰好兩個** entries |
| `boundary_conditions.<name>.type` | string | — | 只能是 `fixed_temperature` |
| `boundary_conditions.<name>.value_K` | number | K | 必要 |
| `time.dt_s` | positive number | s | transient 必要 |
| `time.end_s` | positive number | s | transient 必要；整除檢查在案例 runner |
| `time.initial_condition.split_x_m` | number | m | transient 必要 |
| `time.initial_condition.left_T_K` | number | K | transient 必要 |
| `time.initial_condition.right_T_K` | number | K | transient 必要 |

沒有 framework-level defaults；上表欄位均須明確提供。loader 對未知額外 key 不報錯，
但 model 也不會因此實作它們，因此不要把未使用 key 當成有效功能。


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
| `<case>/material.py` | 案例私有的 steady $k(T)$；只有需要時建立 | 自訂 nonlinear material 時修改 |
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

## Perfect contact 的 topology 規則

兩個 solid 的 surfaces 座標重合，不代表 FEniCSx 中的 temperature DOFs 相連。若物理假設是
perfect thermal contact，geometry 必須建立 **shared/conformal topology**，通常先用 Gmsh
`occ.fragment` 分割相鄰 volumes，再同步、標記與 mesh。不得只建立兩個 coincident but
disconnected surfaces；那會形成兩套獨立介面 nodes，且 generic conduction weak form 不會
自動交換熱量。

建立 mesh 後應像 Test 07 一樣驗證 interface coordinates 沒有重複的 coincident DOFs，並做
heat-flow/temperature continuity sanity check。有限 contact resistance 可使用已支援的
mesh-resolved thin layer；不要把 disconnected surfaces 誤稱為 3D zero-thickness contact。

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
| `materials` | mapping | — | optional；named material definitions |
| `regions` | mapping | — | 至少一個；可 inline properties 或引用 named material |
| `regions.<name>.material` | string | — | optional；`materials` 中的名稱，或 legacy `local` |
| `k`, `rho`, `cp` property | number/mapping | SI | scalar 或 `constant/table/python` definition；transient 三者必要 |
| `boundary_conditions` | mapping | — | 至少一個 fixed-temperature entry |
| `boundary_conditions.<name>.type` | string | — | 只能是 `fixed_temperature` |
| `boundary_conditions.<name>.value_K` | number | K | 必要 |
| `time.dt_s` | positive number | s | transient 必要 |
| `time.end_s` | positive number | s | transient 必要；整除檢查在案例 runner |
| `time.initial_condition.split_x_m` | number | m | transient 必要 |
| `time.initial_condition.left_T_K` | number | K | transient 必要 |
| `time.initial_condition.right_T_K` | number | K | transient 必要 |
| `time.initial_condition.type` | string | — | `uniform`、`split_x`或`by_region`；舊格式省略時為`split_x` |
| `time.initial_condition.value_K` | number | K | `uniform`時必要 |
| `time.initial_condition.default_K` | number | K | `by_region`時必要 |
| `time.initial_condition.regions` | mapping | K | `by_region`的 semantic cell-region overrides；未知 region 會失敗 |
| `contacts.<name>.type` | string | — | thin-layer contact 必須為 `thin_layer_resistance` |
| `contacts.<name>.region` | string | — | 必須指向一個已設定且有 geometry tag 的薄層 region |
| `contacts.<name>.resistance_m2K_W` | positive number | m² K/W | 面積比接觸熱阻 |
| `contacts.<name>.thickness_m` | positive number | m | 必須等於 geometry 薄層的實際法向厚度 |

沒有 framework-level defaults；必要欄位均須明確提供。loader 對未知額外 key 不報錯，
但 model 也不會因此實作它們，因此不要把未使用 key 當成有效功能。

## 建立新 3D transient case 的完整 workflow

以 Test 07 作 conceptual reference，不要照抄其尺寸或 tag names：

1. 建 `run/<case>/geometry.py`，以 Gmsh 產生 3D volume、conformal interfaces、semantic tags
   與適當 mesh size。
2. 每個 material volume 建 dimension-3 physical group；需要 BC 或 heat-flow integral 的
   surface 建 dimension-2 physical group。
3. 建 `case.yaml`，使用 `transient_conduction`，定義每個 region 的 `k/rho/cp`、一個以上
   fixed-temperature BC、uniform、split-x 或 semantic by-region IC、`dt_s` 與 `end_s`。
4. 建 `main.py`：`ensure_mesh` → 讀 tags/manifest → `load_mesh` → `load_case` → 選 linear 或
   nonlinear transient builder → timestep loop。
5. 每步成功後正確更新 `previous`；由 caller 決定 dump cadence。不要重寫 weak form。
6. 用 `analyze(..., heatflow_surfaces=[...])` 取得 global/region temperatures 與指定 surface 熱流。
7. 用 `map_cell_ids`、manifest `mesh_id` 與 `write_dump` 寫結果；完整流程目前採 serial。
8. 先 smoke run，再做 mesh/time-step convergence、limiting case 與 energy balance validation。

### Material property sources

Backward-compatible scalar、explicit constant、CSV table與Python callable分別為：

```yaml
materials:
  sample:
    rho: 1000.0
    cp: {type: constant, value: 100.0}
    k: {type: table, file: materials/k.csv, x: T_K, y: k_W_mK}
regions:
  bar: {material: sample}
```

Python source寫成：

```python
k: {type: python, file: materials/sample.py, function: k}
```

相對路徑以 `case.yaml` 所在目錄解析。Table採piecewise-linear interpolation，numeric
domain外evaluation失敗；Python function必須存在且numeric回傳為finite、positive。
Table 可選用 positive `scale` 做單位轉換，並用 `domain_K: [min, max]`
縮小允許的插值區間；兩端點由原表線性插值。
Single-region steady table/Python `k(T)`走nonlinear builder。Transient若任一 relevant
property為table/Python，case runner必須選nonlinear transient builder與SNES。Legacy
`material: local`仍可由舊runner明確傳module。

### 多 region 與薄層接觸熱阻

steady或transient case 可定義多個 region。Transient各region還需`rho`、`cp`；三種
property皆可為constant/table/Python。非接觸層 region 各自提供 `k`；geometry
的 volume physical-group names 必須對應 region keys。面積比熱阻使用：

```yaml
regions:
  left: {k: 10.0}
  contact_layer: {}
  right: {k: 20.0}

contacts:
  joint:
    type: thin_layer_resistance
    region: contact_layer
    resistance_m2K_W: 0.002
    thickness_m: 0.001
```

model 對接觸層使用：

$$
k_\mathrm{contact}=\frac{\texttt{thickness\_m}}
{\texttt{resistance\_m2K\_W}}.
$$

`thickness_m` 必須與 geometry 中該 layer 的實際法向厚度一致，目前不自動量測。
contact layer 必須被 mesh 解析；這不是 zero-thickness contact formulation。transient、local
$k(T)$ 與 contacts 目前不能組合使用。

# ADR Thermal Dump Format v1

本文件是 ADR Thermal Simulation dump 的唯一格式規格。格式仿照 LAMMPS custom dump：一個文字檔代表一個 timestep，header 描述快照，`FIELDS` 決定每列資料的欄位與順序。

## 1. 檔案與路徑

輸出目錄、頻率與 fields 由各案例的 `main.py` 指定：

```python
dump = {
    "directory": case_dir / "output" / "dump",
    "every": 10,
    "fields": [
        "cell_ID", "region_ID", "x", "y", "z",
        "T", "qx", "qy", "qz", "qmag",
    ],
}
```

檔名是十進位整數 timestep：

```text
0.dump
10.dump
20.dump
```

穩態問題只有 timestep 0，因此只寫 `0.dump`。暫態在 `timestep % every == 0` 時寫檔；若最後一步不在輸出間隔上，是否另存最後一步由 `main.py` 明確決定。

檔案使用 UTF-8、LF newline、空白分隔。

## 2. 完整範例

```text
ITEM: FORMAT_VERSION
1
ITEM: TIMESTEP
0
ITEM: TIME
0.0
ITEM: MESH_ID
287b3fe991f40c0a2526069ce8487657652e2237323ebc118b28d6f83db9b89f
ITEM: NUMBER OF CELLS
2
ITEM: BOUNDS
0.0 0.1
0.0 0.01
0.0 0.01
ITEM: REGIONS
1
1 bar
ITEM: UNITS
x=m y=m z=m T=K qx=W/m^2 qy=W/m^2 qz=W/m^2 qmag=W/m^2
ITEM: FIELDS cell_ID region_ID x y z T qx qy qz qmag
0 1 0.0025 0.005 0.005 3.925 300.0 0.0 0.0 300.0
1 1 0.0075 0.005 0.005 3.775 300.0 0.0 0.0 300.0
```

## 3. Header

Header 項目順序固定。

| 項目 | 必要 | 定義 |
|---|---:|---|
| `FORMAT_VERSION` | 是 | 本規格為整數 `1` |
| `TIMESTEP` | 是 | 非負整數求解步數；穩態為 `0` |
| `TIME` | 是 | 物理時間，單位秒；穩態為 `0.0` |
| `MESH_ID` | 是 | `mesh.py` 建立 mesh cache 時產生並記錄於 `build.json` 的 mesh ID |
| `NUMBER OF CELLS` | 是 | `FIELDS` 後面的 cell 資料列數 |
| `BOUNDS` | 是 | 三行 `min max`，順序為 x、y、z，單位 m |
| `REGIONS` | 條件式 | 選擇 `region_ID` 時必須存在；先寫數量，再寫 `ID name` |
| `UNITS` | 是 | 列出所有有量綱 fields 的單位 |
| `FIELDS` | 是 | 資料欄位名稱及每列的精確欄位順序 |

對 transient：

```text
TIME = TIMESTEP * dt
```

時間只寫在 header，不在每列重複。

## 4. Fields v1

| Field | 型別 | 單位 | 定義 |
|---|---|---|---|
| `cell_ID` | integer | — | mesh pipeline 建立、同一 `MESH_ID` 下跨 timestep 穩定的 finite-element cell ID |
| `region_ID` | integer | — | semantic geometry volume region ID；不是 material ID |
| `x` | float | m | cell centroid x |
| `y` | float | m | cell centroid y |
| `z` | float | m | cell centroid z |
| `T` | float | K | 在 cell centroid 評估的溫度 |
| `qx` | float | W/m² | cell 熱流密度 x 分量 |
| `qy` | float | W/m² | cell 熱流密度 y 分量 |
| `qz` | float | W/m² | cell 熱流密度 z 分量 |
| `qmag` | float | W/m² | $\sqrt{q_x^2+q_y^2+q_z^2}$ |

`cell_ID` 永遠是必要 field。其他 fields 由 `main.py` 選擇。所有 field data 必須先由 `analyze.py` 準備完成；`dump.py` 只選欄、驗證與序列化，不計算 Fourier law、`qmag` 或其他物理量。未知 field 必須立即報錯，不可靜默忽略。

不得假定 `cell_ID` 的數值等於 Gmsh element tag 或 FEniCSx local cell index。Gmsh mesh 匯入 FEniCSx 後可能重新排序；mesh pipeline 必須建立一個可驗證的對應，使每個 dump `cell_ID` 能解析回相同 `MESH_ID` 的 `mesh.msh` 中某一實際 cell。

## 5. Cell sampling

- `cell_ID` 是同一 `MESH_ID` 下穩定的 finite-element cell ID。
- `x y z` 是 cell centroid。
- `T` 在 centroid 評估。
- `q*` 是該 cell 的熱流密度。
- `region_ID` 是 cell 所屬 semantic volume tag。
- v1 只支援此模式；nodes 等明確需求出現後再另行規格化。

`cell` 是 finite-element mesh cell。其實際 element type、vertex coordinates 與 connectivity 由對應的 `build/mesh.msh` 定義；dump 本身不假設 cell 是立方體、四面體或其他特定形狀。dump 的 `x y z` 僅是 sampling location，不能用來重建 cell 形狀。

## 6. ID 與排序

- 同一 `MESH_ID` 下，`cell_ID`、座標和 `region_ID` 在所有 timestep 中不得改變。
- 每個 dump 的資料列依 `cell_ID` 升冪排序。
- mesh 改變後可以重新編號。
- v1 不要求改變 MPI process 數後仍產生完全相同的 ID；此需求等真正需要平行 dump 重現性時再加入。

`MESH_ID` 的最低生命周期要求：

```text
same cached mesh  → same MESH_ID
mesh rebuilt      → new MESH_ID
```

第一版 mapping 驗證：對每個 dumped `cell_ID`，解析對應的 `mesh.msh` cell，從 topology 重新計算 centroid，並確認它在 tolerance 內等於 dump 的 `x y z`。不得只檢查 ID 唯一性。

## 7. 數值與錯誤規則

- 不允許輸出無說明的 `NaN` 或 `Inf`；writer 遇到非有限值必須失敗。
- `NUMBER OF CELLS` 必須等於實際資料列數。
- 每列欄位數必須等於 `FIELDS` 的欄位數。
- writer 不補算缺少的 field；要求的 field 若未由 `analyze.py` 提供，必須失敗。

## 8. 彙總與可視化

`summary.csv` 與 dump 分開：前者保存 region min/max/average、tagged surface total heat flow 等彙總結果；後者保存空間場快照。

簡單的場曲線可只讀 dump。若要畫真正的 3D mesh、surface 或 slice，後處理必須同時讀取：

```text
build/mesh.msh
output/dump/<timestep>.dump
```

`mesh.msh` 提供 topology，dump 提供 field values；相鄰的 `build.json` 記錄該 `mesh.msh` 的 `MESH_ID`。後處理必須先確認 `build.json` 與 dump 的 `MESH_ID` 一致，再依 `cell_ID` 對應；不一致時直接報錯。

可視化由獨立的 Python 程式執行：

```text
postprocess/plot_dump.py
```

模擬流程不自動畫圖。修改配色、視角或選擇 timestep 時，不應重新執行 FEM 求解。

XDMF/HDF5 可作為需要有限元素拓撲或 ParaView 互動檢查時的選配輸出，不屬於 dump v1 必要格式。

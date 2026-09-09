# Verification、accuracy 與 troubleshooting

程式產生輸出不等於 simulation 已驗證。至少檢查解析/benchmark comparison、mesh
convergence、time-step convergence（暫態）與 energy/heat-flux balance。

## 實務 verification workflow

1. 先跑 Test 01，確認安裝與 steady pipeline 的 PASS。
2. 為新 geometry 建立可隔離的簡單 limiting case，核對 units、BC signs 與 symmetry。
3. 使用 $h$, $h/2$, $h/4$ 重建 mesh，比較關鍵溫度與總熱流。
4. 暫態使用 $dt$, $dt/2$, $dt/4$ 比較同一物理時間的結果。
5. 比較 tagged boundaries 的 $\dot Q$；無 source 的 steady case 應近似守恆。
6. 用 $\alpha=k/(\rho c_p)$ 與 $t_\mathrm{diff}\sim L^2/\alpha$ 估計需要解析的時間尺度。

Backward Euler 是一階時間準確；若 halving `dt` 仍顯著改變結果，原 dt 不足。空間上
P1 temperature 對 straight constant-k bar 恰可表示線性解，不能用 Test 01 的極小誤差
推論複雜 geometry 也不需 mesh convergence。

## Troubleshooting

### `Unsupported model.type`

`model.type` 不是目前兩個字串之一。使用 `steady_conduction` 或
`transient_conduction`；其他 physics 尚未實作。

### `Region material currently supports only 'local'`

目前沒有 named-material registry。常數材料直接寫 `k`；案例自訂 steady $k(T)$ 使用
`material: local`，並由同目錄 `material.py` 提供。薄層 contact 則使用
`type: thin_layer_resistance`，不是 named material。

### `Local temperature-dependent material is steady-only in v1`

第一版只驗證 steady $k(T)$。transient $k(T)$、$\rho(T)$、$c_p(T)$ 尚未形成已驗證的
time-stepping contract，因此 validator 會明確拒絕。

### `Local material must define callable: k`

確認案例 `main.py` import 的是正確 `material.py`，且其中定義 `def k(T): ...`。回傳值
必須是 UFL-compatible scalar expression；不要在函式中對 symbolic `T` 使用一般
`numpy.interp`、Python `if T > ...` 或其他只接受 numeric array 的操作。

### Nonlinear solver 未收斂

先檢查 $k(T)$ 在 BC 與預期 solution 範圍是否有限且嚴格為正。過強非線性也可能需要
更好的 initial guess、continuation 或 solver tuning，但這些目前尚未公開成 case options；
不要以放寬 verification tolerance 掩蓋 SNES failure。

### `regions must contain at least one material region`

steady constant-property case 可有多個 regions，但每個 key 都必須對應 geometry 的 volume
semantic tag。transient 與 local $k(T)$ 仍限制單一 region。

### `Every mesh cell must belong to a configured material region`

至少有 cell 沒有被 `regions` 對應的 physical volume tag 覆蓋。檢查 `geometry.py`、
`tags.json` 與 case region names；未標記 volume 不會默認取得某個材料。

### Thin-layer contact 結果不合理

確認 `contacts.<name>.region` 指向實際薄層 volume、`thickness_m` 等於 geometry 的法向
厚度，且薄層至少有可接受品質的 cells。薄層太薄而 mesh size 太大會造成劣質元素；這時
應局部細化或調整 representation，而不是只修改熱阻數值。

### `Stage 2 requires exactly two boundary conditions`

目前 validator hard-code 恰好兩個 BC，兩者都必須為 `fixed_temperature`。

### `Mesh has no facets tagged <name>` 或 semantic name `KeyError`

檢查 `geometry.py` 是否建立相同名稱的 dimension-2 physical group、`build/tags.json` 中
是否存在該 key，以及 `mesh.msh` 是否真的包含 facets。若 tags/cache 與 geometry 不一致，
重建該案例的 build artifacts。

### 改了 geometry，卻仍 reuse 舊 mesh

cache 只 hash `geometry.py`。若 geometry 由外部檔案/環境間接決定，這些變化不會被偵測。
修改 geometry file 本身或移走該案例的 `mesh.msh`、`tags.json`、`build.json` 後再跑。

### 只改 material 或 BC 卻重新 mesh

通常不應發生；確認沒有同時格式化/修改 `geometry.py`，也確認三個 cache files 都存在。

### Transient 缺 `rho` / `cp` / time / IC

所有 transient fields 都沒有 defaults；依 schema補上正值 `rho`, `cp`, `dt_s`, `end_s`
與三個 numeric initial-condition values。

### `time.end_s must be an integer multiple of time.dt_s`

這是 Test 02 runner 的條件。選擇使 `end_s / dt_s` 為整數的值，或在自有 runner 明確定義
最後不足一步的政策。

### Early transient 不合理或消失

比較 $dt$, $dt/2$, $dt/4$；穩定的 implicit scheme 仍可能時間解析度不足。也檢查 IC jump
是否與 mesh 對齊。

### `0.dump` 的 heat flux 全為零

Test 02 的 initial state 是 DG0；`analyze` 對 degree-0 function 明確輸出 zero heat flux，
因為 discontinuous gradient 不能以目前 cell-gradient路徑代表。從第一個 P1 solved step
開始判讀 flux。

### Dump 未產生

dump 不是 solver 自動功能。確認 `main.py` 有呼叫 `analyze`, `map_cell_ids`, `write_dump`，
且 requested fields 全都存在、有限且等長。

### `Dump v1 cell mapping supports serial runs only`

完整 dump workflow 不支援 MPI size > 1。以 serial 執行目前案例。

### PETSc/solver failure

先確認所有 material values 正值、至少有足夠 Dirichlet constraints、mesh 可讀且 tags 非空。
目前 solver options 固定為 LU，沒有 YAML tolerance knobs；若問題只在大 mesh 出現，這也可能
是 direct-solver memory limitation。

### Plot 很像散點而不是平滑場

現有 plotter刻意畫 cell-centroid samples，不含 connectivity/interpolation。真正 mesh/slice
視覺化尚未實作，不能只靠 dump centroid 重建。

# 物理模型、條件與 solver

## Spatial discretization

temperature 使用 continuous first-order Lagrange (`P1`) finite-element space；analysis 時再
interpolate 到 discontinuous piecewise-constant (`DG0`) cell fields。domain 固定按 3D mesh
載入。

## Steady conduction

現行 weak form對應：

$$
\nabla\cdot(k\nabla T)=0,
$$

其中 $k$ 為單一、正值、isotropic scalar constant，單位 W/(m K)。`model.build_model`
雖建立值為 0 的 source constant，但 case 無 heat-source schema，使用者不能指定 $Q$。

必要資料：至少一個由 semantic cell tags 完整覆蓋的 constant-$k$ region，以及兩個
fixed-temperature boundaries。local $k(T)$ 使用下述獨立 nonlinear builder。

## Transient conduction

現行 model 使用 Backward Euler：

$$
\frac{\rho c_p}{\Delta t}(T^{n+1}-T^n)
=\nabla\cdot(k\nabla T^{n+1}).
$$

$\rho$ 單位 kg/m³、$c_p$ 單位 J/(kg K)、$\Delta t$ 單位 s。它是 implicit、時間一階
準確。穩定並不代表準確：太大的 `dt_s` 仍會漏掉 early transient，應做時間收斂測試。

`build_transient_model` 建立單一步驟的 algebraic problem；`end_s`、step count、time loop、
dump schedule 與 state update 是案例 `main.py` 的責任。現有 runner 要求
`end_s / dt_s` 是整數（以 `round` 與 `np.isclose` 檢查）。

## Initial condition

唯一支援形式是沿全域 x 座標切分的兩個常數：

$$
T(x,0)=\begin{cases}
T_\mathrm{left}, & x<x_\mathrm{split},\\
T_\mathrm{right}, & x\ge x_\mathrm{split}.
\end{cases}
$$

初始 state 建在 `DG0` space，因此 discontinuity 可按 cell 表示；它不是 callable、region
mapping、P1 function 或一般 coordinate expression API。之後每一步的解是 P1；現有 runner
第一次 solve 後會以該 P1 function 重建 problem，後續 state 也為 P1。若 discontinuity
沒有與 mesh cell boundary 對齊，cell-center-based DG0 assignment 會造成 mesh-dependent
近似；Test 02 特別將 mesh 在 `x=0.05 m` fragment 對齊。

## Boundary conditions

目前只支援 fixed temperature（Dirichlet）：

$$
T=T_D \quad \text{on }\Gamma_D.
$$

Syntax：

```yaml
boundary_conditions:
  hot_end:
    type: fixed_temperature
    value_K: 4.0
  cold_end:
    type: fixed_temperature
    value_K: 1.0
```

key 必須存在於 `tags.json` 且指向有 mesh facets 的 physical surface。`value_K` 單位 K。
case validator 要求恰好兩個 BC；model 沒有依 `type` 分派其他 BC。

Adiabatic boundary 沒有可設定的 BC type。未被 Dirichlet 標記的 boundary 在弱式中自然為
zero normal flux，但目前恰好兩個 BC 的 validation 仍然存在；不可宣稱已有通用 adiabatic
configuration。

以下皆未實作：specified heat flux、total heat、convection、radiation、真正零厚度
contact/interface law、heat switch。

## Materials 與熱物性限制

- steady constant-property model 可有多個 region，conductivity 以 DG0 field 依 cell tag 指派。
- transient 支援多個 constant-property regions，以 cell tags 建立 DG0 `k/rho/cp` fields。
- `k`、`rho`、`cp` 使用統一 constant/table/Python property representation。
- steady 支援依 cell tags 指派多個 constant scalar $k$，以及單一 local $k(T)$ region；
  兩者目前不能組合。
- 不支援 anisotropic tensor、transient $k(T)$、`rho(T)` 或 `cp(T)`。
- CSV table使用piecewise-linear interpolation；Python callable是local extension code。
- 沒有 materials registry或material database。

## Thin-layer contact resistance

第一版用實體薄層近似面積比接觸熱阻 $R_c''$：

$$
k_\mathrm{contact}=\frac{\delta}{R_c''}.
$$

接觸層必須是 geometry 中獨立、conforming、具有 semantic volume tag 的有限厚度 region。
此時跨層溫降為 $\Delta T=q_nR_c''$。優點是沿用 continuous P1 與既有 linear solve；限制是
薄層必須 mesh-resolved，且 `thickness_m` 與實際幾何厚度由案例作者自行保持一致。

Test 05 已提供 1D P1 zero-thickness contact：介面以兩個重合但不共享的 nodes 保存
獨立 $T_L,T_R$，弱式直接加入 $h_c(T_L-T_R)$。這是獨立 benchmark solver；通用 3D
FEniCSx DG/Nitsche/mortar coupling，以及溫度或壓力相依 contact resistance 仍未實作。

## Linear solver

`solve.make_solver` 建立 `dolfinx.fem.petsc.LinearProblem`，固定 options：

```python
{"ksp_type": "preonly", "pc_type": "lu"}
```

也就是直接 LU solve。`solve.solve` 固定使用 PETSc prefix `steady_bar_`；
`make_solver` 讓 caller 指定 prefix，但不 expose tolerances 或 options mapping。case.yaml 中
沒有 `solver` section、relative/absolute tolerance、nonlinear options 或 convergence monitor。

## Temperature-dependent conductivity 與 nonlinear solver

steady 單一材料可由 CSV table 或案例本地 Python callable 定義 UFL-compatible：

$$
k=k(T),\qquad \nabla\cdot(k(T)\nabla T)=0.
$$

`model.build_nonlinear_model` 建立 residual 與 automatic Jacobian；
`solve.solve_nonlinear` 使用 PETSc SNES `newtonls`，每個 Newton linearization 仍用
preonly/LU。固定設定為 `snes_rtol=1e-10`、`snes_atol=1e-12`、最多 50 iterations，且
linear/nonlinear 不收斂都直接報錯。

第一版不支援 YAML solver options、temperature-dependent multi-region或任何 transient
`k(T)/rho(T)/cp(T)`。後者會在case validation明確拒絕。Python expression必須可由UFL微分。

## MPI 行為

FEniCSx mesh import、assembly、BC facet count 與 summaries 使用 `MPI.COMM_WORLD`，solve 本身
可在 MPI communicator 上工作；但 dump 所需的 `mesh.map_cell_ids` 明確只支援
`comm.size == 1`，否則丟出 `NotImplementedError`。因此現有 end-to-end examples 與 dump
workflow 是 **serial only**。不要用 `mpirun -np 2` 跑這兩個完整案例。

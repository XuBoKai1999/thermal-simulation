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

必要資料：一個 region 的 `k` 與兩個 fixed-temperature boundaries。

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

以下皆未實作：specified heat flux、total heat、convection、radiation、contact/interface
conductance、heat switch。

## Materials 與熱物性限制

- 恰好一個 region；`model` 直接取 `regions` 的第一個 value。
- `k`、`rho`、`cp` 均為 scalar constants。
- 不支援 region-dependent material、多材料 interface、anisotropic tensor、`k(T)`、
  `rho(T)` 或 `cp(T)`。
- 沒有 materials registry 或外部 property table。

## Linear solver

`solve.make_solver` 建立 `dolfinx.fem.petsc.LinearProblem`，固定 options：

```python
{"ksp_type": "preonly", "pc_type": "lu"}
```

也就是直接 LU solve。`solve.solve` 固定使用 PETSc prefix `steady_bar_`；
`make_solver` 讓 caller 指定 prefix，但不 expose tolerances 或 options mapping。case.yaml 中
沒有 `solver` section、relative/absolute tolerance、nonlinear options 或 convergence monitor。

## MPI 行為

FEniCSx mesh import、assembly、BC facet count 與 summaries 使用 `MPI.COMM_WORLD`，solve 本身
可在 MPI communicator 上工作；但 dump 所需的 `mesh.map_cell_ids` 明確只支援
`comm.size == 1`，否則丟出 `NotImplementedError`。因此現有 end-to-end examples 與 dump
workflow 是 **serial only**。不要用 `mpirun -np 2` 跑這兩個完整案例。


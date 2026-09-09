# Test 05 — steady nonlinear contact bar

This 1D P1 finite-element benchmark combines a temperature-dependent material with a true
zero-thickness contact. The two coincident interface nodes are independent, so temperature may jump.

```text
L = 0.1 m                 contact x = 0.05 m
T(0) = 4 K                T(L) = 1 K
k(T) = 10 [1 + 3/13 (T - 2.5)^2] W/(m K)
R''c = 0.004 m² K/W       hc = 250 W/(m² K)
dx = 0.01, 0.005, 0.0025, 0.00125 m
```

Exact regression targets:

```text
T_left = 3 K
T_right = 2 K
contact jump = 1 K
qx = 250 W/m²
q - hc (T_left - T_right) = 0
```

Run from the project root:

```powershell
.\scripts\wsl-run.ps1 "python3 test/05_steady_nonlinear_contact_bar/main.py"
.\scripts\wsl-run.ps1 "python3 test/05_steady_nonlinear_contact_bar/validate.py"
```

Each `build/dx_*/mesh.msh` stores the disconnected 1D topology; the matching
`output/dx_*/dump/0.dump` stores cell-centroid `T` and `q` fields.

The same runner also computes a finest-resolution transient reference with
`rho=1000 kg/m³`, `cp=100 J/(kg K)`, `dx=0.00125 m`, and `dt=0.125 s`. Its
initial state is 4 K throughout the left half and 1 K throughout the right half.
Snapshots at 0, 0.125, 0.5, 2, 10, 50, 100, 200, and 500 s are written under
`output/transient/dump/`. This is a numerical transient reference approaching the analytic
steady endpoint; it is not presented as a transient closed-form solution.

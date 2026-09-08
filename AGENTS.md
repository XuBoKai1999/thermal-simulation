# Execution Environment

This project uses Windows PowerShell for development and Codex interaction.

All Python simulation, FEniCSx, MPI, PETSc, and Gmsh commands must run inside WSL2 Ubuntu.

Do not use the Windows Python installation for simulation.

Use:

```powershell
.\scripts\wsl-run.ps1 "<command>"
```

Examples:

```powershell
.\scripts\wsl-run.ps1 "python3 main.py"
.\scripts\wsl-run.ps1 "python3 -m pytest"
.\scripts\wsl-run.ps1 "mpirun -np 2 python3 main.py"
```

The project directory is shared with WSL through `/mnt/c/...`.

When testing or running code, always execute through `scripts/wsl-run.ps1`.


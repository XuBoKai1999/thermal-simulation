# Thermal Simulation Roadmap

## Current ADR01 geometry status (2026-09-11)

- [x] Human-approved Step 0 decisions recorded in `run/01_ADR01/steps.md`.
- [x] Draft 0 translated directly to case-local Gmsh geometry without a new DSL.
- [x] Ten component groups and eleven connection groups generated and automatically validated.
- [ ] Human interactive inspection and approval of `run/01_ADR01/build/mesh.msh`.
- [ ] Material parameters and thermal solve remain gated after geometry approval.

> 原則：如無必要勿增實體。一次完成並驗證一個真正需要的能力。

## 已完成

- [x] Test 01–07：steady/transient、temperature-dependent properties、multi-region、窄範圍
  contact models、analysis、dump 與 convergence regressions。
- [x] 使用者手冊與 framework readiness audit。
- [x] Source-preserving NIST cryogenic materials mirror、derived tables、listing CLI 與 database
  regressions。

## 現在：ADR01 前置工作

1. [ ] 讓 `case.yaml` 明確引用一個 NIST `material.yaml` property series，沿用既有
   `Property`/table loader；保留 inline syntax，不建立 registry/database abstraction。
2. [ ] 以 focused regression 驗證 external file resolution、series selection、range failure，
   並同步 manual/architecture。
3. [ ] 決定 NIST 未提供的 density 與 1–4 K data 來源；禁止 silent extrapolation。
4. [ ] 完成 ADR01 physical inventory：必要 geometry、semantic regions、材料、contact 假設、
   fixed-temperature surfaces、initial condition、simulation time 與 observables。

## ADR01 baseline

依 `run/01_ADR01/ADR01_steps.md` 的 gates 順序執行：

1. [ ] 建立並目視檢查最小 geometry、tags 與 conformal interfaces；先不 solve。
2. [ ] 建立 solver-valid `case.yaml`，確認所有 property domains 覆蓋目標溫度。
3. [ ] 從 Test 07 重用最小 transient workflow，產生 dump、region statistics 與 boundary
   heat flows；不建立 generic runner。
4. [ ] 完成 smoke run、thermal-path review、mesh/time-step convergence 與 energy sanity check。
5. [ ] 換入可信的 temperature-dependent properties，重跑驗證並形成 baseline report。

## Baseline 後才評估

依實際 sensitivity 一次加入一項：contact resistance、prescribed heat load、time-dependent
boundary、heat switch、radiation、anisotropic conductivity 或 MCE/`C(T,B)`。每項先做最小
獨立 regression，再整合到 ADR01。

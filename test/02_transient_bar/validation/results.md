# Transient bar validation

後處理只讀 `output/dump/*.dump`，不重新執行 FEM。圖中 continuous lines 是獨立
Fourier 解析解，markers 是 3D tetrahedral-cell dump 沿橫截面平均後的結果。

目前展示時間為：

```text
temperature: 0, 1, 2, 5, 10, 20, 500 s
heat flux:      1, 2, 5, 10, 20, 500 s
```

- `temperature_profiles_comparison.png` 顯示初始階躍逐步擴散並趨近線性穩態。
- `heat_flux_profiles_comparison.png` 顯示熱流先集中於 $x=L/2$ 附近，再趨近均勻
  穩態值 $q_x=300\ \mathrm{W/m^2}$。
- $t=0$ 的 heat flux 不作嚴格比較，因初始溫度在 $x=L/2$ 不連續。
- 早期數值與解析曲線的差距主要來自 $\Delta t=1\ \mathrm s$ 的 backward Euler
  時間離散與有限元素空間離散。

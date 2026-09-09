# Transient bar space-time convergence

本測試使用同一物理案例，比較：

```text
dx = 0.01, 0.005, 0.0025 m
dt = 0.0625, 0.03125, 0.015625 s
comparison time = 0.0625, 0.125, 0.25, 0.5 s
```

共 9 組 early-transient run。每組 dump 位於
`output/convergence/dx_*/dt_*/dump/`，後處理只讀 dump 並與獨立 Fourier 解析解比較。

- `temperature_profiles_varying_dt.png`：固定 `dx=0.0025 m`，比較不同 dt。
- `heat_flux_profiles_varying_dt.png`：固定 `dx=0.0025 m`，比較不同 dt。
- `temperature_profiles_varying_dx.png`：固定 `dt=0.015625 s`，比較不同 dx。
- `heat_flux_profiles_varying_dx.png`：固定 `dt=0.015625 s`，比較不同 dx。
- `convergence_errors.csv`：所有 dx、dt 與比較時間的 T/qx RMSE、最大誤差。

粗網格在最早時間的溫度跳躍兩側可見 overshoot/undershoot，`qx` 亦可能出現局部
負值並低估尖峰；加密 dx、dt 後逐漸貼近解析曲線。這些圖刻意不包含後期或穩態，
以免 early-transient 異常被幾乎重合的 late-time profiles 掩蓋。

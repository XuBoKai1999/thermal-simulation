# ADR01 材料與熱物性參數定案（Baseline v1）

> **用途**：直接作為 `run/01_ADR01/` 第一版 post-demagnetization transient thermal baseline 的人類可讀參數規格。  
> **目標溫區**：$1\ \mathrm{K}\le T\le4\ \mathrm{K}$。  
> **模型物理狀態**：假設退磁已完成；GGG 採 $H=0$；目前只做固體導熱暫態，不模擬 magnetocaloric cycle 本身。  
> **性質**：這是一組**baseline modeling decision**，不是對實機材料規格的宣稱。日後若取得實際 RRR、support grade、heat-switch hardware 等資料，再覆寫相應假設。

---

# 0. 先定案：各 region 用什麼

| Region | Baseline material / model | 本版決定 |
|---|---|---|
| `hot_plate` | OFHC Cu / fixed reservoir | **固定 $T=4$ K 邊界**；不必作 solved material region。若日後改成 solved body，沿用 Cu RRR=100。 |
| `cylinder_1` | OFHC Copper | **RRR=100**；baseline 假設。 |
| `heat_switch` | ideal OFF heat switch | **$G_{\rm off}=0$ W/K**；第一版視為理想斷熱，不塞假的 bulk $k,c_p,\rho$。 |
| `cylinder_2` | OFHC Copper | **RRR=100**；baseline 假設。 |
| `ggg` | Gd$_3$Ga$_5$O$_{12}$ | **$H=0$**；使用 Fisher zero-field $c_p$、Daudin zero-field $k$。 |
| `cylinder_3` | OFHC Copper | **RRR=100**。 |
| `cold_stage` | OFHC Copper | **RRR=100**。 |
| `sample` | OFHC Copper | **RRR=100**。 |
| `support_1` | G-10/FR-4 | Runyan–Jones fiber/laminate-plane $k(T)$ 作為 support 軸向 effective scalar。 |
| `support_2` | G-10/FR-4 | 同 `support_1`。 |

其他 baseline 決定：

- Cu nominal case：**RRR = 100**。
- Cu sensitivity case：**RRR = 50**。
- PEEK：**不納入 baseline**。
- 普通實體接觸：第一版仍採 **perfect contact**。
- G-10：**不可描述為 isotropic material**；本版只把文獻中的纖維／laminate plane 導熱率當作支撐桿軸向的 effective $k$。
- heat switch：第一版是 **ideal-open OFF state**。文獻中的 $^3$He switch 數字只作量級參考，不當 ADR01 實機值。

---

# 1. Solver-facing 總表

| Material / model | $\rho$ [kg/m$^3$] | $k(T)$ | $c_p(T)$ | Baseline status |
|---|---:|---|---|---|
| OFHC Cu, RRR=100 | 8960 | Hust–Lankford analytical correlation | White–Collocott analytical correlation | **READY** |
| OFHC Cu, RRR=50 | 8960 | 同式，RRR=50 | 同一 Cu $c_p(T)$ | **READY sensitivity** |
| GGG, $H=0$ | 7100 | Daudin Fig. 1 zero-field，暫採 digitized table | Fisher Table IX zero-field smoothed table | **READY for baseline；$k$ 為 digitized provisional** |
| G-10/FR-4 | 1910 | Runyan–Jones analytical fit | NIST volumetric heat-capacity table轉換 | **READY** |
| Heat switch OFF | N/A | $G_{\rm off}=0$ W/K | N/A | **READY as ideal-open model** |

---

# 2. OFHC Copper

適用：`cylinder_1`, `cylinder_2`, `cylinder_3`, `cold_stage`, `sample`；`hot_plate` 若日後改為 solved body 亦沿用。

## 2.1 Density

第一版視為常數：

$$
\boxed{\rho_{\rm Cu}=8960\ \mathrm{kg/m^3}}
$$

來源：NIST PML — Composition of Copper。

---

## 2.2 Thermal conductivity $k(T,\mathrm{RRR})$

### 來源

J. G. Hust and A. B. Lankford (1984), *Thermal conductivity of aluminum, copper, iron, and tungsten for temperatures from 1 K to the melting point*, NBS IR 84-3007, DOI `10.6028/NBS.IR.84-3007`。

原報告 general correlation（Eq. 1.1.3–1.1.6）與 Cu-specific coefficients（Cu section）可寫成：

$$
\boxed{
k(T)=\frac{1}{W_0+W_i+W_{i0}}
}
$$

其中

$$
W_0=\frac{\beta}{T},
$$

$$
W_i=
\frac{P_1T^{P_2}}
{1+P_1P_3T^{P_2+P_4}
\exp\left[-\left(\frac{P_5}{T}\right)^{P_6}\right]}
+W_c,
$$

$$
W_{i0}=P_7\frac{W_iW_0}{W_i+W_0}.
$$

Cu 的 purity parameter：

$$
\boxed{\beta=\frac{0.634}{\mathrm{RRR}-1}}
$$

$$
\beta_r=\frac{\beta}{0.0003},
\qquad
P_7=\frac{0.838}{\beta_r^{0.1661}}.
$$

固定係數：

| coefficient | value |
|---|---:|
| $P_1$ | $1.754\times10^{-8}$ |
| $P_2$ | $2.763$ |
| $P_3$ | $1102$ |
| $P_4$ | $-0.165$ |
| $P_5$ | $70$ |
| $P_6$ | $1.756$ |

Cu residual correction：

$$
\begin{aligned}
W_c={}&-0.00012\ln(T/420)
\exp\left[-\left(\frac{\ln(T/470)}{0.7}\right)^2\right]\\
&-0.00016\ln(T/73)
\exp\left[-\left(\frac{\ln(T/87)}{0.45}\right)^2\right]\\
&-0.00002\ln(T/18)
\exp\left[-\left(\frac{\ln(T/21)}{0.5}\right)^2\right].
\end{aligned}
$$

$T$ 以 K 代入，輸出：

$$
k:\ \mathrm{W/(m\,K)}.
$$

### ADR01 checkpoints

| $T$ [K] | $k$, RRR=50 [W/(m K)] | $k$, RRR=100 [W/(m K)] |
|---:|---:|---:|
| 1.0 | 77.29 | 156.15 |
| 1.5 | 115.93 | 234.22 |
| 2.0 | 154.57 | 312.29 |
| 2.5 | 193.21 | 390.33 |
| 3.0 | 231.83 | 468.33 |
| 3.5 | 270.45 | 546.28 |
| 4.0 | 309.04 | 624.13 |

Primary-source Table 2.4.1 對 RRR=100 給出約 $156,312,468,624$ W/(m K) at $T=1,2,3,4$ K，與上式一致。

> **重要修正**：舊 working sheet 曾寫成 $\beta=0.634/\mathrm{RRR}$；本版改為與 primary-source recommended table 相符的 $\boxed{0.634/(\mathrm{RRR}-1)}$。

### 本版實際使用

$$
\boxed{\mathrm{RRR}=100}
$$

RRR=50 只保留作 sensitivity case，不混入 nominal baseline。

---

## 2.3 Specific heat $c_p(T)$

### 來源

G. K. White and S. J. Collocott (1984), *Heat Capacity of Reference Materials: Cu and W*, J. Phys. Chem. Ref. Data 13, 1251–1257, DOI `10.1063/1.555728`。

Section 2.1, Eq. (1)，適用於低溫 Cu reference region（1–25 K 對 ADR01 足夠）：

$$
C_{p,m}(T)=\sum_{i=1}^{6} A_iT^{2i-1}
\quad [\mathrm{mJ/(mol\,K)}].
$$

原文係數：

| $i$ | $A_i$ [mJ/(mol K$^{2i}$)] | SI coefficient [J/(mol K$^{2i}$)] |
|---:|---:|---:|
| 1 | $6.9434\times10^{-1}$ | $6.9434\times10^{-4}$ |
| 2 | $4.7548\times10^{-2}$ | $4.7548\times10^{-5}$ |
| 3 | $1.6314\times10^{-6}$ | $1.6314\times10^{-9}$ |
| 4 | $9.4786\times10^{-8}$ | $9.4786\times10^{-11}$ |
| 5 | $-1.3639\times10^{-10}$ | $-1.3639\times10^{-13}$ |
| 6 | $5.3898\times10^{-14}$ | $5.3898\times10^{-17}$ |

因此若直接用 SI：

$$
\boxed{
\begin{aligned}
C_{p,m}(T)= {}&6.9434\times10^{-4}T
+4.7548\times10^{-5}T^3\\
&+1.6314\times10^{-9}T^5
+9.4786\times10^{-11}T^7\\
&-1.3639\times10^{-13}T^9
+5.3898\times10^{-17}T^{11}
\end{aligned}}
$$

單位為 J/(mol K)。

取

$$
M_{\rm Cu}=0.063546\ \mathrm{kg/mol},
$$

solver 使用：

$$
\boxed{c_{p,\rm Cu}(T)=\frac{C_{p,m}(T)}{0.063546}}
$$

單位 J/(kg K)。

### Checkpoints

| $T$ [K] | $c_p$ [J/(kg K)] |
|---:|---:|
| 1.0 | 0.011675 |
| 1.5 | 0.018915 |
| 2.0 | 0.027840 |
| 2.5 | 0.039011 |
| 3.0 | 0.052992 |
| 3.5 | 0.070347 |
| 4.0 | 0.091644 |

此 $c_p(T)$ 不依 ADR01 的 RRR scenario 拆分。

---

# 3. GGG — Gd$_3$Ga$_5$O$_{12}$, $H=0$

適用：`ggg`。

## 3.1 Density

Baseline 直接採：

$$
\boxed{\rho_{\rm GGG}=7100\ \mathrm{kg/m^3}}
$$

來源：T. Mashimo et al. (2006), PRL 96, 105504，文中明列 single-crystal GGG density $7.10\ \mathrm{g/cm^3}$。

Cross-check：Fisher et al. 1973 以晶格常數計得其 sample 約 $7.14\ \mathrm{g/cm^3}$。兩者差約 0.6%；第一版不做平均，固定採 7100 kg/m$^3$。

---

## 3.2 Specific heat $c_p(T,H=0)$

### 來源與選擇

R. A. Fisher et al. (1973), *Magnetothermodynamics of gadolinium gallium garnet. I...*, JCP 59, 4652–4663, DOI `10.1063/1.1680677`。

本版採 **Table IX 的 smoothed correlated zero-field ($0$ G) values**，而不是 raw observations。Table IX 已按作者註記乘上 0.9960 stoichiometry correction。

Table IX 的 $C_H$ 單位為：

$$
\mathrm{gibbs/(mol\ Gd^{3+})}
\equiv
\mathrm{cal/(mol\ Gd^{3+}\,K)}.
$$

作者的 sample-equivalent mass 為 337.45 g per mole Gd$^{3+}$，所以轉成 mass-specific heat：

$$
\boxed{
c_p(T)=C_H(T)\frac{4.184}{0.33745}
=12.39887\,C_H(T)
}
$$

單位 J/(kg K)。

### Solver table：$H=0$

| $T$ [K] | Fisher $C_H$ [cal/(mol Gd$^{3+}$ K)] | $c_p$ [J/(kg K)] |
|---:|---:|---:|
| 1.00 | 1.6116 | 19.982 |
| 1.10 | 1.5165 | 18.803 |
| 1.20 | 1.4144 | 17.537 |
| 1.30 | 1.3126 | 16.275 |
| 1.40 | 1.2151 | 15.066 |
| 1.50 | 1.1238 | 13.934 |
| 1.60 | 1.0395 | 12.889 |
| 1.70 | 0.9625 | 11.934 |
| 1.80 | 0.8927 | 11.069 |
| 1.90 | 0.8298 | 10.289 |
| 2.00 | 0.7719 | 9.571 |
| 2.20 | 0.6748 | 8.367 |
| 2.40 | 0.5934 | 7.358 |
| 2.60 | 0.5249 | 6.508 |
| 2.80 | 0.4672 | 5.793 |
| 3.00 | 0.4186 | 5.190 |
| 3.20 | 0.3771 | 4.676 |
| 3.40 | 0.3415 | 4.234 |
| 3.60 | 0.3104 | 3.849 |
| 3.80 | 0.2835 | 3.515 |
| 4.00 | 0.2597 | 3.220 |

**Interpolation**：第一版對此 table 做 piecewise-linear interpolation 即可；禁止混入有限磁場 series。

> 此處的重要物理限定不是 [100] 軸本身，而是 **$H=0$**。未來真正做 magnetocaloric / finite-field model 時，才需要把 $H$ 與 crystal orientation 一起升格為 state/qualifier。

---

## 3.3 Thermal conductivity $k(T,H=0)$

### 來源確認

B. Daudin, R. Lagnier, B. Salce (1982), *Thermodynamic properties of the gadolinium gallium garnet, Gd$_3$Ga$_5$O$_{12}$, between 0.05 and 25 K*, DOI `10.1016/0304-8853(82)90092-0`。

正文已明確寫：

> “In fig. 1 the zero field conductivity $K(T)$ of sample II in the as-received state is reported.”

因此 **field condition 已解決：Fig. 1 open-circle series 就是 $H=0$ baseline 可用資料**。

文中 stationary-flux measurement 對 $K(T)$ 的 systematic error 報告為小於約 7%。但 Fig. 1 沒有直接給數值表，因此本版採圖上 digitization。

### Baseline digitized table（provisional）

以下是從 Fig. 1 的 log-log open-circle series 擷取／平滑後的第一版數值。原圖縱軸單位是 W/(cm K)，下表已乘 $100$ 轉為 W/(m K)。由於含圖面 digitization，**第一版建議把這條 $k(T)$ 視為約 ±15% 的 model uncertainty**，之後若拿到原始數表再替換。

| $T$ [K] | $k_{\rm GGG}(H=0)$ [W/(m K)] |
|---:|---:|
| 1.00 | 4.6 |
| 1.25 | 11.0 |
| 1.50 | 18.6 |
| 1.75 | 27.7 |
| 2.00 | 37.3 |
| 2.50 | 61.8 |
| 3.00 | 91.4 |
| 3.50 | 121.9 |
| 4.00 | 146.5 |

**Interpolation**：第一版採 piecewise-linear interpolation。  
**禁止**：把 Daudin 的 finite-field results 混進這張表。

### Cross-check

Slack & Oliver (1971), *Thermal Conductivity of Garnets and Phonon Scattering by Rare-Earth Ions*, DOI `10.1103/PhysRevB.4.592`，只作 2–4 K garnet literature cross-check，不取代 Daudin sample-II zero-field baseline。

### 本版狀態

$$
\boxed{\text{usable, but provisional digitized data}}
$$

這是整份 baseline 中最值得日後再精修的 bulk-material parameter。

---

# 4. G-10 / FR-4 supports

適用：`support_1`, `support_2`。

## 4.1 Density

Runyan & Jones (2008), Table 1：

$$
\boxed{\rho_{\rm G10}=1.91\ \mathrm{g/cm^3}=1910\ \mathrm{kg/m^3}}
$$

該 density 是 room-temperature manufacturer property；第一版視為 constant。

---

## 4.2 Thermal conductivity $k(T)$

### 來源

M. C. Runyan and W. C. Jones (2008), *Thermal conductivity of thermally-isolating polymeric and composite structural support materials between 0.3 and 4 K*, DOI `10.1016/j.cryogenics.2008.06.002`。

Table 2 fit：

$$
\boxed{k(T)=\alpha T^{\beta+\gamma T^n}}
$$

G-10/FR-4：

| coefficient | value |
|---|---:|
| $\alpha$ | $12.8\ \mathrm{mW/(m\,K)}=0.0128\ \mathrm{W/(m\,K)}$ |
| $\beta$ | 2.41 |
| $\gamma$ | -0.921 |
| $n$ | 0.222 |

因此：

$$
\boxed{
k_{\rm G10}(T)=0.0128\,T^{2.41-0.921T^{0.222}}
\ \mathrm{W/(m\,K)}
}
$$

valid approximately over 0.3–4.2 K。作者對 fit-generated $k$ 指定約 10% uncertainty。

### Orientation qualifier

文中 bulk fiber-containing composite 的 $k$ 是沿 fiber axis / woven fabric plane 測量。本版定義：

$$
\boxed{k_{\rm support,axial}(T)=k_{\rm Runyan/Jones}(T)}
$$

這只是支撐桿軸向 effective scalar，不代表 G-10 isotropic。

### Checkpoints

| $T$ [K] | $k$ [W/(m K)] |
|---:|---:|
| 1.0 | 0.012800 |
| 1.5 | 0.022601 |
| 2.0 | 0.032309 |
| 2.5 | 0.041406 |
| 3.0 | 0.049690 |
| 3.5 | 0.057103 |
| 4.0 | 0.063658 |

---

## 4.3 Heat capacity

### 主資料源

NIST Cryogenic Material Properties — Regenerator Materials，G-10 column，直接提供：

$$
C_V(T)=\rho c_p(T)
$$

原始單位：

$$
\mathrm{J/(cm^3\,K)}.
$$

因 framework 目前使用 $\rho$ 與 mass-specific $c_p$，以同一 baseline density $1910\ \mathrm{kg/m^3}$ 分拆：

$$
\boxed{
c_p(T)=\frac{10^6\,C_V(T)}{1910}
}
$$

如此 solver 中再乘 $\rho c_p$ 時，會精確回到 NIST 原始 volumetric heat capacity（忽略數字 rounding）。

### 最小 solver table

以下列出 1–4 K 可直接使用的 reduced table；若 Codex 要建立正式 CSV，**優先從 NIST 原始頁逐列匯入完整 1–4 K G-10 column**，而不是只用這 7 點。

| $T$ [K] | NIST $C_V$ [J/(cm$^3$ K)] | converted $c_p$ [J/(kg K)] |
|---:|---:|---:|
| 1.00000 | 0.00048 | 0.25131 |
| 1.52513 | 0.00073 | 0.38220 |
| 2.00544 | 0.00096 | 0.50262 |
| 2.49080 | 0.00119 | 0.62304 |
| 3.02386 | 0.00147 | 0.76963 |
| 3.50725 | 0.00233 | 1.21990 |
| 3.97616 | 0.00316 | 1.65445 |

NIST 原始頁：  
`https://trc.nist.gov/cryogenics/materials/RegeneratorMaterials/Regenerator%20Materials%20rev%2009-22-06.htm`

### Cross-check only

Walker & Anderson (1981), *Thermal conductivity and specific heat of a glass–epoxy composite at temperatures below 4 K*, DOI `10.1063/1.1136614`，其 Fig. 2 顯示 G-10 / G-10CR 的 low-$T$ specific heat，可拿來確認 NIST curve 的量級與趨勢；本版不另外 digitize 該圖，以避免建立兩套競爭 baseline。

---

# 5. Heat switch — 第一版直接定成 ideal OFF

適用：`heat_switch`。

第一版 post-demagnetization baseline 不研究 switch hardware，因此直接定：

$$
\boxed{G_{\rm off}(T)=0\ \mathrm{W/K}}
$$

意義：

- 4 K hot side 與 ADR cold chain 透過 heat switch 的導熱路徑完全斷開；
- `heat_switch` 不應再被當作一個普通 bulk solid 填入 $k,c_p,\rho$；
- 若現有 geometry 中仍有 switch volume，solver-facing implementation 應把它轉成「disabled thermal connection / ideal-open interface」的物理效果，而不是給一個假材料。

## Literature-scale reference（不是 ADR01 parameter）

Catarino & Paine (2011), $^3$He gas-gap heat switch：在約 1.7 K 報告

$$
G_{\rm off}\approx 60\ \mu\mathrm{W/K},
$$

$$
G_{\rm on}\approx96\text{–}100\ \mathrm{mW/K}.
$$

這組值只可用來設計未來 sensitivity / finite-$G_{\rm off}$ case，**不得稱為葛博實機 switch 值**。

---

# 6. 建議實際 material property representation

第一版不要把所有性質硬轉成同一種形式。

| Material | property | representation |
|---|---|---|
| Cu RRR=100 | $\rho$ | constant |
| Cu RRR=100 | $k(T)$ | analytical / Python function |
| Cu | $c_p(T)$ | analytical / Python function |
| Cu RRR=50 | $k(T)$ | 同一 function，RRR parameter=50 |
| GGG | $\rho$ | constant |
| GGG | $c_p(T,H=0)$ | table |
| GGG | $k(T,H=0)$ | provisional table |
| G-10 | $\rho$ | constant |
| G-10 | $k(T)$ | analytical / Python function |
| G-10 | $c_p(T)$ | table（正式版用完整 NIST 1–4 K column） |
| Heat switch OFF | $G_{\rm off}$ | constant conductance = 0 W/K / disabled connection |

---

# 7. Region → parameter record 最終 mapping

```text
hot_plate
    BC: T = 4 K
    solved material: no

cylinder_1
    material: OFHC_Cu_RRR100

heat_switch
    model: ideal_open
    G_off: 0 W/K

cylinder_2
    material: OFHC_Cu_RRR100

ggg
    material: GGG_H0
    rho: 7100 kg/m^3
    cp: Fisher1973_TableIX_H0
    k: Daudin1982_Fig1_H0_digitized_v1

cylinder_3
    material: OFHC_Cu_RRR100

cold_stage
    material: OFHC_Cu_RRR100

sample
    material: OFHC_Cu_RRR100

support_1
    material: G10_FR4_axial_effective

support_2
    material: G10_FR4_axial_effective
```

Sensitivity material record：

```text
OFHC_Cu_RRR50
    same rho and cp as baseline copper
    k(T): Hust-Lankford with RRR = 50
```

---

# 8. 本版哪些東西仍然不是「實機已知」

這些已**決定作 baseline**，但日後取得硬體資料就應覆寫：

1. `cylinder_1`、`cylinder_2` 是 OFHC Cu。
2. Cu RRR=100。
3. support 是 G-10/FR-4，而非 PEEK/G-10CR 其他 grade。
4. Runyan–Jones laminate-plane $k$ 可當 support 軸向 effective $k$。
5. heat switch 是 ideal open，即 $G_{\rm off}=0$。
6. GGG $k(T)$ 目前是從 Daudin Fig. 1 digitize，不是作者原始數表。
7. GGG 的 $c_p$ 與 $k$ 來自不同 specimen / publication；對第一版材料模型可接受，但不代表單一實體樣品的精密 metrology record。

---

# 9. 第一輪 sensitivity 建議

等 nominal baseline 能穩定跑完，再依重要性只做下列三個 sensitivity，不要一次增加太多實體：

| sensitivity | nominal | alternate | 目的 |
|---|---|---|---|
| Cu purity | RRR=100 | RRR=50 | 看 Cu link 對 cooldown time 的影響 |
| GGG $k$ | digitized central curve | $\pm15\%$ | 包含 measurement + digitization/model uncertainty |
| heat switch leak | $G_{\rm off}=0$ | finite $G_{\rm off}$（取得 hardware 後） | 看 4 K leakage 對 cold stage 的影響 |

暫時不需要同時新增 PEEK scenario、radiation、contact resistance、MCE 等因素。

---

# 10. Sources actually used in this baseline

## Copper

1. Hust, J. G.; Lankford, A. B. (1984). *Thermal conductivity of aluminum, copper, iron, and tungsten for temperatures from 1 K to the melting point*. NBS IR 84-3007. DOI: `10.6028/NBS.IR.84-3007`.
2. White, G. K.; Collocott, S. J. (1984). *Heat Capacity of Reference Materials: Cu and W*. J. Phys. Chem. Ref. Data 13, 1251–1257. DOI: `10.1063/1.555728`.
3. Simon, N. J.; Drexler, E. S.; Reed, R. P. (1992). *Properties of Copper and Copper Alloys at Cryogenic Temperatures*. NIST Monograph 177. DOI: `10.6028/NIST.MONO.177` — cross-check.

## GGG

4. Fisher, R. A.; Brodale, G. E.; Hornung, E. W.; Giauque, W. F. (1973). *Magnetothermodynamics of gadolinium gallium garnet. I. Heat capacity, entropy, magnetic moment from 0.5 to 4.2 K, with fields to 90 kG along the [100] axis*. DOI: `10.1063/1.1680677`.
5. Daudin, B.; Lagnier, R.; Salce, B. (1982). *Thermodynamic properties of the gadolinium gallium garnet, Gd3Ga5O12, between 0.05 and 25 K*. DOI: `10.1016/0304-8853(82)90092-0`.
6. Slack, G. A.; Oliver, D. W. (1971). *Thermal Conductivity of Garnets and Phonon Scattering by Rare-Earth Ions*. DOI: `10.1103/PhysRevB.4.592` — cross-check.
7. Mashimo, T. et al. (2006). *Transition to a Virtually Incompressible Oxide Phase at a Shock Pressure of 120 GPa: Gd3Ga5O12*. DOI: `10.1103/PhysRevLett.96.105504`.

## G-10

8. Runyan, M. C.; Jones, W. C. (2008). *Thermal conductivity of thermally-isolating polymeric and composite structural support materials between 0.3 and 4 K*. DOI: `10.1016/j.cryogenics.2008.06.002`.
9. Walker, F. J.; Anderson, A. C. (1981). *Thermal conductivity and specific heat of a glass–epoxy composite at temperatures below 4 K*. DOI: `10.1063/1.1136614` — cross-check.
10. NIST Cryogenic Material Properties — Regenerator Materials, G-10 volumetric heat capacity.

## Heat switch

11. DiPirro, M. J.; Shirron, P. J. (2014). *Heat switches for ADRs*. DOI: `10.1016/j.cryogenics.2014.03.017` — model/background.
12. Catarino, I.; Paine, C. (2011). *$^3$He gas gap heat switch*. DOI: `10.1016/j.cryogenics.2010.10.009` — magnitude example only.

---

# 11. 給 Codex 的實作判定

完成這份參數表之後，材料研究階段不應再無限延伸。對 ADR01 baseline：

- **Cu：READY**
- **G-10：READY**（正式 CSV 請匯入完整 NIST table）
- **GGG $c_p$：READY**
- **GGG $k$：READY_FOR_BASELINE / PROVISIONAL_DIGITIZED**
- **heat switch：READY_AS_IDEAL_OPEN**

因此下一個合理 gate 是：

> 將上述 representation 轉成現有 `lib.materials.Property` 能讀取的 function/table/constant，做 property-level sanity check，再開始第一個 ADR01 transient baseline。

不要為了「更完整」而在此時加入新的材料 family、MCE、radiation、contact resistance 或真實 heat-switch hardware model。

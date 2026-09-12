# ADR01 材料參數工作表（1–4 K）

> **用途**：ADR01 post-demagnetization transient baseline 的材料參數單一工作表。  
> **目標溫區**：$1\ \mathrm{K}\le T\le4\ \mathrm{K}$。  
> **模型狀態**：假設退磁已完成；GGG baseline 採 $H=0$；目前不模擬磁化／退磁本身。  
> **原則**：只填入已有可追溯來源的量。難以可靠抽取的內容先留 `TODO`，不造值、不跨來源範圍靜默外插。  
> **版本性質**：working extraction pass 1；可作為後續 Codex 清洗／轉 CSV 的來源，但尚不是最終材料資料庫。

---

## 0. ADR01 baseline 材料決策

| Region | Baseline material / model | Qualifier | 目前狀態 |
|---|---|---|---|
| `hot_plate` | OFHC Cu / fixed-temperature reservoir | $T=4$ K；若作 solved body 則沿用 Cu RRR=100 | BC 已定 |
| `cylinder_1` | OFHC Cu | RRR=100；**baseline 假設，非實機確認** | 可建參數 |
| `heat_switch` | special thermal-switch model | OFF state；目標參數 $G_{\mathrm{off}}(T)$ | **SPECIAL_MODEL** |
| `cylinder_2` | OFHC Cu | RRR=100；**baseline 假設，非實機確認** | 可建參數 |
| `ggg` | Gd$_3$Ga$_5$O$_{12}$ | $H=0$ | $\rho$ 可用；$k,c_p$ 待抽 |
| `cylinder_3` | OFHC Cu | RRR=100 | 可建參數 |
| `cold_stage` | OFHC Cu | RRR=100 | 可建參數 |
| `sample` | OFHC Cu | RRR=100 | 可建參數 |
| `support_1` | G-10/FR-4 | Runyan–Jones fiber/laminate-plane $k$ 作 effective axial scalar | $k,\rho$ 可用；$c_p$ 表待完整轉錄 |
| `support_2` | G-10/FR-4 | 同 `support_1` | 同上 |

**Cu scenario：**

- nominal baseline：RRR = 100
- sensitivity：RRR = 50

PEEK 不納入第一版 baseline。

---

# 1. OFHC Copper

適用：`cylinder_1`, `cylinder_2`, `cylinder_3`, `cold_stage`, `sample`；`hot_plate` 若改成 solved body 亦可沿用。

需要：

$$
k(T,\mathrm{RRR}),\qquad c_p(T),\qquad \rho.
$$

## 1.1 Density

第一版取常數：

$$
\boxed{\rho_{\mathrm{Cu}}=8960\ \mathrm{kg/m^3}}
$$

來源：NIST Physical Measurement Laboratory, Composition of COPPER。

> 這裡的 $\rho$ 是質量密度，不是 RRR 定義中的 electrical resistivity。

---

## 1.2 Thermal conductivity $k(T,\mathrm{RRR})$

### Source

J. G. Hust and A. B. Lankford (1984), *Thermal conductivity of aluminum, copper, iron, and tungsten for temperatures from 1 K to the melting point*, NBS IR 84-3007, DOI `10.6028/NBS.IR.84-3007`.

### Working correlation

目前工作式採後續低溫文獻中明確歸因於 Hust–Lankford 的 Cu correlation：

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
{1+P_1P_3T^{P_2+P_4}\exp\left[-\left(\frac{P_5}{T}\right)^{P_6}\right]},
$$

$$
W_{i0}=P_7\frac{W_iW_0}{W_i+W_0}.
$$

對 Cu：

$$
\beta=\frac{0.634}{\mathrm{RRR}},
$$

$$
\beta_r=\frac{\beta}{0.0003},
$$

$$
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

輸出單位：

$$
k:\ \mathrm{W/(m\,K)},\qquad T:\ \mathrm K.
$$

### ADR01 checkpoints

| $T$ (K) | $k$, RRR=50 (W/m K) | $k$, RRR=100 (W/m K) |
|---:|---:|---:|
| 1.0 | 78.8642 | 157.7281 |
| 1.5 | 118.2954 | 236.5885 |
| 2.0 | 157.7244 | 315.4396 |
| 2.5 | 197.1485 | 394.2702 |
| 3.0 | 236.5634 | 473.0632 |
| 3.5 | 275.9635 | 551.7943 |
| 4.0 | 315.3409 | 630.4312 |

### 4 K cross-check

NIST OFHC Copper online fit（只允許 4–300 K）在 4 K 約給出：

| RRR | Hust–Lankford working correlation | NIST 4–300 K online fit | difference |
|---:|---:|---:|---:|
| 50 | 315.34 | 320.38 | $-1.57\%$ |
| 100 | 630.43 | 642.30 | $-1.85\%$ |

因此工作式在 4 K endpoint 與 NIST 線上 fit 相容到數 % 內。

> **重要 provenance 註記**：上列係數已在多篇後續低溫導熱文獻中重現並歸因於 Hust–Lankford；本輪尚未從 NBS IR 84-3007 原始 PDF 的 Cu 章節逐字核對每一個係數。正式封存前應做一次 primary-source coefficient verification。

**ADR01 status：`WORKING_READY`**（RRR=100 baseline；RRR=50 sensitivity）。

---

## 1.3 Specific heat $c_p(T)$

### Source

G. K. White and S. J. Collocott (1984), *Heat Capacity of Reference Materials: Cu and W*, J. Phys. Chem. Ref. Data 13, 1251–1257, DOI `10.1063/1.555728`.

該 reference work 的 Cu table 直接覆蓋 1 K 起始溫區。對 1–25 K，可使用下列 copper reference equation：

$$
\boxed{
C_{p,m}(T)=
A_1T+A_3T^3+A_5T^5+A_7T^7+A_9T^9+A_{11}T^{11}
}
$$

其中 $C_{p,m}$ 為 molar heat capacity，單位 $\mathrm{J/(mol\,K)}$，$T$ 以 K 代入。

| coefficient | value |
|---|---:|
| $A_1$ | $6.9434\times10^{-4}$ |
| $A_3$ | $4.7548\times10^{-5}$ |
| $A_5$ | $1.6314\times10^{-9}$ |
| $A_7$ | $9.4786\times10^{-11}$ |
| $A_9$ | $-1.3639\times10^{-13}$ |
| $A_{11}$ | $5.3898\times10^{-17}$ |

使用 Cu molar mass

$$
M_{\mathrm{Cu}}=0.063546\ \mathrm{kg/mol},
$$

轉成 solver 所需的 mass-specific heat：

$$
\boxed{
c_p(T)=\frac{C_{p,m}(T)}{0.063546}
}
$$

單位 $\mathrm{J/(kg\,K)}$。

### Checkpoints

| $T$ (K) | $C_{p,m}$ (J/mol K) | $c_p$ (J/kg K) |
|---:|---:|---:|
| 1.0 | 0.00074189 | 0.0116749 |
| 1.5 | 0.00120202 | 0.0189153 |
| 2.0 | 0.00176913 | 0.0278401 |
| 2.5 | 0.00247902 | 0.0390111 |
| 3.0 | 0.00336742 | 0.0529918 |
| 3.5 | 0.00447015 | 0.0703468 |
| 4.0 | 0.00582362 | 0.0916442 |

White–Collocott 的 published table 在 1, 2, 3, 4 K 分別約為 0.000743, 0.00177, 0.00337, 0.00582 J/(mol K)，與上式相符。

> **provenance 註記**：本輪已用 published table 做數值一致性檢查；上述 polynomial coefficients 仍建議在正式封存前對 primary PDF 的低溫 reference-equation 區段再核一次版面／指數。

**ADR01 status：`WORKING_READY`**。

---

# 2. GGG — Gd$_3$Ga$_5$O$_{12}$

適用：`ggg`。

目前 baseline：

$$
H=0.
$$

需要：

$$
k(T,H=0),\qquad c_p(T,H=0),\qquad \rho.
$$

## 2.1 Density

可直接使用 source-backed scalar：

$$
\boxed{\rho_{\mathrm{GGG}}=7.10\ \mathrm{g/cm^3}=7100\ \mathrm{kg/m^3}}
$$

來源：T. Mashimo et al. (2006), *Transition to a Virtually Incompressible Oxide Phase at a Shock Pressure of 120 GPa: Gd$_3$Ga$_5$O$_{12}$*, Phys. Rev. Lett. 96, 105504, DOI `10.1103/PhysRevLett.96.105504`。

> 有其他文獻常見約 7.08 g/cm³；本工作表目前不取平均，先保留有直接明確來源的 7.10 g/cm³。

**ADR01 status：`READY`**。

---

## 2.2 Heat capacity $c_p(T,H=0)$

### Source locked

R. A. Fisher, G. E. Brodale, E. W. Hornung, W. F. Giauque (1973), *Magnetothermodynamics of gadolinium gallium garnet. I. Heat capacity, entropy, magnetic moment from 0.5 to 4.2 K, with fields to 90 kG along the [100] axis*, DOI `10.1063/1.1680677`.

該文摘要明確指出：

- heat capacity 範圍包含 0.5–4.2 K；
- series 中包含 **zero field**；
- smoothed correlated heat-capacity values 已表列。

### Numerical data

**TODO — primary table extraction pending.**

要求抽取：

$$
\boxed{c_p(T,H=0),\quad 1\le T\le4\ \mathrm K}
$$

不得混入有限磁場 series。

若原始資料是 molar heat capacity，需保留原單位後再轉成 J/(kg K)；轉換時應記錄 GGG molar mass 與 conversion metadata。

**ADR01 status：`PENDING_EXTRACTION`**。

---

## 2.3 Thermal conductivity $k(T,H=0)$

### Candidate source

B. Daudin, R. Lagnier, B. Salce (1982), *Thermodynamic properties of the gadolinium gallium garnet, Gd$_3$Ga$_5$O$_{12}$, between 0.05 and 25 K*, DOI `10.1016/0304-8853(82)90092-0`.

摘要確認其量測包含 thermal conductivity，但同時說明是在 **applied magnetic field** 條件下量測。

### Numerical data

**TODO — field condition unresolved / full-text extraction pending.**

在填任何 $k(T)$ 數值前，先確認：

- 哪條 conductivity series 對應 $H=0$ 或可合理作 baseline 的 field；
- data 是 table 還是 figure；
- 若只有 figure，需要保留 digitization method / figure number / uncertainty。

Slack & Oliver (1971), DOI `10.1103/PhysRevB.4.592`, 可作 2–4 K garnet conductivity cross-check，但本輪不把它直接替代成 GGG baseline curve。

**ADR01 status：`BLOCKED_PENDING_FIELD_VERIFICATION`**。

---

# 3. G-10 / FR-4 support

適用：`support_1`, `support_2`。

需要：

$$
k(T),\qquad c_p(T)\ \text{or}\ \rho c_p(T),\qquad \rho.
$$

## 3.1 Density

Runyan & Jones (2008) Table 1 給出其 G-10/FR-4 sample 的 room-temperature density：

$$
\boxed{\rho_{\mathrm{G10}}=1.91\ \mathrm{g/cm^3}=1910\ \mathrm{kg/m^3}}
$$

> 這是 room-temperature manufacturer property，不是 1–4 K cryogenic density measurement；ADR01 第一版把它當 constant density。

**ADR01 status：`READY_AS_BASELINE_CONSTANT`**。

---

## 3.2 Thermal conductivity $k(T)$

### Source

M. C. Runyan and W. C. Jones (2008), *Thermal conductivity of thermally-isolating polymeric and composite structural support materials between 0.3 and 4 K*, Cryogenics 48, 448–454, DOI `10.1016/j.cryogenics.2008.06.002`, arXiv `0806.1921`.

Fit：

$$
\boxed{
k(T)=\alpha T^{\beta+\gamma T^n}
}
$$

G-10/FR-4 coefficients：

| coefficient | source value | SI value used |
|---|---:|---:|
| $\alpha$ | $12.8\ \mathrm{mW/(m\,K)}$ | $0.0128\ \mathrm{W/(m\,K)}$ |
| $\beta$ | 2.41 | 2.41 |
| $\gamma$ | -0.921 | -0.921 |
| $n$ | 0.222 | 0.222 |

因此：

$$
\boxed{
k_{\mathrm{G10}}(T)
=0.0128\,T^{2.41-0.921T^{0.222}}
\ \mathrm{W/(m\,K)}
}
$$

valid approximately over 0.3–4.2 K。作者對 fit-generated conductivity 給約 10% uncertainty。

### ADR01 modeling qualifier

該 G-10/FR-4 measurement 是沿 woven glass fabric plane / fiber direction。

ADR01 Draft 0 暫時把它解讀為：

$$
\boxed{k_{\mathrm{support,axial}}(T)=k_{\mathrm{Runyan/Jones}}(T)}
$$

即 support 軸向的 effective scalar conductivity；**不可描述為 G-10 isotropic property**。

### Checkpoints

| $T$ (K) | $k(T)$ (W/m K) |
|---:|---:|
| 1.0 | 0.012800 |
| 1.5 | 0.022601 |
| 2.0 | 0.032309 |
| 2.5 | 0.041406 |
| 3.0 | 0.049690 |
| 3.5 | 0.057103 |
| 4.0 | 0.063658 |

**ADR01 status：`READY`**。

---

## 3.3 Volumetric heat capacity / specific heat

### Source

NIST Cryogenic Material Properties — Regenerator Materials 提供 G-10 volumetric heat capacity：

$$
C_V(T)=\rho c_p(T),
$$

原始單位：

$$
\mathrm{J/(cm^3\,K)}.
$$

資料從 1.00000 K 起，覆蓋 ADR01 溫區。

### Conversion

若 solver 需要 mass-specific $c_p$：

$$
\boxed{
c_p(T)=\frac{10^6\,C_V(T)}{1910}
}
$$

其中 $C_V$ 輸入單位為 J/(cm³ K)，結果為 J/(kg K)。

### 已抽取 checkpoints

| NIST $T$ (K) | $C_V=\rho c_p$ (J/cm³ K) | converted $c_p$ (J/kg K) |
|---:|---:|---:|
| 1.00000 | 0.00048 | 0.25131 |
| 2.00544 | 0.00096 | 0.50262 |
| 3.02386 | 0.00147 | 0.76963 |
| 3.97616 | 0.00316 | 1.65445 |

### Full table

**TODO — 將 NIST 1.00000–4.0 K 的完整 G-10 column 逐列轉錄成 solver-ready table。**

目前不要用上面四個 checkpoint 當作唯一 solver table；它們只是 extraction / unit-conversion sanity check。

可另以 Walker & Anderson (1981), DOI `10.1063/1.1136614`, 0.1–4 K G-10 / G-10CR specific-heat measurements 作 primary-literature cross-check。

**ADR01 status：`SOURCE_READY / FULL_TABLE_PENDING`**。

---

# 4. Heat switch

適用：`heat_switch`。

本區域不使用普通 bulk-material tuple：

$$
(k,c_p,\rho).
$$

post-demagnetization baseline 的目標是 OFF state：

$$
\boxed{
\dot Q=G_{\mathrm{off}}(T)\,\Delta T
}
$$

或更一般的 two-temperature conductance model。

## 4.1 ADR01 parameter

$$
\boxed{G_{\mathrm{off}}(T)=\text{TODO}}
$$

原因：實際 heat-switch hardware / principle 尚未確認（gas-gap / superconducting / mechanical / other）。

因此：

- 不指定假 $k(T)$；
- 不指定假 $c_p$；
- 不指定假 $\rho$；
- 不把 geometry 中的 switch volume 默認成 copper。

## 4.2 Literature scale example — NOT ADR01 parameter

Catarino & Paine (2011), $^3$He gas-gap heat switch, DOI `10.1016/j.cryogenics.2010.10.009`：在約 1.7 K 報告

$$
G_{\mathrm{off}}\approx60\ \mu\mathrm{W/K},
$$

$$
G_{\mathrm{on}}\approx100\ \mathrm{mW/K}.
$$

這只能作 magnitude example；除非確認 ADR01 hardware 足夠相同，**不得直接帶入**。

DiPirro & Shirron (2014), DOI `10.1016/j.cryogenics.2014.03.017`, 用於 heat-switch type / selection / ON-OFF physics 背景。

**ADR01 status：`SPECIAL_MODEL / UNRESOLVED`**。

---

# 5. Solver-facing coverage summary

| Material/model | $k(T)$ / $G(T)$ | $c_p(T)$ | $\rho$ | Current status |
|---|---|---|---|---|
| OFHC Cu RRR=100 | working analytical correlation | working analytical correlation | 8960 kg/m³ | **WORKING_READY** |
| OFHC Cu RRR=50 | working analytical correlation | same Cu $c_p(T)$ | 8960 kg/m³ | **WORKING_READY sensitivity** |
| GGG, $H=0$ | **TODO** | **TODO** | 7100 kg/m³ | **INCOMPLETE** |
| G-10/FR-4 | analytical fit ready | full NIST table **TODO**; conversion rule ready | 1910 kg/m³ | **PARTIAL_READY** |
| Heat switch OFF | $G_{\mathrm{off}}(T)$ **TODO** | N/A | N/A | **SPECIAL_MODEL** |

---

# 6. Remaining extraction work, in priority order

1. **GGG $c_p(T,H=0)$**：從 Fisher et al. 1973 的 zero-field table 抽 1–4 K 數值。
2. **GGG $k(T,H=0)$**：取得／閱讀 Daudin et al. 1982 full text，先釐清 magnetic-field condition，再決定是否可抽。
3. **G-10 full $\rho c_p(T)$ table**：把 NIST 1–4 K 完整 column 轉成 table/CSV，保留原始 volumetric data。
4. **Cu primary coefficient verification**：用 NBS IR 84-3007 原文核對 Hust–Lankford Cu correlation 係數；用 White–Collocott primary PDF 核對低溫 Cu reference equation 版面／指數。
5. **Heat switch hardware identity**：沒有硬體型式以前保持 blank，不製造 $G_{\mathrm{off}}$。

---

# 7. Source register

## Copper

- Hust, J. G.; Lankford, A. B. (1984). *Thermal conductivity of aluminum, copper, iron, and tungsten for temperatures from 1 K to the melting point*. NBS IR 84-3007. DOI: `10.6028/NBS.IR.84-3007`.
- White, G. K.; Collocott, S. J. (1984). *Heat Capacity of Reference Materials: Cu and W*. J. Phys. Chem. Ref. Data 13, 1251–1257. DOI: `10.1063/1.555728`.
- Simon, N. J.; Drexler, E. S.; Reed, R. P. (1992). *Properties of Copper and Copper Alloys at Cryogenic Temperatures*. NIST Monograph 177. DOI: `10.6028/NIST.MONO.177`.
- NIST Cryogenic Material Properties — OFHC Copper (4 K+ endpoint cross-check only).
- NIST PML — Composition of COPPER (density).

## GGG

- Fisher, R. A.; Brodale, G. E.; Hornung, E. W.; Giauque, W. F. (1973). *Magnetothermodynamics of gadolinium gallium garnet. I...* DOI: `10.1063/1.1680677`.
- Daudin, B.; Lagnier, R.; Salce, B. (1982). *Thermodynamic properties of the gadolinium gallium garnet...* DOI: `10.1016/0304-8853(82)90092-0`.
- Slack, G. A.; Oliver, D. W. (1971). *Thermal Conductivity of Garnets and Phonon Scattering by Rare-Earth Ions*. DOI: `10.1103/PhysRevB.4.592`.
- Mashimo, T. et al. (2006). *Transition to a Virtually Incompressible Oxide Phase... Gd3Ga5O12*. DOI: `10.1103/PhysRevLett.96.105504`.

## G-10

- Runyan, M. C.; Jones, W. C. (2008). *Thermal conductivity of thermally-isolating polymeric and composite structural support materials between 0.3 and 4 K*. DOI: `10.1016/j.cryogenics.2008.06.002`; arXiv:0806.1921.
- Walker, F. J.; Anderson, A. C. (1981). *Thermal conductivity and specific heat of a glass–epoxy composite at temperatures below 4 K*. DOI: `10.1063/1.1136614`.
- NIST Cryogenic Material Properties — Regenerator Materials (G-10 volumetric heat capacity).

## Heat switch

- DiPirro, M. J.; Shirron, P. J. (2014). *Heat switches for ADRs*. DOI: `10.1016/j.cryogenics.2014.03.017`.
- Catarino, I.; Paine, C. (2011). *$^3$He gas gap heat switch*. DOI: `10.1016/j.cryogenics.2010.10.009`.

---

# 8. Source URLs for local retrieval

- Hust–Lankford NBS IR 84-3007: https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nbsir84-3007.pdf
- White–Collocott: https://srd.nist.gov/jpcrdreprint/1.555728.pdf
- NIST Monograph 177: https://nvlpubs.nist.gov/nistpubs/Legacy/MONO/nistmonograph177.pdf
- Runyan–Jones arXiv: https://arxiv.org/pdf/0806.1921
- NIST G-10 volumetric heat capacity: https://trc.nist.gov/cryogenics/materials/RegeneratorMaterials/Regenerator%20Materials%20rev%2009-22-06.htm
- NIST OFHC Copper: https://trc.nist.gov/cryogenics/materials/OFHC%20Copper/OFHC_Copper_rev1.htm
- Fisher GGG DOI: https://doi.org/10.1063/1.1680677
- Daudin GGG DOI: https://doi.org/10.1016/0304-8853(82)90092-0
- Slack–Oliver DOI: https://doi.org/10.1103/PhysRevB.4.592
- Walker–Anderson DOI: https://doi.org/10.1063/1.1136614
- DiPirro–Shirron NASA record: https://ntrs.nasa.gov/citations/20150008253
- Catarino–Paine DOI: https://doi.org/10.1016/j.cryogenics.2010.10.009
- GGG density paper DOI: https://doi.org/10.1103/PhysRevLett.96.105504


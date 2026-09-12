# ADR01 低溫材料參數來源整理

> **用途**：供人類閱讀、審查與後續交給 Codex 做資料清洗。  
> **目標溫區**：$1\ \mathrm{K} \le T \le 4\ \mathrm{K}$  
> **目前模型階段**：退磁已完成後的暫態熱響應；尚未模擬磁化／退磁本身。  
> **原則**：只列出有明確來源的材料參數；沒有可靠來源或材料身分尚未確定者，明確保留為未決事項，不自行補值。

---

## 1. ADR01 區域與材料對應

目前若不把 `hot_plate` 當成 solved region，而只把它當作固定 $4\ \mathrm{K}$ 邊界條件，則有 9 個 solved regions：

| Region | 目前材料／模型 | 狀態 |
|---|---|---|
| `cylinder_1` | 未確認；OFHC Cu 為候選 | **材料未決** |
| `heat_switch` | Heat switch 等效熱導模型 | **特殊模型** |
| `cylinder_2` | 未確認；OFHC Cu 為候選 | **材料未決** |
| `ggg` | Gadolinium Gallium Garnet, Gd$_3$Ga$_5$O$_{12}$ | **已確認** |
| `cylinder_3` | OFHC Cu | **已確認／高度可信** |
| `cold_stage` | OFHC Cu | **已確認** |
| `sample` | Cu；第一版可用 OFHC Cu 候選 | **基本確定，RRR 未決** |
| `support_1` | G-10/FR-4、G-10CR 或 PEEK | **材料未決** |
| `support_2` | 同 `support_1` | **材料未決** |

因此，第一版真正需要建立的 **bulk material property families** 最少是：

1. OFHC Copper
2. GGG
3. G-10/FR-4 或 G-10CR  
4. PEEK（如果最後不用 G-10）

另外 `heat_switch` 應以 $G_{\mathrm{on}}(T)$ / $G_{\mathrm{off}}(T)$ 或等效熱阻處理，不宜硬塞成普通 bulk material。

---

# 2. OFHC Copper

適用區域：

- `cylinder_3`
- `cold_stage`
- `sample`
- `cylinder_1`、`cylinder_2` 若日後確認為 Cu
- `hot_plate` 若未來改成 solved body

需要參數：

$$
k(T,\mathrm{RRR}), \qquad c_p(T), \qquad \rho
$$

其中低溫 thermal conductivity 對 RRR 很敏感，所以 **RRR 必須保留為材料限定條件**。

---

## 2.1 Thermal conductivity $k(T,\mathrm{RRR})$

### 主要來源

**J. G. Hust and A. B. Lankford (1984)**  
**Thermal conductivity of aluminum, copper, iron, and tungsten for temperatures from 1 K to the melting point**  
NBS IR 84-3007.

- 溫區：**1 K 至熔點**
- 對 ADR01 的用途：主要的 Cu $k(T)$ 來源
- 特色：低溫模型考慮 residual resistivity，並可依 RRR 建立不同 conductivity curve
- DOI：`10.6028/NBS.IR.84-3007`

來源：

- NIST publication page  
  https://www.nist.gov/publications/thermal-conductivity-aluminum-copper-iron-and-tungsten-temperatures-1-k-melting-point
- NIST PDF  
  https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nbsir84-3007.pdf
- DOI  
  https://doi.org/10.6028/NBS.IR.84-3007

### 4 K 以上的交叉檢查來源

**NIST Cryogenic Material Properties — OFHC Copper (UNS C10100/C10200)**

此 NIST 線上頁面提供 RRR = 50, 100, 150, 300, 500 的 thermal-conductivity fits。

來源：

https://trc.nist.gov/cryogenics/materials/OFHC%20Copper/OFHC_Copper_rev1.htm

注意：

- NIST 線上 fit 的 lower range 是 **4 K**。
- 因此它適合拿來檢查 Hust–Lankford 模型在 $4\ \mathrm{K}$ 的接軌狀況。
- **不可把這組 4–300 K fit 向下外插到 1–3 K。**

### 補充 NIST reference

**N. J. Simon, E. S. Drexler, R. P. Reed (1992)**  
**Properties of Copper and Copper Alloys at Cryogenic Temperatures**  
NIST Monograph 177.

- 對 OFHC Cu 的 thermal conductivity、specific heat、thermal expansion、mechanical properties 做大規模整理。
- NIST 的 cryogenic materials reference list 將 OFHC copper conductivity 對應到此 monograph 的相關章節。

來源：

- NIST page  
  https://www.nist.gov/publications/properties-copper-and-copper-alloys-cryogenic-temperatures
- DOI  
  https://doi.org/10.6028/NIST.MONO.177
- NIST cryogenic reference list  
  https://www.nist.gov/mml/acmd/cryogenic-materials-properties-reference-list

### ADR01 建議

Cu 的 $k(T)$ 第一版應至少建立兩組 scenario：

$$
\mathrm{RRR}=50
$$

以及

$$
\mathrm{RRR}=100
$$

在取得實際硬體材料規格前，不要把其中任一組標成最終值。

---

## 2.2 Specific heat $c_p(T)$

### 主要來源

**G. K. White and S. J. Collocott (1984)**  
**Heat Capacity of Reference Materials: Cu and W**  
*Journal of Physical and Chemical Reference Data*, 13, 1251–1257.

- Cu 資料範圍：**1–1300 K**
- 對 ADR01 的用途：主要 Cu $c_p(T)$ 來源
- 論文提供 recommended values 與 interpolation functions
- DOI：`10.1063/1.555728`

來源：

- NIST reference database index  
  https://www.nist.gov/srd/nist-standard-reference-database-journal-physical-and-chemical-reference-data-reprints
- NIST-hosted PDF  
  https://srd.nist.gov/jpcrdreprint/1.555728.pdf
- DOI  
  https://doi.org/10.1063/1.555728

### 補充來源

**Simon, Drexler, Reed (1992), NIST Monograph 177**

NIST 的 cryogenic materials reference list 明確將 OFHC copper specific heat 對應至此 monograph。

來源：

https://www.nist.gov/mml/acmd/cryogenic-materials-properties-reference-list

### ADR01 建議

Cu 的 $c_p(T)$ 不需要和 thermal conductivity 一樣再依 RRR 拆成多組；第一版可直接採 White–Collocott reference curve，並保留原始 molar-specific data 與轉換成 J/(kg K) 的紀錄。

---

## 2.3 Density $\rho$

### 來源

**NIST Physical Measurement Laboratory — Composition of COPPER**

NIST 列出的 copper density：

$$
\rho = 8.960\ \mathrm{g/cm^3}
$$

即

$$
\rho = 8960\ \mathrm{kg/m^3}.
$$

來源：

https://physics.nist.gov/cgi-bin/Star/compos.pl?matno=029

### ADR01 建議

在 $1$–$4\ \mathrm{K}$ 的第一版 thermal FEM 中，可先把 Cu density 視為 constant：

$$
\rho_{\mathrm{Cu}} = 8960\ \mathrm{kg/m^3}.
$$

不要為了 schema 完整性自行捏造 $\rho(T)$。

---

# 3. GGG — Gd$_3$Ga$_5$O$_{12}$

適用區域：

- `ggg`

需要參數：

$$
k(T,H), \qquad c_p(T,H), \qquad \rho
$$

GGG 是 ADR01 中最需要保留物理條件的材料。尤其是 $c_p$ 與磁場有強烈關聯，所以資料必須保留 field condition。

目前 baseline 是：

- 先假設 ADR 已完成退磁；
- $t=0$ 時 GGG 初始溫度約 $1\ \mathrm{K}$；
- 接著只看熱傳；
- 因此目前優先需要：

$$
c_p(T,H=0)
$$

以及對應的 zero-field / baseline thermal conductivity。

---

## 3.1 Heat capacity $c_p(T,H)$

### 主要來源

**R. A. Fisher, G. E. Brodale, E. W. Hornung, W. F. Giauque (1973)**  
**Magnetothermodynamics of gadolinium gallium garnet. I. Heat capacity, entropy, magnetic moment from 0.5 to 4.2 K, with fields to 90 kG along the [100] axis**  
*The Journal of Chemical Physics*, 59, 4652–4663.

- heat-capacity 範圍：**0.5–4.2 K**
- 包含：**zero field**
- 亦包含多個外加磁場值
- 對 ADR01 的用途：目前 baseline 的 GGG $c_p(T,H=0)$ 主要來源
- DOI：`10.1063/1.1680677`

來源：

- DOI  
  https://doi.org/10.1063/1.1680677
- Bibliographic / abstract record  
  https://ouci.dntb.gov.ua/en/works/4MDmN8d7/

文獻摘要明確指出 heat capacity 在類似的 field / temperature ranges 中量測，且包含 zero-field series；作者並整理 smoothed correlated values。

### ADR01 使用規則

建立 dataset 時必須把 magnetic field 當作 source qualifier。

禁止：

- 把 $H=0$ 與有限 $H$ 的 heat capacity 點混在同一條 $c_p(T)$ curve；
- 為了填資料而把不同 crystallographic orientation 的資料混合；
- 把 magnetocaloric cycle 中的 field-dependent thermodynamics 簡化掉卻不留下註記。

第一版只抽：

$$
\boxed{c_p(T,H=0)}
$$

---

## 3.2 Thermal conductivity $k(T,H)$

### 第一優先來源

**B. Daudin, R. Lagnier, B. Salce (1982)**  
**Thermodynamic properties of the gadolinium gallium garnet, Gd$_3$Ga$_5$O$_{12}$, between 0.05 and 25 K**  
*Journal of Magnetism and Magnetic Materials*, 27, 315–322.

- 溫區：**0.05–25 K**
- 實驗量：specific heat、entropy、thermal conductivity、diffusivity
- 對 ADR01 的用途：GGG $k(T)$ 的主要候選來源
- DOI：`10.1016/0304-8853(82)90092-0`

來源：

- ScienceDirect  
  https://www.sciencedirect.com/science/article/pii/0304885382900920
- DOI  
  https://doi.org/10.1016/0304-8853(82)90092-0

### 重要限制

這篇論文摘要明確提到量測是在 **applied magnetic field** 的條件下進行。

因此目前不能只看到「0.05–25 K」就直接把整條 conductivity curve 當成 ADR01 的 $H=0$ 值。

在交給 Codex 前，仍需從全文確認：

1. 哪些 $k(T)$ curve 對應哪個 field；
2. 是否提供 $H=0$ 或近似 zero-field series；
3. 數據是 table 還是 figure；
4. 若只有 figure，digitization 必須記錄 figure number 與 digitization uncertainty。

### 2–4 K 的重要交叉檢查來源

**G. A. Slack and D. W. Oliver (1971)**  
**Thermal Conductivity of Garnets and Phonon Scattering by Rare-Earth Ions**  
*Physical Review B*, 4, 592–609.

- 溫區：**2–300 K**
- 研究 23 種 natural / synthetic garnet single crystals
- 用途：GGG / Gd-garnet 低溫 conductivity 的重要 cross-check 與物理背景
- DOI：`10.1103/PhysRevB.4.592`

來源：

- APS  
  https://journals.aps.org/prb/abstract/10.1103/PhysRevB.4.592
- DOI  
  https://doi.org/10.1103/PhysRevB.4.592

### ADR01 建議

GGG $k(T)$ 尚未到「數值已鎖定」階段。

目前狀態應寫成：

> **source locked, numerical extraction pending**

而不是先造一條方便的 interpolation curve。

---

## 3.3 Density $\rho$

### 主要可用來源

GGG 的文獻常見密度約為 $7.1\ \mathrm{g/cm^3}$。

例如：

**Transition to a virtually incompressible oxide phase at a shock pressure of 120 GPa: Gd$_3$Ga$_5$O$_{12}$**  
*Physical Review Letters* 96, 105504.

文獻摘要明確列出：

$$
\rho = 7.10\ \mathrm{g/cm^3}.
$$

來源：

- PubMed  
  https://pubmed.ncbi.nlm.nih.gov/16605758/
- DOI  
  https://doi.org/10.1103/PhysRevLett.96.105504

另外，近年的 magnetocaloric GGG work 亦常列約 $7.08\ \mathrm{g/cm^3}$。

### ADR01 建議

第一版可採 constant density：

$$
\rho_{\mathrm{GGG}} \approx 7.1\times10^3\ \mathrm{kg/m^3}
$$

但實際 material record 應保留採用的是哪一筆來源值，例如 7.10 或 7.08 g/cm$^3$，不要在資料清洗時混成一個沒有出處的平均值。

---

# 4. G-10 / FR-4 / G-10CR

適用區域：

- `support_1`
- `support_2`

需要參數：

$$
k(T), \qquad c_p(T) \text{ 或 } \rho c_p(T), \qquad \rho
$$

G-10 是 composite，方向性不可忽略。

---

## 4.1 Thermal conductivity $k(T)$

### 主要來源

**M. C. Runyan and W. C. Jones (2008)**  
**Thermal conductivity of thermally-isolating polymeric and composite structural support materials between 0.3 and 4 K**  
*Cryogenics*, 48, 448–454.

- 溫區：fit 約 **0.3–4.2 K**
- 材料包含：G-10/FR-4、PEEK、Vespel、其他 composite / polymer
- DOI：`10.1016/j.cryogenics.2008.06.002`

來源：

- ScienceDirect  
  https://www.sciencedirect.com/science/article/pii/S0011227508000933
- arXiv full text  
  https://arxiv.org/abs/0806.1921
- DOI  
  https://doi.org/10.1016/j.cryogenics.2008.06.002

該文使用：

$$
k(T)=\alpha T^{\beta+\gamma T^n}
$$

G-10/FR-4 fit coefficients：

| coefficient | value |
|---|---:|
| $\alpha$ | $12.8\ \mathrm{mW/(m\,K)}$ |
| $\beta$ | 2.41 |
| $\gamma$ | -0.921 |
| $n$ | 0.222 |

文中對此 fit 的範圍是 0.3–4.2 K，並對 fit 生成的 conductivity 給出約 10% uncertainty 的估計。

### 方向性

Runyan & Jones 明確說明：

- 樣品為 woven-glass / epoxy laminate；
- rods 沿一個 fiber axis 取樣；
- thermal conductivity **沿 woven glass fabric plane / fiber direction** 量測。

因此這組 $k(T)$ 不能在不知道支撐實際纖維方向的情況下自動宣稱為 isotropic G-10 property。

---

## 4.2 Specific heat / volumetric heat capacity

### 原始低溫論文

**F. J. Walker and A. C. Anderson (1981)**  
**Thermal conductivity and specific heat of a glass–epoxy composite at temperatures below 4 K**  
*Review of Scientific Instruments*, 52, 471–472.

- 量測材料：G-10 與 G-10CR
- 溫區：**0.1–4 K**
- 量測：thermal conductivity + specific heat
- DOI：`10.1063/1.1136614`

來源：

- DOI  
  https://doi.org/10.1063/1.1136614
- bibliographic record  
  https://iifiir.org/en/fridoc/thermal-conductivity-and-specific-heat-of-a-glass-epoxy-composite-at-70809

### NIST 可直接使用的表格

**NIST Cryogenic Material Properties — Regenerator Materials**

NIST 提供 G-10 的 **volumetric heat capacity**：

$$
\rho c_p
$$

單位：

$$
\mathrm{J/(cm^3\,K)}
$$

而且表格從：

$$
T=1.00000\ \mathrm{K}
$$

開始，正好覆蓋 ADR01 的 1–4 K。

來源：

https://trc.nist.gov/cryogenics/materials/RegeneratorMaterials/Regenerator%20Materials%20rev%2009-22-06.htm

例如 NIST 表中在 $1\ \mathrm{K}$：

$$
(\rho c_p)_{\mathrm{G10}}
=
0.00048\ \mathrm{J/(cm^3\,K)}.
$$

### ADR01 建議

若 framework 可以直接接受 volumetric heat capacity，則最好直接保留 NIST 原始量：

$$
\rho c_p(T)
$$

若 framework 一定要求 mass-specific $c_p(T)$，再用明確來源的 density 做 conversion，同時保留：

- 原始 volumetric table；
- density source；
- conversion formula；
- processed $c_p(T)$。

---

## 4.3 Density $\rho$

### 來源

Runyan & Jones 2008 的 Table 1 列出其 G-10/FR-4 sample 的 room-temperature density：

$$
\rho = 1.91\ \mathrm{g/cm^3}
$$

即

$$
\rho = 1910\ \mathrm{kg/m^3}.
$$

來源：

https://arxiv.org/abs/0806.1921

文中註明 Table 1 的 density 等 room-temperature properties 主要來自 manufacturer datasheets / websites。

### ADR01 建議

可暫時將：

$$
\rho_{\mathrm{G10}}=1910\ \mathrm{kg/m^3}
$$

視為 constant density baseline，但 provenance 必須寫清楚它是 room-temperature manufacturer property，而不是作者在 1–4 K 重新量測的 cryogenic density。

---

## 4.4 NIST G-10 CR database 的用途與限制

NIST 另有：

**Material Properties: G-10 CR (Fiberglass Epoxy)**

來源：

https://trc.nist.gov/cryogenics/materials/G-10%20CR%20Fiberglass%20Epoxy/G10CRFiberglassEpoxy_rev.htm

該頁提供：

- normal-direction thermal conductivity
- warp-direction thermal conductivity
- specific heat

但其資料範圍主要為 **4–300 K**：

- conductivity data：4–300 K
- conductivity equation range：normal 10–300 K、warp 12–300 K
- specific heat equation range：4–300 K

所以對目前 1–4 K ADR01：

- 可以拿來檢查 4 K endpoint；
- 不可把 conductivity fit 往下外插至 1–3 K。

---

# 5. PEEK

適用區域：

- `support_1`
- `support_2`

僅在最終 support 選擇 PEEK 時使用。

---

## 5.1 Thermal conductivity $k(T)$

### 主要來源

同樣採：

**Runyan & Jones (2008)**  
*Thermal conductivity of thermally-isolating polymeric and composite structural support materials between 0.3 and 4 K.*

來源：

- https://arxiv.org/abs/0806.1921
- https://doi.org/10.1016/j.cryogenics.2008.06.002

對 unfilled PEEK，fit：

$$
k(T)=\alpha T^{\beta+\gamma T^n}
$$

coefficients：

| coefficient | value |
|---|---:|
| $\alpha$ | $3.88\ \mathrm{mW/(m\,K)}$ |
| $\beta$ | 2.41 |
| $\gamma$ | -1.43 |
| $n$ | 0.0884 |

fit range 約 0.3–4.2 K。

文中同時指出不同 PEEK sample / vendor 之 conductivity 可能有顯著差異，並提到其 unfilled PEEK 與較早期文獻在 overlap region 有約 factor 2–3 的差異。因此使用 PEEK 時必須保留 grade / manufacturer / crystallinity 等 qualifiers。

---

## 5.2 Specific heat $c_p(T)$

### 目前狀態

目前尚未鎖定一個可信、直接覆蓋 **1–4 K** 的 PEEK heat-capacity primary source。

Runyan & Jones 2008：

- 提供 PEEK $k(T)$；
- **不提供 PEEK 的低溫 $c_p(T)$ curve**。

網路上容易找到的 PEEK specific-heat values 多半是在室溫或更高溫度，不能直接用於 1–4 K。

因此目前 ADR01 的 PEEK 狀態應明確標為：

> **$k(T)$ source available; $c_p(T)$ source unresolved**

而不是把室溫 specific heat 外插到 1 K。

---

## 5.3 Density $\rho$

### 來源

Runyan & Jones 2008 Table 1：

$$
\rho_{\mathrm{PEEK}}=1.31\ \mathrm{g/cm^3}
$$

即

$$
1310\ \mathrm{kg/m^3}.
$$

來源：

https://arxiv.org/abs/0806.1921

同樣要註明：

- 這是 room-temperature manufacturer property；
- 可作 baseline constant density；
- 不是 cryogenic density measurement。

---

# 6. Heat switch

適用區域：

- `heat_switch`

這個區域不宜當成一般 bulk material 來要求：

$$
k(T),\ c_p(T),\ \rho
$$

比較自然的模型是：

$$
\dot Q
=
G_{\mathrm{switch}}(T)\Delta T
$$

且：

$$
G_{\mathrm{switch}}
=
\begin{cases}
G_{\mathrm{on}}(T), & \text{ON} \\
G_{\mathrm{off}}(T), & \text{OFF}
\end{cases}
$$

---

## 6.1 Heat-switch 類型與 ADR review

### 主要 review

**M. J. DiPirro and P. J. Shirron (2014)**  
**Heat switches for ADRs**  
*Cryogenics*, 62, 172–176.

- 專門討論 ADR heat switches
- 包含：
  - gas-gap heat switches
  - superconducting heat switches
  - mechanical heat switches
- DOI：`10.1016/j.cryogenics.2014.03.017`

來源：

- NASA NTRS  
  https://ntrs.nasa.gov/citations/20150008253
- ScienceDirect  
  https://www.sciencedirect.com/science/article/abs/pii/S001122751400068X
- DOI  
  https://doi.org/10.1016/j.cryogenics.2014.03.017

### ADR01 結論

在不知道實際 heat switch hardware / principle 前：

- 不應指定任意 $G_{\mathrm{on}}$；
- 不應指定任意 $G_{\mathrm{off}}$；
- 不應把薄層幾何自動當成某種 bulk material。

---

## 6.2 具體低溫 gas-gap example

**I. Catarino and C. Paine (2011)**  
**$^3$He gas gap heat switch**  
*Cryogenics*, 51, 45–48.

- 約 $1.7\ \mathrm{K}$：
  - OFF-state conductance 約 $60\ \mu\mathrm{W/K}$
  - ON-state conductance 約 $100\ \mathrm{mW/K}$
- DOI：`10.1016/j.cryogenics.2010.10.009`

來源：

- ScienceDirect  
  https://www.sciencedirect.com/science/article/abs/pii/S0011227510002018
- Universidade NOVA record  
  https://novaresearch.unl.pt/en/publications/sup3suphe-gas-gap-heat-switch/
- DOI  
  https://doi.org/10.1016/j.cryogenics.2010.10.009

這組數字只能作為「實際 ADR heat switch conductance 的量級案例」。

**不能直接當成 ADR01 的 heat-switch parameter**，除非確認我們的 hardware 就是相同或足夠相近的 $^3$He gas-gap switch。

---

# 7. Source coverage summary

| Material / model | $k(T)$ / $G(T)$ | $c_p(T)$ / $\rho c_p(T)$ | $\rho$ | 目前狀態 |
|---|---|---|---|---|
| OFHC Cu | Hust & Lankford 1984；NIST 4 K+ cross-check | White & Collocott 1984 | NIST 8.960 g/cm$^3$ | **資料足夠；RRR 未決** |
| GGG | Daudin et al. 1982；Slack & Oliver 1971 cross-check | Fisher et al. 1973, $H=0$ 可抽 | 約 7.1 g/cm$^3$，peer-reviewed source | **來源已鎖定；仍需精確抽數值與 field condition** |
| G-10/FR-4 | Runyan & Jones 2008 | Walker & Anderson 1981；NIST volumetric table | Runyan & Jones: 1.91 g/cm$^3$ | **1–4 K coverage 很完整** |
| PEEK | Runyan & Jones 2008 | **尚缺可信 1–4 K source** | Runyan & Jones: 1.31 g/cm$^3$ | **transient material record 尚不完整** |
| Heat switch | $G_{\mathrm{on/off}}$，依 hardware | 不適用 | 不適用 | **hardware 未決，不可指定數值** |

---

# 8. 對 ADR01 第一版的材料建議

若只考慮「能否建立一個有資料根據的 post-demagnetization transient baseline」，目前最乾淨的組合是：

### Cu regions

使用：

- $k(T,\mathrm{RRR})$：Hust & Lankford 1984
- $c_p(T)$：White & Collocott 1984
- $\rho$：8960 kg/m$^3$
- RRR：先保留 50 / 100 scenarios

### GGG

使用：

- $c_p(T,H=0)$：Fisher et al. 1973
- $k(T)$：優先從 Daudin et al. 1982 精確抽取，並確認 field condition
- Slack & Oliver 1971 作 2–4 K cross-check
- $\rho$：約 $7.1\times10^3$ kg/m$^3$

### Supports

目前優先建議先採 **G-10 / FR-4** 作 baseline，因為：

- 1–4 K $k(T)$ 有直接 fit；
- 0.1–4 K specific-heat primary literature 存在；
- NIST 另有從 1 K 起的 volumetric heat-capacity table。

PEEK 可保留作第二 scenario，但在取得可信的 1–4 K $c_p(T)$ 前，不宜拿它做完整 transient baseline。

### Heat switch

第一版若只研究 post-demagnetization OFF-state response：

- 可先用 ideal-open / extremely-low-conductance simplification；
- 但必須標註這是模型假設；
- 真正的 $G_{\mathrm{off}}(T)$ 要等 heat-switch type / hardware 確認後才指定。

---

# 9. 尚未解決的材料問題

1. `cylinder_1` 的實際材料是什麼？
2. `cylinder_2` 的實際材料是什麼？
3. Cu hardware 的 RRR 是多少？
4. support 最終是 G-10、G-10CR 還是 PEEK？
5. 若用 G-10，實際 laminate / fiber orientation 為何？
6. GGG Daudin 1982 的 conductivity dataset 中，ADR01 應採哪一個 magnetic-field series？
7. heat switch 實際類型是 gas-gap、superconducting、mechanical，或其他？
8. 若最後選 PEEK，需要再找到可信的 1–4 K $c_p(T)$ primary source。

---

# 10. 後續給 Codex 的資料清洗原則

後續若將這份 source register 交給 Codex，建議要求：

- 原始 source 不覆寫；
- 每筆 data 都保留 DOI / URL；
- 保留 source temperature range；
- 保留 RRR、magnetic field、orientation、grade、manufacturer 等 qualifiers；
- table data 與 digitized figure data 必須區分；
- 若 digitize figure，要保留 figure number 與 digitization uncertainty；
- 單位轉換要保存 conversion metadata；
- 禁止 source range 之外的 silent extrapolation；
- unknown parameter 保持 unknown，不自行補值。

---

## 參考文獻清單

1. Hust, J. G.; Lankford, A. B. (1984). *Thermal conductivity of aluminum, copper, iron, and tungsten for temperatures from 1 K to the melting point*. NBS IR 84-3007. DOI: `10.6028/NBS.IR.84-3007`.

2. Simon, N. J.; Drexler, E. S.; Reed, R. P. (1992). *Properties of Copper and Copper Alloys at Cryogenic Temperatures*. NIST Monograph 177. DOI: `10.6028/NIST.MONO.177`.

3. White, G. K.; Collocott, S. J. (1984). *Heat Capacity of Reference Materials: Cu and W*. Journal of Physical and Chemical Reference Data 13, 1251–1257. DOI: `10.1063/1.555728`.

4. Fisher, R. A.; Brodale, G. E.; Hornung, E. W.; Giauque, W. F. (1973). *Magnetothermodynamics of gadolinium gallium garnet. I. Heat capacity, entropy, magnetic moment from 0.5 to 4.2 K, with fields to 90 kG along the [100] axis*. Journal of Chemical Physics 59, 4652–4663. DOI: `10.1063/1.1680677`.

5. Daudin, B.; Lagnier, R.; Salce, B. (1982). *Thermodynamic properties of the gadolinium gallium garnet, Gd3Ga5O12, between 0.05 and 25 K*. Journal of Magnetism and Magnetic Materials 27, 315–322. DOI: `10.1016/0304-8853(82)90092-0`.

6. Slack, G. A.; Oliver, D. W. (1971). *Thermal Conductivity of Garnets and Phonon Scattering by Rare-Earth Ions*. Physical Review B 4, 592–609. DOI: `10.1103/PhysRevB.4.592`.

7. Runyan, M. C.; Jones, W. C. (2008). *Thermal conductivity of thermally-isolating polymeric and composite structural support materials between 0.3 and 4 K*. Cryogenics 48, 448–454. DOI: `10.1016/j.cryogenics.2008.06.002`.

8. Walker, F. J.; Anderson, A. C. (1981). *Thermal conductivity and specific heat of a glass–epoxy composite at temperatures below 4 K*. Review of Scientific Instruments 52, 471–472. DOI: `10.1063/1.1136614`.

9. DiPirro, M. J.; Shirron, P. J. (2014). *Heat switches for ADRs*. Cryogenics 62, 172–176. DOI: `10.1016/j.cryogenics.2014.03.017`.

10. Catarino, I.; Paine, C. (2011). *3He gas gap heat switch*. Cryogenics 51, 45–48. DOI: `10.1016/j.cryogenics.2010.10.009`.

11. NIST Cryogenic Material Properties — OFHC Copper.  
    https://trc.nist.gov/cryogenics/materials/OFHC%20Copper/OFHC_Copper_rev1.htm

12. NIST Cryogenic Material Properties — G-10 CR Fiberglass Epoxy.  
    https://trc.nist.gov/cryogenics/materials/G-10%20CR%20Fiberglass%20Epoxy/G10CRFiberglassEpoxy_rev.htm

13. NIST Cryogenic Material Properties — Regenerator Materials volumetric heat capacities.  
    https://trc.nist.gov/cryogenics/materials/RegeneratorMaterials/Regenerator%20Materials%20rev%2009-22-06.htm

14. NIST Physical Measurement Laboratory — Composition of COPPER.  
    https://physics.nist.gov/cgi-bin/Star/compos.pl?matno=029

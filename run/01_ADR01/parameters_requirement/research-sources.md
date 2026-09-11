# ADR01 material research — first-pass source index

Target range: **1–4 K**.

This is a source map, not a production database. Codex should preserve provenance and never extrapolate silently.

## 1. OFHC copper

### Thermal conductivity, 1 K upward — primary source

J. G. Hust, A. B. Lankford (1984),  
*Thermal conductivity of aluminum, copper, iron, and tungsten for temperatures from 1 K to the melting point*,  
NBS IR 84-3007. DOI: `10.6028/NBS.IR.84-3007`

NIST:
https://www.nist.gov/publications/thermal-conductivity-aluminum-copper-iron-and-tungsten-temperatures-1-k-melting-point

Use this for `k(T, RRR)` over 1–4 K. Preserve RRR dependence. Prepare at least RRR=50 and RRR=100 candidate series; do not silently choose one.

### NIST online OFHC fit — 4 K cross-check only

https://trc.nist.gov/cryogenics/materials/OFHC%20Copper/OFHC_Copper_rev1.htm

Its listed lower validity limit is 4 K. Do not extrapolate it below 4 K.

### Copper heat capacity, 1 K upward — primary source

G. K. White, S. J. Collocott (1984),  
*Heat Capacity of Reference Materials: Cu and W*,  
Journal of Physical and Chemical Reference Data 13, 1251–1257. DOI: `10.1063/1.555728`

NIST-hosted PDF:
https://srd.nist.gov/jpcrdreprint/1.555728.pdf

The paper evaluates copper heat capacity from 1 K upward and provides recommended/tabulated values and interpolation functions.

### Independent sub-4 K conductivity check

K. Mittag (1973),  
*Kapitza conductance and thermal conductivity of copper, niobium and aluminium in the range from 1.3 to 2.1 K*,  
Cryogenics 13(2), 94–99. DOI: `10.1016/0011-2275(73)90132-X`

### Density

Use a constant density over 1–4 K unless a verified low-temperature density correlation is introduced.
A standard OFHC copper baseline is approximately `8960 kg/m^3`.
Do not fabricate rho(T).

---

## 2. GGG — Gd3Ga5O12

GGG heat capacity is strongly magnetic-field dependent.

### Heat capacity / entropy / magnetic moment, exact ADR range

R. A. Fisher, G. E. Brodale, E. W. Hornung, W. F. Giauque (1973),  
*Magnetothermodynamics of gadolinium gallium garnet. I. Heat capacity, entropy, magnetic moment from 0.5 to 4.2 K, with fields to 90 kG along the [100] axis*,  
Journal of Chemical Physics 59, 4652–4663. DOI: `10.1063/1.1680677`

E. W. Hornung, R. A. Fisher, G. E. Brodale, W. F. Giauque (1974),  
*Magnetothermodynamics of gadolinium gallium garnet. II. Heat capacity, entropy, magnetic moment from 0.5 to 4.2 K, with fields to 90 kG, along the [111] axis*,  
Journal of Chemical Physics 61, 282–291. DOI: `10.1063/1.1681634`

These include zero-field heat-capacity measurements over the target range. For the current post-demagnetization baseline, prioritize H=0 data. Do not mix fields.

### Thermal conductivity / heat capacity / diffusivity

B. Daudin, R. Lagnier, B. Salce (1982),  
*Thermodynamic properties of the gadolinium gallium garnet, Gd3Ga5O12, between 0.05 and 25 K*,  
Journal of Magnetism and Magnetic Materials 27, 315–322. DOI: `10.1016/0304-8853(82)90092-0`

https://www.sciencedirect.com/science/article/pii/0304885382900920

High-priority source for GGG `k(T)` in 1–4 K.

If values must be digitized from a figure, record:
- figure number;
- digitization method;
- estimated digitization uncertainty;
- original source range.

### Modern ADR context / density

M. Kleinhans et al. (2022),  
*Magnetocaloric properties of R3Ga5O12 (R = Tb, Gd, Nd, Dy)*, arXiv:2204.01752

https://arxiv.org/abs/2204.01752

This open paper lists GGG density `7.08 g/cm^3`. Baseline:
`rho = 7080 kg/m^3`.

---

## 3. Low-k support candidates

### 0.3–4.2 K thermal conductivity: PEEK and G-10/FR-4

M. C. Runyan, W. C. Jones (2008),  
*Thermal conductivity of thermally-isolating polymeric and composite structural support materials between 0.3 and 4 K*,  
Cryogenics 48, 448–454. DOI: `10.1016/j.cryogenics.2008.06.002`  
arXiv:0806.1921

Open full text:
https://arxiv.org/html/0806.1921

Fit:
`k(T) = alpha * T^(beta + gamma*T^n)`

Published coefficients:

| material | alpha [mW/(m K)] | beta | gamma [1/K^n] | n |
|---|---:|---:|---:|---:|
| PEEK | 3.88 | 2.41 | -1.43 | 0.0884 |
| G-10/FR-4 | 12.8 | 2.41 | -0.921 | 0.222 |

The authors state about 10% uncertainty for conductivity generated from these fits over 0.3–4 K.

Important:
- G-10/FR-4 was measured along the plane / glass-fiber direction;
- composite anisotropy must be preserved;
- room-temperature densities in the same paper:
  - PEEK: `1.31 g/cm^3`
  - G-10/FR-4: `1.91 g/cm^3`

### G-10 heat capacity down to 1 K

NIST Regenerator Materials:
https://trc.nist.gov/cryogenics/materials/RegeneratorMaterials/Regenerator%20Materials%20rev%2009-22-06.htm

Contains tabulated **volumetric heat capacity** for G-10 starting at 1 K in `J/(cm^3 K)`.

Prefer preserving the source quantity `rho*cp`. If converting to mass-specific `cp`, retain the original table and conversion metadata.

### NIST G-10CR page — 4 K comparison only

https://trc.nist.gov/cryogenics/materials/G-10%20CR%20Fiberglass%20Epoxy/G10CRFiberglassEpoxy_rev.htm

Do not extrapolate its conductivity fits below their stated equation ranges.

### PEEK heat-capacity gap

Runyan/Jones provides good `k(T)` but not `cp(T)`.
Do not invent PEEK cp by analogy with another polymer.

Until a credible 1–4 K PEEK heat-capacity source is found, PEEK remains an incomplete transient-material candidate.

For a first fully source-backed transient support model, G-10 currently has better coverage.

---

## 4. Heat switch

Do not research generic bulk `k, cp, rho` solely because the geometry has a thin switch region.

Intended abstraction:
- `G_on(T)`
- `G_off(T)`

or equivalent thermal resistance.

The actual switch technology is still unspecified, so numerical values remain TBD.

---

## 5. Coverage matrix

| property family | k, 1–4 K | cp, 1–4 K | rho | unresolved qualifier |
|---|---|---|---|---|
| OFHC Cu | YES: Hust & Lankford | YES: White & Collocott | constant available | actual RRR |
| GGG, H=0 | likely YES: Daudin et al. | YES: Fisher/Hornung/Giauque | 7.08 g/cc | exact extraction / field bookkeeping |
| G-10 support | YES: Runyan & Jones | YES: NIST volumetric table | 1.91 g/cc candidate | grade / orientation |
| PEEK support | YES: Runyan & Jones | GAP | 1.31 g/cc candidate | cp source |
| heat switch | special model | special model | n/a | switch technology |

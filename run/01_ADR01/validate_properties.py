"""Validate ADR01 Baseline v1 solver-facing material properties."""

from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lib.case import load_case

import properties


case = load_case(Path(__file__).with_name("case.yaml"))
props = case["_region_properties"]


def check(actual, expected, tolerance, label):
    error = np.max(np.abs(np.asarray(actual) - np.asarray(expected)))
    if error > tolerance:
        raise AssertionError(f"{label}: error {error} > {tolerance}")
    print(f"{label}: max_abs_error={error:.6g} PASS")


temperatures = np.array([1.0, 2.0, 3.0, 4.0])
check(properties.copper_k_rrr100(temperatures), [156.15, 312.29, 468.33, 624.13], 0.01, "Cu RRR100 k")
check(properties.copper_cp(temperatures), [0.011675, 0.027840, 0.052992, 0.091644], 1e-6, "Cu cp")
check(properties.copper_k_rrr50(temperatures), [77.29, 154.57, 231.83, 309.04], 0.01, "Cu RRR50 k")
check(properties.g10_k(temperatures), [0.012800, 0.032309, 0.049690, 0.063658], 1e-6, "G10 k")

for region, names in (("ggg", ("k", "cp")), ("support_1", ("cp",))):
    for name in names:
        prop = props[region][name]
        endpoints = prop.evaluate(np.array([1.0, 4.0]))
        if not np.all(endpoints > 0):
            raise AssertionError(f"{region}.{name} is not positive")
        for outside in (0.999, 4.001):
            try:
                prop.evaluate(outside)
            except ValueError:
                pass
            else:
                raise AssertionError(f"{region}.{name} silently extrapolated")
        print(f"{region}.{name}: endpoints={endpoints.tolist()} domain/positivity PASS")

ggg_k = props["ggg"]["k"]
check(ggg_k.evaluate(np.array([1.0, 2.0, 3.0, 4.0])), [4.6, 37.3, 91.4, 146.5], 0, "GGG k table points")
check(ggg_k.evaluate(2.25), 49.55, 1e-12, "GGG k interpolation")
ggg_cp = props["ggg"]["cp"]
check(ggg_cp.evaluate(np.array([1.0, 2.0, 3.0, 4.0])), [19.982, 9.571, 5.190, 3.220], 0, "GGG cp table points")

g10_cp = props["support_1"]["cp"]
check(g10_cp.evaluate(1.0), 0.00048e6 / 1910.0, 1e-14, "G10 cp volumetric conversion")
check(1910.0 * g10_cp.evaluate(1.0), 480.0, 1e-10, "G10 volumetric reconstruction")

length = 5.0e-4
area = 1.9634954084936207e-5
k = props["heat_switch"]["k"].evaluate()
conductance = k * area / length
check(conductance, 6.0e-5, 1e-15, "heat-switch G")
print(f"heat-switch R={1/conductance:.9g} K/W, Q(1K)={conductance*1e6:.9g} uW, Q(3K)={3*conductance*1e6:.9g} uW")
switch_volume = area * length
switch_capacity = switch_volume
cu_cp_4 = properties.copper_cp(4.0)
adjacent_capacities = [
    8960.0 * cu_cp_4 * np.pi * (0.006 / 2) ** 2 * height
    for height in (0.0315, 0.010)
]
capacity_ratio = switch_capacity / min(adjacent_capacities)
if capacity_ratio >= 1e-3:
    raise AssertionError(f"heat-switch thermal-capacitance ratio={capacity_ratio}")
print(f"heat-switch C={switch_capacity:.9g} J/K, ratio_to_min_adjacent_Cu={capacity_ratio:.9g} PASS")

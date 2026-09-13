"""Baseline v1 analytical thermal properties (valid from 1 K through 4 K)."""

import numpy as np
import ufl


def _numeric(T):
    return isinstance(T, (int, float, np.number, np.ndarray))


def _checked(T):
    if _numeric(T):
        values = np.asarray(T, dtype=float)
        if not np.isfinite(values).all() or (values < 1.0).any() or (values > 4.0).any():
            raise ValueError("ADR01 property temperature is outside [1, 4] K")
    return T


def copper_k(T, RRR=100):
    T = _checked(T)
    log = np.log if _numeric(T) else ufl.ln
    exp = np.exp if _numeric(T) else ufl.exp
    beta = 0.634 / (RRR - 1)
    w0 = beta / T
    wc = (
        -0.00012 * log(T / 420) * exp(-(log(T / 470) / 0.7) ** 2)
        -0.00016 * log(T / 73) * exp(-(log(T / 87) / 0.45) ** 2)
        -0.00002 * log(T / 18) * exp(-(log(T / 21) / 0.5) ** 2)
    )
    wi = 1.754e-8 * T**2.763 / (
        1 + 1.754e-8 * 1102 * T ** (2.763 - 0.165)
        * exp(-(70 / T) ** 1.756)
    ) + wc
    p7 = 0.838 / (beta / 0.0003) ** 0.1661
    return 1 / (w0 + wi + p7 * wi * w0 / (wi + w0))


def copper_k_rrr100(T):
    return copper_k(T, 100)


def copper_k_rrr50(T):
    return copper_k(T, 50)


def copper_cp(T):
    T = _checked(T)
    molar = (
        6.9434e-4 * T + 4.7548e-5 * T**3 + 1.6314e-9 * T**5
        + 9.4786e-11 * T**7 - 1.3639e-13 * T**9 + 5.3898e-17 * T**11
    )
    return molar / 0.063546


def g10_k(T):
    T = _checked(T)
    return 0.0128 * T ** (2.41 - 0.921 * T**0.222)

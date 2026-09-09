"""Minimal 1D P1 solver for a zero-thickness thermal contact."""

import numpy as np


def solve_steady_rod(x_left, x_right, conductivity, contact_h, hot_T, cold_T):
    """Solve two P1 rods coupled by q=h(T_left-T_right), per unit area."""
    x_left, x_right = np.asarray(x_left), np.asarray(x_right)
    x = np.concatenate((x_left, x_right))
    elements = [
        (i, i + 1) for i in range(len(x_left) - 1)
    ] + [
        (len(x_left) + i, len(x_left) + i + 1)
        for i in range(len(x_right) - 1)
    ]
    left_interface = len(x_left) - 1
    right_interface = len(x_left)
    temperature = np.interp(x, (x.min(), x.max()), (hot_T, cold_T))
    temperature[right_interface:] -= 0.5
    temperature[:left_interface + 1] += 0.5
    gauss = (-1 / np.sqrt(3), 1 / np.sqrt(3))

    def residual(values):
        result = np.zeros_like(values)
        for a, b in elements:
            length = x[b] - x[a]
            gradient = (values[b] - values[a]) / length
            mean_k = sum(
                conductivity(
                    0.5 * ((1 - point) * values[a] + (1 + point) * values[b])
                ) for point in gauss
            ) / 2
            result[a] -= mean_k * gradient
            result[b] += mean_k * gradient
        jump_flux = contact_h * (
            values[left_interface] - values[right_interface]
        )
        result[left_interface] += jump_flux
        result[right_interface] -= jump_flux
        result[0] = values[0] - hot_T
        result[-1] = values[-1] - cold_T
        return result

    for iteration in range(20):
        r = residual(temperature)
        if np.linalg.norm(r, np.inf) < 1.0e-10:
            break
        step = 1.0e-7
        jacobian = np.column_stack([
            (residual(temperature + step * np.eye(1, len(x), j)[0]) - r) / step
            for j in range(len(x))
        ])
        temperature += np.linalg.solve(jacobian, -r)
    else:
        raise RuntimeError("Nonlinear contact solve did not converge")

    cell_T = np.array([(temperature[a] + temperature[b]) / 2 for a, b in elements])
    cell_x = np.array([(x[a] + x[b]) / 2 for a, b in elements])
    cell_q = np.array([
        -conductivity((temperature[a] + temperature[b]) / 2)
        * (temperature[b] - temperature[a]) / (x[b] - x[a])
        for a, b in elements
    ])
    conservative_q = []
    for a, b in elements:
        mean_k = sum(
            conductivity(
                0.5 * ((1 - point) * temperature[a] + (1 + point) * temperature[b])
            ) for point in gauss
        ) / 2
        conservative_q.append(
            -mean_k * (temperature[b] - temperature[a]) / (x[b] - x[a])
        )
    return {
        "x": x, "temperature": temperature, "elements": elements,
        "cell_x": cell_x, "cell_T": cell_T, "cell_q": cell_q,
        "conservative_q": np.asarray(conservative_q),
        "T_left": temperature[left_interface],
        "T_right": temperature[right_interface],
        "iterations": iteration,
    }


def advance_transient_rod(
    x_left, x_right, previous, conductivity, contact_h, rho_cp, dt, hot_T, cold_T
):
    """Advance the same disconnected P1 rod by one implicit-Euler step."""
    x_left, x_right = np.asarray(x_left), np.asarray(x_right)
    x = np.concatenate((x_left, x_right))
    previous = np.asarray(previous)
    elements = [
        (i, i + 1) for i in range(len(x_left) - 1)
    ] + [
        (len(x_left) + i, len(x_left) + i + 1)
        for i in range(len(x_right) - 1)
    ]
    left_interface, right_interface = len(x_left) - 1, len(x_left)
    gauss = (-1 / np.sqrt(3), 1 / np.sqrt(3))

    def residual(values):
        result = np.zeros_like(values)
        for a, b in elements:
            length = x[b] - x[a]
            delta = values[[a, b]] - previous[[a, b]]
            result[[a, b]] += rho_cp * length / (6 * dt) * np.array(
                [2 * delta[0] + delta[1], delta[0] + 2 * delta[1]]
            )
            gradient = (values[b] - values[a]) / length
            mean_k = sum(
                conductivity(0.5 * ((1 - p) * values[a] + (1 + p) * values[b]))
                for p in gauss
            ) / 2
            result[a] -= mean_k * gradient
            result[b] += mean_k * gradient
        contact_q = contact_h * (values[left_interface] - values[right_interface])
        result[left_interface] += contact_q
        result[right_interface] -= contact_q
        result[0] = values[0] - hot_T
        result[-1] = values[-1] - cold_T
        return result

    temperature = previous.copy()
    temperature[0], temperature[-1] = hot_T, cold_T
    for iteration in range(12):
        r = residual(temperature)
        if np.linalg.norm(r, np.inf) < 1.0e-9:
            break
        step = 1.0e-7
        jacobian = np.column_stack([
            (residual(temperature + step * np.eye(1, len(x), j)[0]) - r) / step
            for j in range(len(x))
        ])
        temperature += np.linalg.solve(jacobian, -r)
    else:
        raise RuntimeError("Transient nonlinear contact solve did not converge")
    return temperature

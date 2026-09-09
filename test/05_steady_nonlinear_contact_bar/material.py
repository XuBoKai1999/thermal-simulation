"""Temperature-dependent conductivity for Test 05."""


def k(temperature):
    return 10.0 * (1.0 + 3.0 / 13.0 * (temperature - 2.5) ** 2)


def phi(temperature):
    theta = temperature - 2.5
    return 10.0 * (theta + theta**3 / 13.0)

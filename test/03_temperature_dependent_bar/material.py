"""Case-local material law; functions receive a UFL temperature expression."""


K0 = 10.0
BETA = 0.1


def k(T):
    return K0 * (1.0 + BETA * T)

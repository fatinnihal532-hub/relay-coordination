"""IEC 60255-151 inverse-time overcurrent characteristics.

    t = TMS * k / ((I / Is) ** alpha - 1)
"""
import numpy as np

CURVES = {
    "SI": (0.14, 0.02),    # standard inverse
    "VI": (13.5, 1.0),     # very inverse
    "EI": (80.0, 2.0),     # extremely inverse
    "LTI": (120.0, 1.0),   # long-time inverse
}


def trip_time(I, pickup, tms, curve="SI", inst=None):
    """Operating time in seconds. Returns inf below pickup; `inst` is an optional
    instantaneous (50) setting in primary amps with a 0.05 s operating time."""
    k, a = CURVES[curve]
    I = np.asarray(I, dtype=float)
    m = I / pickup
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(m > 1.0, tms * k / (m ** a - 1.0), np.inf)
    if inst is not None:
        t = np.where(I >= inst, np.minimum(t, 0.05), t)
    return t

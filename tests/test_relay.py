import numpy as np
import pytest
from relay import default_feeder, grade, grade_lp, check_margins, trip_time
from relay.coordination import pickup_setting, sensitivity


@pytest.mark.parametrize("curve,ref", [("SI", 2.9706), ("VI", 1.5), ("EI", 0.8081), ("LTI", 13.3333)])
def test_iec_curves_at_10x(curve, ref):
    assert abs(float(trip_time(1000, 100, 1.0, curve)) - ref) < 1e-3


def test_no_trip_below_pickup():
    assert np.isinf(trip_time(99, 100, 0.1, "SI"))


def test_instantaneous_element():
    assert float(trip_time(5000, 100, 1.0, "SI", inst=4000)) == pytest.approx(0.05)


def test_pickup_steps():
    ct, ps = pickup_setting(394, 1.5)
    assert ct == 400 and ps == 600 and ps >= 1.5 * 394


def test_fault_levels_fall_along_feeder():
    f = default_feeder()
    I = [f.fault_3ph(i) for i in range(len(f.buses))]
    assert all(a > b for a, b in zip(I, I[1:]))
    assert all(f.fault_2ph_min(i) < f.fault_3ph(i) for i in range(len(f.buses)))


@pytest.mark.parametrize("curve", ["SI", "VI", "EI"])
def test_coordinated_for_every_curve(curve):
    f = default_feeder()
    S = grade(f, curve=curve)
    assert min(check_margins(f, S)) >= 0.3 - 1e-9


def test_lp_matches_sequential():
    f = default_feeder()
    S = grade(f, tms_step=1e-9)
    assert np.allclose(grade_lp(f, S), [s.tms for s in S], atol=1e-6)


def test_sensitivity():
    f = default_feeder()
    assert min(r for _, r in sensitivity(f, grade(f))) >= 1.5


def test_bad_grading_is_detected():
    f = default_feeder()
    S = grade(f)
    S[1].tms = 0.05            # feeder breaker graded too fast: it no longer clears recloser A by 0.3 s
    assert min(check_margins(f, S)) < 0.3

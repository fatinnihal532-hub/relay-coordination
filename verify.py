"""Checks behind every number quoted in the README.   Run:  python verify.py"""
import numpy as np
from relay import default_feeder, grade, grade_lp, check_margins, trip_time
from relay.coordination import sensitivity

checks = []


def check(name, ok, detail=""):
    checks.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}")


# 1. The curves reproduce the IEC 60255 textbook values at 10x pickup, TMS 1
for curve, ref in [("SI", 2.971), ("VI", 1.500), ("EI", 0.808)]:
    t = float(trip_time(1000, 100, 1.0, curve))
    check(f"IEC {curve} curve at 10x pickup = {ref} s", abs(t - ref) < 1e-3, f"({t:.4f} s)")

f = default_feeder()

# 2. Fault levels: hand calculation of the substation bus fault
zs = 11**2 / 500
zt = 0.10 * 11**2 / 20
z = complex(zs / np.sqrt(101), zs * 10 / np.sqrt(101)) + complex(zt / np.sqrt(226), zt * 15 / np.sqrt(226))
hand = 1.1 * 11e3 / np.sqrt(3) / abs(z)
check("11 kV bus fault matches hand calculation", abs(f.fault_3ph(0) - hand) < 1e-6,
      f"({f.fault_3ph(0)/1e3:.2f} kA)")

S = grade(f)

# 3. Every pair keeps at least 0.3 s over every fault current both relays can see
m = check_margins(f, S)
check("CTI >= 0.3 s for every pair, over the full fault range", min(m) >= 0.3 - 1e-9,
      "(" + ", ".join(f"{x:.3f}" for x in m) + " s)")

# 4. Linear programming reaches the same TMS as sequential grading (no rounding)
S_exact = grade(f, tms_step=1e-9)
lp = grade_lp(f, S_exact)
diff = max(abs(a - s.tms) for a, s in zip(lp, S_exact))
check("LP optimum equals sequential grading", diff < 1e-6, f"(max difference {diff:.1e})")

# 5. Rounded settings are never below the exact optimum
check("Rounded TMS >= exact TMS", all(s.tms >= e.tms - 1e-12 for s, e in zip(S, S_exact)))

# 6. Every pickup rides through load; every relay sees the smallest fault in its zone
check("Pickup >= 1.05 x load everywhere", all(s.pickup >= 1.05 * s.load_a for s in S))
sens = [r for _, r in sensitivity(f, S)]
check("Minimum fault / pickup >= 1.5 in every zone", min(sens) >= 1.5,
      "(" + ", ".join(f"{x:.2f}" for x in sens) + ")")

# 7. Instantaneous elements do not reach past the next breaker
for k, s in enumerate(S[:-1]):
    if s.inst is not None:
        nxt = S[k + 1].bus if S[k + 1].bus > s.bus else None
        if nxt is not None:
            check(f"{s.name} 50 element stays short of {f.buses[nxt]}",
                  s.inst > f.fault_3ph(nxt, "max"))

# 8. Close-in fault clearing times quoted in the README
t_cb = float(trip_time(f.fault_3ph(0), S[1].pickup, S[1].tms, S[1].curve, S[1].inst))
t_inc = float(trip_time(f.fault_3ph(0), S[0].pickup, S[0].tms, S[0].curve, S[0].inst))
check("Close-in feeder fault: breaker 0.05 s, incomer backup 0.41 s",
      abs(t_cb - 0.05) < 1e-9 and abs(t_inc - 0.413) < 5e-3, f"({t_cb:.2f} s / {t_inc:.3f} s)")

print(f"\n{sum(checks)}/{len(checks)} checks passed")
raise SystemExit(0 if all(checks) else 1)

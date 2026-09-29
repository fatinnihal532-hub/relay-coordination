"""Regenerate docs/*.svg and results/*.csv."""
import os
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from relay import default_feeder, grade, trip_time, check_margins
from relay.coordination import constraints, sensitivity

plt.rcParams.update({"svg.fonttype": "none", "svg.hashsalt": "fixed", "font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
NAVY, GOLD, RED, TEAL, GREY = "#1F3864", "#C9971C", "#B3261E", "#2E7D6B", "#777777"
COLORS = [GREY, NAVY, TEAL, GOLD]


def compact_svg(path):
    """Shrink a matplotlib SVG: round coordinates to 0.1 pt and drop metadata."""
    s = open(path).read()
    s = re.sub(r"<metadata>.*?</metadata>\s*", "", s, flags=re.S)
    s = re.sub(r"-?\d+\.\d{2,}", lambda m: f"{float(m.group()):.1f}".rstrip("0").rstrip("."), s)
    s = re.sub(r"\n\s+", "\n", s)
    open(path, "w").write(s)


os.makedirs("docs", exist_ok=True)
os.makedirs("results", exist_ok=True)

f = default_feeder()
S = grade(f)

# 1. time-current characteristic
fig, ax = plt.subplots(figsize=(7.2, 5.0))
I = np.geomspace(100, 12000, 240)
for s, c in zip(S, COLORS):
    t = trip_time(I, s.pickup, s.tms, s.curve, s.inst)
    lbl = f"{s.name}: Is {s.pickup:.0f} A, TMS {s.tms:.2f}" + (f", 50 at {s.inst/1e3:.2f} kA" if s.inst else "")
    ax.loglog(I, t, color=c, lw=2, label=lbl)
for i, b in enumerate(f.buses):
    Imax = f.fault_3ph(i)
    ax.axvline(Imax, color=GREY, ls=":", lw=1)
    ax.text(Imax * 1.03, 12 if i % 2 == 0 else 5, f"{b}\n{Imax/1e3:.2f} kA", fontsize=7.5, color=GREY, va="top")
for k in range(len(S) - 1):
    Ig, td = max(constraints(f, S[k], S[k + 1]), key=lambda p: p[1])
    tu = float(trip_time(Ig, S[k].pickup, S[k].tms, S[k].curve, S[k].inst))
    ax.annotate("", xy=(Ig, tu), xytext=(Ig, td), arrowprops=dict(arrowstyle="<->", color=RED, lw=1.2))
    ax.text(Ig * 0.95, np.sqrt(tu * td), f"{tu - td:.2f} s", color=RED, fontsize=8, ha="right", va="center",
            bbox=dict(facecolor="white", edgecolor="none", pad=1))
ax.set_xlim(100, 12000)
ax.set_ylim(0.02, 20)
ax.set_xlabel("Fault current at 11 kV (A)")
ax.set_ylabel("Operating time (s)")
ax.set_title("Time-current coordination, IEC standard inverse", loc="left", fontweight="bold")
ax.grid(True, which="both", alpha=0.2)
ax.legend(frameon=False, fontsize=8, loc="lower left")
fig.tight_layout()
fig.savefig("docs/tcc.svg")
compact_svg("docs/tcc.svg")
plt.close(fig)

# 2. single-line diagram
fig, ax = plt.subplots(figsize=(8.4, 2.4))
ax.axis("off")
ax.set_xlim(0, 10.2)
ax.set_ylim(0, 2.4)
y = 1.3
ax.text(0.3, y + 0.55, "33 kV grid\n500 MVA", ha="center", fontsize=8)
ax.plot([0.3, 0.3], [y + 0.25, y], color="k")
for dx in (0.95, 1.2):
    ax.add_patch(plt.Circle((dx, y), 0.17, fill=False, lw=1.5))
ax.text(1.07, y - 0.55, "20 MVA\n33/11 kV\n10%", ha="center", fontsize=7.5)
ax.plot([0.3, 0.78], [y, y], color="k")
ax.plot([1.37, 2.0], [y, y], color="k")
xs = [2.2, 4.8, 7.1, 9.6]
for i, (x, b) in enumerate(zip(xs, f.buses)):
    ax.plot([x, x], [y - 0.45, y + 0.45], color=NAVY, lw=4)
    ax.text(x, y + 0.6, b, ha="center", fontsize=8, fontweight="bold", color=NAVY)
    ax.text(x, y - 0.75, f"{f.fault_3ph(i)/1e3:.2f} kA max\n{f.fault_2ph_min(i)/1e3:.2f} kA min",
            ha="center", fontsize=7, color=GREY)
    if f.loads_mva[i]:
        ax.annotate("", xy=(x + 0.35, y - 0.35), xytext=(x, y - 0.2), arrowprops=dict(arrowstyle="->", color="k"))
        ax.text(x + 0.42, y - 0.38, f"{f.loads_mva[i]:.1f} MVA", fontsize=7)
ax.plot([2.0, 2.2], [y, y], color="k")
brk = [(2.02, 0), (2.45, 1), (5.05, 2), (7.35, 3)]
for (bx, k), c in zip(brk, COLORS):
    ax.add_patch(plt.Rectangle((bx - 0.09, y - 0.09), 0.18, 0.18, color=c))
    ax.text(bx, y + 0.18 if k else y - 0.3, f"R{k+1}", ha="center", fontsize=7.5, color=c, fontweight="bold")
for (a, b), (L, *_) in zip([(2.2, 4.8), (4.8, 7.1), (7.1, 9.6)], f.sections):
    ax.plot([a, b], [y, y], color="k")
    ax.text((a + b) / 2 + 0.15, y + 0.12, f"{L:.0f} km", fontsize=7.5, ha="center")
fig.tight_layout()
fig.savefig("docs/single_line.svg")
compact_svg("docs/single_line.svg")
plt.close(fig)

# tables
with open("results/settings.csv", "w") as fh:
    fh.write("relay,ct_primary_a,load_a,pickup_a,plug_setting,curve,tms,inst_a\n")
    for s in S:
        fh.write(f"{s.name},{s.ct},{s.load_a:.0f},{s.pickup:.1f},{s.pickup/s.ct:.2f},{s.curve},{s.tms:.2f},"
                 f"{'' if s.inst is None else f'{s.inst:.0f}'}\n")
with open("results/margins.csv", "w") as fh:
    fh.write("upstream,downstream,min_cti_s\n")
    for k, m in enumerate(check_margins(f, S)):
        fh.write(f"{S[k].name},{S[k+1].name},{m:.3f}\n")
with open("results/sensitivity.csv", "w") as fh:
    fh.write("relay,zone_end,min_fault_over_pickup\n")
    for s, (b, r) in zip(S, sensitivity(f, S)):
        fh.write(f"{s.name},{b},{r:.2f}\n")
print("figures in docs/, tables in results/")

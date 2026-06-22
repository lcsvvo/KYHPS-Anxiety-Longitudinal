"""
figure3_final.py
================================================================================
Figure 3 (FINAL) — styled to match Figure 1 & Figure 2.

Design rules (mirror Fig 1/2):
  - English only; neutral descriptive panel titles "A.  <variable>".
  - Axis titles in English with unit/range in brackets.
  - Group colours: Stable green / Onset orange / Recovery blue / Persistent red.
  - Plain coloured lines + markers, uniform weight (no group emphasis).
  - One shared, frameless legend.
  - NO in-figure annotation boxes, tags, arrows, or insight text.
    (All interpretation lives in the figure caption only.)

Data: same pipeline as depression_panel_v2.py (validated; GAD-7 W5 means match
      the published trajectory table 2.06 / 6.53 / 2.74 / 6.55).

Output: Figure3_FINAL.png (300 dpi) + Figure3_FINAL.pdf
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- typography to match Fig 1/2 (default DejaVu Sans, English) -------------
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.unicode_minus": False,
    "font.size": 10.5,
    "axes.titlesize": 11.5,
    "axes.labelsize": 10.5,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "legend.fontsize": 10,
})

w = pd.read_csv("data/processed/merged/KYHPS_STU_5y_wide_final.csv")


def num(c):
    return pd.to_numeric(w[c], errors="coerce")


def col(key, k):
    cs = [c for c in w.columns if key in c and c.endswith(f"_w{k}")]
    return cs[0] if cs else None


# ---- variable construction (identical to validated pipeline) ----------------
GAD = {}
for k in (3, 4, 5):
    items = sorted([c for c in w.columns if "GAD-7" in c and c.endswith(f"_w{k}")])
    GAD[k] = w[items].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=7) - 7

FUT = {k: 5 - num(col("스트레스 경험(미래)", k)) for k in (3, 4, 5)}       # reverse-coded
FAM = {k: 5 - num(col("스트레스 경험(가족관계)", k)) for k in (3, 4, 5)}    # reverse-coded
SLP = {k: num(col("수면시간(주중)", k)) for k in (3, 4, 5)}

DEP = {k: np.where(num(col("우울감 경험", k)).notna(),
                   (num(col("우울감 경험", k)) == 2).astype(float), np.nan) for k in (1, 5)}
d1 = pd.Series(DEP[1], index=w.index)
d5 = pd.Series(DEP[5], index=w.index)
grp = pd.Series(np.where(d1.isna() | d5.isna(), "Missing",
                np.where((d1 == 0) & (d5 == 0), "Stable",
                np.where((d1 == 0) & (d5 == 1), "Onset",
                np.where((d1 == 1) & (d5 == 0), "Recovery", "Persistent")))),
                index=w.index)

VARS = {"GAD7": GAD, "FutureStress": FUT, "FamilyStress": FAM, "Sleep": SLP}
GROUPS = ["Stable", "Onset", "Recovery", "Persistent"]
WAVES = (3, 4, 5)
means = {v: {g: [pd.Series(VARS[v][k], index=w.index)[grp == g].mean() for k in WAVES]
             for g in GROUPS} for v in VARS}

# ---- style maps (match Fig 2 group colours) ---------------------------------
COLORS = {"Stable": "#2ca02c", "Onset": "#ff7f0e",
          "Recovery": "#1f77b4", "Persistent": "#d62728"}
x = np.array([3, 4, 5])

PANELS = [
    ("GAD7",         "A", "GAD-7 anxiety",          "GAD-7 score [0-21]"),
    ("FutureStress", "B", "Future stress",          "Future stress [1-4]"),
    ("FamilyStress", "C", "Family stress",          "Family stress [1-4]"),
    ("Sleep",        "D", "Weekday sleep duration", "Sleep duration [code 1-8]"),
]

fig, axes = plt.subplots(2, 2, figsize=(10.0, 7.6))
axes = axes.ravel()

for ax, (v, letter, title, ylab) in zip(axes, PANELS):
    for g in GROUPS:
        ax.plot(x, means[v][g], color=COLORS[g], lw=2.2,
                marker="o", ms=6, mfc=COLORS[g], mec=COLORS[g], label=g)
    ax.set_title(f"{letter}.  {title}", fontweight="bold", loc="left")
    ax.set_xlabel("Survey wave")
    ax.set_ylabel(ylab)
    ax.set_xticks(x)
    ax.set_xticklabels(["W3", "W4", "W5"])
    ax.margins(x=0.10)
    ax.grid(axis="y", ls=":", alpha=0.45)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)

# one shared, frameless legend (top, single row)
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False,
           bbox_to_anchor=(0.5, 0.965), handlelength=2.0, columnspacing=2.2)

fig.suptitle("Figure 3.  Within-trajectory change in anxiety, stress, and sleep across W3–W5",
             fontweight="bold", fontsize=13.5, y=0.995)

fig.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig("Figure3_FINAL.png", dpi=300, bbox_inches="tight")
fig.savefig("Figure3_FINAL.pdf", bbox_inches="tight")
print("[saved] Figure3_FINAL.png / Figure3_FINAL.pdf")
for v in VARS:
    print(v, {g: [round(m, 2) for m in means[v][g]] for g in GROUPS})

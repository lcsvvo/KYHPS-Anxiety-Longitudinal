"""
figure3_change_coupling.py
================================================================================
Figure 3 — 우울 궤적 집단별 W3~W5 변화 궤적 (불안-스트레스의 동행, change coupling)

[목적]
  이미 수행한 W3~W5 변화 분석을 시각화한다(새 분석 아님). 4개 우울 궤적
  집단(Stable/Onset/Recovery/Persistent)에서 GAD-7 불안, 미래·가족 스트레스,
  주중 수면시간의 차수별(W3/W4/W5) 평균 궤적을 한 화면에 제시한다.

[입력]  data/processed/merged/KYHPS_STU_5y_wide_final.csv
[출력]  Figure3_change_coupling.png  (300 dpi)
        Figure3_change_coupling.pdf  (벡터, 제출용)
        outputs/tables/figure3_change_means.csv  (재현용 48셀 평균표)

[변수 정의 — depression_panel_v2.py와 동일]
  - GAD-7(0~21)  = 7문항(1~4코딩) 합 - 7
  - 스트레스      = 5 - 원점수 (역코딩, ↑=스트레스 많음)
  - 수면(주중)    = 원점수(1~8 코드, ↑=수면 많음)
  - 궤적 집단     = W1·W5 우울감 경험(==2) 조합
                    Stable(0,0) / Onset(0,1) / Recovery(1,0) / Persistent(1,1)
[주의] 평균은 관측 동시측정 값이며 인과로 해석하지 않는다.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ------------------------------------------------------------------ 한글 폰트
for _fp in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if os.path.exists(_fp):
        fm.fontManager.addfont(_fp)
plt.rcParams["font.family"] = "Noto Sans CJK JP"   # CJK KR 글리프 포함
plt.rcParams["axes.unicode_minus"] = False

WIDE = "data/processed/merged/KYHPS_STU_5y_wide_final.csv"
w = pd.read_csv(WIDE)


def num(c):
    return pd.to_numeric(w[c], errors="coerce")


def col(key, k):
    cs = [c for c in w.columns if key in c and c.endswith(f"_w{k}")]
    return cs[0] if cs else None


# ------------------------------------------------------------------ 변수 구축
GAD = {}
for k in (3, 4, 5):
    items = sorted([c for c in w.columns if "GAD-7" in c and c.endswith(f"_w{k}")])
    GAD[k] = w[items].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=7) - 7

FUT = {k: 5 - num(col("스트레스 경험(미래)", k)) for k in (3, 4, 5)}      # 역코딩
FAM = {k: 5 - num(col("스트레스 경험(가족관계)", k)) for k in (3, 4, 5)}   # 역코딩
SLP = {k: num(col("수면시간(주중)", k)) for k in (3, 4, 5)}

# 궤적 집단(W1·W5 우울감 경험)
DEP = {k: np.where(num(col("우울감 경험", k)).notna(),
                   (num(col("우울감 경험", k)) == 2).astype(float), np.nan) for k in (1, 5)}
d1 = pd.Series(DEP[1], index=w.index)
d5 = pd.Series(DEP[5], index=w.index)
grp = pd.Series(np.where(d1.isna() | d5.isna(), "Missing",
                np.where((d1 == 0) & (d5 == 0), "Stable",
                np.where((d1 == 0) & (d5 == 1), "Onset",
                np.where((d1 == 1) & (d5 == 0), "Recovery", "Persistent")))),
                index=w.index)

# ------------------------------------------------------------------ 셀 평균/표준오차
VARS = {"GAD7": GAD, "FutureStress": FUT, "FamilyStress": FAM, "Sleep": SLP}
GROUPS = ["Stable", "Onset", "Recovery", "Persistent"]
WAVES = (3, 4, 5)

stat = {}   # stat[var][group] = (means[3], se[3], n)
records = []
for vname, vd in VARS.items():
    stat[vname] = {}
    for g in GROUPS:
        mask = (grp == g)
        means, ses, ns = [], [], []
        for k in WAVES:
            v = pd.Series(vd[k], index=w.index)[mask].dropna()
            means.append(v.mean())
            ses.append(v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else np.nan)
            ns.append(len(v))
            records.append({"variable": vname, "group": g, "wave": f"W{k}",
                            "mean": round(float(v.mean()), 4),
                            "se": round(float(ses[-1]), 4), "n": int(ns[-1])})
        stat[vname][g] = (np.array(means), np.array(ses), ns)

os.makedirs("outputs/tables", exist_ok=True)
pd.DataFrame(records).to_csv("outputs/tables/figure3_change_means.csv",
                             index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 시각화 설정
COLORS = {"Stable": "#2ca02c", "Onset": "#ff7f0e",
          "Recovery": "#1f77b4", "Persistent": "#d62728"}
LABEL = {"Stable": "Stable (유지·비우울)", "Onset": "Onset (발생)",
         "Recovery": "Recovery (회복)", "Persistent": "Persistent (지속)"}
EMPH = {"Onset", "Recovery"}        # 변화 주인공 → 굵게
MARKER = {"Stable": "s", "Onset": "o", "Recovery": "o", "Persistent": "^"}
x = np.array([3, 4, 5])

PANELS = [
    ("GAD7",         "A", "GAD-7 불안 (0~21)",        "GAD-7 점수",
     "Onset ↑  /  Recovery ↓"),
    ("FutureStress", "B", "미래 스트레스 (역코딩 ↑=스트레스 큼)", "스트레스 점수",
     "Onset ↑  /  Recovery ≈ 유지"),
    ("FamilyStress", "C", "가족 스트레스 (역코딩 ↑=스트레스 큼)", "스트레스 점수",
     "Onset ↑  /  Recovery ↓"),
    ("Sleep",        "D", "주중 수면시간 (1~8 코드, ↑=수면 많음)", "수면시간 코드",
     "전 집단 공통 ↓"),
]

fig, axes = plt.subplots(2, 2, figsize=(11.0, 8.4))
axes = axes.ravel()

for ax, (vname, letter, title, ylab, tag) in zip(axes, PANELS):
    for g in GROUPS:
        means, ses, ns = stat[vname][g]
        emph = g in EMPH
        ax.errorbar(x, means, yerr=1.96 * ses,
                    color=COLORS[g], lw=2.7 if emph else 1.7,
                    alpha=1.0 if emph else 0.72,
                    marker=MARKER[g], ms=7 if emph else 5,
                    mfc=COLORS[g] if emph else "white",
                    mec=COLORS[g], mew=1.6,
                    capsize=2.5, elinewidth=0.9, zorder=5 if emph else 3,
                    label=LABEL[g])
    ax.set_title(f"({letter}) {title}", fontsize=12, fontweight="bold", loc="left")
    ax.set_xlabel("조사 차수")
    ax.set_ylabel(ylab)
    ax.set_xticks(x)
    ax.set_xticklabels(["W3", "W4", "W5"])
    ax.margins(x=0.10)
    ax.grid(axis="y", ls=":", alpha=0.45)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    # 방향 태그(코너 주석) — 데이터가 지지하는 방향만 표기
    box_fc = "#fff3e0" if vname != "Sleep" else "#eef2f7"
    ax.text(0.97, 0.06, tag, transform=ax.transAxes, ha="right", va="bottom",
            fontsize=10.5, fontweight="bold", color="#333333",
            bbox=dict(boxstyle="round,pad=0.35", fc=box_fc, ec="#cccccc", lw=0.8))

# 상단 공통 범례
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False,
           bbox_to_anchor=(0.5, 1.005), fontsize=11, handlelength=2.2,
           columnspacing=1.8)

fig.suptitle("그림 3.  우울 궤적 집단별 W3~W5 변화 궤적: 불안–스트레스의 동행(change coupling)",
             fontsize=13.5, fontweight="bold", y=1.065)

fig.text(0.5, -0.012,
         "값은 차수별 관측 평균(오차막대 = 95% CI). 굵은 선(Onset·Recovery)은 변화가 큰 집단. "
         "스트레스는 역코딩(↑=스트레스 큼). 동시측정 평균이므로 인과 해석 불가.",
         ha="center", fontsize=9.0, color="#555555")

fig.tight_layout(rect=[0, 0.01, 1, 0.99])
for ext, dpi in [("png", 300), ("pdf", 300)]:
    fig.savefig(f"Figure3_change_coupling.{ext}", dpi=dpi, bbox_inches="tight")
print("[저장] Figure3_change_coupling.png / .pdf")
print("[저장] outputs/tables/figure3_change_means.csv")

# 콘솔 검증 출력
print("\n=== W3 / W4 / W5 means ===")
for vname in VARS:
    print(f"\n## {vname}")
    for g in GROUPS:
        m, s, n = stat[vname][g]
        print(f"  {g:11s} " + "  ".join(f"W{k}={mm:.3f}" for k, mm in zip(WAVES, m))
              + f"   ΔW3→W5={m[2]-m[0]:+.3f}  (n={n[0]})")

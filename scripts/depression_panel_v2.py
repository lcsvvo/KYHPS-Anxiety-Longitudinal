"""
depression_panel_v2.py
================================================================================
청소년 우울/불안 — 패널 격상판(v2).

[목적]
  완성 논문(v1)의 횡단 '4군 기저 비교'를, 같은 개인을 추적하는 within-person
  패널 분석으로 격상한다. 핵심 기여는 두 가지다.
    (1) GAD-7(연속, 표준 0-21로 교정)을 주 결과로 사용.
    (2) '스마트폰 해리(dissociation)' — 스마트폰은 within-person 동인이 아니라
        between-person 특성 — 를 불안(GAD-7)·우울(단일문항) 두 결과에서 일관 검증.
  + 표본외(train/test, seed=20260619) 검증으로 Alcohol 프로젝트와 동일 기준 부여.

[입력] data/processed/merged/KYHPS_STU_5y_wide_final.csv  (GAD-7 + 예측변수 W3-5)
       data/processed/cleaned/KYHPS_STU_analysis_long.csv (5파 조화 우울 패널)
[출력] outputs/tables/dep_v2_*.xlsx + 콘솔
[주의] GAD-7 표준 = 7문항합(1-4코딩, 7-28) - 7 = 0-21.
"""
import os
import math
import numpy as np
import pandas as pd

RNG = 20260619
TEST_FRAC = 0.30
OUTDIR = "outputs/tables"
os.makedirs(OUTDIR, exist_ok=True)
w = pd.read_csv("data/processed/merged/KYHPS_STU_5y_wide_final.csv")
L5 = pd.read_csv("data/processed/cleaned/KYHPS_STU_analysis_long.csv")


# ------------------------------------------------------------------ 유틸
def num(c):
    return pd.to_numeric(w[c], errors="coerce")


def col(key, k):
    cs = [c for c in w.columns if key in c and c.endswith(f"_w{k}")]
    return cs[0] if cs else None


def ncdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def pz(z):
    return 2 * (1 - ncdf(abs(z)))


def stars(p):
    return "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "n.s."


def auc(score, y):
    score, y = np.asarray(score, float), np.asarray(y, int)
    pos, neg = score[y == 1], score[y == 0]
    if not len(pos) or not len(neg):
        return np.nan
    r = pd.Series(np.concatenate([pos, neg])).rank().values
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def ols(y, Xcols):
    X = np.column_stack([np.ones(len(y))] + Xcols)
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ beta
    r2 = 1 - np.sum((y - yhat) ** 2) / np.sum((y - y.mean()) ** 2)
    return beta, r2


def mundlak(df, ycol, preds, pid="pid"):
    """LPM Mundlak: y ~ within(편차) + between(개인평균), pid 군집강건 SE."""
    d = df.dropna(subset=[ycol] + preds).copy()
    for p in preds:
        m = d.groupby(pid)[p].transform("mean")
        d[p + "_w"] = d[p] - m
        d[p + "_b"] = m
    cols = [p + "_w" for p in preds] + [p + "_b" for p in preds]
    X = np.column_stack([np.ones(len(d))] + [d[c].values for c in cols])
    y = d[ycol].values
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    u = y - X @ beta
    bread = np.linalg.inv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for _, idx in d.groupby(pid).indices.items():
        s = X[idx].T @ u[idx]
        meat += np.outer(s, s)
    se = np.sqrt(np.diag(bread @ meat @ bread))
    names = ["const"] + cols
    out = []
    for p in preds:
        iw, ib = names.index(p + "_w"), names.index(p + "_b")
        out.append({"변수": p,
                    "within_β": round(beta[iw], 4), "within_p": round(pz(beta[iw] / se[iw]), 4),
                    "within_sig": stars(pz(beta[iw] / se[iw])),
                    "between_β": round(beta[ib], 4), "between_sig": stars(pz(beta[ib] / se[ib]))})
    return pd.DataFrame(out), len(d), d[pid].nunique()


def save(df, name):
    p = os.path.join(OUTDIR, name)
    try:
        df.to_excel(p, index=False)
    except Exception:
        p = p.replace(".xlsx", ".csv")
        df.to_csv(p, index=False)
    print(f"  [저장] {p}")


# ------------------------------------------------------------------ 변수 구축
GAD = {}
for k in (3, 4, 5):
    items = sorted([c for c in w.columns if "GAD-7" in c and c.endswith(f"_w{k}")])
    GAD[k] = w[items].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=7) - 7
DEP = {k: np.where(num(col("우울감 경험", k)).notna(),
                   (num(col("우울감 경험", k)) == 2).astype(float), np.nan) for k in (1, 2, 3, 4, 5)}
KEYS = {"smartphone": "스마트폰 이용시간(주중)", "sleep": "수면시간(주중)",
        "stress_acad": "스트레스 경험(학업)", "stress_future": "스트레스 경험(미래)",
        "stress_friend": "스트레스 경험(친구관계)", "stress_appear": "스트레스 경험(외모)",
        "stress_family": "스트레스 경험(가족관계)"}
STRESS = {k for k in KEYS if k.startswith("stress")}
P = {}
for nm, key in KEYS.items():
    s = {k: num(col(key, k)) for k in (3, 4, 5)}
    if nm in STRESS:
        s = {k: 5 - s[k] for k in (3, 4, 5)}   # 역코딩 ↑=스트레스 많음
    P[nm] = s
PREDS = list(P.keys())


def long_from_wide(outcome):
    rows = []
    for k in (3, 4, 5):
        dd = pd.DataFrame({"pid": w.index, "y": outcome[k]})
        for nm in PREDS:
            dd[nm] = P[nm][k]
        rows.append(dd)
    return pd.concat(rows)


# ================================================================ 1. 핵심: 스마트폰 해리
print("========== [1] within/between 분해 — 스마트폰 해리 ==========")
mg, ng, pg = mundlak(long_from_wide(GAD), "y", PREDS)
print(f"[A] 결과=GAD-7(불안, W3-5)  person-waves={ng}, N={pg}")
print(mg.to_string(index=False))
save(mg, "dep_v2_mundlak_gad7.xlsx")

md, nd, pd_ = mundlak(long_from_wide({k: pd.Series(DEP[k]) for k in (3, 4, 5)}), "y", PREDS)
print(f"\n[B] 결과=우울 단일문항(W3-5, 동일창)  person-waves={nd}, N={pd_}")
print(md.to_string(index=False))
save(md, "dep_v2_mundlak_dep_w35.xlsx")

# [C] 5파 우울(조화 long) within/between — 더 긴 창 robustness
L5b = L5.rename(columns={"depression": "y"})
preds5 = ["smartphone", "sleep", "stress_academic", "physical_activity", "fastfood"]
mc, nc, pc = mundlak(L5b, "y", preds5)
print(f"\n[C] 결과=우울 단일문항(5파 W1-5, 조화)  person-waves={nc}, N={pc}")
print(mc.to_string(index=False))
save(mc, "dep_v2_mundlak_dep_5wave.xlsx")

# 해리 요약
diss = pd.DataFrame([
    {"결과/창": "GAD-7 불안 (W3-5)",
     "smartphone within": f"{mg.loc[mg.변수=='smartphone','within_β'].iloc[0]:+.4f} {mg.loc[mg.변수=='smartphone','within_sig'].iloc[0]}",
     "smartphone between": f"{mg.loc[mg.변수=='smartphone','between_β'].iloc[0]:+.4f} {mg.loc[mg.변수=='smartphone','between_sig'].iloc[0]}"},
    {"결과/창": "우울 단일문항 (W3-5)",
     "smartphone within": f"{md.loc[md.변수=='smartphone','within_β'].iloc[0]:+.4f} {md.loc[md.변수=='smartphone','within_sig'].iloc[0]}",
     "smartphone between": f"{md.loc[md.변수=='smartphone','between_β'].iloc[0]:+.4f} {md.loc[md.변수=='smartphone','between_sig'].iloc[0]}"},
    {"결과/창": "우울 단일문항 (5파 W1-5)",
     "smartphone within": f"{mc.loc[mc.변수=='smartphone','within_β'].iloc[0]:+.4f} {mc.loc[mc.변수=='smartphone','within_sig'].iloc[0]}",
     "smartphone between": f"{mc.loc[mc.변수=='smartphone','between_β'].iloc[0]:+.4f} {mc.loc[mc.변수=='smartphone','between_sig'].iloc[0]}"},
])
print("\n[해리 요약]")
print(diss.to_string(index=False))
save(diss, "dep_v2_smartphone_dissociation.xlsx")


# ================================================================ 2. 표본외 검증
print("\n========== [2] 표본외(train/test, seed=20260619) ==========")
rng = np.random.RandomState(RNG)
# (2a) GAD-7: within Δ공변량이 W5 불안을 표본외 예측하는가 (개인단위)
base = pd.concat([GAD[3], GAD[5]] + [P[p][3] for p in PREDS] + [P[p][5] for p in PREDS], axis=1).dropna()
base.columns = ["g3", "g5"] + [f"{p}_3" for p in PREDS] + [f"{p}_5" for p in PREDS]
for p in PREDS:
    base[f"d_{p}"] = base[f"{p}_5"] - base[f"{p}_3"]
te = rng.rand(len(base)) < TEST_FRAC
dc = [f"d_{p}" for p in PREDS]
bA, _ = ols(base.loc[~te, "g5"].values, [base.loc[~te, "g3"].values])
predA = np.column_stack([np.ones(te.sum()), base.loc[te, "g3"].values]) @ bA
bB, _ = ols(base.loc[~te, "g5"].values, [base.loc[~te, "g3"].values] + [base.loc[~te, c].values for c in dc])
predB = np.column_stack([np.ones(te.sum()), base.loc[te, "g3"].values] +
                        [base.loc[te, c].values for c in dc]) @ bB
def r2_oos(yt, pr): return 1 - np.sum((yt - pr) ** 2) / np.sum((yt - yt.mean()) ** 2)
yt = base.loc[te, "g5"].values
oos = pd.DataFrame([
    {"표본외 과제": "W5 불안 ~ baseline(gad3)만", "지표": "test R²", "값": round(r2_oos(yt, predA), 3)},
    {"표본외 과제": "W5 불안 ~ +within Δ공변량", "지표": "test R²", "값": round(r2_oos(yt, predB), 3)},
])
print(oos.to_string(index=False))
save(oos, "dep_v2_oos.xlsx")


# ================================================================ 3. 4군 기저(교정 GAD) 서술
print("\n========== [3] 4군 궤적 × GAD-7(교정) 서술 ==========")
d1 = pd.Series(DEP[1]); d5 = pd.Series(DEP[5])
grp = pd.Series(np.where(d1.isna() | d5.isna(), "Missing",
                np.where((d1 == 0) & (d5 == 0), "Stable",
                np.where((d1 == 0) & (d5 == 1), "Onset",
                np.where((d1 == 1) & (d5 == 0), "Recovery", "Persistent")))), index=w.index)
g5 = GAD[5]
rows = []
groups_for_kw = []
for gname in ["Stable", "Onset", "Recovery", "Persistent"]:
    v = g5[grp == gname].dropna()
    groups_for_kw.append(v.values)
    rows.append({"군": gname, "N": len(v), "GAD7_W5_평균(0-21)": round(v.mean(), 2),
                 "%≥10(중등도)": round(100 * (v >= 10).mean(), 1)})
# Kruskal-Wallis H
allv = np.concatenate(groups_for_kw)
ranks = pd.Series(allv).rank().values
n = len(allv)
H = 0
idx = 0
for g in groups_for_kw:
    r = ranks[idx:idx + len(g)]
    idx += len(g)
    H += len(g) * (r.mean() - (n + 1) / 2) ** 2
H = 12 / (n * (n + 1)) * H
traj = pd.DataFrame(rows)
print(traj.to_string(index=False))
print(f"  Kruskal-Wallis H(df=3)={H:.1f}  (>16.27 → p<.001)  [교정척도: 중등도는 소수만]")
save(traj, "dep_v2_trajectory_gad.xlsx")

print("\n완료. outputs/tables/dep_v2_*.xlsx 저장.")

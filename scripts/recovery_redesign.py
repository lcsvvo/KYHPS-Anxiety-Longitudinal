"""
recovery_redesign.py
================================================================================
청소년 우울/불안 '회복(Recovery)' 재설계 분석 — GAD-7 기반 within-person 접근.

[목적]
  적대적 감사에서 드러난 원형 Recovery(단일문항 우울 W1→W5 이분)의 치명적 약점
  ─ 평균회귀(RTM), 분류잡음, 단발 끝점 ─ 을 교정하고, 회복을 '집단'이 아니라
  '과정'으로 재정의하여 RTM 너머 실제 신호가 남는지 표본외로 검증한다.

[재설계 4원칙]
  1) 결과변수 = GAD-7 연속(표준 0-21). 단일문항 우울은 보조/강건성으로만.
  2) within-person 분해(Mundlak): "누가 불안한가"가 아니라
     "같은 사람이 좋아지는 해에 무엇이 함께 변하나".
  3) 회복 정의 = (D) 연속 개선 기울기 + (C) 2연속 파 확인(sustained) 회복.
     단발 임계통과(원형·완성논문 방식)는 폐기.
  4) RTM 벤치마크 = 관측 회복을 AR(1) 기대와 비교하여 인공물분을 제거.
  + 표본외(train/test, seed=20260619) 검증 — Alcohol 프로젝트와 '동일 기준'.

[입력]  data/processed/merged/KYHPS_STU_5y_wide_final.csv   (읽기 전용)
[출력]  outputs/tables/rec_*.xlsx + 콘솔 요약

[주의]  GAD-7 문항은 1-4 코딩 → 표준점수 = 합(7~28) - 7 = 0~21.
        완성 논문은 합(7~28)을 0~21로 표기하고 '≥10=중등도'를 잘못 적용했음.
        본 스크립트는 표준 0~21로 교정 후 임상컷(≥10)을 사용한다.
"""
import os
import math
import numpy as np
import pandas as pd

# ------------------------------------------------------------------ 설정
RNG = 20260619           # Alcohol 프로젝트와 동일 시드(비교 공정성)
TEST_FRAC = 0.30
THR = 10                 # GAD-7 표준(0-21) 임상 중등도 컷
DATA = "data/processed/merged/KYHPS_STU_5y_wide_final.csv"
OUTDIR = "outputs/tables"
os.makedirs(OUTDIR, exist_ok=True)
w = pd.read_csv(DATA)


# ------------------------------------------------------------------ 유틸
def num(c):
    return pd.to_numeric(w[c], errors="coerce")


def col(key, wave):
    """key 를 포함하고 _w{wave} 로 끝나는 첫 컬럼명(없으면 None)."""
    cs = [c for c in w.columns if key in c and c.endswith(f"_w{wave}")]
    return cs[0] if cs else None


def ncdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def pz(z):
    return 2 * (1 - ncdf(abs(z)))


def auc(score, y):
    """순위 기반 AUC (Alcohol 스크립트와 동일 구현)."""
    score = np.asarray(score, float)
    y = np.asarray(y, int)
    pos, neg = score[y == 1], score[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    r = pd.Series(np.concatenate([pos, neg])).rank().values
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def ols(y, Xcols):
    """절편 포함 OLS. 반환: beta, 예측, R²."""
    X = np.column_stack([np.ones(len(y))] + Xcols)
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ beta
    r2 = 1 - np.sum((y - yhat) ** 2) / np.sum((y - y.mean()) ** 2)
    return beta, yhat, r2


def logit_irls(X, y, iters=60, ridge=1e-6):
    """numpy 로지스틱 회귀(IRLS). X 는 절편 포함, 예측변수는 표준화 권장."""
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(X @ beta, -30, 30)))
        W = np.clip(p * (1 - p), 1e-6, None)
        z = X @ beta + (y - p) / W
        H = (X.T * W) @ X + ridge * np.eye(X.shape[1])
        beta_new = np.linalg.solve(H, (X.T * W) @ z)
        if np.max(np.abs(beta_new - beta)) < 1e-8:
            return beta_new
        beta = beta_new
    return beta


def save(df, name):
    path = os.path.join(OUTDIR, name)
    try:
        df.to_excel(path, index=False)
    except Exception:
        path = path.replace(".xlsx", ".csv")
        df.to_csv(path, index=False)
    print(f"  [저장] {path}")


# ============================================================ 0. 변수 구축
# GAD-7 표준점수(0-21) = 7문항 합(1-4 코딩, 7-28) - 7
GAD = {}
for k in (3, 4, 5):
    items = sorted([c for c in w.columns if "GAD-7" in c and c.endswith(f"_w{k}")])
    raw = w[items].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=7)
    GAD[k] = raw - 7
G = pd.DataFrame({f"gad{k}": GAD[k] for k in (3, 4, 5)})

# 단일문항 우울(1=없음, 2=있음) → 1=우울
DEP = {}
for k in (1, 2, 3, 4, 5):
    c = col("우울감 경험", k)
    v = num(c)
    DEP[k] = np.where(v.notna(), (v == 2).astype(float), np.nan)
D = pd.DataFrame({f"d{k}": DEP[k] for k in (1, 2, 3, 4, 5)})

# 시간가변 예측변수(W3-5, 일관 순서형). 스트레스는 역코딩(↑=스트레스 많음).
PRED_KEYS = {
    "smartphone": "스마트폰 이용시간(주중)",
    "sleep": "수면시간(주중)",
    "stress_acad": "스트레스 경험(학업)",
    "stress_future": "스트레스 경험(미래)",
    "stress_friend": "스트레스 경험(친구관계)",
    "stress_appear": "스트레스 경험(외모)",
    "stress_family": "스트레스 경험(가족관계)",
}
STRESS = {"stress_acad", "stress_future", "stress_friend", "stress_appear", "stress_family"}
P = {}
for name, key in PRED_KEYS.items():
    cols = {k: col(key, k) for k in (3, 4, 5)}
    if any(v is None for v in cols.values()):
        print(f"  [경고] {name} 일부 차수 결측 → 제외")
        continue
    series = {k: num(cols[k]) for k in (3, 4, 5)}
    if name in STRESS:                      # 역코딩: 5 - x (1-4 척도 → ↑=스트레스↑)
        series = {k: 5 - series[k] for k in (3, 4, 5)}
    P[name] = series
PREDS = list(P.keys())

SEX = num(col("학생 성별", 1))              # 1=남, 2=여 (가정)
print(f"분석 표본: N={len(w)} | 예측변수 {len(PREDS)}개 | GAD-7 차수 W3-5")


# ============================================================ 1. 측정 품질
print("\n========== [1] 측정 품질: GAD-7(연속) vs 단일문항 ==========")
# Cronbach alpha (W3)
items3 = sorted([c for c in w.columns if "GAD-7" in c and c.endswith("_w3")])
Xa = w[items3].apply(pd.to_numeric, errors="coerce").dropna()
kk = Xa.shape[1]
alpha = kk / (kk - 1) * (1 - Xa.var(ddof=1).sum() / Xa.sum(axis=1).var(ddof=1))


def retest(a, b):
    d = pd.concat([G[a], G[b]], axis=1).dropna()
    return d.iloc[:, 0].corr(d.iloc[:, 1])


long_g = G.reset_index().melt("index", var_name="wave", value_name="g").dropna()
btw = long_g.groupby("index")["g"].mean().var(ddof=1)
wth = long_g.groupby("index")["g"].var(ddof=1).mean()
icc = btw / (btw + wth)
meas = pd.DataFrame([
    {"지표": "Cronbach α (W3)", "GAD-7 연속": round(alpha, 3), "단일문항 우울": "N/A(단일)"},
    {"지표": "test-retest r (W3-W4)", "GAD-7 연속": round(retest("gad3", "gad4"), 3),
     "단일문항 우울": round(D["d3"].corr(D["d4"]), 3)},
    {"지표": "test-retest r (W4-W5)", "GAD-7 연속": round(retest("gad4", "gad5"), 3),
     "단일문항 우울": round(D["d4"].corr(D["d5"]), 3)},
    {"지표": "ICC (between/total)", "GAD-7 연속": round(icc, 3), "단일문항 우울": "—"},
    {"지표": "%≥10(중등도, 표준 0-21)", "GAD-7 연속": round(100 * (G["gad5"] >= THR).mean(), 1),
     "단일문항 우울": round(100 * np.nanmean(DEP[5]), 1)},
])
print(meas.to_string(index=False))
print(f"  해석: GAD-7 ICC={icc:.2f} → within-person 분산 {100*(1-icc):.0f}% (회복 관측 가능)")
save(meas, "rec_measurement_quality.xlsx")


# ============================================================ 2. 회복 정의 비교
print("\n========== [2] 회복 정의 비교 (단발 폐기 → 확인·연속) ==========")
hi3 = G["gad3"] >= THR                       # W3 임상적 고불안(at-risk)
rows = []
# (원형) 단일문항 W1→W5 이분
orig = ((D.d1 == 1) & (D.d5 == 0))
durable = ((D.d1 == 1) & (D.d2 == 0) & (D.d3 == 0) & (D.d4 == 0) & (D.d5 == 0))
rows.append({"정의": "원형 단일문항 W1→W5", "분모(at-risk)": int((D.d1 == 1).sum()),
             "회복 N": int(orig.sum()), "회복률%": round(100 * orig.sum() / (D.d1 == 1).sum(), 1),
             "지속성 검증": f"durable(W2-5 내내 정상) {int(durable.sum())}명 = {round(100*durable.sum()/orig.sum())}%"})
# (단발) GAD high@W3 → W5<10
single = (G["gad5"][hi3] < THR)
rows.append({"정의": "GAD 단발(high@W3→W5<10)", "분모(at-risk)": int(hi3.sum()),
             "회복 N": int(single.sum()), "회복률%": round(100 * single.mean(), 1),
             "지속성 검증": "단발 끝점 — RTM 취약(아래 [3])"})
# (확인) GAD high@W3 → W4<10 & W5<10
conf = ((G["gad4"][hi3] < THR) & (G["gad5"][hi3] < THR))
rows.append({"정의": "GAD 확인(high@W3→W4&W5<10)", "분모(at-risk)": int(hi3.sum()),
             "회복 N": int(conf.sum()), "회복률%": round(100 * conf.mean(), 1),
             "지속성 검증": "2연속 파 확인 → RTM 강건"})
# (연속) within-person 기울기(개선=음의 기울기)
slope = (G["gad5"] - G["gad3"]) / 2.0        # 파당 변화(W3→W5)
rows.append({"정의": "연속 개선 기울기(ΔGAD/파)", "분모(at-risk)": int(G[["gad3", "gad5"]].dropna().shape[0]),
             "회복 N": int((slope < 0).sum()), "회복률%": round(100 * (slope < 0).mean(), 1),
             "지속성 검증": f"평균 기울기 {slope.mean():+.2f}/파 (임계 불필요)"})
defs = pd.DataFrame(rows)
print(defs.to_string(index=False))
save(defs, "rec_definitions.xlsx")


# ============================================================ 3. RTM 감사
print("\n========== [3] RTM 감사: 관측 회복 vs AR(1) 기대 ==========")
d35 = pd.concat([G["gad3"], G["gad5"]], axis=1).dropna()
d35.columns = ["g3", "g5"]
b1, b0 = np.polyfit(d35["g3"], d35["g5"], 1)
resid_sd = np.std(d35["g5"] - (b0 + b1 * d35["g3"]), ddof=2)
sub = d35[d35["g3"] >= THR]
rec_obs = float((sub["g5"] < THR).mean())
rtm_exp = float(np.mean([ncdf((THR - (b0 + b1 * x)) / resid_sd) for x in sub["g3"]]))
# RTM 너머 구조: gad5 ~ gad3  vs  + within-person Δ공변량
base = pd.concat([G["gad3"], G["gad5"]] + [P[p][3] for p in PREDS] + [P[p][5] for p in PREDS],
                 axis=1).dropna()
base.columns = ["g3", "g5"] + [f"{p}_3" for p in PREDS] + [f"{p}_5" for p in PREDS]
_, _, r2_ar = ols(base["g5"].values, [base["g3"].values])
dcov = [(base[f"{p}_5"] - base[f"{p}_3"]).values for p in PREDS]
_, _, r2_full = ols(base["g5"].values, [base["g3"].values] + dcov)
rtm = pd.DataFrame([
    {"검정": "관측 회복 P(<10@W5 | high@W3)", "값": round(rec_obs, 3), "비교/해석": "단발 회복률"},
    {"검정": "AR(1)/RTM 기대 회복", "값": round(rtm_exp, 3),
     "비교/해석": f"관측≈기대 → 단발은 RTM (r35={d35['g3'].corr(d35['g5']):.2f})"},
    {"검정": "확인 회복 P(<10@W4&W5 | high@W3)", "값": round(float(conf.mean()), 3),
     "비교/해석": "단발의 약 절반만 지속"},
    {"검정": "R²(gad5~gad3) [RTM/자기회귀분]", "값": round(r2_ar, 3), "비교/해석": "끝점 예측의 RTM 성분"},
    {"검정": "R²(+ within Δ공변량)", "값": round(r2_full, 3), "비교/해석": "RTM 너머 구조 추가"},
    {"검정": "ΔR² (RTM 초과 설명력)", "값": round(r2_full - r2_ar, 3),
     "비교/해석": "양(+)이면 회복에 실제 구조 존재"},
])
print(rtm.to_string(index=False))
save(rtm, "rec_rtm_audit.xlsx")


# ============================================================ 4. within/between (Mundlak)
print("\n========== [4] within-person 분해 (Mundlak, pid 군집강건) ==========")
recs = []
for k in (3, 4, 5):
    dd = pd.DataFrame({"pid": w.index, "gad": G[f"gad{k}"]})
    for p in PREDS:
        dd[p] = P[p][k]
    recs.append(dd)
L = pd.concat(recs).dropna()
for p in PREDS:
    m = L.groupby("pid")[p].transform("mean")
    L[p + "_w"] = L[p] - m          # within(개인내 편차)
    L[p + "_b"] = m                 # between(개인 평균)
Xcols = [f"{p}_w" for p in PREDS] + [f"{p}_b" for p in PREDS]
X = np.column_stack([np.ones(len(L))] + [L[c].values for c in Xcols])
y = L["gad"].values
beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
u = y - X @ beta
bread = np.linalg.inv(X.T @ X)
meat = np.zeros((X.shape[1], X.shape[1]))
for _, idx in L.groupby("pid").indices.items():
    s = X[idx].T @ u[idx]
    meat += np.outer(s, s)
se = np.sqrt(np.diag(bread @ meat @ bread))
names = ["const"] + Xcols
mund = []
for p in PREDS:
    iw = names.index(f"{p}_w")
    ib = names.index(f"{p}_b")
    mund.append({"변수": p,
                 "within_β": round(beta[iw], 3), "within_p": round(pz(beta[iw] / se[iw]), 4),
                 "between_β": round(beta[ib], 3), "between_p": round(pz(beta[ib] / se[ib]), 4)})
mund = pd.DataFrame(mund)
print(mund.to_string(index=False))
print(f"  person-waves N={len(L)} | 핵심: 스마트폰 within 유의성 확인(동인 vs 특성)")
save(mund, "rec_mundlak_within_between.xlsx")


# ============================================================ 5. 표본외 검증(Alcohol 동일 기준)
print("\n========== [5] 표본외(train/test, seed=20260619) — Alcohol과 동일 기준 ==========")
rng = np.random.RandomState(RNG)
oos = []

# (5a) 회복 '과정' OOS: 개인단위 분할 → ΔGAD(W3→W5) ~ ΔCov 예측 test R²
proc = base.copy()
proc["dgad"] = proc["g5"] - proc["g3"]
for p in PREDS:
    proc[f"d_{p}"] = proc[f"{p}_5"] - proc[f"{p}_3"]
te = rng.rand(len(proc)) < TEST_FRAC
dcols = [f"d_{p}" for p in PREDS]
Xtr = np.column_stack([np.ones((~te).sum())] + [proc.loc[~te, c].values for c in dcols])
btr, _, _ = ols(proc.loc[~te, "dgad"].values, [proc.loc[~te, c].values for c in dcols])
Xte = np.column_stack([np.ones(te.sum())] + [proc.loc[te, c].values for c in dcols])
pred_te = Xte @ btr
ss_res = np.sum((proc.loc[te, "dgad"].values - pred_te) ** 2)
ss_tot = np.sum((proc.loc[te, "dgad"].values - proc.loc[te, "dgad"].mean()) ** 2)
r2_te = 1 - ss_res / ss_tot
oos.append({"표본외 과제": "회복과정 ΔGAD(W3→W5)~ΔCov", "N_test": int(te.sum()),
            "지표": "test R²", "값": round(r2_te, 3),
            "해석": "within 회복과정이 표본외에서도 재현되는가"})

# (5b) 회복 '예측' OOS: high@W3 중, 조기신호(W3값+W3→W4 변화)로 확인회복 분류 → test AUC
atrisk = G["gad3"] >= THR
feat = pd.DataFrame({"pid": w.index})
feat["gad3"] = G["gad3"]
for p in PREDS:
    feat[f"chg_{p}"] = P[p][4] - P[p][3]            # W3→W4 조기변화(누설 방지)
feat["y"] = ((G["gad4"] < THR) & (G["gad5"] < THR)).astype(float)   # 확인 회복
fcols = ["gad3"] + [f"chg_{p}" for p in PREDS]
dat = feat[atrisk][fcols + ["y"]].dropna()
auc_rec = np.nan
n_te2 = 0
if len(dat) > 60:
    z = (dat[fcols] - dat[fcols].mean()) / dat[fcols].std(ddof=0)
    te2 = rng.rand(len(dat)) < TEST_FRAC
    n_te2 = int(te2.sum())
    Xtr = np.column_stack([np.ones((~te2).sum()), z[~te2].values])
    bb = logit_irls(Xtr, dat["y"].values[~te2])
    Xte = np.column_stack([np.ones(te2.sum()), z[te2].values])
    risk = 1 / (1 + np.exp(-np.clip(Xte @ bb, -30, 30)))
    auc_rec = auc(risk, dat["y"].values[te2])
oos.append({"표본외 과제": "확인회복 분류(high@W3, 조기신호)", "N_test": n_te2,
            "지표": "test AUC", "값": round(auc_rec, 3) if auc_rec == auc_rec else "N/A",
            "해석": "누가 지속 회복하는지 표본외 예측력"})
oos_df = pd.DataFrame(oos)
print(oos_df.to_string(index=False))
save(oos_df, "rec_oos_validation.xlsx")

print("\n완료. 모든 산출물은 outputs/tables/rec_*.xlsx 에 저장됨.")

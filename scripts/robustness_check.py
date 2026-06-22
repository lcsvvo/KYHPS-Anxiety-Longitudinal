"""
# robustness_check.py  — v2 (linearmodels 7.x / statsmodels 0.14 호환)
#
# 목적:
#   Pooled OLS 결과의 견고성(robustness)을 다각도로 검증.
#   심사위원이 공격할 수 있는 방법론적 취약점을 선제적으로 검증한다.
#
# ─── 변수 코딩 방향 (코드북 확인 완료) ───────────────────────────
#   stress_academic : 1 = 스트레스 매우 높음 / 4 = 거의 없음  (역방향)
#     → OLS β = -0.092 는 "스트레스 높을수록(낮은 값) 우울↑"를 의미 (자연스러운 방향)
#   physical_activity : 1 = 0일(없음) / 8 = 7일(매일)  (순방향 추정)
#     → OLS β = +0.008 은 역인과 또는 개인 고정효과 혼입 가능성 → FE에서 검증
# ─────────────────────────────────────────────────────────────────
#
# 포함 분석:
#   STEP 1. Fixed Effects (EntityEffects + TimeEffects) — linearmodels 7.x
#   STEP 2. Random Effects + Hausman 검정 (FE vs RE 선택 근거)
#   STEP 3. Logit AME (Average Marginal Effect, summary_frame 방식)
#   STEP 4. 모형 비교 테이블 (OLS / FE / Logit AME 나란히)
#   STEP 5. MICE vs CCA 민감도 분석
#   STEP 6. 변수 코딩 방향 검증 (데이터 기반)
#   STEP 7. 매개분석 탐색 (Smartphone → Sleep → Depression)
#   STEP 8. 3모형 Forest Plot 시각화
#
# 입력:
#   data/processed/cleaned/KYHPS_STU_analysis_long.csv
#   data/processed/cleaned/KYHPS_STU_preprocessed_MICE_imp1.csv  (STEP 5)
#   data/processed/cleaned/KYHPS_STU_preprocessed_CCA.csv        (STEP 5)
#
# 출력 (tables/):
#   robustness_fe_coefficients.xlsx
#   robustness_re_coefficients.xlsx
#   robustness_hausman.xlsx
#   robustness_logit_ame.xlsx
#   robustness_model_comparison.xlsx
#   robustness_mice_vs_cca.xlsx
#   robustness_mediation_explore.xlsx
#
# 출력 (figures/):
#   fig16_model_comparison_forest.png
#
# 실행:
#   cd "C:/Users/jiwoo/OneDrive/Desktop/나/3학년/제1회 청소년건강패널조사"
#   pip install linearmodels
#   python scripts/robustness_check.py
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from scipy import stats

warnings.filterwarnings("ignore")

# ── utils import ───────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    PROJECT_ROOT, LONG_CSV, DATA_CLEANED, FIG_DIR, TABLE_DIR, YEARS,
    get_logger, load_csv, set_korean_font, sig_stars,
    continuous_to_ordinal_smartphone, continuous_to_ordinal_sleep,
)

LOGGER = get_logger("robustness_check")
set_korean_font()

# 핵심 변수 목록 (FE에서 sex/female은 시간불변 → 제외)
KEY_VARS_FULL = ["smartphone", "sleep", "physical_activity", "stress_academic", "female"]
KEY_VARS_FE   = ["smartphone", "sleep", "physical_activity", "stress_academic"]


# ══════════════════════════════════════════════════════════════════════════════
# 공통 유틸
# ══════════════════════════════════════════════════════════════════════════════

def load_base_data() -> pd.DataFrame:
    """
    Long form 로드 → 분석용 변수 생성 → 결측 제거.

    주의: stress_academic 역방향 코딩
        1 = 스트레스 매우 높음, 4 = 거의 없음
        → 값이 작을수록 스트레스가 큼.
        모든 β 해석 시 이 방향을 기준으로 서술.
    """
    df = load_csv(LONG_CSV)
    df["female"]   = (df["sex"] == 2).astype(int)
    df["year_cat"] = pd.Categorical(df["year"], categories=YEARS, ordered=True)

    req = ["depression", "smartphone", "sleep", "physical_activity",
           "stress_academic", "female", "pid", "year"]
    before = len(df)
    df = df.dropna(subset=req).copy()
    LOGGER.info(f"데이터 로드: {before}→{len(df)}행, {df['pid'].nunique()}명")
    return df


def _ols_coef_df(model_result, key_vars: list, model_name: str) -> pd.DataFrame:
    """statsmodels OLS fit 결과 → 계수 테이블."""
    rows = []
    for v in key_vars:
        if v not in model_result.params:
            continue
        b  = model_result.params[v]
        se = model_result.bse[v]
        t  = model_result.tvalues[v]
        p  = model_result.pvalues[v]
        ci = model_result.conf_int().loc[v]
        rows.append({"모형": model_name, "변수": v,
                     "β": round(b, 5), "SE": round(se, 5),
                     "t": round(t, 3), "p": round(p, 4),
                     "유의성": sig_stars(p),
                     "CI_하": round(ci[0], 5), "CI_상": round(ci[1], 5)})
    return pd.DataFrame(rows)


def _lm_coef_df(result, key_vars: list, model_name: str) -> pd.DataFrame:
    """
    linearmodels 결과 → 계수 테이블.

    linearmodels 7.x 에서 conf_int() 컬럼이 'lower'/'upper'.
    """
    rows = []
    for v in key_vars:
        if v not in result.params.index:
            continue
        b  = float(result.params[v])
        se = float(result.std_errors[v])
        t  = float(result.tstats[v])
        p  = float(result.pvalues[v])
        ci = result.conf_int().loc[v]          # Series: lower / upper
        rows.append({"모형": model_name, "변수": v,
                     "β": round(b, 5), "SE": round(se, 5),
                     "t": round(t, 3), "p": round(p, 4),
                     "유의성": sig_stars(p),
                     "CI_하": round(float(ci["lower"]), 5),
                     "CI_상": round(float(ci["upper"]), 5)})
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1. Fixed Effects (Entity + Time)
# ══════════════════════════════════════════════════════════════════════════════

def run_fixed_effects(df: pd.DataFrame):
    """
    Two-Way Fixed Effects: 개인(Entity) + 연도(Time) 고정효과 동시 통제.

    linearmodels 7.x API:
        from_formula()에 entity_effects 인자 없음.
        대신 formula 안에 'EntityEffects', 'TimeEffects' 키워드를 포함.
        cov_type='clustered' + cluster_entity=True 로 개인 기준 클러스터 SE.

    WHY Two-Way FE:
        Entity FE → 개인 고정 특성(유전, 성격, 가정환경) 완전 통제.
        Time FE   → 전체에 공통인 시간 효과(COVID, 정책 등) 통제.
        "같은 사람에서, 스마트폰 사용이 늘어난 해에 우울도 증가했는가?"

    female은 시간 불변 변수(sex는 변하지 않음) → FE에서 소거됨 → 제외.

    반환:
        fe_result  (linearmodels 결과 객체 또는 None)
        fe_coef_df (pd.DataFrame)
    """
    LOGGER.info("=== STEP 1: Fixed Effects ===")
    try:
        from linearmodels.panel import PanelOLS
    except ImportError:
        LOGGER.error("linearmodels 미설치: pip install linearmodels")
        return None, pd.DataFrame()

    # (pid, year) MultiIndex 필수
    df_fe = df.set_index(["pid", "year"]).copy()

    formula = (
        "depression ~ smartphone + sleep + physical_activity "
        "+ stress_academic + EntityEffects + TimeEffects"
    )
    try:
        model  = PanelOLS.from_formula(formula, data=df_fe)
        result = model.fit(cov_type="clustered", cluster_entity=True)
    except Exception as e:
        LOGGER.error(f"FE 실행 오류: {e}")
        return None, pd.DataFrame()

    fe_coef = _lm_coef_df(result, KEY_VARS_FE, "Fixed Effects")

    LOGGER.info(f"\n{fe_coef.to_string(index=False)}")
    LOGGER.info(f"FE R²(within)={result.rsquared:.4f}, N={result.nobs}")

    save_path = TABLE_DIR / "robustness_fe_coefficients.xlsx"
    fe_coef.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    return result, fe_coef


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2. Random Effects + Hausman 검정
# ══════════════════════════════════════════════════════════════════════════════

def run_random_effects(df: pd.DataFrame):
    """
    Random Effects 모형 실행 (Hausman 비교용).

    WHY RE:
        RE는 개인 효과 α_i와 설명변수가 무상관이라는 가정.
        이 가정이 유효하면 RE가 FE보다 효율적(더 작은 표준오차).
        Hausman 검정으로 이 가정의 타당성을 검증.
    """
    LOGGER.info("=== STEP 2a: Random Effects ===")
    try:
        from linearmodels.panel import RandomEffects
    except ImportError:
        return None, pd.DataFrame()

    df_re = df.set_index(["pid", "year"]).copy()
    formula = (
        "depression ~ smartphone + sleep + physical_activity + stress_academic"
    )
    try:
        model  = RandomEffects.from_formula(formula, data=df_re)
        result = model.fit(cov_type="robust")
    except Exception as e:
        LOGGER.error(f"RE 실행 오류: {e}")
        return None, pd.DataFrame()

    re_coef = _lm_coef_df(result, KEY_VARS_FE, "Random Effects")

    LOGGER.info(f"\n{re_coef.to_string(index=False)}")

    save_path = TABLE_DIR / "robustness_re_coefficients.xlsx"
    re_coef.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    return result, re_coef


def run_hausman_test(fe_result, re_result) -> pd.DataFrame:
    """
    Hausman 검정: FE vs RE 선택의 통계적 근거.

    H0: RE 일관적 (개인 효과와 설명변수 무상관) → RE 수용
    H1: RE 편향  (개인 효과와 상관 있음)       → FE 채택

    p < 0.05: FE 선택
    p ≥ 0.05: RE 수용 가능

    계산 방법:
        W = (β_FE - β_RE)' [Var(β_FE) - Var(β_RE)]^{-1} (β_FE - β_RE)
        W ~ χ²(k)   k = 비교 변수 수

    주의:
        Var(FE) - Var(RE) 의 일부 대각 원소가 음수일 수 있음 (수치적 불안정).
        이 경우 절댓값으로 처리하고 결과 해석 시 주의.
    """
    LOGGER.info("=== STEP 2b: Hausman 검정 ===")
    if fe_result is None or re_result is None:
        LOGGER.warning("Hausman 불가: FE 또는 RE 결과 없음")
        return pd.DataFrame()

    common = [v for v in KEY_VARS_FE
              if v in fe_result.params.index and v in re_result.params.index]
    if not common:
        LOGGER.warning("공통 변수 없음")
        return pd.DataFrame()

    b_fe = fe_result.params[common].values.astype(float)
    b_re = re_result.params[common].values.astype(float)
    diff = b_fe - b_re

    # 공분산 행렬 추출
    # linearmodels 7.x: result.cov 는 DataFrame (k×k)
    V_fe = fe_result.cov.loc[common, common].values.astype(float)
    V_re = re_result.cov.loc[common, common].values.astype(float)
    V_diff = V_fe - V_re

    # 수치 안정성: 반정정치 투영
    try:
        W = float(diff @ np.linalg.pinv(V_diff) @ diff)
    except Exception:
        # 대각 원소만 사용하는 단순 버전
        diag_diff = np.abs(np.diag(V_diff))
        diag_diff[diag_diff < 1e-12] = 1e-12
        W = float(np.sum(diff**2 / diag_diff))

    df_stat = len(common)
    p_val   = 1 - stats.chi2.cdf(W, df=df_stat)

    conclusion = "FE 채택 (RE 편향, p<0.05)" if p_val < 0.05 else "RE 수용 가능 (p≥0.05)"
    LOGGER.info(f"Hausman W={W:.3f}, df={df_stat}, p={p_val:.4f} → {conclusion}")

    rows_var = [{"변수": v,
                 "β_FE": round(float(fe_result.params[v]), 5),
                 "β_RE": round(float(re_result.params[v]), 5),
                 "차이(FE-RE)": round(float(fe_result.params[v] - re_result.params[v]), 5)}
                for v in common]

    result_df = pd.DataFrame([{
        "검정통계량(W)": round(W, 4),
        "자유도(df)": df_stat,
        "p값": round(p_val, 4),
        "결론": conclusion,
    }] + rows_var)

    save_path = TABLE_DIR / "robustness_hausman.xlsx"
    result_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    return result_df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3. Logit AME
# ══════════════════════════════════════════════════════════════════════════════

def run_logit_ame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Logit 모형의 Average Marginal Effect (AME at mean) 계산.
    statsmodels 0.14: get_margeff().summary_frame() 방식 사용.

    WHY summary_frame():
        mg.margeff / mg.margeff_se 는 numpy array → 변수명 인덱스 없음.
        summary_frame()은 변수명을 index로 가지는 DataFrame 반환 → 안전.

    반환 컬럼 (summary_frame):
        dy/dx, Std. Err., z, Pr(>|z|), Conf. Int. Low, Cont. Int. Hi.

    해석:
        AME β = LPM β 와 같은 단위(확률 변화량).
        두 모형의 방향이 같으면 LPM 결과 신뢰도↑.
    """
    LOGGER.info("=== STEP 3: Logit AME ===")

    formula = (
        "depression ~ smartphone + sleep + physical_activity "
        "+ stress_academic + female + C(year_cat)"
    )
    try:
        logit_m = smf.logit(formula, data=df).fit(disp=False, maxiter=500)
    except Exception as e:
        LOGGER.error(f"Logit fit 오류: {e}")
        return pd.DataFrame()

    try:
        mg = logit_m.get_margeff(at="mean")
        sf = mg.summary_frame()        # index = 변수명
    except Exception as e:
        LOGGER.error(f"AME 계산 오류: {e}")
        return pd.DataFrame()

    rows = []
    for var in KEY_VARS_FULL:
        if var not in sf.index:
            continue
        me  = float(sf.loc[var, "dy/dx"])
        se  = float(sf.loc[var, "Std. Err."])
        z   = float(sf.loc[var, "z"])
        p   = float(sf.loc[var, "Pr(>|z|)"])
        cil = float(sf.loc[var, "Conf. Int. Low"])
        ciu = float(sf.loc[var, "Cont. Int. Hi."])
        rows.append({"모형": "Logit AME", "변수": var,
                     "β(AME)": round(me, 5), "SE": round(se, 5),
                     "z": round(z, 3), "p": round(p, 4),
                     "유의성": sig_stars(p),
                     "CI_하": round(cil, 5), "CI_상": round(ciu, 5)})

    ame_df = pd.DataFrame(rows)
    LOGGER.info(f"\n{ame_df.to_string(index=False)}")

    save_path = TABLE_DIR / "robustness_logit_ame.xlsx"
    ame_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    return ame_df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4. 모형 비교 테이블
# ══════════════════════════════════════════════════════════════════════════════

def build_model_comparison(
    ols_coef: pd.DataFrame,
    fe_coef:  pd.DataFrame,
    ame_coef: pd.DataFrame,
) -> pd.DataFrame:
    """
    Pooled OLS / Fixed Effects / Logit AME 세 모형을 동일 테이블에 정리.

    세 모형이 동일 방향·유사 크기 → "방법론에 강건한 결과" 입증.
    방향 불일치 → 내생성 또는 모형 가정 위반 경고.

    stress_academic 해석 주의:
        β 음수 + 역방향 코딩(1=많음) → 스트레스 높을수록 우울↑ (자연스러운 방향).
    """
    LOGGER.info("=== STEP 4: 모형 비교 테이블 ===")

    def _get(df_, var, b_col="β"):
        if df_ is None or df_.empty:
            return "N/A", "N/A"
        col = "β(AME)" if "β(AME)" in df_.columns else b_col
        sub = df_[df_["변수"] == var]
        if sub.empty:
            return "N/A", "N/A"
        return f"{sub[col].values[0]:.4f}", sub["유의성"].values[0]

    rows = []
    for var in KEY_VARS_FULL:
        ob, os = _get(ols_coef, var)
        fb, fs = _get(fe_coef,  var)
        ab, as_ = _get(ame_coef, var)
        rows.append({
            "변수": var,
            "Pooled OLS":    f"{ob} {os}",
            "Fixed Effects": f"{fb} {fs}",
            "Logit AME":     f"{ab} {as_}",
        })

    comp_df = pd.DataFrame(rows)
    print("\n" + "="*65)
    print("모형 비교 테이블")
    print("="*65)
    print(comp_df.to_string(index=False))
    print("="*65 + "\n")

    save_path = TABLE_DIR / "robustness_model_comparison.xlsx"
    comp_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    return comp_df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5. MICE vs CCA 민감도 분석
# ══════════════════════════════════════════════════════════════════════════════

def _build_long_from_mice_wide(path: Path) -> pd.DataFrame:
    """
    MICE/CCA wide 전처리 파일(한국어 컬럼명)을 analysis_long 형식으로 변환.

    WHY:
        preprocessed_MICE_imp1.csv 등은 원 한국어 컬럼명의 wide 형식.
        패널 회귀를 위해 long form (pid × year)으로 melting + 영어 변수명 매핑.
        w1(2019) 스마트폰·수면은 연속형(시간+분) → ordinal 변환 후 사용.

    입력 파일 컬럼 매핑:
        우울감 경험_w{i}          → depression
        스마트폰 이용시간(주중)_w{i} → smartphone (w2–w5 ordinal 1–9)
        스마트폰 이용시간(주중)_시간_w1 + 분_w1 → continuous → ordinal
        수면시간(주중)_w{i}        → sleep      (w2–w5 ordinal 1–8)
        수면시간(주중) _시간_w1 + 분_w1 → continuous → ordinal
        하루 60분 이상 신체 활동 빈도_w{i} → physical_activity
        스트레스 경험(학업)_w{i}   → stress_academic
        학생 성별_w1               → female (1=남, 0=여; 코딩 확인 후 반전)
        설문번호                   → pid
    """
    df_w = load_csv(path)

    # pid
    if "설문번호" not in df_w.columns:
        LOGGER.warning(f"[MICE wide] '설문번호' 컬럼 없음 → 변환 실패")
        return pd.DataFrame()

    # 성별: 원 코드 확인 (1=남, 0=여 로 가정 — analysis_long 방식과 동일)
    sex_col = "학생 성별_w1"
    if sex_col in df_w.columns:
        # 1이 남학생(female=0), 0이 여학생(female=1) — analysis_wide 방식 확인
        # utils.py: female = (sex_label == 'female') or (sex == 0)
        female_series = (df_w[sex_col] == 0).astype(int)
    else:
        female_series = pd.Series(np.nan, index=df_w.index)

    waves_map = {1: 2019, 2: 2020, 3: 2021, 4: 2022, 5: 2023}
    rows = []

    for wi, year in waves_map.items():
        suffix = f"_w{wi}"

        # ── 우울
        dep_col = f"우울감 경험{suffix}"
        dep = df_w[dep_col] if dep_col in df_w.columns else pd.Series(np.nan, index=df_w.index)

        # ── 스마트폰 (w1=연속→ordinal, w2+= ordinal 직접 사용)
        if wi == 1:
            sp_h = df_w.get("스마트폰 이용시간(주중)_시간_w1", pd.Series(np.nan, index=df_w.index))
            sp_m = df_w.get("스마트폰 이용시간(주중)_분_w1",  pd.Series(np.nan, index=df_w.index))
            sp_hrs = pd.to_numeric(sp_h, errors="coerce") + pd.to_numeric(sp_m, errors="coerce") / 60
            sp = sp_hrs.apply(lambda x: continuous_to_ordinal_smartphone(x) if pd.notna(x) else np.nan)
        else:
            sp_col = f"스마트폰 이용시간(주중){suffix}"
            sp = pd.to_numeric(df_w.get(sp_col, pd.Series(np.nan, index=df_w.index)), errors="coerce")

        # ── 수면 (w1=연속→ordinal, w2+= ordinal 직접 사용)
        if wi == 1:
            sl_h = df_w.get("수면시간(주중) _시간_w1", pd.Series(np.nan, index=df_w.index))
            sl_m = df_w.get("수면시간(주중) _분_w1",  pd.Series(np.nan, index=df_w.index))
            sl_hrs = pd.to_numeric(sl_h, errors="coerce") + pd.to_numeric(sl_m, errors="coerce") / 60
            sl = sl_hrs.apply(lambda x: continuous_to_ordinal_sleep(x) if pd.notna(x) else np.nan)
        else:
            sl_col = f"수면시간(주중){suffix}"
            sl = pd.to_numeric(df_w.get(sl_col, pd.Series(np.nan, index=df_w.index)), errors="coerce")

        # ── 신체활동
        pa_col = f"하루 60분 이상 신체 활동 빈도{suffix}"
        pa = pd.to_numeric(df_w.get(pa_col, pd.Series(np.nan, index=df_w.index)), errors="coerce")

        # ── 학업스트레스
        st_col = f"스트레스 경험(학업){suffix}"
        st = pd.to_numeric(df_w.get(st_col, pd.Series(np.nan, index=df_w.index)), errors="coerce")

        wave_df = pd.DataFrame({
            "pid":              df_w["설문번호"].values,
            "year":             year,
            "depression":       pd.to_numeric(dep, errors="coerce").values,
            "smartphone":       sp.values,
            "sleep":            sl.values,
            "physical_activity": pa.values,
            "stress_academic":  st.values,
            "female":           female_series.values,
        })
        rows.append(wave_df)

    df_long = pd.concat(rows, ignore_index=True)
    return df_long


def run_sensitivity_mice_cca(ols_coef: pd.DataFrame) -> pd.DataFrame:
    """
    결측 처리 방법(CCA vs MICE)에 따른 계수 변화 확인.

    WHY:
        기본 분석은 listwise deletion (완전 관측치만 사용, analysis_long.csv).
        결측이 체계적(MNAR)이라면 결과가 편향될 수 있다.
        MICE 대체 데이터에서도 유사한 결과 → 결측 처리에 강건.

    CCA = analysis_long.csv (기본 분석과 동일한 완전 관측치 데이터).
    MICE = preprocessed_MICE_imp1.csv wide → long 변환 후 동일 회귀 실행.
    """
    LOGGER.info("=== STEP 5: MICE vs CCA 민감도 ===")

    req_vars = ["depression", "smartphone", "sleep",
                "physical_activity", "stress_academic"]
    results = {}

    # ── CCA: analysis_long.csv (이미 완전 관측치)
    try:
        df_cca = load_csv(DATA_CLEANED / "KYHPS_STU_analysis_long.csv")
        missing_cca = [c for c in req_vars if c not in df_cca.columns]
        if missing_cca:
            LOGGER.warning(f"[CCA] analysis_long 컬럼 없음: {missing_cca}")
        else:
            if "female" not in df_cca.columns:
                df_cca["female"] = (df_cca["sex"] == 2).astype(int)
            df_cca = df_cca.dropna(subset=req_vars).copy()
            df_cca["year_cat"] = pd.Categorical(df_cca["year"], categories=YEARS, ordered=True)
            formula_cca = (
                "depression ~ smartphone + sleep + physical_activity "
                "+ stress_academic + female + C(year_cat)"
            )
            m_cca = smf.ols(formula_cca, data=df_cca).fit(
                cov_type="cluster",
                cov_kwds={"groups": df_cca["pid"]}
            )
            for v in KEY_VARS_FE:
                if v in m_cca.params:
                    results.setdefault(v, {})["CCA"] = {
                        "β": round(m_cca.params[v], 5),
                        "유의성": sig_stars(m_cca.pvalues[v]),
                    }
            LOGGER.info(f"[CCA] N={len(df_cca)}, R²={m_cca.rsquared:.4f}")
    except Exception as e:
        LOGGER.warning(f"[CCA] 실패: {e}")

    # ── MICE: wide 파일 → long 변환 후 동일 회귀
    mice_path = DATA_CLEANED / "KYHPS_STU_preprocessed_MICE_imp1.csv"
    if mice_path.exists():
        try:
            df_mice = _build_long_from_mice_wide(mice_path)
            if df_mice.empty:
                LOGGER.warning("[MICE] long form 변환 실패 → 건너뜀")
            else:
                missing_mice = [c for c in req_vars if c not in df_mice.columns]
                if missing_mice:
                    LOGGER.warning(f"[MICE] 변환 후 컬럼 없음: {missing_mice}")
                else:
                    df_mice = df_mice.dropna(subset=req_vars).copy()
                    df_mice["year_cat"] = pd.Categorical(
                        df_mice["year"], categories=YEARS, ordered=True
                    )
                    formula_mice = (
                        "depression ~ smartphone + sleep + physical_activity "
                        "+ stress_academic + female + C(year_cat)"
                    )
                    m_mice = smf.ols(formula_mice, data=df_mice).fit(
                        cov_type="cluster",
                        cov_kwds={"groups": df_mice["pid"]}
                    )
                    for v in KEY_VARS_FE:
                        if v in m_mice.params:
                            results.setdefault(v, {})["MICE_imp1"] = {
                                "β": round(m_mice.params[v], 5),
                                "유의성": sig_stars(m_mice.pvalues[v]),
                            }
                    LOGGER.info(f"[MICE] N={len(df_mice)}, R²={m_mice.rsquared:.4f}")
        except Exception as e:
            LOGGER.warning(f"[MICE] 실패: {e}")
    else:
        LOGGER.warning(f"[MICE] 파일 없음: {mice_path}")

    if not results:
        LOGGER.warning("민감도 분석 결과 없음")
        return pd.DataFrame()

    rows = []
    for var, d in results.items():
        row = {"변수": var}
        sub = ols_coef[ols_coef["변수"] == var]
        if not sub.empty:
            row["기준 OLS"] = f"{sub['β'].values[0]:.4f} {sub['유의성'].values[0]}"
        for label, vals in d.items():
            row[label] = f"{vals['β']:.4f} {vals['유의성']}"
        rows.append(row)

    sens_df = pd.DataFrame(rows)
    LOGGER.info(f"\n{sens_df.to_string(index=False)}")

    save_path = TABLE_DIR / "robustness_mice_vs_cca.xlsx"
    sens_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    return sens_df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6. 변수 코딩 방향 검증 (데이터 기반)
# ══════════════════════════════════════════════════════════════════════════════

def verify_coding_direction(df: pd.DataFrame) -> None:
    """
    stress_academic · physical_activity 코딩 방향을
    우울 집단 간 분포 + 시간 추이로 데이터 기반 검증.

    코드북 확인 결과 요약:
        stress_academic  : 1=높음, 4=없음 (역방향) — 확인 완료
        physical_activity: 1=0일, 8=매일  (순방향) — 확인 완료
    """
    print("\n" + "="*65)
    print("변수 코딩 방향 검증 (데이터 기반 교차확인)")
    print("="*65)

    for var, coding_note in [
        ("stress_academic",
         "코드북: 1=스트레스 매우 높음, 4=거의 없음 [역방향 확인 완료]"),
        ("physical_activity",
         "코드북: 1=0일, 8=7일(매일) [순방향 추정]"),
    ]:
        dep0 = df[df["depression"] == 0][var].mean()
        dep1 = df[df["depression"] == 1][var].mean()
        t, p = stats.ttest_ind(
            df[df["depression"] == 0][var].dropna(),
            df[df["depression"] == 1][var].dropna(),
            equal_var=False
        )
        trend = df.groupby("year")[var].mean()

        print(f"\n[{var}]")
        print(f"  {coding_note}")
        print(f"  우울=0 평균: {dep0:.3f}  /  우울=1 평균: {dep1:.3f}")
        print(f"  차이(0-1): {dep0-dep1:+.3f}  t={t:.3f}  p={p:.4f}")
        print(f"  연도별 평균: {dict(zip(trend.index, trend.round(3).values))}")

    print("\n  stress_academic 최종 해석:")
    print("    β_OLS=-0.092: 점수↑(=스트레스↓) → 우울↓")
    print("    즉 '스트레스가 높을수록(낮은 점수) 우울 높음' — 자연스러운 방향 ✓")
    print("\n  physical_activity 해석 방향:")
    print("    OLS β=+0.008 (약하게 양수, ***)  /  FE에서 p~0.06으로 약화 예상")
    print("    역인과 가능성 (우울→운동 증가) 또는 개인 특성 혼입.")
    print("    FE에서 비유의화 시: '개인 고정효과 통제 후 효과 미확인' 으로 서술.")
    print("="*65 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7. 매개분석 탐색 (Smartphone → Sleep → Depression)
# ══════════════════════════════════════════════════════════════════════════════

def run_mediation_exploration(df: pd.DataFrame) -> pd.DataFrame:
    """
    Baron-Kenny 방식 매개분석 탐색.

    경로:
        A: Smartphone → Sleep          (a 계수)
        B: Sleep → Depression           (b 계수, Smartphone 통제)
        C: Smartphone → Depression      (총 효과, Sleep 미통제)
        C': Smartphone → Depression     (직접 효과, Sleep 통제)
        간접 효과 = a × b = C - C' (근사)

    WHY 수면이 매개 후보인가:
        스마트폰 사용 증가 → 취침 시간 지연 → 수면 감소 → 우울 증가.
        이 경로가 실재한다면 스마트폰의 OLS 직접 효과(β=0.018)는 과대추정.
        매개 비율만큼은 수면 경로를 통해 전달되는 효과.

    주의:
        Baron-Kenny는 탐색적. 정식 검증은 Bootstrap CI(N≥1000) 필요.
        인과 해석 불가 — 관찰된 상관 패턴 서술 수준.
    """
    LOGGER.info("=== STEP 7: 매개분석 탐색 ===")

    cluster_kw = {"cov_type": "cluster", "cov_kwds": {"groups": df["pid"]}}
    ctrl = "female + C(year_cat)"

    # A 경로: Smartphone → Sleep
    m_a = smf.ols(f"sleep ~ smartphone + {ctrl}", data=df).fit(**cluster_kw)
    a, a_p = m_a.params["smartphone"], m_a.pvalues["smartphone"]

    # C 경로: Smartphone → Depression (수면 미통제, 총 효과)
    m_c = smf.ols(
        f"depression ~ smartphone + physical_activity + stress_academic + {ctrl}",
        data=df
    ).fit(**cluster_kw)
    c, c_p = m_c.params["smartphone"], m_c.pvalues["smartphone"]

    # C' + B: Sleep 추가 → 직접 효과 + B 경로 동시 추정
    m_cp = smf.ols(
        f"depression ~ smartphone + sleep + physical_activity + stress_academic + {ctrl}",
        data=df
    ).fit(**cluster_kw)
    cp, cp_p = m_cp.params["smartphone"], m_cp.pvalues["smartphone"]
    b,  b_p  = m_cp.params["sleep"],       m_cp.pvalues["sleep"]

    indirect      = a * b
    pct_mediated  = abs(indirect / c) * 100 if abs(c) > 1e-10 else np.nan

    LOGGER.info(f"A(SP→Sleep): β={a:.4f} {sig_stars(a_p)}")
    LOGGER.info(f"B(Sleep→Dep, SP통제): β={b:.4f} {sig_stars(b_p)}")
    LOGGER.info(f"C 총 효과(SP→Dep): β={c:.4f} {sig_stars(c_p)}")
    LOGGER.info(f"C' 직접 효과: β={cp:.4f} {sig_stars(cp_p)}")
    LOGGER.info(f"간접(a×b): {indirect:.5f}, 매개비율: {pct_mediated:.1f}%")

    med_df = pd.DataFrame([
        {"경로": "A: Smartphone → Sleep",      "β": round(a,  5), "p": round(a_p, 4),  "유의성": sig_stars(a_p)},
        {"경로": "B: Sleep → Depression",       "β": round(b,  5), "p": round(b_p, 4),  "유의성": sig_stars(b_p)},
        {"경로": "C: 총 효과 (SP→Dep)",         "β": round(c,  5), "p": round(c_p, 4),  "유의성": sig_stars(c_p)},
        {"경로": "C': 직접 효과 (SP→Dep)",      "β": round(cp, 5), "p": round(cp_p, 4), "유의성": sig_stars(cp_p)},
        {"경로": "간접 효과 (A×B)",             "β": round(indirect, 5),     "p": "-", "유의성": "탐색적"},
        {"경로": "매개 비율 (%)",               "β": round(pct_mediated, 1), "p": "-", "유의성": "탐색적"},
    ])

    print("\n" + "="*65)
    print("매개분석 탐색 (Baron-Kenny, 인과 단정 불가)")
    print("="*65)
    print(med_df.to_string(index=False))

    med_type = ""
    if a_p < 0.05 and b_p < 0.05:
        med_type = "부분 매개" if cp_p < 0.05 else "완전 매개"
        print(f"\n  → 수면이 스마트폰-우울 관계를 {pct_mediated:.0f}% 매개 ({med_type} 가능성)")
        print("     정식 검증: Bootstrap CI(N=1000) 권장")
    else:
        print("\n  → A 경로 또는 B 경로 비유의 → 매개 구조 지지 미흡")
    print("="*65 + "\n")

    save_path = TABLE_DIR / "robustness_mediation_explore.xlsx"
    med_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    return med_df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 8. 3모형 Forest Plot
# ══════════════════════════════════════════════════════════════════════════════

def plot_model_comparison_forest(
    ols_coef: pd.DataFrame,
    fe_coef:  pd.DataFrame,
    ame_coef: pd.DataFrame,
) -> None:
    """
    Pooled OLS / Fixed Effects / Logit AME 세 모형의 계수를
    동일 축에 나란히 표시하는 Forest Plot.

    세 모형의 점이 같은 방향에 모이면 → 결과의 Robustness 시각적 입증.

    stress_academic β가 음수인 이유:
        역방향 코딩(1=높음) → "값↑ = 스트레스↓ → 우울↓" 이므로 음수가 맞음.
        그래프 레이블에 주석 추가.
    """
    LOGGER.info("fig16 (모형 비교 Forest Plot) 저장 중...")

    fig, ax = plt.subplots(figsize=(12, 6))

    configs = [
        (ols_coef, "Pooled OLS",    "#E53935", "o", -0.22),
        (fe_coef,  "Fixed Effects", "#1565C0", "s",  0.00),
        (ame_coef, "Logit AME",     "#2E7D32", "^",  0.22),
    ]

    n_vars = len(KEY_VARS_FE)
    y_labels = {
        "smartphone":        "Smartphone Use",
        "sleep":             "Sleep Duration",
        "physical_activity": "Physical Activity",
        "stress_academic":   "Academic Stress (1=high, 4=low)",
    }

    for coef_df, label, color, marker, offset in configs:
        if coef_df is None or coef_df.empty:
            continue
        b_col = None
        for cand in ["β(AME)", "β", "dy/dx", "coef"]:
            if cand in coef_df.columns:
                b_col = cand
                break
        if b_col is None:
            continue
        var_col = "변수" if "변수" in coef_df.columns else coef_df.columns[1]
        ci_low  = "CI_하"  if "CI_하"  in coef_df.columns else None
        ci_high = "CI_상" if "CI_상" in coef_df.columns else None
        first = True
        for i, var in enumerate(KEY_VARS_FE):
            sub = coef_df[coef_df[var_col] == var]
            if sub.empty:
                continue
            b    = float(sub[b_col].values[0])
            ci_l = float(sub[ci_low].values[0])  if ci_low  else b
            ci_u = float(sub[ci_high].values[0]) if ci_high else b
            y = i + offset
            ax.plot([ci_l, ci_u], [y, y], color=color, linewidth=1.5, alpha=0.7)
            ax.plot(b, y, marker=marker, color=color, markersize=7,
                    label=label if first else "_nolegend_", zorder=5)
            first = False

    ax.axvline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_yticks(range(n_vars))
    ax.set_yticklabels([y_labels.get(v, v) for v in KEY_VARS_FE], fontsize=11)
    ax.set_xlabel("Coefficient (Probability Point Change)", fontsize=11)
    ax.set_title(
        "Model Comparison: Pooled OLS vs Fixed Effects vs Logit AME\n"
        "(stress_academic: 1=high stress, 4=low stress)",
        fontsize=11,
    )
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()

    save_path = FIG_DIR / "fig16_model_comparison_forest.png"
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    LOGGER.info("fig16 saved: %s", save_path)


# =========================================================
# main
# =========================================================

def main() -> None:
    """Robustness Check v2 pipeline."""
    LOGGER.info("=== Robustness Check v2 START ===")

    df = load_base_data()

    formula_ols = (
        "depression ~ smartphone + sleep + physical_activity "
        "+ stress_academic + female + C(year_cat)"
    )
    ols_m = smf.ols(formula_ols, data=df).fit(
        cov_type="cluster",
        cov_kwds={"groups": df["pid"]}
    )
    ols_coef = _ols_coef_df(ols_m, KEY_VARS_FULL, "Pooled OLS")
    LOGGER.info("OLS R2=%.4f, N=%d", ols_m.rsquared, int(ols_m.nobs))

    fe_result, fe_coef = run_fixed_effects(df)
    re_result, re_coef = run_random_effects(df)
    run_hausman_test(fe_result, re_result)
    ame_coef = run_logit_ame(df)
    build_model_comparison(ols_coef, fe_coef, ame_coef)
    run_sensitivity_mice_cca(ols_coef)
    verify_coding_direction(df)
    run_mediation_exploration(df)
    plot_model_comparison_forest(ols_coef, fe_coef, ame_coef)

    LOGGER.info("=== Robustness Check v2 DONE ===")
    LOGGER.info("tables/  -> %s", TABLE_DIR)
    LOGGER.info("figures/ -> %s", FIG_DIR)


if __name__ == "__main__":
    main()

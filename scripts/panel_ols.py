"""
# panel_ols.py

목적:
    KYHPS long form 데이터에서 청소년 우울감을 종속변수로 하는
    패널 회귀분석 실행 (Pooled OLS → Fixed Effects 순서로 단계 확장).

분석 단계에서의 역할:
    - EDA와 집단 비교 이후 "양적 관계의 방향과 크기"를 추정하는 단계
    - 교란 변수를 통제한 상태에서 스마트폰·수면의 독립적 효과 추정
    - 성별 × 스마트폰 상호작용 검증 (H2)
    - Fixed Effects 모형으로 개인 내 변화 기반 인과 추정 시도

입력:
    - data/processed/cleaned/KYHPS_STU_analysis_long.csv   (25,255 rows × 11 cols)

출력 (tables/):
    - panel_ols_coefficients.xlsx        : Pooled OLS 계수 테이블
    - panel_fe_coefficients.xlsx         : Fixed Effects 계수 테이블 (linearmodels 설치 시)
    - panel_interaction_coefficients.xlsx: 상호작용 모형 계수 테이블

출력 (figures/):
    - fig14_regression_coefficients.png  : 계수 시각화 (Forest Plot)
    - fig15_interaction_plot.png         : 성별 × 스마트폰 상호작용 시각화

주의:
    - 우울 변수가 이분형(0/1)이므로 OLS 계수는 확률 변화량(LPM) 해석
    - Fixed Effects 모형은 linearmodels 패키지 필요
      (pip install linearmodels)
    - 학업스트레스 변수 코딩 방향(1=스트레스 많음 or 적음) 사전 확인 필수
    - 클러스터 표준오차(pid 기준): 개인 내 반복 측도 상관 보정

분석 모형 구조:
    Model 1: depression_it = β₀ + β₁smartphone_it + β₂sleep_it + β₃physical_it
                             + β₄stress_it + β₅female_i + Σ γ_t Year_t + ε_it
    Model 2: Model 1 + β₆(smartphone × female)
    Model 3: Fixed Effects (within estimator, 개인 고정효과 통제)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from scipy import stats

# ── utils import ──────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    PROJECT_ROOT, LONG_CSV, FIG_DIR, TABLE_DIR,
    YEARS, get_logger, load_csv, set_korean_font, sig_stars,
)

LOGGER = get_logger("panel_ols")
KOREAN_FONT_OK = set_korean_font()


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 1. 데이터 로드 및 전처리
# ──────────────────────────────────────────────────────────────────────────────

def load_and_prepare_long() -> pd.DataFrame:
    """
    long form 데이터 로드 후 회귀분석용 변수 생성.

    Returns
    -------
    df_reg : pd.DataFrame

    변수 설명:
        pid          : 개인 식별자 (패널 ID)
        year         : 조사 연도 (2019-2023)
        depression   : 우울감 경험 (0=없음, 1=있음) ← 종속변수
        smartphone   : 스마트폰 이용시간 (순위형 1-9)
        sleep        : 수면시간 (순위형 1-8)
        physical_activity : 신체활동 빈도 (일/주)
        stress_academic   : 학업 스트레스
        sex          : 성별 (1=남, 2=여)

    WHY long form으로 회귀하는가:
        개인×연도를 하나의 관측치로 보아
        시간에 따른 변화를 모형에 포함할 수 있음.
        wide form 회귀는 시점 간 의존성을 무시하는 문제 있음.
    """
    LOGGER.info("Long form 로드 및 전처리")

    if not LONG_CSV.exists():
        raise FileNotFoundError(f"long form 파일 없음: {LONG_CSV}")

    df = load_csv(LONG_CSV)
    LOGGER.info(f"로드 shape: {df.shape}")
    LOGGER.info(f"컬럼: {df.columns.tolist()}")

    df_reg = df.copy()

    # ── female 더미 생성 ──────────────────────────────────────────
    # WHY: sex=1(남), sex=2(여) 코딩에서 여=1, 남=0 더미로 변환
    #      회귀 계수가 "여학생 대비" 방향으로 직관적으로 해석됨
    sex_col = "sex" if "sex" in df_reg.columns else None
    if sex_col:
        df_reg["female"] = (df_reg[sex_col] == 2).astype(int)
    else:
        LOGGER.warning("sex 컬럼 없음, female 더미 생성 불가")
        df_reg["female"] = np.nan

    # ── 연도 범주형 변환 ──────────────────────────────────────────
    # WHY: year를 연속형으로 넣으면 "선형 시간 추세"만 포착.
    #      범주형(더미)으로 넣으면 각 연도의 독립 효과 추정 가능.
    #      기준 연도 = 2019 (COVID 이전)
    df_reg["year_cat"] = pd.Categorical(df_reg["year"], categories=YEARS, ordered=True)

    # ── 결측 제거 ─────────────────────────────────────────────────
    req_cols = ["depression", "smartphone", "sleep", "physical_activity",
                "stress_academic", "female", "pid", "year"]
    before = len(df_reg)
    df_reg = df_reg.dropna(subset=req_cols).copy()
    after  = len(df_reg)
    LOGGER.info(f"결측 제거: {before}→{after}행 ({before-after}행 제거)")

    LOGGER.info(f"분석 데이터: {df_reg.shape[0]}행, {df_reg['pid'].nunique()}명")
    return df_reg


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 2. 공통 계수 추출 함수
# ──────────────────────────────────────────────────────────────────────────────

def extract_coef_table(
    model_result,
    key_vars: list[str],
    model_name: str
) -> pd.DataFrame:
    """
    statsmodels fit 결과에서 핵심 변수의 계수 테이블 추출.

    Parameters
    ----------
    model_result : statsmodels RegressionResults
    key_vars : list[str]  출력할 변수명 목록
    model_name : str      모형 이름 (테이블 컬럼용)

    Returns
    -------
    pd.DataFrame  컬럼: 변수, β, SE, t, p, 유의성, CI_하, CI_상
    """
    rows = []
    for v in key_vars:
        if v not in model_result.params:
            LOGGER.warning(f"변수 없음: {v}")
            continue
        b    = model_result.params[v]
        se   = model_result.bse[v]
        t    = model_result.tvalues[v]
        p    = model_result.pvalues[v]
        ci   = model_result.conf_int().loc[v]
        rows.append({
            "모형":   model_name,
            "변수":   v,
            "β":      round(b, 5),
            "SE":     round(se, 5),
            "t":      round(t, 3),
            "p":      round(p, 4),
            "유의성": sig_stars(p),
            "CI_하":  round(ci[0], 5),
            "CI_상":  round(ci[1], 5),
        })
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 3. Model 1: Pooled OLS (기본 모형)
# ──────────────────────────────────────────────────────────────────────────────

def run_pooled_ols(df_reg: pd.DataFrame) -> tuple:
    """
    Model 1: Pooled OLS with cluster-robust standard errors.

    종속변수: depression (0/1) — Linear Probability Model(LPM)
    독립변수: smartphone, sleep, physical_activity, stress_academic,
              female, year_cat 더미

    Parameters
    ----------
    df_reg : pd.DataFrame

    Returns
    -------
    (model_result, coef_df) : tuple

    WHY Pooled OLS인가 (한계 포함):
        ① 가장 해석이 단순하고 직관적인 기저 모형
        ② 클러스터 SE로 개인 내 상관 보정
        ③ 한계: 개인 고정 특성(성격, 가정환경 등) 미통제 → Model 3 FE로 보완

    WHY Linear Probability Model(이진 종속 변수에 OLS)?
        - 계수를 "확률 변화량"으로 직접 해석 가능 (로짓보다 직관적)
        - 패널 FE와의 비교가 용이
        - 한계: 예측값이 [0,1] 범위를 벗어날 수 있음
               (이 경우 예측값 범위 확인 권장)
    """
    LOGGER.info("=== Model 1: Pooled OLS ===")

    formula = (
        "depression ~ smartphone + sleep + physical_activity + "
        "stress_academic + female + C(year_cat)"
    )

    # WHY cov_type='cluster': 같은 개인이 5번 측정되므로
    #     반복 측도 간 오차가 상관됨. 클러스터 SE로 이를 보정하지 않으면
    #     표준오차가 과소 추정(p값 과소)되어 1종 오류 가능성 증가.
    model = smf.ols(formula, data=df_reg).fit(
        cov_type="cluster",
        cov_kwds={"groups": df_reg["pid"]}
    )

    LOGGER.info(f"R²={model.rsquared:.4f}, Adj.R²={model.rsquared_adj:.4f}, N={int(model.nobs)}")

    key_vars = ["smartphone", "sleep", "physical_activity", "stress_academic", "female"]
    coef_df = extract_coef_table(model, key_vars, model_name="Pooled OLS")

    LOGGER.info(f"\n{coef_df.to_string(index=False)}")

    # 연도 더미 계수 별도 출력
    year_params = {k: v for k, v in model.params.items() if "year_cat" in k}
    LOGGER.info("연도 더미 (기준: 2019):")
    for k, b in year_params.items():
        yr = k.replace("C(year_cat)[T.", "").replace("]", "")
        p  = model.pvalues[k]
        LOGGER.info(f"  {yr}: β={b:.4f} {sig_stars(p)}")

    save_path = TABLE_DIR / "panel_ols_coefficients.xlsx"
    coef_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    return model, coef_df


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 4. Model 2: 성별 × 스마트폰 상호작용 모형
# ──────────────────────────────────────────────────────────────────────────────

def run_interaction_model(df_reg: pd.DataFrame) -> tuple:
    """
    Model 2: Pooled OLS with female × smartphone interaction term.

    H2 검증: "스마트폰의 우울 효과가 여학생에서 더 강하게 나타나는가?"

    Parameters
    ----------
    df_reg : pd.DataFrame

    Returns
    -------
    (model_result, coef_df) : tuple

    WHY 상호작용 항이 필요한가:
        스마트폰의 주효과(β₁)는 "남녀 평균" 효과이지만,
        실제로는 성별에 따라 효과 크기가 다를 수 있음.
        female × smartphone 상호작용 계수(β₆)가 양수이면
        → 여학생에서 스마트폰 효과가 β₁+β₆ (더 강함)
        → 남학생에서 스마트폰 효과는 β₁
    """
    LOGGER.info("=== Model 2: 성별×스마트폰 상호작용 ===")

    formula = (
        "depression ~ smartphone * female + sleep + "
        "physical_activity + stress_academic + C(year_cat)"
    )

    model = smf.ols(formula, data=df_reg).fit(
        cov_type="cluster",
        cov_kwds={"groups": df_reg["pid"]}
    )

    key_vars = ["smartphone", "female", "smartphone:female",
                "sleep", "physical_activity", "stress_academic"]
    coef_df = extract_coef_table(model, key_vars, model_name="Interaction")

    LOGGER.info(f"\n{coef_df.to_string(index=False)}")

    save_path = TABLE_DIR / "panel_interaction_coefficients.xlsx"
    coef_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    # 상호작용 해석
    int_key = "smartphone:female"
    if int_key in model.params:
        b_int = model.params[int_key]
        p_int = model.pvalues[int_key]
        b_main = model.params.get("smartphone", np.nan)
        LOGGER.info(
            f"상호작용 해석:\n"
            f"  남학생 스마트폰 효과: β={b_main:.4f}\n"
            f"  여학생 스마트폰 효과: β={b_main:.4f}+{b_int:.4f}={b_main+b_int:.4f}\n"
            f"  상호작용: β={b_int:.4f}, p={p_int:.4f} {sig_stars(p_int)}"
        )

    return model, coef_df


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 5. Model 3: Fixed Effects (Within Estimator)
# ──────────────────────────────────────────────────────────────────────────────

def run_fixed_effects(df_reg: pd.DataFrame) -> tuple:
    """
    Model 3: Panel Fixed Effects (Entity Effects = 개인 고정효과).
    """
    LOGGER.info("=== Model 3: Fixed Effects ===")

    try:
        from linearmodels.panel import PanelOLS
    except ImportError:
        LOGGER.warning(
            "linearmodels 미설치. 아래 명령 실행 후 재시도:\n"
            "  pip install linearmodels"
        )
        return None, None

    # --------------------------------------------------
    # MultiIndex 설정
    # linearmodels는 (entity, time) index 필요
    # --------------------------------------------------
    df_fe = df_reg.set_index(["pid", "year"])

    # --------------------------------------------------
    # Fixed Effects 공식
    # EntityEffects = 개인 고정효과
    # TimeEffects   = 연도 고정효과
    # --------------------------------------------------
    formula = """
    depression ~ 1
    + smartphone
    + sleep
    + physical_activity
    + stress_academic
    + TimeEffects
    + EntityEffects
    """

    # --------------------------------------------------
    # 모델 적합
    # --------------------------------------------------
    model = PanelOLS.from_formula(
        formula,
        data=df_fe
    )

    result = model.fit(
        cov_type="clustered",
        cluster_entity=True
    )

    LOGGER.info(f"\n{result.summary}")

    # --------------------------------------------------
    # 계수 테이블 생성
    # --------------------------------------------------
    key_vars = [
        "smartphone",
        "sleep",
        "physical_activity",
        "stress_academic"
    ]

    rows = []

    for v in key_vars:

        if v not in result.params.index:
            continue

        b = result.params[v]
        se = result.std_errors[v]
        t = result.tstats[v]
        p = result.pvalues[v]
        ci = result.conf_int().loc[v]

        rows.append({
            "모형": "Fixed Effects",
            "변수": v,
            "β": round(b, 5),
            "SE": round(se, 5),
            "t": round(t, 3),
            "p": round(p, 4),
            "유의성": sig_stars(p),
            "CI_하": round(ci["lower"], 5),
            "CI_상": round(ci["upper"], 5),
        })

    coef_df = pd.DataFrame(rows)

    LOGGER.info(f"\n{coef_df.to_string(index=False)}")

    save_path = TABLE_DIR / "panel_fe_coefficients.xlsx"

    coef_df.to_excel(save_path, index=False)

    LOGGER.info(f"저장: {save_path}")

    return result, coef_df
  


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 6. 계수 시각화 (Forest Plot)
# ──────────────────────────────────────────────────────────────────────────────

def plot_coefficient_forest(coef_df: pd.DataFrame, model_name: str = "Pooled OLS") -> None:
    """
    회귀 계수를 Forest Plot (가로 막대 + CI) 형태로 시각화.

    Parameters
    ----------
    coef_df : pd.DataFrame  (extract_coef_table 반환값)
    model_name : str

    WHY Forest Plot을 쓰는가:
        계수와 신뢰구간을 동시에 시각화해 "크기와 불확실성"을 직관적으로 표현.
        표 형태보다 독자가 방향성과 유의성을 빠르게 파악할 수 있음.
    """
    LOGGER.info("fig14 (계수 시각화) 저장 중...")

    # sex 관련 변수 제외 (상호작용 모형에서 복잡해지므로 주요 변수만)
    plot_vars = ["smartphone", "sleep", "physical_activity", "stress_academic", "female"]
    sub = coef_df[coef_df["변수"].isin(plot_vars)].copy()

    if sub.empty:
        LOGGER.warning("시각화할 변수 없음")
        return

    fig, ax = plt.subplots(figsize=(9, 5))

    y_pos = range(len(sub))
    betas = sub["β"].values
    cis   = (sub["CI_상"].values - sub["CI_하"].values) / 2

    # 색상: 양수=붉은계, 음수=파란계
    colors = ["#E53935" if b > 0 else "#1E88E5" for b in betas]

    ax.barh(list(y_pos), betas, xerr=cis, color=colors, alpha=0.85,
            error_kw=dict(ecolor="black", capsize=5, linewidth=1.5), height=0.55)

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(sub["변수"].values, fontsize=11)
    ax.axvline(0, color="black", lw=1.2, linestyle="--")
    ax.set_xlabel("Regression Coefficient (β) with 95% CI", fontsize=11)
    ax.set_title(
        f"{model_name}: Predictors of Depression\n"
        "(LPM, Cluster SE by Individual, Year FE Controlled)",
        fontsize=11, fontweight="bold"
    )

    # 유의성 별표
    for i, (_, row) in enumerate(sub.iterrows()):
        offset = row["CI_상"] + abs(row["β"]) * 0.05 + 0.001
        ax.annotate(
            row["유의성"],
            xy=(offset, i),
            ha="left", va="center", fontsize=10, color="darkred"
        )

    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()

    save_path = FIG_DIR / "fig14_regression_coefficients.png"
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    LOGGER.info(f"저장: {save_path}")


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 7. 상호작용 효과 시각화
# ──────────────────────────────────────────────────────────────────────────────

def plot_interaction_effect(df_reg: pd.DataFrame, model_result) -> None:
    """
    성별 × 스마트폰 상호작용 시각화:
    스마트폰 사용 수준별 우울 예측 확률을 남/여 그룹으로 비교.

    Parameters
    ----------
    df_reg : pd.DataFrame
    model_result : statsmodels OLS result (Model 2)

    WHY 상호작용 시각화가 필요한가:
        상호작용 계수(β=0.011)만으로는 "어느 스마트폰 수준에서
        얼마나 차이가 나는가"를 직관적으로 알기 어려움.
        예측값 그래프로 실질적 의미를 확인해야 함.
    """
    LOGGER.info("fig15 (상호작용 시각화) 저장 중...")

    # 스마트폰 사용 수준 범위 (1-9 순위형)
    sp_range = np.linspace(1, 9, 50)

    # 다른 변수들은 표본 평균값으로 고정 (marginal effect 추정)
    # WHY: 다른 변수를 평균에 고정해야 "스마트폰만의 효과"를 분리 가능
    mean_vals = df_reg[["sleep", "physical_activity", "stress_academic"]].mean()

    pred_data = []
    for sex_val, sex_label in [(0, "Male (female=0)"), (1, "Female (female=1)")]:
        # 예측용 데이터프레임 생성
        X_pred = pd.DataFrame({
            "smartphone":       sp_range,
            "female":           sex_val,
            "sleep":            mean_vals["sleep"],
            "physical_activity": mean_vals["physical_activity"],
            "stress_academic":   mean_vals["stress_academic"],
            "year_cat":          pd.Categorical([2021]*len(sp_range),
                                               categories=YEARS, ordered=True),
        })

        try:
            preds = model_result.predict(X_pred)
        except Exception as e:
            LOGGER.warning(f"예측 실패: {e}")
            return

        for sp, pred in zip(sp_range, preds):
            pred_data.append({"smartphone": sp, "sex_label": sex_label, "pred_prob": pred})

    pred_df = pd.DataFrame(pred_data)

    fig, ax = plt.subplots(figsize=(9, 5))

    for sex_label, color, ls in [
        ("Male (female=0)",   "steelblue", "-"),
        ("Female (female=1)", "crimson",   "--"),
    ]:
        sub = pred_df[pred_df["sex_label"] == sex_label]
        ax.plot(sub["smartphone"], sub["pred_prob"],
                color=color, linestyle=ls, lw=2.2, label=sex_label)

    ax.set_xlabel("Smartphone Use (ordinal 1-9)", fontsize=11)
    ax.set_ylabel("Predicted Probability of Depression", fontsize=11)
    ax.set_title(
        "Interaction: Smartphone × Female\n"
        "(Other variables held at mean, Year=2021)",
        fontsize=11, fontweight="bold"
    )
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    save_path = FIG_DIR / "fig15_interaction_plot.png"
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    LOGGER.info(f"저장: {save_path}")


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 8. 모형 비교 요약 출력
# ──────────────────────────────────────────────────────────────────────────────

def print_model_comparison(m1_coef: pd.DataFrame, m2_coef: pd.DataFrame) -> None:
    """
    Model 1 vs Model 2 핵심 계수 비교 콘솔 출력.

    WHY 모형 비교가 필요한가:
        상호작용 항 추가 후 주효과가 어떻게 변화하는지 확인.
        smartphone 주효과는 상호작용 모형에서는 "남학생만의 효과"로 재해석됨.
    """
    print("\n" + "="*70)
    print("모형 비교 요약 (핵심 변수)")
    print("="*70)

    compare_vars = ["smartphone", "sleep", "physical_activity", "stress_academic", "female"]
    print(f"{'변수':<25} {'M1_β':>10} {'M1_p':>10} {'M2_β':>10} {'M2_p':>10}")
    print("-"*70)

    for var in compare_vars:
        row1 = m1_coef[m1_coef["변수"] == var]
        row2 = m2_coef[m2_coef["변수"] == var]
        b1 = f"{row1['β'].values[0]:.4f}" if not row1.empty else "N/A"
        p1 = f"{row1['유의성'].values[0]}" if not row1.empty else "N/A"
        b2 = f"{row2['β'].values[0]:.4f}" if not row2.empty else "N/A"
        p2 = f"{row2['유의성'].values[0]}" if not row2.empty else "N/A"
        print(f"  {var:<23} {b1:>10} {p1:>10} {b2:>10} {p2:>10}")

    # 상호작용 항
    int_row = m2_coef[m2_coef["변수"] == "smartphone:female"]
    if not int_row.empty:
        print("-"*70)
        print(
            f"  {'smartphone:female':<23} {'':>10} {'':>10} "
            f"{int_row['β'].values[0]:>10.4f} {int_row['유의성'].values[0]:>10}"
        )
    print("="*70 + "\n")


# ──────────────────────────────────────────────────────────────────────────────
# 메인 실행 진입점
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    실행 순서:
        1. Long form 데이터 로드 및 전처리
        2. Model 1: Pooled OLS (기본 모형)
        3. Model 2: 성별×스마트폰 상호작용 모형
        4. Model 3: Fixed Effects (linearmodels 설치 필요)
        5. Forest Plot 시각화
        6. 상호작용 시각화
        7. 모형 비교 콘솔 출력

    VS Code 터미널 실행:
        cd /path/to/kyhps-anxiety-dynamics
        python scripts/panel_ols.py

    Fixed Effects 실행 시 사전 설치:
        pip install linearmodels
    """
    LOGGER.info("━━━ Panel OLS 분석 시작 ━━━")

    # 1. 데이터 로드
    df_reg = load_and_prepare_long()

    # 2. Model 1: Pooled OLS
    m1_result, m1_coef = run_pooled_ols(df_reg)

    # 3. Model 2: 상호작용
    m2_result, m2_coef = run_interaction_model(df_reg)

    # 4. Model 3: Fixed Effects (linearmodels 없으면 skip)
    m3_result, m3_coef = run_fixed_effects(df_reg)

    # 5. Forest Plot
    if m1_coef is not None:
        plot_coefficient_forest(m1_coef, model_name="Pooled OLS")

    # 6. 상호작용 시각화
    if m2_result is not None:
        plot_interaction_effect(df_reg, m2_result)

    # 7. 모형 비교
    if m1_coef is not None and m2_coef is not None:
        print_model_comparison(m1_coef, m2_coef)

    LOGGER.info("━━━ Panel OLS 분석 완료 ━━━")
    LOGGER.info(f"figures/ → {FIG_DIR}")
    LOGGER.info(f"tables/  → {TABLE_DIR}")

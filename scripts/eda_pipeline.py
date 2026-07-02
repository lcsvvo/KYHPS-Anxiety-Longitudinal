"""
# eda_pipeline.py

목적:
    KYHPS 청소년건강패널 데이터 전체 EDA(탐색적 데이터 분석) 파이프라인.
    분석 결과 재현성을 위해 단계별로 분리된 함수로 구성.

분석 단계에서의 역할:
    [1단계] 데이터 구조 확인 (컬럼, 형태, 변수 분포)
    [2단계] 결측 패턴 분석
    [3단계] 기술통계 및 연도별 평균 추이
    [4단계] 스파게티 플롯 (개인 궤적 시각화)
    [5단계] 성별 하위집단 추이
    [6단계] 변화 점수 분포
    [7단계] 우울 궤적 집단 분포

입력:
    - data/processed/cleaned/KYHPS_STU_analysis_wide.csv  (5051 × 39)
    - data/processed/cleaned/KYHPS_STU_analysis_long.csv  (25255 × 11)

출력 (figures/):
    - fig01_mean_trend_6vars.png      : 6개 변수 연도별 평균 추이
    - fig02_spaghetti_6vars.png       : 개인 궤적 (무작위 100명 표본)
    - fig03_gender_subgroup.png       : 성별 하위집단 추이
    - fig04_change_score_dist.png     : 변화 점수 분포
    - fig11_depression_group_dist.png : 우울 궤적 집단 분포

출력 (tables/):
    - mean_trend_by_year.xlsx         : 연도별 평균 테이블
    - missing_summary.xlsx            : 결측 요약
    - change_score_summary.xlsx       : 변화 점수 기술통계
    - depression_group_dist.xlsx      : 우울 집단 분포

주의:
    - 스마트폰/수면 2019 측정 방식이 2020-2023과 다름 (연속→순위형 변환 적용)
    - 이 파일의 그래프 출력에는 영문 레이블 사용 (한글 폰트 환경에 따라 분기)
    - 분석 대상: wide form 기준 5,051명
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")    # GUI 없는 환경용; VS Code에서는 제거 가능
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

# ── 프로젝트 내부 유틸리티 import ─────────────────────────────────────────────
# WHY: sys.path에 scripts/ 상위(=프로젝트 루트)를 추가해야
#      어느 디렉터리에서 실행해도 utils를 찾을 수 있음
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    PROJECT_ROOT, WIDE_CSV, LONG_CSV, FIG_DIR, TABLE_DIR,
    YEARS, WAVES, VAR_PREFIXES, VAR_LABELS,
    get_logger, load_csv, add_dep_group_column, set_korean_font,
)

LOGGER = get_logger("eda_pipeline")
KOREAN_FONT_OK = set_korean_font()


# ──────────────────────────────────────────────────────────────────────────────
# STEP 0. 데이터 로드
# ──────────────────────────────────────────────────────────────────────────────

def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    wide / long form 분석 데이터 로드.

    Returns
    -------
    (df_wide, df_long) : tuple
        wide : 5051 rows × 39 cols (한 행 = 한 학생)
        long : 25255 rows × 11 cols (한 행 = 한 학생-연도)

    WHY wide vs long 두 가지를 모두 유지하는가:
        - wide  → 집단 비교, 변화 점수, 기저값 분석에 유리
        - long  → 회귀분석, 추이 시각화, 반복 측도 분석에 유리
        두 형태 모두 필요하므로 변환 없이 각각 저장해 두는 것이 효율적.
    """
    LOGGER.info("데이터 로드 시작")

    if not WIDE_CSV.exists():
        raise FileNotFoundError(f"wide form 파일 없음: {WIDE_CSV}")
    if not LONG_CSV.exists():
        raise FileNotFoundError(f"long form 파일 없음: {LONG_CSV}")

    df_wide = load_csv(WIDE_CSV)
    df_long = load_csv(LONG_CSV)

    LOGGER.info(f"wide shape: {df_wide.shape}")
    LOGGER.info(f"long shape: {df_long.shape}")

    return df_wide, df_long


# ──────────────────────────────────────────────────────────────────────────────
# STEP 1. 데이터 구조 확인
# ──────────────────────────────────────────────────────────────────────────────

def describe_structure(df_wide: pd.DataFrame, df_long: pd.DataFrame) -> None:
    """
    데이터 기본 구조를 콘솔에 출력. 저장 파일 없음.

    WHY: 분석 전 컬럼 목록·dtypes·기본 통계를 확인하지 않으면
         잘못된 변수명이나 타입으로 이후 분석이 조용히 실패할 수 있음.
    """
    LOGGER.info("=== STEP 1: 데이터 구조 ===")
    print("\n[wide form 컬럼]")
    print(df_wide.columns.tolist())
    print("\n[long form 컬럼]")
    print(df_long.columns.tolist())
    print("\n[wide 기술통계 (수치형 컬럼)]")
    print(df_wide.describe().round(3))
    print("\n[long 연도별 응답 수]")
    print(df_long["year"].value_counts().sort_index())


# ──────────────────────────────────────────────────────────────────────────────
# STEP 2. 결측 패턴 분석
# ──────────────────────────────────────────────────────────────────────────────

def analyze_missing(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    주요 변수(웨이브별)의 결측 건수·비율 요약.

    Parameters
    ----------
    df_wide : pd.DataFrame

    Returns
    -------
    missing_df : pd.DataFrame  (변수 × [결측 수, 결측률])

    WHY: 패널 데이터에서 결측은 단순 오류가 아닐 수 있음.
         중도탈락(attrition)이 체계적으로 발생하면 완전응답자 분석 결과가
         편향될 수 있음(선택 편향). 먼저 결측 규모를 파악해야 함.
    """
    LOGGER.info("=== STEP 2: 결측 패턴 분석 ===")

    # 주요 변수×웨이브의 결측만 집계
    target_cols = [
        f"{var}_{w}"
        for var in VAR_PREFIXES
        for w in WAVES
        if f"{var}_{w}" in df_wide.columns
    ]

    missing_df = pd.DataFrame({
        "column":    target_cols,
        "missing_n": [df_wide[c].isna().sum() for c in target_cols],
        "missing_pct": [round(df_wide[c].isna().mean() * 100, 2) for c in target_cols],
        "valid_n":   [df_wide[c].notna().sum() for c in target_cols],
    })

    # 변수명 파싱 (prefix, wave)
    missing_df["variable"] = missing_df["column"].str.rsplit("_", n=1).str[0]
    missing_df["wave"]     = missing_df["column"].str.rsplit("_", n=1).str[1]

    LOGGER.info(f"\n{missing_df.to_string(index=False)}")

    save_path = TABLE_DIR / "missing_summary.xlsx"
    missing_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    return missing_df


# ──────────────────────────────────────────────────────────────────────────────
# STEP 3. 연도별 평균 추이 계산 및 시각화
# ──────────────────────────────────────────────────────────────────────────────

def compute_mean_trends(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    6개 변수의 연도별(w1-w5) 평균·표준편차 계산.

    Parameters
    ----------
    df_wide : pd.DataFrame

    Returns
    -------
    trend_df : pd.DataFrame
        컬럼: variable, year, mean, std, n

    WHY: 집단 평균 추이 그래프는 "전반적 패턴"을 보여주지만
         개인 수준의 이질성을 숨김. 이 함수는 기초 집계만 담당하고
         실제 이질성은 STEP 4 스파게티 플롯에서 시각화.
    """
    LOGGER.info("=== STEP 3: 연도별 평균 추이 ===")

    records = []
    for var in VAR_PREFIXES:
        for w, yr in zip(WAVES, YEARS):
            col = f"{var}_{w}"
            if col not in df_wide.columns:
                continue
            s = df_wide[col].dropna()
            records.append({
                "variable": var,
                "year":     yr,
                "mean":     round(s.mean(), 4),
                "std":      round(s.std(),  4),
                "n":        len(s),
            })

    trend_df = pd.DataFrame(records)
    LOGGER.info(f"\n{trend_df.to_string(index=False)}")

    save_path = TABLE_DIR / "mean_trend_by_year.xlsx"
    trend_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    return trend_df


def plot_mean_trends(trend_df: pd.DataFrame) -> None:
    """
    6개 변수 연도별 평균 추이 6-panel 그래프 저장.

    Parameters
    ----------
    trend_df : pd.DataFrame  (compute_mean_trends 반환값)

    WHY COVID 음영 구간(2020-2021)을 표시하는 이유:
         코호트가 코로나 팬데믹을 중1→고1 전환 시기에 경험함.
         환경 급변 시점을 표시해야 "추이의 원인"을 독자가 맥락적으로 이해.
    """
    LOGGER.info("fig01 저장 중...")

    # depression은 비율(0/1) 평균이므로 별도 축 처리 필요할 수 있음
    # 여기서는 일관성을 위해 동일 축 사용

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.suptitle(
        "KYHPS 2019-2023: Mean Trends by Variable\n"
        "(Shaded: COVID period 2020-2021)",
        fontsize=13, fontweight="bold"
    )

    colors = ["#2196F3", "#FF5722", "#4CAF50", "#FF9800", "#9C27B0", "#E91E63"]

    for ax, var, color in zip(axes.flatten(), VAR_PREFIXES, colors):
        sub = trend_df[trend_df["variable"] == var]
        if sub.empty:
            ax.set_visible(False)
            continue

        # 평균선 + 95% CI (mean ± 1.96*SE)
        means = sub["mean"].values
        ses   = (sub["std"] / np.sqrt(sub["n"])).values
        yrs   = sub["year"].values

        ax.plot(yrs, means, "o-", color=color, lw=2.2, ms=7, zorder=3)
        ax.fill_between(yrs, means - 1.96 * ses, means + 1.96 * ses,
                        alpha=0.15, color=color, label="95% CI")

        # COVID 기간 음영
        ax.axvspan(2020, 2021, alpha=0.08, color="gray", zorder=0)
        ax.text(2020.5, ax.get_ylim()[0] if ax.get_ylim()[0] != 0 else means.min() * 0.95,
                "COVID", fontsize=7, color="gray", ha="center")

        label_str = VAR_LABELS.get(var, var) if KOREAN_FONT_OK else var.replace("_", " ").title()
        ax.set_title(label_str, fontsize=10, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_xticks(YEARS)
        ax.grid(alpha=0.3)

        # 전체 변화량 표시
        delta = round(means[-1] - means[0], 3)
        ax.annotate(
            f"Δ = {delta:+.3f}",
            xy=(0.97, 0.05), xycoords="axes fraction",
            ha="right", fontsize=9,
            color=color, fontweight="bold"
        )

    plt.tight_layout()
    save_path = FIG_DIR / "fig01_mean_trend_6vars.png"
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    LOGGER.info(f"저장: {save_path}")


# ──────────────────────────────────────────────────────────────────────────────
# STEP 4. 스파게티 플롯 (개인 궤적)
# ──────────────────────────────────────────────────────────────────────────────

def plot_spaghetti(df_wide: pd.DataFrame, n_sample: int = 100, seed: int = 42) -> None:
    """
    개인 궤적 스파게티 플롯: 무작위 n_sample명의 5년 추이 시각화.

    Parameters
    ----------
    df_wide : pd.DataFrame
    n_sample : int  표본 추출 수 (기본 100)
    seed : int      재현성을 위한 난수 시드

    WHY 스파게티 플롯이 중요한가:
        집단 평균선은 "평균 학생"의 궤적을 보여주지만
        실제로 "평균 학생"은 존재하지 않음.
        일부는 급등, 일부는 급락, 일부는 변화 없음.
        개인 이질성(heterogeneity)이 연구의 핵심이므로
        반드시 개인 궤적을 시각화해야 함.
    """
    LOGGER.info("fig02 (스파게티) 저장 중...")

    rng = np.random.default_rng(seed)
    idx = rng.choice(len(df_wide), size=min(n_sample, len(df_wide)), replace=False)
    sample = df_wide.iloc[idx]

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.suptitle(
        f"Individual Trajectories (random n={n_sample})\n"
        "+ Group Mean (bold line)",
        fontsize=13, fontweight="bold"
    )

    plot_vars = [v for v in VAR_PREFIXES if v != "depression"]  # 연속형만
    plot_vars_all = VAR_PREFIXES  # depression 포함 전체

    for ax, var in zip(axes.flatten(), VAR_PREFIXES):
        cols_exist = [f"{var}_{w}" for w in WAVES if f"{var}_{w}" in df_wide.columns]
        yrs_exist  = [WAVE_TO_YEAR[w] for w in WAVES if f"{var}_{w}" in df_wide.columns]

        if not cols_exist:
            ax.set_visible(False)
            continue

        # 개인 궤적 (반투명 가는 선)
        for _, row in sample.iterrows():
            vals = [row.get(c) for c in cols_exist]
            if all(pd.isna(v) for v in vals):
                continue
            ax.plot(yrs_exist, vals, color="steelblue", alpha=0.12, lw=0.8)

        # 집단 평균선 (굵게)
        group_means = [df_wide[c].mean() for c in cols_exist]
        ax.plot(yrs_exist, group_means, color="crimson", lw=2.5, zorder=5,
                label="Group Mean")

        # COVID 음영
        ax.axvspan(2020, 2021, alpha=0.07, color="gray")

        label_str = var.replace("_", " ").title()
        ax.set_title(label_str, fontsize=10, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_xticks(yrs_exist)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)

    plt.tight_layout()
    save_path = FIG_DIR / "fig02_spaghetti_6vars.png"
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    LOGGER.info(f"저장: {save_path}")


# 웨이브→연도 역방향 매핑 (함수 내부에서 사용)
WAVE_TO_YEAR = {w: yr for w, yr in zip(WAVES, YEARS)}


# ──────────────────────────────────────────────────────────────────────────────
# STEP 5. 성별 하위집단 추이
# ──────────────────────────────────────────────────────────────────────────────

def plot_gender_subgroup(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    성별(남/여)로 분리한 연도별 평균 추이 시각화.

    Parameters
    ----------
    df_wide : pd.DataFrame

    Returns
    -------
    gender_df : pd.DataFrame  (저장용)

    WHY: 우울감은 성별에 따라 패턴이 다르게 나타나는 것이 선행 연구 결론.
         전체 평균만 보면 이 차이가 묻힘.
         성별 × 시간 상호작용 여부를 탐색적으로 확인.

    성별 코딩:
         sex=1 → 남학생, sex=2 → 여학생
         (wide form에서 '학생 성별_w1' 컬럼 사용)
    """
    LOGGER.info("=== STEP 5: 성별 하위집단 ===")

    # sex 컬럼 이름 파악
    sex_col = "학생 성별_w1" if "학생 성별_w1" in df_wide.columns else "sex"
    if sex_col not in df_wide.columns:
        LOGGER.warning(f"성별 컬럼 없음, 건너뜀")
        return pd.DataFrame()

    records = []
    for var in VAR_PREFIXES:
        for w, yr in zip(WAVES, YEARS):
            col = f"{var}_{w}"
            if col not in df_wide.columns:
                continue
            for sex_val, sex_label in [(1, "Male"), (2, "Female")]:
                sub = df_wide[df_wide[sex_col] == sex_val][col].dropna()
                records.append({
                    "variable":  var,
                    "year":      yr,
                    "sex_label": sex_label,
                    "mean":      round(sub.mean(), 4),
                    "n":         len(sub),
                })

    gender_df = pd.DataFrame(records)

    save_path = TABLE_DIR / "subgroup_gender_means.xlsx"
    gender_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    # 시각화
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.suptitle(
        "Gender Subgroup Trajectories (Male vs Female)",
        fontsize=13, fontweight="bold"
    )

    for ax, var in zip(axes.flatten(), VAR_PREFIXES):
        sub_var = gender_df[gender_df["variable"] == var]
        if sub_var.empty:
            ax.set_visible(False)
            continue

        for sex_label, color, ls in [
            ("Male",   "steelblue",  "-"),
            ("Female", "crimson",    "--"),
        ]:
            sub = sub_var[sub_var["sex_label"] == sex_label]
            ax.plot(sub["year"], sub["mean"],
                    color=color, linestyle=ls, lw=2, ms=7,
                    marker="o", label=sex_label)

        ax.axvspan(2020, 2021, alpha=0.07, color="gray")
        ax.set_title(var.replace("_", " ").title(), fontsize=10, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_xticks(YEARS)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)

    plt.tight_layout()
    save_path_fig = FIG_DIR / "fig03_gender_subgroup.png"
    plt.savefig(save_path_fig, dpi=150, bbox_inches="tight")
    plt.close()
    LOGGER.info(f"저장: {save_path_fig}")

    return gender_df


# ──────────────────────────────────────────────────────────────────────────────
# STEP 6. 변화 점수 분포
# ──────────────────────────────────────────────────────────────────────────────

def plot_change_score_distribution(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    2019→2023 변화 점수(_change) 분포 히스토그램 + 기술통계.

    Parameters
    ----------
    df_wide : pd.DataFrame

    Returns
    -------
    change_summary_df : pd.DataFrame

    WHY 변화 점수가 중요한가:
        "종단 분석의 핵심은 집단 수준 평균이 아닌 개인 내 변화량".
        변화 점수 = x_w5 - x_w1 은 각 개인의 '방향'과 '크기'를 동시에 담음.
        이 분포를 보면:
          - 얼마나 많은 개인이 증가/감소 방향인지
          - 이상치(극단적 변화)가 있는지
          - 변화가 정규분포인지(모수 검정 가정 확인)
        등을 확인할 수 있음.
    """
    LOGGER.info("=== STEP 6: 변화 점수 분포 ===")

    change_vars = [f"{v}_change" for v in VAR_PREFIXES if f"{v}_change" in df_wide.columns]
    if not change_vars:
        LOGGER.warning("_change 컬럼 없음, 건너뜀")
        return pd.DataFrame()

    # 기술통계
    records = []
    for col in change_vars:
        s = df_wide[col].dropna()
        records.append({
            "variable":  col,
            "N":         len(s),
            "mean":      round(s.mean(), 4),
            "std":       round(s.std(),  4),
            "median":    round(s.median(), 4),
            "min":       round(s.min(), 4),
            "max":       round(s.max(), 4),
            "pct_increase": round((s > 0).mean() * 100, 1),
            "pct_decrease": round((s < 0).mean() * 100, 1),
            "pct_no_change": round((s == 0).mean() * 100, 1),
        })

    change_df = pd.DataFrame(records)
    LOGGER.info(f"\n{change_df.to_string(index=False)}")

    save_path = TABLE_DIR / "change_score_summary.xlsx"
    change_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    # 시각화
    n_cols = 3
    n_rows = int(np.ceil(len(change_vars) / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 4 * n_rows))
    axes = axes.flatten()
    fig.suptitle("Change Score Distribution (2019→2023)", fontsize=13, fontweight="bold")

    for ax, col in zip(axes, change_vars):
        s = df_wide[col].dropna()
        ax.hist(s, bins=30, color="steelblue", edgecolor="white", linewidth=0.5, alpha=0.85)
        ax.axvline(0, color="crimson", lw=1.5, linestyle="--", label="No change")
        ax.axvline(s.mean(), color="orange", lw=1.5, linestyle="-", label=f"Mean={s.mean():.2f}")
        ax.set_title(col.replace("_change", "").replace("_", " ").title(), fontsize=10, fontweight="bold")
        ax.set_xlabel("Change score (w5 - w1)")
        ax.set_ylabel("Count")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    # 남은 빈 칸 숨기기
    for ax in axes[len(change_vars):]:
        ax.set_visible(False)

    plt.tight_layout()
    save_path_fig = FIG_DIR / "fig04_change_score_dist.png"
    plt.savefig(save_path_fig, dpi=150, bbox_inches="tight")
    plt.close()
    LOGGER.info(f"저장: {save_path_fig}")

    return change_df


# ──────────────────────────────────────────────────────────────────────────────
# STEP 7. 우울 궤적 집단 분포
# ──────────────────────────────────────────────────────────────────────────────

def analyze_depression_groups(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    4개 우울 궤적 집단(Stable/Onset/Recovery/Persistent) 분포 계산 및 시각화.

    Parameters
    ----------
    df_wide : pd.DataFrame

    Returns
    -------
    group_df : pd.DataFrame (집단 분포 요약)

    WHY: 우울감은 2시점 비교(w1 vs w5)로 4개 궤적 집단을 정의할 수 있음.
         이 집단화는 "누가 우울해졌나(Onset)"를 분석하는 데 필수 전제.
         단순 발생률(%) 대신 궤적 패턴을 본다는 것이 종단 분석의 핵심.
    """
    LOGGER.info("=== STEP 7: 우울 궤적 집단 ===")

    df = add_dep_group_column(df_wide)
    counts = df["dep_group"].value_counts()
    pcts   = df["dep_group"].value_counts(normalize=True).round(4) * 100

    group_df = pd.DataFrame({
        "group": counts.index,
        "N":     counts.values,
        "pct":   pcts.values,
    })
    LOGGER.info(f"\n{group_df.to_string(index=False)}")

    save_path = TABLE_DIR / "depression_group_dist.xlsx"
    group_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    # 시각화
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Depression Trajectory Groups (2019→2023)", fontsize=13, fontweight="bold")

    display_order = ["Stable", "Onset", "Recovery", "Persistent", "Missing"]
    color_map = {
        "Stable":     "#4CAF50",
        "Onset":      "#F44336",
        "Recovery":   "#2196F3",
        "Persistent": "#9C27B0",
        "Missing":    "#9E9E9E",
    }
    ordered = [g for g in display_order if g in group_df["group"].values]
    ns   = [group_df.loc[group_df["group"] == g, "N"].values[0]   for g in ordered]
    pcts_ = [group_df.loc[group_df["group"] == g, "pct"].values[0] for g in ordered]
    clrs = [color_map[g] for g in ordered]

    # 막대 그래프
    ax1 = axes[0]
    bars = ax1.bar(ordered, ns, color=clrs, edgecolor="white", linewidth=1.5)
    ax1.bar_label(bars, labels=[f"{n:,}" for n in ns], padding=4, fontsize=11, fontweight="bold")
    ax1.set_ylabel("Count (N)")
    ax1.set_title("Count by Group")
    ax1.grid(axis="y", alpha=0.3)

    # 파이 차트 (Missing 제외)
    ax2 = axes[1]
    pie_groups = [g for g in ordered if g != "Missing"]
    pie_ns     = [group_df.loc[group_df["group"] == g, "N"].values[0] for g in pie_groups]
    pie_clrs   = [color_map[g] for g in pie_groups]
    wedges, texts, autotexts = ax2.pie(
        pie_ns,
        labels=pie_groups,
        colors=pie_clrs,
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.82,
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight("bold")
    ax2.set_title("Proportion (excl. Missing)")

    plt.tight_layout()
    save_path_fig = FIG_DIR / "fig11_depression_group_dist.png"
    plt.savefig(save_path_fig, dpi=150, bbox_inches="tight")
    plt.close()
    LOGGER.info(f"저장: {save_path_fig}")

    return group_df


# ──────────────────────────────────────────────────────────────────────────────
# 메인 실행 진입점
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    실행 순서:
        1. 데이터 로드
        2. 구조 확인 (콘솔 출력)
        3. 결측 분석 → missing_summary.xlsx
        4. 연도별 평균 계산 → mean_trend_by_year.xlsx
        5. 평균 추이 시각화 → fig01
        6. 스파게티 플롯 → fig02
        7. 성별 하위집단 → fig03 + subgroup_gender_means.xlsx
        8. 변화 점수 분포 → fig04 + change_score_summary.xlsx
        9. 우울 궤적 집단 → fig11 + depression_group_dist.xlsx

    VS Code 터미널 실행:
        cd /path/to/kyhps-anxiety-dynamics
        python scripts/eda_pipeline.py
    """
    LOGGER.info("━━━ EDA Pipeline 시작 ━━━")

    # 1. 로드
    df_wide, df_long = load_data()

    # 2. 구조 확인
    describe_structure(df_wide, df_long)

    # 3. 결측 분석
    missing_df = analyze_missing(df_wide)

    # 4-5. 평균 추이
    trend_df = compute_mean_trends(df_wide)
    plot_mean_trends(trend_df)

    # 6. 스파게티
    plot_spaghetti(df_wide, n_sample=100, seed=42)

    # 7. 성별 하위집단
    gender_df = plot_gender_subgroup(df_wide)

    # 8. 변화 점수 분포
    change_df = plot_change_score_distribution(df_wide)

    # 9. 우울 궤적 집단
    group_df = analyze_depression_groups(df_wide)

    LOGGER.info("━━━ EDA Pipeline 완료 ━━━")
    LOGGER.info(f"figures/  → {FIG_DIR}")
    LOGGER.info(f"tables/   → {TABLE_DIR}")

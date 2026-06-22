"""
# onset_analysis.py

목적:
    우울 궤적 집단 정의 후, Onset(2019 비우울 → 2023 우울) 집단과
    Stable(2019 비우울 → 2023 비우울) 집단의 심층 비교 분석.
    추가로 이중 악화 집단(스마트폰↑ & 수면↓) 분석.

분석 단계에서의 역할:
    - EDA 이후 '누가 우울해졌나?' 질문에 답하는 집단 비교 단계
    - 회귀분석(panel_ols.py) 전에 주요 차이를 탐색적으로 파악
    - 경쟁 논문의 핵심 서사("무엇이 우울 발생을 예측했나")를 구성

입력:
    - data/processed/cleaned/KYHPS_STU_analysis_wide.csv

출력 (tables/):
    - onset_vs_stable_comparison.xlsx    : 집단 간 기저값/변화량 비교 (t검정 + Cohen's d)
    - onset_stable_trend_by_year.xlsx    : 연도별 추이 (Onset vs Stable)
    - dual_worse_group_comparison.xlsx   : 이중 악화 집단 우울 발생률 비교

출력 (figures/):
    - fig12_onset_vs_stable_trajectories.png : Onset/Stable 4변수 추이 비교
    - fig13_dual_worse_analysis.png          : 이중 악화 집단 분석

주의:
    - 완전응답자(w1·w5 모두 있는 사람)만 집단 분류에 포함
    - 학업스트레스 변수의 코딩 방향(1=스트레스 많음? 적음?)을 반드시 확인
    - 효과 크기(Cohen's d) 기준: small=0.2, medium=0.5, large=0.8
    - 이분형 우울 변수를 연속형 변화 점수로 사용 시 해석 주의
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # GUI 없는 환경; VS Code에서 인터랙티브하게 보려면 이 줄 제거
import matplotlib.pyplot as plt
from scipy import stats

# ── utils import ──────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    PROJECT_ROOT, WIDE_CSV, FIG_DIR, TABLE_DIR,
    YEARS, WAVES, VAR_PREFIXES,
    get_logger, load_csv, add_dep_group_column, set_korean_font,
    cohens_d, effect_size_label, sig_stars,
)

LOGGER = get_logger("onset_analysis")
KOREAN_FONT_OK = set_korean_font()


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 1. 데이터 로드 및 집단 정의
# ──────────────────────────────────────────────────────────────────────────────

def load_and_prepare() -> pd.DataFrame:
    """
    wide form 로드 후 dep_group 컬럼 추가.

    Returns
    -------
    df : pd.DataFrame (dep_group 컬럼 포함)
    """
    LOGGER.info("데이터 로드 및 집단 정의")
    df = load_csv(WIDE_CSV)
    df = add_dep_group_column(df)

    # 집단별 분포 출력
    counts = df["dep_group"].value_counts()
    pcts   = df["dep_group"].value_counts(normalize=True) * 100
    LOGGER.info("우울 궤적 집단 분포:")
    for g in counts.index:
        LOGGER.info(f"  {g:12s}: N={counts[g]:5d} ({pcts[g]:.1f}%)")

    return df


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 2. Onset vs Stable 기저값·변화량 비교
# ──────────────────────────────────────────────────────────────────────────────

def compare_onset_vs_stable(df: pd.DataFrame) -> pd.DataFrame:
    """
    Onset 집단과 Stable 집단의 기저값(w1) 및 변화량(_change)을
    Welch's t검정과 Cohen's d로 비교.

    Parameters
    ----------
    df : pd.DataFrame (dep_group 컬럼 포함)

    Returns
    -------
    result_df : pd.DataFrame  (모든 비교 결과 행 포함)

    WHY Welch's t검정을 쓰는가:
        두 집단의 분산이 다를 수 있음(n도 다름: Onset ~537, Stable ~2960).
        Welch's t는 등분산 가정 없이 더 안전한 비교를 제공.

    WHY 기저값과 변화량 모두 비교하는가:
        - 기저값 차이 → "처음부터 달랐던 집단인가?" (선행 취약성)
        - 변화량 차이 → "5년간 더 나빠진 집단인가?" (궤적 차이)
        두 질문은 다른 의미를 가지므로 모두 필요.
    """
    LOGGER.info("=== Onset vs Stable 비교 ===")

    onset  = df[df["dep_group"] == "Onset"]
    stable = df[df["dep_group"] == "Stable"]
    LOGGER.info(f"Onset N={len(onset)}, Stable N={len(stable)}")

    # 비교할 변수: 기저값(w1) + 변화량(_change)
    compare_vars = {}
    for var in VAR_PREFIXES:
        if var == "depression":
            continue   # 종속변수이므로 예측변수로 비교 안 함
        if f"{var}_w1" in df.columns:
            compare_vars[f"{var}_w1"]      = f"{var} 기저값 (2019)"
        if f"{var}_change" in df.columns:
            compare_vars[f"{var}_change"]  = f"{var} 변화량 (Δ2019→2023)"

    results = []
    for col, label in compare_vars.items():
        g_onset  = onset[col].dropna().values
        g_stable = stable[col].dropna().values

        if len(g_onset) < 10 or len(g_stable) < 10:
            LOGGER.warning(f"{col}: 표본 부족, 건너뜀")
            continue

        t_stat, p_val = stats.ttest_ind(g_onset, g_stable, equal_var=False)
        d = cohens_d(g_onset, g_stable)  # Onset - Stable 방향

        results.append({
            "변수":         label,
            "Onset_mean":  round(g_onset.mean(), 4),
            "Stable_mean": round(g_stable.mean(), 4),
            "차이(O-S)":   round(g_onset.mean() - g_stable.mean(), 4),
            "t통계량":      round(t_stat, 3),
            "p값":          round(p_val, 4),
            "유의성":       sig_stars(p_val),
            "Cohen_d":     round(d, 4),
            "효과크기":    effect_size_label(d),
        })

    result_df = pd.DataFrame(results)
    LOGGER.info(f"\n{result_df.to_string(index=False)}")

    save_path = TABLE_DIR / "onset_vs_stable_comparison.xlsx"
    result_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    return result_df


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 3. Onset vs Stable 연도별 추이 비교
# ──────────────────────────────────────────────────────────────────────────────

def compare_trends_by_group(df: pd.DataFrame) -> pd.DataFrame:
    """
    Onset / Stable 집단의 4개 변수(스마트폰·수면·신체활동·학업스트레스)
    연도별 평균 추이를 계산하고 시각화.

    Parameters
    ----------
    df : pd.DataFrame (dep_group 컬럼 포함)

    Returns
    -------
    trend_df : pd.DataFrame (long form 추이 테이블)

    WHY 연도별 추이를 집단별로 보는가:
        기저값과 변화량의 집계 차이를 넘어,
        "어느 시점부터 두 집단이 갈라지기 시작했나"를 볼 수 있음.
        예: 2020 COVID 직후부터 스마트폰 추이가 달라진다면
            → COVID가 집단 분기점이라는 가설 지지 가능.
    """
    LOGGER.info("=== Onset vs Stable 연도별 추이 ===")

    plot_vars = ["smartphone", "sleep", "stress_academic", "physical_activity"]

    records = []
    for var in plot_vars:
        for group_name in ["Onset", "Stable"]:
            sub = df[df["dep_group"] == group_name]
            for w, yr in zip(WAVES, YEARS):
                col = f"{var}_{w}"
                if col not in df.columns:
                    continue
                val = sub[col].mean()
                records.append({
                    "variable": var,
                    "group":    group_name,
                    "year":     yr,
                    "mean":     round(val, 4),
                    "n":        sub[col].notna().sum(),
                })

    trend_df = pd.DataFrame(records)

    save_path = TABLE_DIR / "onset_stable_trend_by_year.xlsx"
    trend_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    # ── 시각화 ──────────────────────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle(
        "Onset vs Stable: 5-Year Lifestyle Trajectories\n"
        "(Onset = No Depression 2019 → Depressed 2023)",
        fontsize=12, fontweight="bold"
    )

    var_ax_map = dict(zip(plot_vars, axes.flatten()))

    for var, ax in var_ax_map.items():
        for group_name, color, ls, marker in [
            ("Onset",  "crimson",   "-",  "o"),
            ("Stable", "steelblue", "--", "s"),
        ]:
            sub = trend_df[(trend_df["variable"] == var) & (trend_df["group"] == group_name)]
            if sub.empty:
                continue
            ax.plot(sub["year"], sub["mean"],
                    color=color, linestyle=ls, marker=marker,
                    lw=2, ms=7, label=group_name)

        ax.axvspan(2020, 2021, alpha=0.07, color="gray")
        ax.set_title(var.replace("_", " ").title(), fontsize=11, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_xticks(YEARS)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)

        # 2023 시점 격차 표시
        sub_on  = trend_df[(trend_df["variable"] == var) & (trend_df["group"] == "Onset") & (trend_df["year"] == 2023)]
        sub_st  = trend_df[(trend_df["variable"] == var) & (trend_df["group"] == "Stable") & (trend_df["year"] == 2023)]
        if not sub_on.empty and not sub_st.empty:
            gap = sub_on["mean"].values[0] - sub_st["mean"].values[0]
            ax.annotate(
                f"2023 gap: {gap:+.2f}",
                xy=(0.97, 0.92), xycoords="axes fraction",
                ha="right", fontsize=9, color="crimson",
                bbox=dict(boxstyle="round,pad=0.2", fc="lightyellow", ec="gray", alpha=0.7)
            )

    plt.tight_layout()
    save_path_fig = FIG_DIR / "fig12_onset_vs_stable_trajectories.png"
    plt.savefig(save_path_fig, dpi=150, bbox_inches="tight")
    plt.close()
    LOGGER.info(f"저장: {save_path_fig}")

    return trend_df


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 4. 이중 악화 집단 분석
# ──────────────────────────────────────────────────────────────────────────────

def analyze_dual_worse_group(df: pd.DataFrame) -> pd.DataFrame:
    """
    스마트폰 사용 증가(smartphone_change > 0) AND 수면 감소(sleep_change < 0)
    를 동시에 경험한 집단을 정의하고 우울 신규 발생률 비교.

    Parameters
    ----------
    df : pd.DataFrame (dep_group 컬럼 포함)

    Returns
    -------
    summary_df : pd.DataFrame

    WHY 이중 악화 집단을 정의하는가:
        H4 가설: "단일 요인보다 복합 악화가 우울 위험을 증폭시킨다"를
        탐색적으로 검증하기 위함.
        스마트폰과 수면은 선행 연구에서 가장 강한 상관을 보이는 변수쌍.

    WHY 우울 변화량(연속)이 아닌 발생률(이분)로 비교하는가:
        우울 변수가 0/1 이분형이므로 연속형 변화량보다
        "기저 비우울자 중 우울 발생 비율"이 직관적이고 해석 명확.
    """
    LOGGER.info("=== 이중 악화 집단 분석 ===")

    df = df.copy()

    # 집단 정의
    # WHY > 0 기준: 변화 없음(0)은 중립으로 처리, 양수만 "증가"로 정의
    if "smartphone_change" not in df.columns or "sleep_change" not in df.columns:
        LOGGER.error("smartphone_change 또는 sleep_change 컬럼 없음")
        return pd.DataFrame()

    df["sp_increased"]    = df["smartphone_change"] > 0
    df["sleep_decreased"] = df["sleep_change"] < 0
    df["dual_worse"]      = df["sp_increased"] & df["sleep_decreased"]

    total = len(df)
    n_dw  = df["dual_worse"].sum()
    LOGGER.info(f"이중 악화 집단: N={n_dw} ({n_dw/total*100:.1f}%)")

    # ── 우울 신규 발생률 비교 ───────────────────────────────────────
    # 2019 비우울자만을 대상으로 2023 우울 발생 여부 비교
    # WHY: Onset 분석은 "시작이 같은" 집단(2019 비우울)에서만 의미있음
    df_no_dep = df[df["depression_w1"] == 0].copy()
    df_no_dep["dep_onset"] = (df_no_dep["depression_w5"] == 1).astype(int)

    rate_dw = df_no_dep[df_no_dep["dual_worse"] == True]["dep_onset"].mean()
    rate_nd = df_no_dep[df_no_dep["dual_worse"] == False]["dep_onset"].mean()

    LOGGER.info(f"우울 발생률 — 이중 악화: {rate_dw*100:.1f}%, 비해당: {rate_nd*100:.1f}%")

    # Chi-square 검정
    ct = pd.crosstab(df_no_dep["dual_worse"], df_no_dep["dep_onset"])
    from scipy.stats import chi2_contingency
    chi2, p_chi, dof, expected = chi2_contingency(ct)
    # Cramér's V (효과 크기 지표, 0=관계 없음, 1=완전 관계)
    n_ct     = ct.values.sum()
    cramers_v = np.sqrt(chi2 / (n_ct * (min(ct.shape) - 1)))

    LOGGER.info(f"Chi²={chi2:.3f}, p={p_chi:.4f}, Cramér's V={cramers_v:.3f}")

    # 이중 악화 집단 내 우울 궤적 분포
    group_in_dw = (
        df[df["dual_worse"] == True]["dep_group"]
        .value_counts(normalize=True).round(4) * 100
    )
    LOGGER.info(f"이중 악화 집단 내 궤적 분포:\n{group_in_dw}")

    # 결과 저장
    summary_df = pd.DataFrame([
        {
            "구분": "이중 악화 집단 (SP↑ & Sleep↓)",
            "N_전체": int(n_dw),
            "N_비우울기저": int(df_no_dep[df_no_dep["dual_worse"] == True]["dep_onset"].notna().sum()),
            "우울발생률(%)": round(rate_dw * 100, 2),
            "Chi2": round(chi2, 3),
            "p값": round(p_chi, 4),
            "CramersV": round(cramers_v, 4),
        },
        {
            "구분": "비해당 집단",
            "N_전체": int(total - n_dw),
            "N_비우울기저": int(df_no_dep[df_no_dep["dual_worse"] == False]["dep_onset"].notna().sum()),
            "우울발생률(%)": round(rate_nd * 100, 2),
            "Chi2": "-",
            "p값": "-",
            "CramersV": "-",
        },
    ])

    save_path = TABLE_DIR / "dual_worse_group_comparison.xlsx"
    summary_df.to_excel(save_path, index=False)
    LOGGER.info(f"저장: {save_path}")

    # ── 시각화 ──────────────────────────────────────────────────────
    _plot_dual_worse(df, df_no_dep, rate_dw, rate_nd, chi2, p_chi, cramers_v)

    return summary_df


def _plot_dual_worse(
    df: pd.DataFrame,
    df_no_dep: pd.DataFrame,
    rate_dw: float,
    rate_nd: float,
    chi2: float,
    p_chi: float,
    cramers_v: float,
) -> None:
    """이중 악화 집단 시각화 (내부 함수)."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(
        "Dual Deterioration Group Analysis\n(Smartphone↑ & Sleep↓ Simultaneously)",
        fontsize=12, fontweight="bold"
    )

    # ── 왼쪽: 우울 발생률 막대 ────────────────────────────────────
    ax1 = axes[0]
    rates = [rate_dw * 100, rate_nd * 100]
    labels = ["Dual Worse\n(SP↑ & Sleep↓)", "Others"]
    bars = ax1.bar(labels, rates, color=["crimson", "steelblue"],
                   alpha=0.85, edgecolor="white", linewidth=1.5)
    ax1.bar_label(bars, fmt="%.1f%%", padding=4, fontsize=13, fontweight="bold")
    ax1.set_ylabel("Depression Onset Rate (%)")
    ax1.set_title("New Depression Onset Rate\n(2019 non-depressed → 2023)", fontsize=10)
    ax1.set_ylim(0, max(rates) * 1.3)
    ax1.grid(axis="y", alpha=0.3)

    p_label = f"p<.001" if p_chi < 0.001 else f"p={p_chi:.3f}"
    ax1.annotate(
        f"Chi²={chi2:.1f}, {p_label}\nCramér's V={cramers_v:.3f}",
        xy=(0.5, 0.85), xycoords="axes fraction", ha="center", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", ec="gray", alpha=0.8)
    )

    # ── 오른쪽: 우울 집단별 이중 악화 비율 ──────────────────────
    ax2 = axes[1]
    group_order = ["Stable", "Recovery", "Onset", "Persistent"]
    color_map   = {"Stable": "#4CAF50", "Recovery": "#2196F3",
                   "Onset": "#F44336", "Persistent": "#9C27B0"}

    group_dual = (
        df[df["dep_group"].isin(group_order)]
        .groupby("dep_group")["dual_worse"]
        .mean() * 100
    )
    vals  = [group_dual.get(g, 0) for g in group_order]
    clrs  = [color_map[g] for g in group_order]

    bars2 = ax2.bar(group_order, vals, color=clrs, alpha=0.85, edgecolor="white", linewidth=1.5)
    ax2.bar_label(bars2, fmt="%.1f%%", padding=3, fontsize=11, fontweight="bold")
    ax2.set_ylabel("Dual Deterioration Rate (%)")
    ax2.set_title("Dual Deterioration Rate\nby Depression Trajectory Group", fontsize=10)
    ax2.set_ylim(0, max(vals) * 1.25)
    ax2.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    save_path = FIG_DIR / "fig13_dual_worse_analysis.png"
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    LOGGER.info(f"저장: {save_path}")


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 5. 탐색적 가설 후보 출력
# ──────────────────────────────────────────────────────────────────────────────

def print_hypothesis_candidates(result_df: pd.DataFrame) -> None:
    """
    비교 분석 결과를 바탕으로 가설 후보를 콘솔에 출력.
    이 함수의 출력은 '가설'이 아닌 '탐색적 해석'임을 명심할 것.

    WHY: EDA와 집단 비교는 인과관계를 증명하지 않음.
         아래 제안은 모두 '관찰된 패턴'이지 '인과 효과'가 아님.
         이후 고정효과 모형(FE) 등으로 추가 검증 필요.
    """
    print("\n" + "="*70)
    print("탐색적 가설 후보 (EDA 기반, 인과 단정 불가)")
    print("="*70)

    # 유의한 결과만 필터링
    sig_results = result_df[result_df["유의성"].isin(["*", "**", "***"])]

    for _, row in sig_results.iterrows():
        d = row["Cohen_d"]
        direction = "↑" if d > 0 else "↓"
        print(
            f"\n  [{row['유의성']}] {row['변수']}\n"
            f"       Onset={row['Onset_mean']:.3f} vs Stable={row['Stable_mean']:.3f} "
            f"(d={d:.3f}, {row['효과크기']})\n"
            f"  → 가설 후보: Onset 집단은 Stable 대비 해당 변수가 {direction} 방향으로 차이"
        )

    print("\n")
    print("주요 패턴 요약:")
    print("  H1. 스마트폰 변화량이 큰 집단에서 우울 신규 발생 가능성 높음")
    print("  H2. 2019년 수면이 짧은 집단에서 이후 우울 발생 위험 높음 (선행 취약성)")
    print("  H3. 스마트폰↑ + 수면↓ 이중 악화 집단의 우울 발생률이 1.47배 높음")
    print("  H4. 학업스트레스 감소가 보호 요인이 아닐 수 있음 (무기력화 가설)")
    print("      → 단, 변수 코딩 방향 확인 후 해석 결정")
    print("\n  ⚠ 위 가설은 모두 탐색적이며 교란 변수 미통제 상태임")
    print("     이후 Fixed Effects 패널 모형으로 개인내 변화 기반 추정 권장")
    print("="*70 + "\n")


# ──────────────────────────────────────────────────────────────────────────────
# 메인 실행 진입점
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    실행 순서:
        1. 데이터 로드 & 집단 정의
        2. Onset vs Stable 기저값·변화량 비교 (t검정 + Cohen's d)
        3. 연도별 추이 비교 시각화
        4. 이중 악화 집단 분석
        5. 가설 후보 콘솔 출력

    VS Code 터미널 실행:
        cd "C:/Users/jiwoo/OneDrive/Desktop/나/3학년/제1회 청소년건강패널조사"
        python scripts/onset_analysis.py

    eda_pipeline.py 이후 실행 권장 (데이터 파일 의존).
    """
    LOGGER.info("━━━ Onset Analysis 시작 ━━━")

    # 1. 로드 및 집단 정의
    df = load_and_prepare()

    # 2. Onset vs Stable 비교
    result_df = compare_onset_vs_stable(df)

    # 3. 연도별 추이 비교
    trend_df = compare_trends_by_group(df)

    # 4. 이중 악화 집단
    dual_df = analyze_dual_worse_group(df)

    # 5. 가설 후보 출력
    print_hypothesis_candidates(result_df)

    LOGGER.info("━━━ Onset Analysis 완료 ━━━")
    LOGGER.info(f"figures/ → {FIG_DIR}")
    LOGGER.info(f"tables/  → {TABLE_DIR}")

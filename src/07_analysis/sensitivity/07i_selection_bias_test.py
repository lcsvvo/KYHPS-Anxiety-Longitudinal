"""
src/07_analysis/sensitivity/07i_selection_bias_test.py
───────────────────────────────────────────────────────
Selection Bias (탈락 편향) 진단 분석.

목적:
    완전응답자(COMPLETE_5YR)와 탈락자(ATTRITION_*)의
    기저(2019년) 특성이 통계적으로 유의하게 다른지 검증.
    → 논문 Methods / Supplementary에 활용.

검증 방법:
    - 연속형 변수: Welch's t-test (등분산 미가정)
    - 이진/범주형 변수: Chi-square test
    - 효과 크기: Cohen's d / Cramér's V

출력:
    outputs/tables/attrition_bias_test_YYYY-MM-DD.xlsx
    outputs/tables/attrition_bias_test_YYYY-MM-DD.csv
"""

import sys
from pathlib import Path
from datetime import date
import pandas as pd
import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.utils.logger import get_logger
from src.utils.paths import CLEANED_DIR, TRACKING_DIR, OUTPUT_TABLES

log = get_logger("07i_selection_bias_test")


def cohens_d(group1: pd.Series, group2: pd.Series) -> float:
    """Cohen's d 효과 크기 계산."""
    n1, n2 = len(group1.dropna()), len(group2.dropna())
    if n1 < 2 or n2 < 2:
        return np.nan
    pooled_std = np.sqrt(
        ((n1 - 1) * group1.std() ** 2 + (n2 - 1) * group2.std() ** 2)
        / (n1 + n2 - 2)
    )
    return (group1.mean() - group2.mean()) / pooled_std if pooled_std > 0 else np.nan


def test_continuous(complete: pd.Series, attrition: pd.Series, var_label: str) -> dict:
    """연속형 변수 t-test."""
    c = complete.dropna()
    a = attrition.dropna()
    if len(c) < 2 or len(a) < 2:
        return {"변수": var_label, "비고": "데이터 부족"}

    t_stat, p_val = stats.ttest_ind(c, a, equal_var=False)
    d = cohens_d(c, a)

    return {
        "변수": var_label,
        "유형": "연속형",
        "완전응답자_평균(SD)": f"{c.mean():.2f} ({c.std():.2f})",
        "탈락자_평균(SD)":    f"{a.mean():.2f} ({a.std():.2f})",
        "t통계량": round(t_stat, 3),
        "p값": round(p_val, 4),
        "Cohen's d": round(d, 3) if not np.isnan(d) else "-",
        "유의성": "***" if p_val < 0.001 else "**" if p_val < 0.01
                  else "*" if p_val < 0.05 else "ns",
    }


def test_categorical(complete: pd.Series, attrition: pd.Series, var_label: str) -> dict:
    """범주형 변수 Chi-square test."""
    c = complete.dropna()
    a = attrition.dropna()

    if len(c) < 5 or len(a) < 5:
        return {"변수": var_label, "비고": "데이터 부족"}

    # 교차표 생성
    all_cats = pd.concat([c, a]).unique()
    c_counts = c.value_counts().reindex(all_cats, fill_value=0)
    a_counts = a.value_counts().reindex(all_cats, fill_value=0)
    contingency = pd.DataFrame({"complete": c_counts, "attrition": a_counts})

    try:
        chi2, p_val, _, _ = stats.chi2_contingency(contingency)
        # Cramér's V
        n = len(c) + len(a)
        cramers_v = np.sqrt(chi2 / (n * (min(contingency.shape) - 1)))
    except Exception:
        return {"변수": var_label, "비고": "Chi-square 계산 오류"}

    return {
        "변수": var_label,
        "유형": "범주형",
        "완전응답자_%": f"{(c == c.mode()[0]).mean()*100:.1f}",
        "탈락자_%":    f"{(a == a.mode()[0]).mean()*100:.1f}",
        "χ²": round(chi2, 3),
        "p값": round(p_val, 4),
        "Cramér's V": round(cramers_v, 3),
        "유의성": "***" if p_val < 0.001 else "**" if p_val < 0.01
                  else "*" if p_val < 0.05 else "ns",
    }


def main() -> None:
    log.info("=" * 60)
    log.info("07i_selection_bias_test: 탈락 편향 진단 시작")
    log.info("=" * 60)

    OUTPUT_TABLES.mkdir(parents=True, exist_ok=True)

    # 추적 상태 파일 로드
    tracking_path = TRACKING_DIR / "KYHPS_STU_tracking_status.csv"
    if not tracking_path.exists():
        log.error("추적 상태 파일 없음. 04a_label_tracking_status 먼저 실행 필요.")
        return

    df_tracking = pd.read_csv(tracking_path, encoding="utf-8")

    # 기저 데이터 (2019년) 로드
    base_candidates = [
        CLEANED_DIR / "KYHPS_STU_preprocessed_CCA.csv",
        CLEANED_DIR / "KYHPS_STU_smoking_flagged.csv",
    ]
    base_path = next((p for p in base_candidates if p.exists()), None)

    if base_path is None:
        log.error("기저 데이터 없음.")
        return

    try:
        df_base = pd.read_csv(base_path, encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        df_base = pd.read_csv(base_path, encoding="cp949", low_memory=False)

    log.info(f"기저 데이터: {base_path.name} | shape={df_base.shape}")

    # 추적 상태 병합
    id_col = next((c for c in ["pid", "ID", "id"] if c in df_base.columns), df_base.columns[0])
    df_merge = df_base.merge(
        df_tracking[["pid", "track_status", "is_complete"]],
        left_on=id_col, right_on="pid", how="inner"
    )

    complete_mask   = df_merge["is_complete"] == True
    attrition_mask  = df_merge["track_status"].str.startswith("ATTRITION")

    n_complete  = complete_mask.sum()
    n_attrition = attrition_mask.sum()
    log.info(f"\n완전응답자: {n_complete:,}명 | 탈락자: {n_attrition:,}명")

    # ── 검증 변수 목록 (실제 컬럼명으로 수정 필요) ────────────────────
    log.info(f"\n[설정] 실제 컬럼명 확인:")
    log.info(df_merge.columns.tolist()[:30])

    CONTINUOUS_VARS = {
        # "age_2019": "기준연도 연령",
    }
    CATEGORICAL_VARS = {
        # "sex": "성별",
        # "smk_current_2019": "흡연 여부(2019)",
    }

    results = []
    for col, label in CONTINUOUS_VARS.items():
        if col in df_merge.columns:
            r = test_continuous(df_merge.loc[complete_mask, col],
                                df_merge.loc[attrition_mask, col], label)
            results.append(r)

    for col, label in CATEGORICAL_VARS.items():
        if col in df_merge.columns:
            r = test_categorical(df_merge.loc[complete_mask, col],
                                 df_merge.loc[attrition_mask, col], label)
            results.append(r)

    if results:
        df_result = pd.DataFrame(results)
        out_xlsx = OUTPUT_TABLES / f"attrition_bias_test_{date.today()}.xlsx"
        df_result.to_excel(out_xlsx, index=False)
        log.info(f"\n저장: {out_xlsx}")
        log.info(df_result.to_string(index=False))
    else:
        log.info("\n[주의] CONTINUOUS_VARS, CATEGORICAL_VARS에 실제 변수명 입력 후 재실행 필요")

    log.info("\n✅ 07i_selection_bias_test 완료")


if __name__ == "__main__":
    main()

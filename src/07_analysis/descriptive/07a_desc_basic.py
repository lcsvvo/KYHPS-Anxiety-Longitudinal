"""
src/07_analysis/descriptive/07a_desc_basic.py
──────────────────────────────────────────────
논문 Table 1: 대상자 기본 특성 기술통계 자동 생성.

출력:
    outputs/tables/table1_descriptive_YYYY-MM-DD.xlsx
"""

import sys
from pathlib import Path
from datetime import date
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.utils.logger import get_logger
from src.utils.paths import CLEANED_DIR, TRACKING_DIR, OUTPUT_TABLES, PANEL_YEARS

log = get_logger("07a_desc_basic")


def weighted_mean(series: pd.Series, weights: pd.Series) -> float:
    """가중 평균 계산."""
    valid = series.notna() & weights.notna()
    if valid.sum() == 0:
        return np.nan
    return np.average(series[valid], weights=weights[valid])


def weighted_pct(series: pd.Series, weights: pd.Series, value=1) -> float:
    """가중 비율 계산 (이진 변수)."""
    valid = series.notna() & weights.notna()
    if valid.sum() == 0:
        return np.nan
    mask = series[valid] == value
    return np.average(mask, weights=weights[valid]) * 100


def describe_variable(df: pd.DataFrame,
                       var_col: str,
                       weight_col: str,
                       var_label: str,
                       var_type: str = "continuous") -> dict:
    """
    단일 변수 기술통계 계산.

    Args:
        var_type: 'continuous' 또는 'binary' 또는 'categorical'
    """
    if var_col not in df.columns:
        return {"변수": var_label, "비고": "컬럼 없음"}

    if var_type == "continuous":
        w_mean = weighted_mean(df[var_col], df[weight_col])
        sd = df[var_col].std()
        return {
            "변수": var_label,
            "N": df[var_col].notna().sum(),
            "가중평균": round(w_mean, 2) if not np.isnan(w_mean) else "-",
            "SD": round(sd, 2),
            "최소": df[var_col].min(),
            "최대": df[var_col].max(),
        }
    elif var_type == "binary":
        w_pct = weighted_pct(df[var_col], df[weight_col])
        return {
            "변수": var_label,
            "N": df[var_col].notna().sum(),
            "가중비율(%)": round(w_pct, 1) if not np.isnan(w_pct) else "-",
        }
    return {}


def main() -> None:
    log.info("=" * 60)
    log.info("07a_desc_basic: 기술통계 Table 1 생성 시작")
    log.info("=" * 60)

    OUTPUT_TABLES.mkdir(parents=True, exist_ok=True)

    # 완전응답자 데이터 탐색
    candidates = [
        CLEANED_DIR / "KYHPS_STU_preprocessed_CCA.csv",
        CLEANED_DIR / "KYHPS_STU_smoking_flagged.csv",
    ]
    input_path = next((p for p in candidates if p.exists()), None)

    if input_path is None:
        log.error("분석 입력 파일 없음. 05_cleaning 단계 먼저 실행 필요.")
        return

    try:
        df = pd.read_csv(input_path, encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(input_path, encoding="cp949", low_memory=False)

    log.info(f"입력: {input_path.name} | shape={df.shape}")

    # 가중치 컬럼 확인
    weight_col = "w_panel_5yr"
    if weight_col not in df.columns:
        log.warning(f"패널 가중치 컬럼 '{weight_col}' 없음 → 비가중 분석 수행")
        df[weight_col] = 1.0

    # ── 기술통계 계산 (변수명은 실제 데이터에 맞게 수정 필요) ─────────
    log.info("\n변수 목록을 확인하고 아래 변수명을 실제 컬럼명으로 수정하세요:")
    log.info(df.columns.tolist()[:20])  # 처음 20개 컬럼 출력

    # 예시 통계 (실제 변수명 확인 후 수정)
    results = []
    example_vars = {
        "sex":         ("성별(남=1)", "binary"),
        "age_2019":    ("기준연도 연령", "continuous"),
        "smk_current_2019": ("흡연 여부(2019)", "binary"),
    }

    for col, (label, vtype) in example_vars.items():
        stat = describe_variable(df, col, weight_col, label, vtype)
        if stat:
            results.append(stat)

    # 전체 요약
    log.info(f"\n전체 대상자: {len(df):,}명")
    log.info(f"연도별 컬럼 수: {df.shape[1]}")

    # Excel 저장
    if results:
        df_table1 = pd.DataFrame(results)
        out_path = OUTPUT_TABLES / f"table1_descriptive_{date.today()}.xlsx"
        df_table1.to_excel(out_path, index=False)
        log.info(f"\n저장: {out_path}")

    log.info("\n[주의] 변수명은 실제 데이터 컬럼명으로 수정 후 재실행 필요")
    log.info("✅ 07a_desc_basic 완료")


if __name__ == "__main__":
    main()

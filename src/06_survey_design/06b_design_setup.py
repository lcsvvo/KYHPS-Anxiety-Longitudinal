"""
src/06_survey_design/06b_design_setup.py
─────────────────────────────────────────
KYHPS 복합표본설계 객체 설정 및 가중치 적용 유틸리티.

KYHPS 표본설계:
    - 층화 집락 2단계 추출 (Stratified Two-stage Cluster Sampling)
    - 1차 추출 단위: 학교 (school_id)
    - 2차 추출 단위: 학급/개인
    - 층화 변수: 시도 × 학교급
    - 가중치 변수: 연도별 횡단 가중치 + 5개년 패널 가중치

참고: 표본설계 및 분석방법 2부.pdf (docs/codebooks/)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.utils.logger import get_logger
from src.utils.paths import CLEANED_DIR, WEIGHTED_DIR, PANEL_YEARS

log = get_logger("06b_design_setup")


# ── KYHPS 복합표본설계 메타정보 ────────────────────────────────────────
# ※ 실제 변수명은 코드북(docs/codebooks/KYHPS_마스터_코드북.xlsx) 확인 후 수정
DESIGN_META = {
    "weight_cross": {y: f"w_cross_{y}" for y in PANEL_YEARS},  # 연도별 횡단 가중치
    "weight_panel": "w_panel_5yr",       # 5개년 패널 가중치
    "strata_col":   "strata_id",         # 층화 변수 (시도×학교급)
    "cluster_col":  "school_id",         # 1차 추출 단위 (학교)
    "design_type":  "Stratified two-stage cluster sampling",
}


def get_design_meta() -> dict:
    """KYHPS 설계 메타정보 반환."""
    return DESIGN_META.copy()


def apply_weights(df: pd.DataFrame,
                  weight_col: str,
                  normalize: bool = True) -> pd.DataFrame:
    """
    데이터프레임에 가중치 컬럼 유효성 검사 후 정규화 적용.

    Args:
        df: 입력 데이터프레임
        weight_col: 가중치 컬럼명
        normalize: True이면 가중치 합을 표본 크기로 정규화

    Returns:
        가중치 검증 완료 데이터프레임
    """
    if weight_col not in df.columns:
        log.warning(f"가중치 컬럼 없음: {weight_col} → 모두 1로 대체")
        df[weight_col] = 1.0
        return df

    n_missing = df[weight_col].isna().sum()
    if n_missing > 0:
        log.warning(f"가중치 결측: {n_missing}건 → 1.0으로 대체")
        df[weight_col] = df[weight_col].fillna(1.0)

    if normalize:
        n = len(df)
        w_sum = df[weight_col].sum()
        df[weight_col] = df[weight_col] / w_sum * n
        log.info(f"가중치 정규화 완료 (합 → {n:,})")

    log.info(f"가중치 요약: min={df[weight_col].min():.4f} | "
             f"max={df[weight_col].max():.4f} | "
             f"mean={df[weight_col].mean():.4f}")
    return df


def create_statsmodels_design_info(df: pd.DataFrame) -> dict:
    """
    statsmodels WLS / linearmodels PanelOLS 사용을 위한 설계 정보 반환.

    사용 예시:
        design = create_statsmodels_design_info(df)
        model = smf.wls("outcome ~ x1 + x2",
                        data=df,
                        weights=df[design['weight_col']]).fit(
                            cov_type='cluster',
                            cov_kwds={'groups': df[design['cluster_col']]}
                        )
    """
    meta = get_design_meta()
    return {
        "weight_col":  meta["weight_panel"],
        "cluster_col": meta["cluster_col"],
        "strata_col":  meta["strata_col"],
        "note": ("복합표본 분산 추정: cluster-robust SE 사용. "
                 "층화 정보는 단순 군집 SE로 근사 처리."),
    }


def main() -> None:
    log.info("=" * 60)
    log.info("06b_design_setup: 복합표본설계 정보 출력")
    log.info("=" * 60)

    meta = get_design_meta()
    log.info(f"설계 유형: {meta['design_type']}")
    log.info(f"층화 변수: {meta['strata_col']}")
    log.info(f"군집 변수: {meta['cluster_col']}")
    log.info(f"패널 가중치: {meta['weight_panel']}")
    log.info(f"횡단 가중치: {meta['weight_cross']}")

    log.info("\n[중요] 실제 변수명은 코드북 확인 후 DESIGN_META 딕셔너리 수정 필요")
    log.info("참조: docs/codebooks/KYHPS_표본설계_분석방법_2부.pdf")
    log.info("\n✅ 06b_design_setup 완료")


if __name__ == "__main__":
    main()

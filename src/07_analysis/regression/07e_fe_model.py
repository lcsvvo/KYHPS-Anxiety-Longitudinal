"""
src/07_analysis/regression/07e_fe_model.py
───────────────────────────────────────────
Fixed Effects (FE) 패널 모형 추정.

분석 흐름:
    1. Long form 데이터 로드 (pid × year)
    2. 개인 고정 효과 통제 (Within estimator)
    3. Cluster-robust SE 적용 (1차 추출 단위: school_id)
    4. 결과 테이블 저장

의존 패키지:
    pip install linearmodels statsmodels

출력:
    outputs/tables/fe_model_results_YYYY-MM-DD.xlsx
"""

import sys
from pathlib import Path
from datetime import date
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.utils.logger import get_logger
from src.utils.paths import CLEANED_DIR, OUTPUT_TABLES

log = get_logger("07e_fe_model")


def load_long_form(path: Path) -> pd.DataFrame | None:
    """Long form 데이터 로드."""
    if not path.exists():
        log.error(f"파일 없음: {path}")
        return None
    try:
        df = pd.read_csv(path, encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="cp949", low_memory=False)
    log.info(f"Long form 로드: {path.name} | shape={df.shape}")
    return df


def run_fe_model(df: pd.DataFrame,
                 outcome: str,
                 covariates: list[str],
                 entity_col: str = "pid",
                 time_col: str = "year",
                 cluster_col: str = "school_id") -> pd.DataFrame | None:
    """
    linearmodels PanelOLS (Fixed Effects) 모형 추정.

    Args:
        df: Long form 데이터프레임
        outcome: 종속변수 컬럼명
        covariates: 독립변수 목록
        entity_col: 개인 ID 컬럼
        time_col: 연도 컬럼
        cluster_col: 군집 변수 (학교 ID)

    Returns:
        pd.DataFrame: 회귀계수, SE, p-value 테이블
    """
    try:
        from linearmodels.panel import PanelOLS
    except ImportError:
        log.error("linearmodels 미설치. 실행: pip install linearmodels")
        return None

    # 필수 컬럼 확인
    required = [outcome, entity_col, time_col] + covariates
    missing = [c for c in required if c not in df.columns]
    if missing:
        log.error(f"컬럼 없음: {missing}")
        log.info(f"사용 가능 컬럼: {df.columns.tolist()[:30]}")
        return None

    # MultiIndex 설정
    df_panel = df.set_index([entity_col, time_col])

    # 공식 구성
    formula = f"{outcome} ~ {' + '.join(covariates)} + EntityEffects"
    log.info(f"모형 공식: {formula}")

    try:
        model = PanelOLS.from_formula(formula, data=df_panel)

        # Cluster-robust SE
        if cluster_col in df.columns:
            clusters = df.set_index([entity_col, time_col])[cluster_col]
            res = model.fit(cov_type="clustered", cluster_entity=True)
        else:
            log.warning(f"군집 변수 없음: {cluster_col} → 개인 수준 cluster SE 사용")
            res = model.fit(cov_type="clustered", cluster_entity=True)

        log.info(f"\n── FE 모형 결과 ──")
        log.info(f"R² (within): {res.rsquared:.4f}")
        log.info(f"관측치 수: {res.nobs:,}")
        log.info(f"개체 수: {res.entity_info.total:,}")

        # 결과 테이블 정리
        df_result = pd.DataFrame({
            "변수": res.params.index,
            "계수(β)": res.params.values.round(4),
            "표준오차": res.std_errors.values.round(4),
            "t통계량": res.tstats.values.round(3),
            "p값": res.pvalues.values.round(4),
            "95%CI_하한": res.conf_int()["lower"].values.round(4),
            "95%CI_상한": res.conf_int()["upper"].values.round(4),
            "유의성": ["***" if p < 0.001 else "**" if p < 0.01
                       else "*" if p < 0.05 else "†" if p < 0.1 else ""
                       for p in res.pvalues],
        })
        return df_result

    except Exception as e:
        log.error(f"모형 추정 실패: {e}")
        return None


def main() -> None:
    log.info("=" * 60)
    log.info("07e_fe_model: Fixed Effects 패널 모형 시작")
    log.info("=" * 60)

    OUTPUT_TABLES.mkdir(parents=True, exist_ok=True)

    # 입력 파일 탐색 (Long form)
    input_candidates = [
        CLEANED_DIR / "KYHPS_STU_long_cleaned.csv",
        CLEANED_DIR / "KYHPS_STU_preprocessed_CCA.csv",
    ]
    input_path = next((p for p in input_candidates if p.exists()), None)

    if input_path is None:
        log.error("Long form 입력 파일 없음.")
        log.info("필요 파일: data/processed/cleaned/KYHPS_STU_long_cleaned.csv")
        log.info("03_merge 단계에서 Long form 생성 후 재실행 필요.")
        return

    df = load_long_form(input_path)
    if df is None:
        return

    # ── 분석 설정 (실제 변수명으로 수정 필요) ────────────────────────
    log.info("\n[설정] 아래 변수명을 실제 데이터 컬럼명으로 수정하세요:")
    log.info(f"  사용 가능 컬럼: {df.columns.tolist()[:20]}")

    OUTCOME    = "smk_current"          # 종속변수 (흡연 여부)
    COVARIATES = ["age", "sex", "ses"]  # 독립변수 목록
    ENTITY_COL = "pid"
    TIME_COL   = "year"

    df_result = run_fe_model(
        df=df,
        outcome=OUTCOME,
        covariates=COVARIATES,
        entity_col=ENTITY_COL,
        time_col=TIME_COL,
    )

    if df_result is not None:
        out_path = OUTPUT_TABLES / f"fe_model_results_{date.today()}.xlsx"
        df_result.to_excel(out_path, index=False)
        log.info(f"\n결과 저장: {out_path}")
        log.info(df_result.to_string(index=False))

    log.info("\n✅ 07e_fe_model 완료")


if __name__ == "__main__":
    main()

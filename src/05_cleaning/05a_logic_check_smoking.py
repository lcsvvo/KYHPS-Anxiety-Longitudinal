"""
src/05_cleaning/05a_logic_check_smoking.py
───────────────────────────────────────────
흡연 관련 변수의 연도 간 논리 불일치 검출 및 플래그 부여.

논리 규칙 (docs/logic_rules.md 기준):
    RULE_SMK_001: 현재흡연(=1) + 흡연시작연령 결측 → 플래그
    RULE_SMK_002: 비흡연(=0) + 전년도흡연(=1) → 금연 전환 (정상, quit_flag=1)
    RULE_SMK_003: 흡연시작연령 > 현재연령 → 논리 불가, 결측 처리
    RULE_SMK_004: 비흡연이면서 평생흡연량 > 0 → 플래그

입력:
    data/processed/merged/KYHPS_STU_2019_2023_wide.csv

출력:
    data/processed/cleaned/KYHPS_STU_smoking_flagged.csv
    logs/data_quality/smoking_logic_errors_YYYY-MM-DD.csv
"""

import sys
from pathlib import Path
from datetime import date
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.utils.logger import get_logger
from src.utils.paths import MERGED_DIR, CLEANED_DIR, LOG_QUALITY, PANEL_YEARS

log = get_logger("05a_logic_check_smoking")

# ── 흡연 관련 표준 변수명 (variable_map 적용 후 기준) ─────────────────
SMK_CURRENT   = "smk_current"       # 현재 흡연 여부 (0/1)
SMK_START_AGE = "smk_start_age"     # 흡연 시작 연령
SMK_LIFETIME  = "smk_lifetime_amt"  # 평생 흡연량
AGE_COL       = "age"               # 현재 연령


def check_rule_smk_001(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """
    RULE_SMK_001: 현재흡연(=1)이면서 흡연시작연령 결측.
    → data_quality_flag = 'SMK_001'
    """
    errors = []
    c_curr = f"{SMK_CURRENT}_{year}"
    c_age  = f"{SMK_START_AGE}_{year}"

    if c_curr not in df.columns or c_age not in df.columns:
        return pd.DataFrame()

    mask = (df[c_curr] == 1) & (df[c_age].isna())
    flagged = df.loc[mask, ["pid"]].copy()
    flagged["year"]           = year
    flagged["variable"]       = c_age
    flagged["error_type"]     = "logical_inconsistency"
    flagged["original_value"] = np.nan
    flagged["corrected_value"]= "flagged_missing"
    flagged["rule_applied"]   = "RULE_SMK_001"
    flagged["confidence"]     = "high"

    if len(flagged) > 0:
        log.info(f"  RULE_SMK_001 [{year}]: {len(flagged)}건 검출")

    return flagged


def check_rule_smk_003(df: pd.DataFrame, year: int, birth_year: int = 2008) -> pd.DataFrame:
    """
    RULE_SMK_003: 흡연시작연령 > 현재연령 (논리 불가).
    → 흡연시작연령을 NaN 처리
    """
    errors = []
    c_age_smk = f"{SMK_START_AGE}_{year}"
    current_age = year - birth_year  # 코호트 기준 연령 추정

    if c_age_smk not in df.columns:
        return pd.DataFrame()

    mask = df[c_age_smk] > current_age
    flagged = df.loc[mask, ["pid", c_age_smk]].copy()
    flagged["year"]           = year
    flagged["variable"]       = c_age_smk
    flagged["error_type"]     = "impossible_value"
    flagged["original_value"] = flagged[c_age_smk]
    flagged["corrected_value"]= np.nan
    flagged["rule_applied"]   = "RULE_SMK_003"
    flagged["confidence"]     = "high"

    if len(flagged) > 0:
        log.info(f"  RULE_SMK_003 [{year}]: {len(flagged)}건 검출 → 결측 처리")
        df.loc[mask, c_age_smk] = np.nan  # 원본 수정

    return flagged.drop(columns=[c_age_smk])


def main() -> None:
    log.info("=" * 60)
    log.info("05a_logic_check_smoking: 흡연 논리 검증 시작")
    log.info("=" * 60)

    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    LOG_QUALITY.mkdir(parents=True, exist_ok=True)

    # 입력 파일 탐색
    input_path = MERGED_DIR / "KYHPS_STU_2019_2023_wide.csv"
    if not input_path.exists():
        input_path = MERGED_DIR / "KYHPS_STU_5y_wide_final.csv"

    if not input_path.exists():
        log.error("입력 파일 없음. 03_merge 단계 먼저 실행 필요.")
        return

    try:
        df = pd.read_csv(input_path, encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(input_path, encoding="cp949", low_memory=False)

    log.info(f"입력: {input_path.name} | shape={df.shape}")

    # ID 컬럼 확인
    id_col = next((c for c in ["pid", "ID", "id"] if c in df.columns), df.columns[0])
    if "pid" not in df.columns:
        df = df.rename(columns={id_col: "pid"})

    # ── 규칙별 검증 실행 ─────────────────────────────────────────────
    all_errors = []
    for year in PANEL_YEARS:
        log.info(f"\n[{year}년 검증]")
        all_errors.append(check_rule_smk_001(df, year))
        all_errors.append(check_rule_smk_003(df, year))

    df_errors = pd.concat([e for e in all_errors if not e.empty], ignore_index=True)

    # 오류 로그 저장
    if not df_errors.empty:
        log_path = LOG_QUALITY / f"smoking_logic_errors_{date.today()}.csv"
        df_errors.to_csv(log_path, index=False, encoding="utf-8-sig")
        log.info(f"\n오류 로그 저장: {log_path} ({len(df_errors)}건)")
    else:
        log.info("\n논리 오류 없음")

    # 결과 저장
    out_path = CLEANED_DIR / "KYHPS_STU_smoking_flagged.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    log.info(f"저장: {out_path}")

    log.info("\n✅ 05a_logic_check_smoking 완료")


if __name__ == "__main__":
    main()

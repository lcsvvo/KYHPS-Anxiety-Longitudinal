"""
src/04_tracking/04a_label_tracking_status.py
─────────────────────────────────────────────
패널 ID 기준으로 연도별 응답 여부를 확인하고 추적 상태 코드를 부여.

입력:
    data/processed/merged/KYHPS_STU_2019_2023_wide.csv  (또는 harmonized 완료본)

출력:
    data/processed/tracking/KYHPS_STU_tracking_status.csv
    data/processed/tracking/KYHPS_STU_complete_case_IDs.csv

추적 상태 코드:
    COMPLETE_5YR   : 5개년 전부 응답 (핵심 분석 대상)
    PARTIAL_4YR    : 4개년 응답 (1회 누락)
    PARTIAL_3YR    : 3개년 응답 (2회 누락)
    ATTRITION_EARLY: 2021 이전 탈락
    ATTRITION_LATE : 2022 이후 탈락
    LATE_ENTRY     : 2020 이후 신규 참여
    INVALID        : 주요 변수 결측 과다
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.utils.logger import get_logger
from src.utils.paths import MERGED_DIR, TRACKING_DIR, PANEL_YEARS

log = get_logger("04a_label_tracking_status")

# 추적 상태 코드 정의
TRACKING_STATUS = {
    "COMPLETE_5YR":    "5개년 완전응답자 (2019~2023 모두 응답)",
    "PARTIAL_4YR":     "4개년 응답 (1회 누락)",
    "PARTIAL_3YR":     "3개년 응답 (2회 누락)",
    "ATTRITION_EARLY": "2021 이전 탈락",
    "ATTRITION_LATE":  "2022 이후 탈락",
    "LATE_ENTRY":      "2020 이후 신규 참여",
    "INVALID":         "주요 변수 결측 과다로 제외",
}


def detect_id_column(df: pd.DataFrame) -> str:
    """패널 ID 컬럼 자동 탐지."""
    candidates = ["pid", "ID", "id", "패널ID", "panel_id", "응답자ID"]
    for c in candidates:
        if c in df.columns:
            return c
    # 첫 번째 컬럼을 ID로 간주
    log.warning(f"ID 컬럼 자동 탐지 실패 → 첫 번째 컬럼 사용: {df.columns[0]}")
    return df.columns[0]


def detect_year_response_columns(df: pd.DataFrame) -> dict[int, str | None]:
    """
    Wide form에서 연도별 응답 여부를 나타내는 컬럼 탐지.
    '_YYYY' 패턴 컬럼이 존재하면 해당 연도 응답 확인 가능.
    """
    year_cols = {}
    for year in PANEL_YEARS:
        # 해당 연도 접미사를 가진 컬럼 존재 여부 확인
        yr_cols = [c for c in df.columns if str(year) in c]
        year_cols[year] = yr_cols[0] if yr_cols else None
    return year_cols


def assign_tracking_status(row: pd.Series, resp_cols: list[str]) -> tuple[str, int, int | None]:
    """
    개별 응답자의 추적 상태를 결정.

    Returns:
        (status_code, n_responses, dropout_year)
    """
    responses = [1 if pd.notna(row.get(c)) else 0 for c in resp_cols]
    n_resp = sum(responses)
    years = PANEL_YEARS

    # 탈락 연도 탐지 (첫 번째 결측 이후 모두 결측인 경우)
    dropout_year = None
    for i, (resp, year) in enumerate(zip(responses, years)):
        if resp == 0 and all(r == 0 for r in responses[i:]):
            dropout_year = year
            break

    # 상태 코드 결정
    if n_resp == 5:
        return "COMPLETE_5YR", n_resp, None
    elif n_resp == 4:
        return "PARTIAL_4YR", n_resp, dropout_year
    elif n_resp == 3:
        return "PARTIAL_3YR", n_resp, dropout_year
    elif responses[0] == 0 and responses[1] == 0:
        return "LATE_ENTRY", n_resp, None
    elif dropout_year and dropout_year <= 2021:
        return "ATTRITION_EARLY", n_resp, dropout_year
    elif dropout_year and dropout_year >= 2022:
        return "ATTRITION_LATE", n_resp, dropout_year
    else:
        return "INVALID", n_resp, None


def main() -> None:
    log.info("=" * 60)
    log.info("04a_label_tracking_status: 추적 상태 라벨링 시작")
    log.info("=" * 60)

    TRACKING_DIR.mkdir(parents=True, exist_ok=True)

    # 입력 파일 탐색 (wide form 우선)
    input_candidates = [
        MERGED_DIR / "KYHPS_STU_2019_2023_wide.csv",
        MERGED_DIR / "KYHPS_STU_5y_wide_final.csv",
    ]
    input_path = next((p for p in input_candidates if p.exists()), None)

    if input_path is None:
        log.error("입력 파일 없음. data/processed/merged/ 확인 필요.")
        return

    log.info(f"입력 파일: {input_path.name}")

    try:
        df = pd.read_csv(input_path, encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(input_path, encoding="cp949", low_memory=False)

    log.info(f"로드 완료 | shape={df.shape}")

    id_col = detect_id_column(df)
    year_col_map = detect_year_response_columns(df)

    log.info(f"ID 컬럼: {id_col}")
    log.info(f"연도별 대표 컬럼: {year_col_map}")

    resp_cols = [v for v in year_col_map.values() if v is not None]

    if not resp_cols:
        log.error("연도별 응답 컬럼 탐지 실패. 수동으로 variable_map 설정 필요.")
        return

    # 추적 상태 라벨링
    results = []
    for _, row in df.iterrows():
        status, n_resp, dropout_yr = assign_tracking_status(row, resp_cols)
        results.append({
            "pid": row[id_col],
            **{f"resp_{y}": (1 if pd.notna(row.get(c)) else 0)
               for y, c in year_col_map.items() if c},
            "n_responses": n_resp,
            "track_status": status,
            "is_complete": status == "COMPLETE_5YR",
            "dropout_year": dropout_yr,
        })

    df_tracking = pd.DataFrame(results)

    # 요약 출력
    log.info("\n── 추적 상태 분포 ──")
    for status, desc in TRACKING_STATUS.items():
        n = (df_tracking["track_status"] == status).sum()
        pct = n / len(df_tracking) * 100
        log.info(f"  {status:20s}: {n:5,}명 ({pct:5.1f}%) | {desc}")

    # 저장
    out_tracking = TRACKING_DIR / "KYHPS_STU_tracking_status.csv"
    df_tracking.to_csv(out_tracking, index=False, encoding="utf-8-sig")
    log.info(f"\n저장: {out_tracking}")

    # 완전응답자 ID 목록
    df_complete = df_tracking[df_tracking["is_complete"]][["pid"]]
    out_complete = TRACKING_DIR / "KYHPS_STU_complete_case_IDs.csv"
    df_complete.to_csv(out_complete, index=False, encoding="utf-8-sig")
    log.info(f"저장: {out_complete} ({len(df_complete):,}명)")

    log.info("\n✅ 04a_label_tracking_status 완료")


if __name__ == "__main__":
    main()

"""
src/01_intake/01a_load_raw.py
──────────────────────────────
KYHPS 원시 CSV 데이터 로드 및 기본 검증.

실행:
    python src/01_intake/01a_load_raw.py

출력:
    콘솔/로그에 각 연도별 shape, 컬럼 수, 기본 결측 요약 출력.
    실제 파일 저장은 하지 않음 (raw → harmonized는 02단계에서 수행).
"""

import sys
from pathlib import Path
import pandas as pd

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.utils.logger import get_logger
from src.utils.paths import RAW_STUDENT, RAW_PARENT, PANEL_YEARS

log = get_logger("01a_load_raw")


def load_year(subject: str, year: int) -> pd.DataFrame:
    """
    단일 연도 원시 CSV 로드.

    Args:
        subject: 'student' 또는 'parent'
        year: 연도 (예: 2019)

    Returns:
        pd.DataFrame: 로드된 원시 데이터
    """
    base = RAW_STUDENT if subject == "student" else RAW_PARENT
    file_name = f"KYHPS_{'STU' if subject == 'student' else 'PAR'}_{year}_raw.csv"
    path = base / str(year) / file_name

    if not path.exists():
        log.warning(f"파일 없음: {path}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(path, encoding="utf-8", low_memory=False)
        log.info(f"[{subject.upper()} {year}] 로드 완료 | shape={df.shape}")
        return df
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="cp949", low_memory=False)
        log.info(f"[{subject.upper()} {year}] CP949 인코딩으로 로드 | shape={df.shape}")
        return df


def summarize(df: pd.DataFrame, label: str) -> None:
    """데이터 기본 요약 출력."""
    if df.empty:
        return
    missing_pct = df.isnull().mean().mean() * 100
    log.info(f"  {label} | 행={len(df):,} | 열={df.shape[1]} | 전체결측={missing_pct:.1f}%")


def main() -> None:
    log.info("=" * 60)
    log.info("01a_load_raw: KYHPS 원시 데이터 로드 시작")
    log.info("=" * 60)

    for subject in ["student", "parent"]:
        log.info(f"\n── {subject.upper()} 데이터 ──")
        for year in PANEL_YEARS:
            df = load_year(subject, year)
            summarize(df, f"{subject.upper()} {year}")

    log.info("\n✅ 01a_load_raw 완료")


if __name__ == "__main__":
    main()

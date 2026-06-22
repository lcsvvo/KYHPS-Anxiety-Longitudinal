"""
# utils.py

목적:
    모든 분석 스크립트가 공통으로 import하는 유틸리티 모음.
    코드 중복 제거 및 일관성 보장.

역할:
    - 프로젝트 루트 / 데이터 / 출력 경로 상수 정의
    - 로거 초기화
    - CSV 인코딩 자동 감지 로더
    - 우울 궤적 집단 레이블 부여
    - Cohen's d / 효과크기 레이블 계산
    - matplotlib 한글 폰트 설정 (Windows 기준)

입력:
    없음 (다른 스크립트에서 import)

출력:
    없음 (함수·상수 제공)

주의:
    - 이 파일은 단독 실행용이 아니라 import 전용임
    - 경로는 이 파일 위치(scripts/)를 기준으로 자동 계산
    - 로컬 환경에 따라 한글 폰트 이름이 다를 수 있음
      (Windows: 'Malgun Gothic', Mac: 'AppleGothic')
"""

import logging
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ──────────────────────────────────────────────────────────────────────────────
# 경로 상수 정의
#
# WHY: 경로를 상수로 중앙화하면 데이터 이동 시 한 곳만 수정하면 됨.
#      __file__을 기준으로 계산하므로 스크립트 실행 위치와 무관하게 동작.
# ──────────────────────────────────────────────────────────────────────────────

# 이 파일(scripts/utils.py)의 상위 디렉터리 = 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 데이터 경로
DATA_RAW_STUDENT = PROJECT_ROOT / "data" / "raw" / "student"
DATA_PROCESSED   = PROJECT_ROOT / "data" / "processed"
DATA_CLEANED     = DATA_PROCESSED / "cleaned"
DATA_MERGED      = DATA_PROCESSED / "merged"

# 주요 분석 데이터 파일 경로
WIDE_CSV = DATA_CLEANED / "KYHPS_STU_analysis_wide.csv"
LONG_CSV = DATA_CLEANED / "KYHPS_STU_analysis_long.csv"

# 출력 경로
OUTPUT_DIR  = PROJECT_ROOT / "outputs"
FIG_DIR     = OUTPUT_DIR / "figures"
TABLE_DIR   = OUTPUT_DIR / "tables"
LOG_DIR     = OUTPUT_DIR / "logs"

# 설정 경로
CONFIG_DIR  = PROJECT_ROOT / "config"

# 출력 폴더 없으면 자동 생성
for _d in [FIG_DIR, TABLE_DIR, LOG_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# 연도 / 웨이브 상수
# ──────────────────────────────────────────────────────────────────────────────

YEARS  = [2019, 2020, 2021, 2022, 2023]
WAVES  = ["w1", "w2", "w3", "w4", "w5"]

# WHY: year↔wave 매핑을 딕셔너리로 제공해 루프에서 편리하게 사용
YEAR_TO_WAVE = dict(zip(YEARS, WAVES))
WAVE_TO_YEAR = dict(zip(WAVES, YEARS))

# 분석 대상 변수 목록 (prefix 기준)
VAR_PREFIXES = [
    "smartphone",
    "sleep",
    "physical_activity",
    "fastfood",
    "stress_academic",
    "depression",
]

# 변수별 한글 레이블 (그래프 제목용)
VAR_LABELS = {
    "smartphone":       "스마트폰 이용시간 (순위형 1-9)",
    "sleep":            "수면시간 (순위형 1-8)",
    "physical_activity":"신체활동 빈도 (일/주)",
    "fastfood":         "패스트푸드 섭취 빈도",
    "stress_academic":  "학업 스트레스",
    "depression":       "우울감 경험 (비율)",
}


# ──────────────────────────────────────────────────────────────────────────────
# 로거 초기화
# ──────────────────────────────────────────────────────────────────────────────

def get_logger(script_name: str) -> logging.Logger:
    """
    파일 + 콘솔에 동시 출력하는 로거 반환.

    Parameters
    ----------
    script_name : str
        로그 파일명에 사용할 스크립트 이름 (예: "eda_pipeline")

    Returns
    -------
    logging.Logger

    WHY: 실행 시각·스크립트명·레벨을 로그에 남겨 디버깅을 쉽게 하기 위함.
         results 재현 시 "언제 무엇을 실행했는지" 추적 가능.
    """
    log_file = LOG_DIR / f"{date.today()}_{script_name}.log"

    logger = logging.getLogger(script_name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:          # 중복 핸들러 방지
        return logger

    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    # 파일 핸들러
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # 콘솔 핸들러
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


# ──────────────────────────────────────────────────────────────────────────────
# CSV 로더 (인코딩 자동 감지)
# ──────────────────────────────────────────────────────────────────────────────

def load_csv(path: Path, **kwargs) -> pd.DataFrame:
    """
    UTF-8 → CP949(EUC-KR) 순으로 인코딩 시도하여 CSV 로드.

    Parameters
    ----------
    path : Path
        CSV 파일 경로
    **kwargs :
        pd.read_csv에 전달할 추가 인자

    Returns
    -------
    pd.DataFrame

    WHY: KYHPS 원시 데이터 일부가 CP949로 저장되어 있어
         encoding 오류 없이 로드하기 위한 방어 코드.
    """
    for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr"):
        try:
            df = pd.read_csv(path, encoding=enc, **kwargs)
            return df
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError(f"[load_csv] 지원 인코딩으로 로드 실패: {path}")


# ──────────────────────────────────────────────────────────────────────────────
# 우울 궤적 집단 정의
# ──────────────────────────────────────────────────────────────────────────────

def assign_dep_group(row: pd.Series) -> str:
    """
    개인의 w1(2019), w5(2023) 우울 여부로 궤적 집단 레이블 부여.

    집단 정의:
        Stable     : w1=0, w5=0  (지속 비우울)
        Onset      : w1=0, w5=1  (신규 발생)  ← 핵심 분석 집단
        Recovery   : w1=1, w5=0  (회복)
        Persistent : w1=1, w5=1  (지속 우울)
        Missing    : w1 또는 w5 결측

    Parameters
    ----------
    row : pd.Series
        wide form 데이터의 한 행 (depression_w1, depression_w5 컬럼 필요)

    WHY: w1과 w5만 사용하는 이유는 "5년 전체 변화" 방향을 명확하게
         정의하기 위함. 중간 파동(w2-w4)은 안정성 검토 시 별도 분석.
    """
    w1 = row.get("depression_w1")
    w5 = row.get("depression_w5")

    if pd.isna(w1) or pd.isna(w5):
        return "Missing"
    if w1 == 0 and w5 == 0:
        return "Stable"
    if w1 == 0 and w5 == 1:
        return "Onset"
    if w1 == 1 and w5 == 0:
        return "Recovery"
    if w1 == 1 and w5 == 1:
        return "Persistent"
    return "Unknown"


def add_dep_group_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    wide form 데이터프레임에 dep_group 컬럼 추가.

    Parameters
    ----------
    df : pd.DataFrame
        depression_w1, depression_w5 컬럼이 있는 wide form DF

    Returns
    -------
    pd.DataFrame (복사본)
    """
    df = df.copy()
    df["dep_group"] = df.apply(assign_dep_group, axis=1)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# 통계 유틸리티
# ──────────────────────────────────────────────────────────────────────────────

def cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
    """
    독립 두 집단의 Cohen's d (pooled SD 기준) 계산.

    Parameters
    ----------
    group1, group2 : np.ndarray
        결측 제거된 수치형 배열

    Returns
    -------
    float  (group1 - group2 방향; 양수 = group1이 큼)

    WHY: t 검정의 p값만으로는 표본이 클 때 무의미한 차이도 유의해짐.
         Cohen's d로 실질적 효과 크기를 별도 보고해야 논문 신뢰도 높아짐.
    """
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return np.nan
    var1 = np.var(group1, ddof=1)
    var2 = np.var(group2, ddof=1)
    pooled_sd = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_sd == 0:
        return np.nan
    return float((np.mean(group1) - np.mean(group2)) / pooled_sd)


def effect_size_label(d: float) -> str:
    """
    Cohen's d 절댓값을 언어적 레이블로 변환.

    기준 (Cohen, 1988):
        |d| < 0.2  → trivial
        0.2 ≤ |d| < 0.5 → small
        0.5 ≤ |d| < 0.8 → medium
        |d| ≥ 0.8  → large
    """
    if pd.isna(d):
        return "N/A"
    d = abs(d)
    if d < 0.2:
        return "trivial"
    if d < 0.5:
        return "small"
    if d < 0.8:
        return "medium"
    return "large"


def sig_stars(p: float) -> str:
    """p값 → 유의성 별표 변환."""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "n.s."


# ──────────────────────────────────────────────────────────────────────────────
# matplotlib 한글 폰트 설정
# ──────────────────────────────────────────────────────────────────────────────

def set_korean_font() -> bool:
    """
    Windows / Mac / Linux 환경에서 한글 폰트를 자동으로 설정.

    Returns
    -------
    bool : 한글 폰트 설정 성공 여부

    WHY: matplotlib 기본 폰트는 CJK 문자를 지원하지 않아
         한글이 □□□□로 깨짐. 환경별 폰트를 순서대로 시도.

    실패 시:
         영문 레이블을 대신 사용하는 것이 안전 (깨진 그래프보다 낫다).
    """
    candidates = [
        "Malgun Gothic",    # Windows
        "AppleGothic",      # Mac
        "NanumGothic",      # Linux (설치 시)
        "DejaVu Sans",      # fallback (한글 불가, 깨짐 없음)
    ]

    available_fonts = {f.name for f in fm.fontManager.ttflist}

    for font in candidates:
        if font in available_fonts:
            matplotlib.rcParams["font.family"] = font
            matplotlib.rcParams["axes.unicode_minus"] = False
            return font != "DejaVu Sans"   # DejaVu이면 한글 불가

    # 마지막 수단: 시스템에서 한글 폰트 파일 직접 탐색
    import platform
    if platform.system() == "Windows":
        font_path = Path("C:/Windows/Fonts/malgun.ttf")
        if font_path.exists():
            fm.fontManager.addfont(str(font_path))
            matplotlib.rcParams["font.family"] = "Malgun Gothic"
            matplotlib.rcParams["axes.unicode_minus"] = False
            return True

    return False


# ──────────────────────────────────────────────────────────────────────────────
# 2019 연속형 → 순위형 변환 함수
#
# WHY: 2019년 스마트폰/수면 데이터는 '시간' 단위 연속형인 반면
#      2020–2023년은 1–9 / 1–8 순위형 범주.
#      비교 가능하게 만들기 위해 2019 연속형을 동일 범주 구간으로 변환.
#      단, 이 변환은 정보 손실을 수반하므로 '방법론적 한계'로 반드시 명시.
# ──────────────────────────────────────────────────────────────────────────────

def continuous_to_ordinal_smartphone(hours: float) -> int:
    """
    2019년 스마트폰 사용 시간(연속, 단위: 시간) → 1–9 순위형 변환.

    구간 기준 (2020년 설문 선택지와 매핑):
        1: 30분 미만
        2: 30분–1시간 미만
        3: 1–2시간 미만
        4: 2–3시간 미만
        5: 3–4시간 미만
        6: 4–5시간 미만
        7: 5–6시간 미만
        8: 6–7시간 미만
        9: 7시간 이상
    """
    if pd.isna(hours):
        return np.nan
    if hours < 0.5:  return 1
    if hours < 1.0:  return 2
    if hours < 2.0:  return 3
    if hours < 3.0:  return 4
    if hours < 4.0:  return 5
    if hours < 5.0:  return 6
    if hours < 6.0:  return 7
    if hours < 7.0:  return 8
    return 9


def continuous_to_ordinal_sleep(hours: float) -> int:
    """
    2019년 수면 시간(연속, 단위: 시간) → 1–8 순위형 변환.

    구간 기준 (2020년 설문 선택지와 매핑):
        1: 5시간 미만
        2: 5시간–6시간 미만
        3: 6–7시간 미만
        4: 7–8시간 미만
        5: 8–9시간 미만
        6: 9–10시간 미만
        7: 10–11시간 미만
        8: 11시간 이상
    """
    if pd.isna(hours):
        return np.nan
    if hours < 5.0:   return 1
    if hours < 6.0:   return 2
    if hours < 7.0:   return 3
    if hours < 8.0:   return 4
    if hours < 9.0:   return 5
    if hours < 10.0:  return 6
    if hours < 11.0:  return 7
    return 8


# ──────────────────────────────────────────────────────────────────────────────
# 모듈 단독 실행 시 경로 상태 출력 (디버깅용)
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger = get_logger("utils_check")
    logger.info(f"PROJECT_ROOT : {PROJECT_ROOT}")
    logger.info(f"WIDE_CSV     : {WIDE_CSV}  (exists={WIDE_CSV.exists()})")
    logger.info(f"LONG_CSV     : {LONG_CSV}  (exists={LONG_CSV.exists()})")
    logger.info(f"FIG_DIR      : {FIG_DIR}  (exists={FIG_DIR.exists()})")
    logger.info(f"TABLE_DIR    : {TABLE_DIR}  (exists={TABLE_DIR.exists()})")

    ok = set_korean_font()
    logger.info(f"한글 폰트 설정 성공: {ok}")

    # 데이터 파일 존재 여부 확인
    for path, name in [(WIDE_CSV, "wide"), (LONG_CSV, "long")]:
        if path.exists():
            df_test = load_csv(path, nrows=3)
            logger.info(f"[{name}] 로드 성공: {df_test.shape}")
        else:
            logger.warning(f"[{name}] 파일 없음: {path}")

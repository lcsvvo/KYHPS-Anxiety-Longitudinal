"""
src/utils/paths.py
──────────────────
프로젝트 경로 상수 정의.
모든 스크립트에서 이 모듈을 통해 경로를 참조한다.
절대 경로를 하드코딩하지 말 것.
"""

from pathlib import Path

# ── 프로젝트 루트 (이 파일 위치 기준 2단계 상위) ──────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ── Data 레이어 ───────────────────────────────────────────────────────
RAW_DIR          = PROJECT_ROOT / "data" / "raw"
RAW_STUDENT      = RAW_DIR / "student"
RAW_PARENT       = RAW_DIR / "parent"

PROCESSED_DIR    = PROJECT_ROOT / "data" / "processed"
HARMONIZED_DIR   = PROCESSED_DIR / "harmonized"
MERGED_DIR       = PROCESSED_DIR / "merged"
TRACKING_DIR     = PROCESSED_DIR / "tracking"
CLEANED_DIR      = PROCESSED_DIR / "cleaned"
WEIGHTED_DIR     = PROCESSED_DIR / "weighted"

# ── 설정 파일 ─────────────────────────────────────────────────────────
CONFIG_DIR       = PROJECT_ROOT / "src" / "00_config"
VARMAP_STUDENT   = CONFIG_DIR / "variable_map_student.yaml"
VARMAP_PARENT    = CONFIG_DIR / "variable_map_parent.yaml"

# ── 로그 ─────────────────────────────────────────────────────────────
LOG_PIPELINE     = PROJECT_ROOT / "logs" / "pipeline"
LOG_QUALITY      = PROJECT_ROOT / "logs" / "data_quality"
LOG_AI           = PROJECT_ROOT / "logs" / "ai_sessions"

# ── 산출물 ───────────────────────────────────────────────────────────
OUTPUT_TABLES    = PROJECT_ROOT / "outputs" / "tables"
OUTPUT_FIGURES   = PROJECT_ROOT / "outputs" / "figures"

# ── 연도 범위 ─────────────────────────────────────────────────────────
PANEL_YEARS      = list(range(2019, 2024))  # 2019~2023
COMPLETE_N_YEARS = 5                         # 완전응답자 기준 연도 수


def ensure_dirs() -> None:
    """필수 출력 디렉토리를 모두 생성."""
    for d in [LOG_PIPELINE, LOG_QUALITY, MERGED_DIR,
              TRACKING_DIR, CLEANED_DIR, WEIGHTED_DIR,
              OUTPUT_TABLES, OUTPUT_FIGURES]:
        d.mkdir(parents=True, exist_ok=True)

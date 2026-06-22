"""
src/utils/logger.py
───────────────────
KYHPS 파이프라인 공통 로거.
모든 스크립트에서 get_logger()를 import하여 사용.
"""

import logging
import sys
from datetime import date
from pathlib import Path


def get_logger(script_name: str, log_dir: str = "logs/pipeline") -> logging.Logger:
    """
    표준화된 파이프라인 로거 반환.

    Args:
        script_name: 스크립트 식별자 (예: '01a_load_raw')
        log_dir: 로그 저장 디렉토리 (기본: logs/pipeline/)

    Returns:
        logging.Logger: 파일 + 콘솔 동시 출력 로거
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    log_file = log_path / f"{date.today()}_{script_name}.log"

    logger = logging.getLogger(script_name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger  # 중복 핸들러 방지

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 파일 핸들러
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)

    # 콘솔 핸들러
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger

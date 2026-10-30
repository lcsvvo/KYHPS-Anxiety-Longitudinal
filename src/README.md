# Source

**자료 처리와 보조 분석**의 단계별 코드 안내. 핵심 모형은 [Scripts](../scripts/README.md)에 위치.

| Folder | Content |
|---|---|
| `00_config/` | 차수별 변수 매핑 |
| `01_intake/` | 자료 로드, 값 라벨과 코드북 생성 |
| `02_harmonize/`, `03_merge/` | 현재 `__init__.py`만 포함, 독립 조화 및 병합 모듈 미포함 |
| `04_tracking/` | 응답 및 탈락 상태 분류 |
| `05_cleaning/` | 논리 불일치 처리 |
| `06_survey_design/` | 조사 설계 설정 |
| `07_analysis/` | 기술통계, FE 모형, 선택편향 보조 분석 |
| `08_visualization/` | 요약 엑셀 생성 |
| `utils/` | 경로와 로깅 공통 함수 |

- 결측 처리 구현은 [Preprocessing Notebook](../notebooks/EXP004_preprocessing.ipynb) 참조
- **원자료부터 패널 구성까지의 전체 자동 실행은 미지원**
- 자료 배치는 [Data](../data/README.md), 실행 절차는 [Reproduction](../docs/reproduce.md) 참조

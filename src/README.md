# `src/` — 번호순 재현 파이프라인

원자료(KYHPS W1–W5)를 분석용 패널로 만드는 **intake → tracking → cleaning → analysis** 단계를 번호순으로 담는다. 실제 **모형 추정과 결과표·그림 생성은 [`scripts/`](../scripts/README.md)** 에서 이뤄진다.

## 단계 구성 및 현재 포함 범위

| 단계 | 폴더 | 역할 | 저장소 포함 상태 |
|---|---|---|---|
| 00 | `00_config/` | 변수 매핑(`variable_map_*.yaml`), 설계 메타데이터 | 포함 |
| 01 | `01_intake/` | 원자료 로드 · 값 라벨 추출 · 마스터 코드북 · 구조 점검 | 포함 (`01a`,`01c`,`01d`,`01e`) |
| 02 | `02_harmonize/` | 차수 간 변수명 조화 | **`__init__.py`만** — 아래 주 참조 |
| 03 | `03_merge/` | wide + long complete-case 패널 병합 | **`__init__.py`만** — 아래 주 참조 |
| 04 | `04_tracking/` | 응답·탈락 추적 상태 라벨링 | 포함 (`04a`) |
| 05 | `05_cleaning/` | 논리 불일치 점검(흡연) 등 | 포함 (`05a`) — 결측 전처리는 아래 주 참조 |
| 06 | `06_survey_design/` | 가중치·층화·군집 설계 셋업 | 포함 (`06b`) |
| 07 | `07_analysis/` | 기술통계 · FE 회귀 · 선택편향 검정 | 포함 (`07a`,`07e`,`07i`) |
| 08 | `08_visualization/` | 요약 엑셀 빌드 | 포함 (`08`) |
| — | `utils/` | 경로(`paths.py`)·로깅(`logger.py`) 공용 모듈 | 포함 |

## 정직한 범위 주석 (Scope notes)

- **02_harmonize · 03_merge 는 현재 `__init__.py`만 포함**한다. 차수 조화·병합 로직은 분석 당시 탐색 노트북 단계에서 수행됐고, 독립 파이프라인 모듈로는 이 공개 저장소에 포함되지 않았다. 따라서 원자료로부터의 패널 재구성은 이 저장소만으로는 완결되지 않는다(한계).
- **결측 전처리(CCA / LOCF / MICE / RevLOCF)** 는 `05_cleaning`의 스크립트가 아니라 [`notebooks/EXP004_preprocessing.ipynb`](../notebooks/EXP004_preprocessing.ipynb)에 구현돼 있으며, 그 민감도 결과는 `results/tables/robustness_mice_vs_cca.xlsx`로 연결된다.
- **핵심 모형(Mundlak within–between)은 `src/07_analysis`가 아니라 [`scripts/depression_panel_v2.py`](../scripts/depression_panel_v2.py)에 있다.** `src/07_analysis/regression/07e_fe_model.py`는 FE 모형 보조 구현이다.

> 요컨대 `src/`는 intake·전처리·보조분석의 재현 골격이고, 논문 헤드라인 분석의 정본 코드는 `scripts/`에 있다.

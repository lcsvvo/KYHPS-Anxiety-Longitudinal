# `notebooks/` — 탐색 EDA · 전처리

원자료(KYHPS W1–W5)를 분석 패널로 만들기 전 단계의 탐색·전처리 노트북. 논문 정본 분석은 여기 없고 [`scripts/`](../scripts/README.md)에 있다.

## 노트북 구성

| 노트북 | 역할 | 연결 |
|---|---|---|
| `EXP002_data_structure_inspection.ipynb` | W1–W5 원자료 구조·기초통계 점검 | → [`src/01_intake`](../src/README.md) |
| `EXP003_tracking_label.ipynb` | 응답·탈락 추적 상태 레이블링 탐색 | → [`src/04_tracking`](../src/README.md) |
| `EXP004_preprocessing.ipynb` | 결측 대치(CCA · LOCF · RevLOCF · MICE) 구현·민감도 | → [`results/tables/robustness_mice_vs_cca.xlsx`](../results/tables) |

## 기술 스택

| 구분 | 도구 |
|---|---|
| 데이터 처리 | pandas, numpy |
| 통계 점검 | scipy (stats) |
| 결측 대치 | scikit-learn — IterativeImputer · BayesianRidge(MICE), StandardScaler |
| 추적 탐색 | scikit-learn — LogisticRegression |

## 동작 원리

- 구조 점검(EXP002). pandas로 W1–W5 원자료를 로드하고 변수·분포·기초통계를 scipy로 확인.
- 추적 레이블(EXP003). 응답·탈락 패턴을 표준화 + 로지스틱 회귀로 탐색해 추적 상태를 레이블링.
- 결측 대치(EXP004). CCA · LOCF · RevLOCF · MICE(IterativeImputer+BayesianRidge)를 비교하고 민감도를 `robustness_mice_vs_cca.xlsx`로 연결.

## 역할 분담

- 루트 [`README.md`](../README.md): 연구 질문·방법·결과 서사.
- 이 폴더: 위 서사 이전의 탐색·전처리 노트북 지도.
- 정본 모형(Mundlak within–between)은 [`scripts/`](../scripts/README.md), 재현 골격은 [`src/`](../src/README.md).

> 원자료는 승인 기반 제한자료로 미포함. 배치 안내는 [`data/README.md`](../data/README.md).

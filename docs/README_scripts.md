# KYHPS 분석 스크립트 실행 가이드

> 제1회 청소년건강패널조사(KYHPS) 공모전 분석 프로젝트  
> Python 재현 가능 분석 환경 — VS Code에서 직접 실행·수정·디버깅 가능

---

## 프로젝트 구조

```
제1회 청소년건강패널조사/
├── scripts/
│   ├── utils.py            ← [공통] 경로·함수·상수 (다른 파일이 import)
│   ├── eda_pipeline.py     ← [1단계] 전체 EDA (결측, 추이, 스파게티, 집단 분포)
│   ├── onset_analysis.py   ← [2단계] Onset vs Stable 집단 비교 + 이중 악화 집단
│   └── panel_ols.py        ← [3단계] 패널 OLS·Fixed Effects 회귀분석
│
├── data/
│   └── processed/cleaned/
│       ├── KYHPS_STU_analysis_wide.csv   ← 5,051 × 39 (분석용 wide form)
│       └── KYHPS_STU_analysis_long.csv   ← 25,255 × 11 (분석용 long form)
│
├── outputs/
│   ├── figures/            ← PNG 그래프 저장
│   ├── tables/             ← XLSX 테이블 저장
│   └── logs/               ← 실행 로그 저장
│
├── config/
│   └── variable_map.yaml   ← 변수명 매핑 (null 채워야 함)
│
├── requirements.txt        ← 패키지 목록
└── README_scripts.md       ← 이 파일
```

---

## 빠른 시작

### 1. 가상환경 생성 (권장)

```powershell
# PowerShell / VS Code 터미널
cd "C:\Users\jiwoo\OneDrive\Desktop\나\3학년\제1회 청소년건강패널조사"

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

### 2. 실행 순서 (반드시 이 순서로)

```powershell
# 현재 디렉터리: 프로젝트 루트 (위 cd 명령 이후)

# [1단계] EDA 전체 파이프라인
python scripts/eda_pipeline.py

# [2단계] Onset vs Stable 집단 비교 + 이중 악화 집단
python scripts/onset_analysis.py

# [3단계] 패널 회귀분석 (Fixed Effects 포함)
python scripts/panel_ols.py
```

> **중요**: `eda_pipeline.py`가 먼저 실행되어야 하는 건 아니지만,  
> 분석 흐름 이해를 위해 순서대로 실행 권장.

---

## 파일별 상세 설명

### `scripts/utils.py`

| 항목 | 내용 |
|------|------|
| 역할 | 다른 스크립트가 `import`하는 공통 함수·상수 모음 |
| 단독 실행 | `python scripts/utils.py` → 경로 존재 여부 확인 |
| 입력 | 없음 |
| 출력 | 없음 (함수·상수 제공) |
| 주요 내용 | 경로 상수, 로거, load_csv, add_dep_group_column, cohens_d, set_korean_font |

---

### `scripts/eda_pipeline.py`

| 항목 | 내용 |
|------|------|
| 역할 | 전체 EDA 파이프라인 — 데이터 구조 파악부터 집단 분포까지 |
| 입력 | `KYHPS_STU_analysis_wide.csv`, `KYHPS_STU_analysis_long.csv` |
| 출력 (figures) | `fig01_mean_trend_6vars.png`, `fig02_spaghetti_6vars.png`, `fig03_gender_subgroup.png`, `fig04_change_score_dist.png`, `fig11_depression_group_dist.png` |
| 출력 (tables) | `mean_trend_by_year.xlsx`, `missing_summary.xlsx`, `change_score_summary.xlsx`, `depression_group_dist.xlsx` |

**함수 목록 및 역할:**

| 함수 | 역할 |
|------|------|
| `load_data()` | wide/long CSV 로드 |
| `describe_structure()` | 컬럼·기술통계 콘솔 출력 |
| `analyze_missing()` | 결측 건수·비율 집계 |
| `compute_mean_trends()` | 연도별 평균·SD 계산 |
| `plot_mean_trends()` | 추이 그래프 저장 |
| `plot_spaghetti()` | 개인 궤적 스파게티 플롯 |
| `plot_gender_subgroup()` | 성별 하위집단 추이 |
| `plot_change_score_distribution()` | 변화 점수 히스토그램 |
| `analyze_depression_groups()` | 우울 궤적 4집단 분포 |

---

### `scripts/onset_analysis.py`

| 항목 | 내용 |
|------|------|
| 역할 | Onset(우울 신규 발생) 집단 심층 분석 — "누가 우울해졌나?" |
| 입력 | `KYHPS_STU_analysis_wide.csv` |
| 출력 (figures) | `fig12_onset_vs_stable_trajectories.png`, `fig13_dual_worse_analysis.png` |
| 출력 (tables) | `onset_vs_stable_comparison.xlsx`, `onset_stable_trend_by_year.xlsx`, `dual_worse_group_comparison.xlsx` |

**함수 목록 및 역할:**

| 함수 | 역할 |
|------|------|
| `load_and_prepare()` | 로드 + dep_group 컬럼 생성 |
| `compare_onset_vs_stable()` | Welch t검정 + Cohen's d 비교 |
| `compare_trends_by_group()` | 연도별 추이 + fig12 저장 |
| `analyze_dual_worse_group()` | SP↑ & Sleep↓ 집단 우울 발생률 비교 |
| `print_hypothesis_candidates()` | 탐색적 가설 후보 출력 |

---

### `scripts/panel_ols.py`

| 항목 | 내용 |
|------|------|
| 역할 | 패널 회귀분석 — 생활습관 변수의 우울에 대한 독립적 효과 추정 |
| 입력 | `KYHPS_STU_analysis_long.csv` |
| 출력 (figures) | `fig14_regression_coefficients.png`, `fig15_interaction_plot.png` |
| 출력 (tables) | `panel_ols_coefficients.xlsx`, `panel_interaction_coefficients.xlsx`, `panel_fe_coefficients.xlsx` |

**함수 목록 및 역할:**

| 함수 | 역할 |
|------|------|
| `load_and_prepare_long()` | long form 전처리 (female 더미, year 범주형) |
| `run_pooled_ols()` | Model 1: Pooled OLS + 클러스터 SE |
| `run_interaction_model()` | Model 2: 성별×스마트폰 상호작용 |
| `run_fixed_effects()` | Model 3: FE (linearmodels 필요) |
| `plot_coefficient_forest()` | 계수 Forest Plot |
| `plot_interaction_effect()` | 상호작용 효과 시각화 |
| `print_model_comparison()` | M1 vs M2 비교 출력 |

---

## 핵심 분석 발견 요약

### 우울 궤적 집단 (N=5,051)

| 집단 | N | 비율 |
|------|---|------|
| Stable (비우울 유지) | 2,960 | 58.6% |
| Onset (신규 우울 발생) | 537 | 10.6% |
| Recovery (우울 → 비우울) | 515 | 10.2% |
| Persistent (지속 우울) | 231 | 4.6% |
| Missing | 808 | 16.0% |

### Onset vs Stable 주요 차이 (탐색적)

| 변수 | 방향 | 유의성 | Cohen's d |
|------|------|--------|-----------|
| 스마트폰 변화량 | Onset↑ | ** | 0.157 (trivial) |
| 학업스트레스 변화량 | Onset↓ | *** | -0.209 (small) |
| 기저 학업스트레스 | Onset↓ | *** | -0.216 (small) |
| 패스트푸드 변화량 | Onset↑ | ** | 0.161 (trivial) |

> ⚠ 학업스트레스 계수 방향: **코딩 방향 확인 필수** (1=스트레스 많음 인지 확인)

### 패널 OLS 결과 (N=22,447 관측치)

| 변수 | β | 유의성 | 해석 |
|------|---|--------|------|
| 스마트폰 | +0.0181 | *** | 스마트폰↑ → 우울 확률↑ |
| 수면 | -0.0138 | *** | 수면↑ → 우울 확률↓ |
| 여학생 | +0.0513 | *** | 여학생 우울 위험 더 높음 |
| SP×여학생 상호작용 | +0.0112 | *** | 여학생에서 스마트폰 효과 더 강함 |

---

## 탐색적 가설 후보 (인과 단정 불가)

```
H1. 스마트폰 사용 증가폭이 큰 청소년일수록 우울감 발생 가능성이 높다.
H2. 수면 감소폭이 큰 청소년일수록 우울감 발생 가능성이 높다.
H3. 스마트폰↑ + 수면↓ 동시 악화 집단은 우울 신규 발생률이 더 높다 (15.6% vs 10.6%).
H4. 스마트폰의 우울 효과는 여학생에서 더 강하게 나타난다.
H5. 코로나 직후(2019→2020) 스마트폰 급증이 이후 우울 궤적을 예측한다.
```

---

## 자주 발생하는 오류 해결

| 오류 | 원인 | 해결 |
|------|------|------|
| `ModuleNotFoundError: utils` | 실행 디렉터리 문제 | 프로젝트 루트에서 실행: `cd "...제1회 청소년건강패널조사"` |
| `FileNotFoundError: KYHPS_STU_analysis_wide.csv` | 데이터 파일 없음 | `data/processed/cleaned/` 경로 확인 |
| `UnicodeDecodeError` | CSV 인코딩 문제 | `load_csv()`가 자동 처리; 실패 시 `encoding="cp949"` 수동 지정 |
| `ModuleNotFoundError: linearmodels` | FE 모형 패키지 미설치 | `pip install linearmodels` |
| 한글 그래프 깨짐 | 폰트 없음 | `set_korean_font()` 자동 시도; 실패 시 영문 레이블로 출력 |

---

## 다음 단계 권장 분석

1. **학업스트레스 코딩 방향 확인** — 코드북 `표본설계 및 분석방법 2부.pdf` 참조
2. **조기 변화량 로지스틱 회귀** — 2019→2020 변화량으로 2023 우울 발생 예측
3. **복합 악화 점수 생성** — SP↑+Sleep↓+PA↓+FF↑ 중 해당 수 → 발생률 곡선
4. **Fixed Effects 모형 실행** — `pip install linearmodels` 후 panel_ols.py 재실행
5. **Recovery 집단 분석** — 회복 예측 요인 → 보호 요인 제언

---

> 마지막 업데이트: 2026-05-18  
> 문의: jiwooo411@gachon.ac.kr

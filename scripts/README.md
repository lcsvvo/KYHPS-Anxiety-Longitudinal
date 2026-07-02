# `scripts/` — 분석 · 그림 스크립트

`src/`가 원자료를 분석용 패널로 만드는 번호순 파이프라인이라면, `scripts/`는 그 위에서 **모형을 추정하고 결과표·그림을 생성**하는 실행 스크립트다. **핵심 분석(Mundlak within–between)은 여기 [`depression_panel_v2.py`](depression_panel_v2.py)에 있다.**

> 모든 스크립트는 저장소 루트에서 실행하며, `results/tables/`(표)와 `figures/`(그림)에 산출물을 쓴다. 원자료는 제한자료로 미포함이므로, `data/raw/`에 직접 배치해야 실행된다(→ [`data/README.md`](../data/README.md)).

## 실행 순서 및 산출물 매핑

| 순서 | 스크립트 | 역할 | 주요 산출물 (`results/tables/`) |
|---|---|---|---|
| 1 (핵심) | `depression_panel_v2.py` | **Mundlak within–between 분해** + person 군집강건 SE, 표본외 검증 | `dep_v2_mundlak_gad7.xlsx`, `dep_v2_mundlak_dep_w35.xlsx`, `dep_v2_mundlak_dep_5wave.xlsx`, `dep_v2_oos.xlsx`, `dep_v2_smartphone_dissociation.xlsx`, `dep_v2_trajectory_gad.xlsx` |
| 2 | `onset_analysis.py` | W1 기저 Onset vs. Stable 비교(Welch t), 이중악화 집단 | `onset_vs_stable_comparison.xlsx`, `onset_stable_trend_by_year.xlsx`, `depression_group_dist.xlsx` |
| 3 | `recovery_redesign.py` | Recovery vs. Persistent 재설계 분석 | `rec_definitions.xlsx`, `rec_mundlak_within_between.xlsx`, `rec_oos_validation.xlsx`, `rec_measurement_quality.xlsx`, `rec_rtm_audit.xlsx` |
| 4 | `panel_ols.py` | 패널 OLS · Fixed Effects 회귀 | `panel_ols_coefficients.xlsx`, `panel_fe_coefficients.xlsx`, `panel_interaction_coefficients.xlsx` |
| 5 | `robustness_check.py` | FE / RE / Hausman / logit AME / CCA·LOCF·MICE 민감도 | `robustness_*.xlsx` (fe, re, hausman, logit_ame, mediation_explore, mice_vs_cca, model_comparison) |
| 6 | `dep_v2_robustness.py` | `depression_panel_v2` 결과의 추가 강건성 점검 | `dep_v2_*` 보조 표 |
| — | `eda_pipeline.py` | 탐색적 EDA(결측·연도추이·집단분포) | `missing_summary.xlsx`, `mean_trend_by_year.xlsx`, `change_score_summary.xlsx`, `covid_impact_summary.xlsx` 등 |
| 그림 | `figure3_final.py` | **Figure 3 정본** (변화 동조) | `figures/Figure3_change_coupling.png`, `figure3_change_means.csv` |
| 그림 | `figure3_change_coupling.py` | Figure 3 변형(변화 동조) | 위 정본과 중복 — 정본은 `figure3_final.py` |
| 공통 | `utils.py` | 경로·로깅·로딩 등 공용 헬퍼 (다른 스크립트가 import) | — |

> Figure 1(within–between)·Figure 2(궤적)는 위 `dep_v2_*`·`rec_*` 산출표에서 생성된다. 결과 수치 → 산출 파일의 전체 대응은 [`docs/reproduce.md`](../docs/reproduce.md) §5 참조.

## 주의

- 모든 train/test split seed = **20260619**.
- 산출표는 기계 생성물이므로 수기 편집하지 않는다(스크립트 재실행으로 재생성).

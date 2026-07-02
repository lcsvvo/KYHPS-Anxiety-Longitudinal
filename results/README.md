# `results/` — 모형 산출표

`scripts/`가 생성하는 결과표(xlsx/csv). 기계 생성물이므로 수기 편집하지 않고 스크립트 재실행으로 재생성한다. 스크립트→표 매핑: [`scripts/README.md`](../scripts/README.md), 결과 수치→파일 대응: [`docs/reproduce.md`](../docs/reproduce.md) §5.

## `tables/` 파일군

| 접두어 | 무엇 | 생성 스크립트 |
|---|---|---|
| `dep_v2_*` | **핵심 Mundlak** — GAD-7/우울 within·between, 표본외(OOS), 창 비교, 스마트폰 해리 | `depression_panel_v2.py` |
| `rec_*` | 회복(Recovery) 재설계 — 정의·측정품질·within-between·OOS·RTM 감사 | `recovery_redesign.py` |
| `onset_*`, `depression_group_*`, `dual_worse_*` | Onset vs. Stable 기저·추세, 궤적 집단 분포, 이중악화 비교 | `onset_analysis.py` |
| `panel_*` | 패널 OLS·FE·상호작용 계수 | `panel_ols.py` |
| `robustness_*` | FE/RE/Hausman/logit AME/MICE-vs-CCA/모형비교 | `robustness_check.py` |
| `mean_trend_by_year`, `missing_summary`, `change_score_summary`, `covid_impact_summary`, `subgroup_gender_means` | 탐색적 EDA 요약 | `eda_pipeline.py` |
| `figure3_change_means.csv` | Figure 3의 집단별 변화 평균 | `figure3_final.py` |
| `정제요약보고_KYHPS_5y.xlsx` | 정제 단계 요약 보고 | 전처리 단계 |

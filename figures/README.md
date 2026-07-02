# `figures/` — 그림

원고·README에 쓰인 최종 그림. 모두 `scripts/`가 `results/tables/`의 산출표에서 재생성한다(→ [`scripts/README.md`](../scripts/README.md), [`docs/reproduce.md`](../docs/reproduce.md)).

| 파일 | 내용 | 생성 |
|---|---|---|
| `Figure1_within_between.png` | 변수별 within(●)·between(■) Mundlak 계수 + 95% CI — 스마트폰은 between만 유의 | `dep_v2_*` 표에서 |
| `Figure2_trajectories.png` | 5개년 우울 궤적 — 차수별 유병률, 집단별 W5 GAD-7·중등도(≥10) 비율 | `dep_v2_*`·`rec_*` 표에서 |
| `Figure3_change_coupling.png` | W3→W5 변화 동조 (불안·미래·가족 스트레스·수면) | `scripts/figure3_final.py` |

## `eda/` — 선별 탐색 그림

| 파일 | 내용 |
|---|---|
| `fig03_gender_subgroup.png` | 성별 하위그룹 추이 |
| `fig10_key_paradox_dual_axis.png` | key paradox (이중축) |
| `fig12_onset_vs_stable_trajectories.png` | Onset vs. Stable 궤적 |

> 탐색 그림은 최종 결과가 아니라 분석 과정 기록용이다.

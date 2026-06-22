# Reproduction Guide

This guide reproduces the analysis end-to-end. The **input data are restricted and not included** (see [`../data/README.md`](../data/README.md)); the steps below assume you have obtained the KYHPS microdata and placed it under `data/raw/`.

All random splits use seed **20260619**.

## 0. Environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # Python 3.11
```

## 1. Build the analytic panel (`src/`)

The numbered pipeline turns raw wave files into the analytic tables.

| Stage | Folder | Purpose |
|---|---|---|
| 00 | `src/00_config/` | variable maps (`variable_map_student.yaml`), design metadata |
| 01 | `src/01_intake/` | load raw wave files, extract value labels, build master codebook |
| 02–03 | `src/02_harmonize/`, `src/03_merge/` | align names across W1–W5, merge to wide + long complete-case panel |
| 04 | `src/04_tracking/` | response / attrition tracking labels |
| 05 | `src/05_cleaning/` | logic checks, GAD-7 standardization (0–21), stress reverse-coding |
| 06 | `src/06_survey_design/` | weight / strata / cluster setup |
| 07–08 | `src/07_analysis/`, `src/08_visualization/` | descriptive, FE model, selection-bias test, summary export |

> Note: `src/00_config/variable_map_student.yaml` maps analysis variables to raw column names; confirm it matches your copy of the data before running.

## 2. Core model — Mundlak within–between

```bash
python scripts/depression_panel_v2.py
```
Outputs → `results/tables/`:
- `dep_v2_mundlak_gad7.xlsx` — primary GAD-7 within/between coefficients + cluster-robust SE
- `dep_v2_mundlak_dep_w35.xlsx`, `dep_v2_mundlak_dep_5wave.xlsx` — depression outcome, short vs. long window
- `dep_v2_oos.xlsx` — out-of-sample test R² (0.125 → 0.206)
- `dep_v2_smartphone_dissociation.xlsx`, `dep_v2_trajectory_gad.xlsx`

## 3. Supporting analyses

```bash
python scripts/onset_analysis.py       # W1 baseline Onset vs. Stable (Welch t)
python scripts/recovery_redesign.py    # Recovery vs. Persistent; rec_* tables
python scripts/panel_ols.py            # panel OLS / FE coefficients
python scripts/robustness_check.py     # CCA/LOCF/MICE, Hausman, model comparison
```

## 4. Figures

```bash
python scripts/figure3_final.py            # Figure3 (change coupling)
python scripts/figure3_change_coupling.py  # change-coupling variant
```
(Figure1 within–between and Figure2 trajectories are produced from the `dep_v2_*` / `rec_*` outputs.)

## 5. Map: result → file

| Reported number | Source file |
|---|---|
| Smartphone between β=+0.113 / within β=+0.023 | `results/tables/dep_v2_mundlak_gad7.xlsx` |
| Test R² 0.125 → 0.206 | `results/tables/dep_v2_oos.xlsx` |
| Trajectory N (Stable/Onset/Recovery/Persistent) | `results/tables/depression_group_dist.xlsx` |
| W1 Onset vs. Stable baseline | `results/tables/onset_vs_stable_comparison.xlsx` |
| Sex × trajectory | `results/tables/subgroup_gender_means.xlsx` |

# Data — Not Included (Restricted Access)

The **Korean Youth Health Panel Survey (KYHPS)** microdata used in this project are **restricted-access** and are governed by the data provider's terms of use. They are **not redistributed** in this repository — neither the raw files nor any person-level processed/derived files.

## What this folder would contain locally

```
data/
├── raw/         # original KYHPS student & parent files, W1–W5 (2019–2023)   🔒 not included
└── processed/   # harmonized / merged / cleaned analytic tables               🔒 not included
                 #   (e.g., complete-case panel, CCA / LOCF / MICE versions)
```

## How to obtain the data

KYHPS microdata are provided to approved researchers through the official data-distribution channel of the survey's administering institution. Access typically requires an application and agreement to the data-use terms. Once obtained, place the raw files under `data/raw/` following the directory layout expected by `src/01_intake/`.

## Why it is excluded

- The data are **not licensed for public redistribution**.
- The files contain **individual-level adolescent health records**.
- Publishing them would violate the data-use agreement.

This repository is fully **auditable without the data**: the complete processing and analysis pipeline (`src/`, `scripts/`) and all result tables (`results/tables/`) are included, so the methodology can be reviewed end-to-end. Only the inputs are withheld.

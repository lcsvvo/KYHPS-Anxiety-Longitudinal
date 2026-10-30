# Reproduction

**제한자료와 가공 패널을 확보한 환경**의 실행 안내.

## Setup

저장소 루트에서 의존성 설치. Python 3.11 기준.

```bash
pip install -r requirements.txt
```

## Inputs

- [Data 안내](../data/README.md)에 맞춰 원자료와 가공 패널 배치
- 핵심 입력은 `data/processed/merged/KYHPS_STU_5y_wide_final.csv`, `data/processed/cleaned/KYHPS_STU_analysis_long.csv`
- 조화, 병합의 독립 모듈 일부가 미포함돼 **원자료만으로 전체 패널 재구성은 불가**
- 자료 처리 구성은 [Source](../src/README.md), 결측 처리는 [Notebooks](../notebooks/README.md) 참조

## Run

저장소 루트에서 필요한 분석 실행.

```bash
python scripts/depression_panel_v2.py
python scripts/onset_analysis.py
python scripts/recovery_redesign.py
python scripts/figure3_final.py
```

- 분할 seed는 **20260619**
- 보조 모형과 민감도 분석은 [Scripts](../scripts/README.md) 참조

## Outputs

- 핵심 모형 출력은 `outputs/tables/dep_v2_*.xlsx`
- Figure 3 출력은 실행 위치의 `Figure3_FINAL.png`, `Figure3_FINAL.pdf`
- 기존 공개 결과는 [Results](../results/README.md), 대표 그림은 [Figures](../figures/README.md) 참조
- 산출물 공개 전 **개인 단위 값과 ID 목록 제외** 필요

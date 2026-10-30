# Scripts

**모형 추정, 집단 비교, 그림 생성** 스크립트 안내.

| Script | Content |
|---|---|
| [depression_panel_v2.py](depression_panel_v2.py) | Mundlak 모형, 군집강건 표준오차, 표본외 평가와 관측 구간 비교 |
| [onset_analysis.py](onset_analysis.py) | 신규 발생과 비우울 유지 집단 비교 |
| [recovery_redesign.py](recovery_redesign.py) | 회복과 지속 집단 비교 |
| [panel_ols.py](panel_ols.py) | OLS, FE 보조 모형 |
| [robustness_check.py](robustness_check.py), [dep_v2_robustness.py](dep_v2_robustness.py) | 모형과 결측 처리 민감도 분석 |
| [eda_pipeline.py](eda_pipeline.py) | 결측, 연도, 집단별 탐색 |
| [figure3_final.py](figure3_final.py) | Figure 3 생성 |
| [figure3_change_coupling.py](figure3_change_coupling.py) | Figure 3 대안 구성 |
| [utils.py](utils.py) | 공통 경로, 자료 로딩, 로깅 함수 |

## Run

- 저장소 루트에서 의존성 설치와 스크립트 실행

```bash
pip install -r requirements.txt
python scripts/depression_panel_v2.py
```

- 제한자료와 가공 패널 별도 확보 필요. 입력 경로는 [Data](../data/README.md) 참조
- 분할 seed는 **20260619**

## Outputs

- 핵심 모형은 **`outputs/tables/dep_v2_*.xlsx`**에 저장
- `figure3_final.py`는 실행 위치에 `Figure3_FINAL.png`, `Figure3_FINAL.pdf` 생성
- `results/tables/`와 `figures/`는 기존 공개 산출물 위치. 스크립트의 실제 출력 경로와 구분 필요
- 공개 결과표 대응은 [Results](../results/README.md) 참조

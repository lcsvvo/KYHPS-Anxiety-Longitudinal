# Data

**KYHPS 제한자료**의 접근 조건과 로컬 배치 안내.

## Source

- **한국청소년건강패널조사, KYHPS**, 2019~2023년 W1~W5 학생 및 보호자 자료
- 조사 수행기관의 자료 이용 신청과 승인 절차에 따라 확보

## Paths

```text
data/
├── raw/                  # 승인받은 원자료
└── processed/
    ├── merged/           # 차수별 통합 자료
    └── cleaned/          # 정제된 분석 패널
```

- 핵심 모형 입력: `processed/merged/KYHPS_STU_5y_wide_final.csv`
- 5개 차수 우울 패널 입력: `processed/cleaned/KYHPS_STU_analysis_long.csv`
- 전처리 구성은 [Source](../src/README.md), 실행 순서는 [실행 안내](../docs/reproduce.md) 참조

## Access

- **원자료, 개인 단위 가공자료, 응답자 ID 목록은 공개 제외**
- 노트북 출력과 정제 보고서에도 개인값이 포함되지 않도록 주의 필요
- 일부 독립 조화, 병합 모듈이 없어 원자료 배치만으로 전체 재현은 불가

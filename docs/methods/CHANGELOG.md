# CHANGELOG

> 모든 주요 변경 사항을 이 파일에 기록한다.  
> 형식: `[YYYY-MM-DD] [유형] 설명`  
> 유형: `STRUCT`(구조변경) | `DATA`(데이터처리) | `CODE`(코드변경) | `DOCS`(문서) | `FIX`(수정)

---

## 2026-05-18

- `[STRUCT]` 프로젝트 전체 폴더 구조 재설계 및 생성
  - `data/raw/student/`, `data/raw/parent/` — 연도별 원시 데이터
  - `data/processed/` — harmonized / merged / tracking / cleaned / weighted
  - `src/00_config ~ 08_visualization/` — 단계별 분석 스크립트
  - `experiments/`, `logs/`, `docs/`, `outputs/`

- `[DATA]` 기존 파일 전체 재배치 완료
  - 학생/부모 원시 CSV → `data/raw/student|parent/YYYY/`
  - 부모 R/SPS 레이블 스크립트 → `data/raw/parent/YYYY/`
  - 병합 데이터 → `data/processed/merged/`
  - 추적 라벨 / ID 목록 → `data/processed/tracking/`
  - 전처리 결과 → `data/processed/cleaned/`
  - 마스터 코드북 / 통계집 → `docs/codebooks/`

- `[CODE]` 핵심 Python 스크립트 신규 생성
  - `src/utils/logger.py` — 공통 로거
  - `src/utils/paths.py` — 경로 상수
  - `src/01_intake/01a_load_raw.py` — 원시 데이터 로드
  - `src/04_tracking/04a_label_tracking_status.py` — 추적 상태 라벨링
  - `src/05_cleaning/05a_logic_check_smoking.py` — 흡연 논리 검증
  - `src/06_survey_design/06b_design_setup.py` — 복합표본설계
  - `src/07_analysis/descriptive/07a_desc_basic.py` — 기술통계
  - `src/07_analysis/regression/07e_fe_model.py` — FE 패널 모형
  - `src/07_analysis/sensitivity/07i_selection_bias_test.py` — 탈락 편향 진단

- `[DOCS]` 설계 가이드 및 프로토콜 문서 작성
  - `KYHPS_연구워크스페이스_설계가이드.md`
  - `docs/logic_rules.md` — 논리 검증 규칙 정의서
  - `docs/tracking_protocol.md` — 추적 상태 라벨링 프로토콜
  - `src/00_config/variable_map_student.yaml` — 학생 변수 매핑
  - `src/00_config/variable_map_parent.yaml` — 부모 변수 매핑

---

## 다음 작업 예정

- [ ] `variable_map_*.yaml` 실제 원본 컬럼명 입력 (코드북 참조)
- [ ] `DESIGN_META` 가중치/층화/군집 변수명 확인 및 입력
- [ ] `01a_load_raw.py` 실행하여 데이터 로드 검증
- [ ] `04a_label_tracking_status.py` 실행하여 추적 상태 확인
- [ ] `05a_logic_check_smoking.py` 실행하여 흡연 논리 오류 검출

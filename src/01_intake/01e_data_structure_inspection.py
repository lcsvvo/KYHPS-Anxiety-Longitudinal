"""
KYHPS 데이터 구조 확인 (Data Structure Inspection)
======================================================
대상: 학생 wide (fin_student_wide_5y 또는 merged)
      보호자 원시 데이터 (파별 CSV) + fin_parent_wide_5y
목적: 전처리 전 데이터의 구조적 특성 전수 파악
      학생-보호자 결합 분석을 위한 ID 매칭 및 탈락 패턴 비교 포함
"""

import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# 0. 데이터 로딩
# ─────────────────────────────────────────────
DATA_PATH = r"C:\Users\jiwoo\OneDrive\Desktop\나\3학년\제1회 청소년건강패널조사\2019-23_student_merged_wide_format.csv"

df = pd.read_csv(DATA_PATH, low_memory=False, encoding='cp949')
print("=" * 65)
print("[ 0. 기본 정보 ]")
print("=" * 65)
print(f"  행(피험자) 수: {df.shape[0]:,}")
print(f"  열(변수)  수: {df.shape[1]:,}")
print(f"  메모리 사용량: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
print(f"  ID 컬럼    : '설문번호' (예: {df['설문번호'].iloc[0]})")

# ─────────────────────────────────────────────
# 1. 파(Wave)별 컬럼 구성 분석
# ─────────────────────────────────────────────
print("\n" + "=" * 65)
print("[ 1. 파(Wave)별 컬럼 구성 ]")
print("=" * 65)

WAVES = ['w1', 'w2', 'w3', 'w4', 'w5']
WAVE_YEARS = {'w1': 2019, 'w2': 2020, 'w3': 2021, 'w4': 2022, 'w5': 2023}

wave_cols = {}
for w in WAVES:
    wave_cols[w] = [c for c in df.columns if c.endswith(f'_{w}')]

print(f"\n  {'파':>4} {'연도':>6} {'총컬럼':>8} {'완전결측(100%)':>15} {'부분결측':>10} {'완전응답':>10}")
print(f"  {'-'*55}")
for w in WAVES:
    excl = ['가중치', '보정계수']
    analysis_cols = [c for c in wave_cols[w] if not any(x in c for x in excl)]
    miss_rates = df[analysis_cols].isnull().mean()
    n_full_miss = (miss_rates == 1.0).sum()
    n_partial   = ((miss_rates > 0) & (miss_rates < 1)).sum()
    n_complete  = (miss_rates == 0).sum()
    print(f"  {w:>4} {WAVE_YEARS[w]:>6} {len(analysis_cols):>8} {n_full_miss:>15} {n_partial:>10} {n_complete:>10}")

# 파간 변수 신규 추가 현황
print("\n  [ 파간 신규 추가 변수 (W1 대비) ]")
w1_bases = set(c.replace('_w1', '') for c in wave_cols['w1'])
for w in ['w2', 'w3', 'w4', 'w5']:
    w_bases = set(c.replace(f'_{w}', '') for c in wave_cols[w])
    new = w_bases - w1_bases
    print(f"    {w}: +{len(new)}개 신규 | 예시: {list(new)[:3]}")

# 전 파 공통 변수 수
all_bases = set.intersection(*[
    set(c.replace(f'_{w}', '') for c in wave_cols[w]) for w in WAVES
])
print(f"\n  전 파(W1~W5) 공통 변수: {len(all_bases)}개")

# ─────────────────────────────────────────────
# 2. 데이터 타입 분포 & 변수 분류
# ─────────────────────────────────────────────
print("\n" + "=" * 65)
print("[ 2. 변수 타입 분류 ]")
print("=" * 65)

dtype_dist = df.dtypes.value_counts()
print(f"\n  dtype 분포: {dict(dtype_dist)}")

numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
object_cols  = df.select_dtypes(include='object').columns.tolist()

# 범주형 vs 연속형 분류 (unique ≤ 10: 범주형 후보)
cat_candidates  = [c for c in numeric_cols if df[c].nunique(dropna=True) <= 10]
cont_candidates = [c for c in numeric_cols if df[c].nunique(dropna=True) > 10]

print(f"  범주형 후보 (unique ≤ 10): {len(cat_candidates):>4}개")
print(f"  연속형 후보 (unique  > 10): {len(cont_candidates):>4}개")
print(f"  문자열(object)          : {len(object_cols):>4}개  → {object_cols}")

# 코드 체계 확인 (이분형 변수: 1=예/2=아니오 구조)
print("\n  [ 이분형 변수 코딩 체계 확인 (W1) ]")
key_binary_vars = [
    '학생 성별_w1',
    '평생담배제품사용경험률_w1',
    '평생 음주 경험(잔 기준)_w1',
    '우울감 경험_w1',
]
for v in key_binary_vars:
    if v in df.columns:
        vc = df[v].value_counts(dropna=False).to_dict()
        print(f"    {v:40s}: {vc}")

print("\n  ※ 코딩 규칙: 1=예(있음/남성), 2=아니오(없음/여성) — 0 기반 아님 주의")

# ─────────────────────────────────────────────
# 3. 결측값 구조 분석
# ─────────────────────────────────────────────
print("\n" + "=" * 65)
print("[ 3. 결측값 구조 분석 ]")
print("=" * 65)

# 3-1. 파별 응답 지표 생성 (종단 가중치 기준)
weight_cols_map = {w: f'종단면 가중치_{w}' for w in WAVES}
for w, col in weight_cols_map.items():
    df[f'responded_{w}'] = df[col].notna().astype(int)

resp_cols = [f'responded_{w}' for w in WAVES]
df['waves_completed'] = df[resp_cols].sum(axis=1)

print(f"\n  [ 파별 응답률 ]")
for w in WAVES:
    n = df[f'responded_{w}'].sum()
    print(f"    {w} ({WAVE_YEARS[w]}): {n:,}명 ({n/len(df)*100:.1f}%)")

complete = (df['waves_completed'] == 5).sum()
print(f"\n  5개년 완전 응답: {complete:,}명 ({complete/len(df)*100:.1f}%)")
print(f"  탈락 (any wave): {len(df)-complete:,}명 ({(len(df)-complete)/len(df)*100:.1f}%)")

# 3-2. 결측 패턴 (응답 패턴 문자열)
df['response_pattern'] = df[resp_cols].apply(
    lambda r: ''.join(r.astype(str)), axis=1
)
print(f"\n  [ 응답 패턴 분포 (상위 10개) ]")
pat_dist = df['response_pattern'].value_counts()
for pat, cnt in pat_dist.head(10).items():
    label = "완전응답" if pat == '11111' else (
            "재진입" if ('0' in pat[:-1] and '1' in pat[1:] and pat[pat.find('0')+1:].count('1') > 0) else "단조탈락"
    )
    print(f"    {pat}  n={cnt:>5}  ({cnt/len(df)*100:.1f}%)  [{label}]")

# 3-3. 결측 유형 분류: 구조적 vs 탈락 결측
print(f"\n  [ 결측 유형 구분 ]")
# 예시: 음주 잔 기준 — 모금 기준 '아니오'(=2)인 경우 구조적 skip
if '평생 음주 경험(모금 기준)_w1' in df.columns and '평생 음주 경험(잔 기준)_w1' in df.columns:
    structural_miss = ((df['평생 음주 경험(모금 기준)_w1'] == 2) &
                       df['평생 음주 경험(잔 기준)_w1'].isna()).sum()
    attrition_miss = (df['responded_w1'] == 0).sum()
    total_miss = df['평생 음주 경험(잔 기준)_w1'].isna().sum()
    print(f"    '평생 음주 경험(잔 기준)_w1' 총 결측: {total_miss:,}건")
    print(f"      └ 구조적 결측 (모금 기준=아니오): {structural_miss:,}건 ({structural_miss/total_miss*100:.1f}%)")
    print(f"      └ 탈락 결측 (W1 미응답)         : {attrition_miss:,}건")
    print(f"      └ 기타 결측                     : {total_miss-structural_miss-attrition_miss:,}건")

# ─────────────────────────────────────────────
# 4. 핵심 변수 기술통계
# ─────────────────────────────────────────────
print("\n" + "=" * 65)
print("[ 4. 핵심 변수 기술통계 (W1) ]")
print("=" * 65)

print(f"\n  [ 종단 가중치 분포 ]")
wt = df['종단면 가중치_w1']
print(f"    min={wt.min():.2f}, max={wt.max():.2f}, "
      f"mean={wt.mean():.2f}, median={wt.median():.2f}, std={wt.std():.2f}")
print(f"    ※ 가중치 범위: {wt.max()/wt.min():.1f}배 → 복합표본 설계 반영 필수")

# 음주 이력 역전 탐지
print(f"\n  [ 평생 음주 경험(잔 기준) 파별 추이 ]")
drink_vars = [f'평생 음주 경험(잔 기준)_{w}' for w in WAVES]
for v in drink_vars:
    if v in df.columns:
        yes = (df[v] == 1).sum()
        no  = (df[v] == 2).sum()
        na  = df[v].isna().sum()
        total_valid = yes + no
        rate = yes / total_valid * 100 if total_valid > 0 else 0
        print(f"    {v:40s}: 있음={yes:,} 없음={no:,} 결측={na:,} | 유병률={rate:.1f}%")

# 역전 사례 파전이별
print(f"\n  [ 음주 이력 역전 파전이별 ]")
sub = df[drink_vars].copy()
for v in drink_vars:
    sub[v] = sub[v].map({1: 1, 2: 0})
for i in range(1, 5):
    prev, curr = sub[drink_vars[i-1]], sub[drink_vars[i]]
    valid = prev.notna() & curr.notna()
    rev = ((prev == 1) & (curr == 0) & valid).sum()
    base = ((prev == 1) & valid).sum()
    print(f"    W{i}→W{i+1}: 역전 {rev:,}건 / 직전 '있음' {base:,}건 = {rev/base*100:.1f}%")

# ─────────────────────────────────────────────
# 5. 복합표본 설계 변수 확인
# ─────────────────────────────────────────────
print("\n" + "=" * 65)
print("[ 5. 복합표본 설계 변수 확인 ]")
print("=" * 65)

design_vars = ['층화변수(strata)_w1', '군집(cluster)_w1',
               '종단면 가중치_w1', '유한모집단보정계수_w1']
for v in design_vars:
    if v in df.columns:
        s = df[v]
        print(f"  {v}: unique={s.nunique()}, null={s.isna().sum()}, "
              f"range=[{s.min():.2f}, {s.max():.2f}]")

print("\n  ※ 분석 시 svydesign(strata=층화변수, cluster=군집, weights=종단면가중치) 지정 필수")


# ─────────────────────────────────────────────
# 6. 보호자 데이터 구조 확인
# ─────────────────────────────────────────────
print("\n" + "=" * 65)
print("[ 6. 보호자 데이터 구조 확인 ]")
print("=" * 65)

PARENT_DATA_DIR = r"C:\Users\jiwoo\OneDrive\Desktop\나\3학년\제1회 청소년건강패널조사\data\보호자_20260506_46302_데이터"
PARENT_WIDE_PATH = r"C:\Users\jiwoo\OneDrive\Desktop\나\3학년\제1회 청소년건강패널조사\output_cleaning\fin_parent_wide_5y.csv"

import os

# 6-1. 파별 원시 데이터 구조
print(f"\n  [ 보호자 파별 원시 데이터 구조 ]")
print(f"  {'파':>4} {'연도':>6} {'N':>6} {'컬럼수':>8} {'완전결측':>10} {'부분결측':>10}")
print(f"  {'-'*50}")
parent_raw = {}
for i, (w, yr) in enumerate(zip(WAVES, [2019, 2020, 2021, 2022, 2023])):
    fpath = os.path.join(PARENT_DATA_DIR, f"{yr}_보호자_20260506_46302.csv")
    try:
        d = pd.read_csv(fpath, low_memory=False, encoding='cp949')
        parent_raw[w] = d
        mr = d.drop(columns=['설문번호'], errors='ignore').isnull().mean()
        print(f"  {w:>4} {yr:>6} {len(d):>6} {d.shape[1]:>8} "
              f"{(mr == 1.0).sum():>10} {((mr > 0) & (mr < 1)).sum():>10}")
    except FileNotFoundError:
        print(f"  {w:>4} {yr:>6} [파일 없음: {fpath}]")

# 6-2. W1 전용 변수 (W2부터 소멸)
if 'w1' in parent_raw and 'w2' in parent_raw:
    w1_vars = set(parent_raw['w1'].columns) - {'설문번호'}
    w2_vars = set(parent_raw['w2'].columns) - {'설문번호'}
    w1_only = w1_vars - w2_vars
    print(f"\n  [ W1 전용 변수 (W2 이후 미수집): {len(w1_only)}개 ]")
    for v in sorted(w1_only):
        print(f"    - {v}")

# 6-3. 핵심 보호자 변수 기술통계 (W1)
if 'w1' in parent_raw:
    print(f"\n  [ 보호자 핵심 변수 분포 (W1) ]")
    key_p_vars = [
        '학부모 성별', '가구의 경제상태', '가족의 화목도',
        '가구 내 음주자 유무', '가구 내 흡연자 유무',
        '부모의 자녀 음주에 대한 허용', '부모의 자녀 흡연에 대한 허용',
    ]
    for v in key_p_vars:
        if v in parent_raw['w1'].columns:
            s = parent_raw['w1'][v]
            print(f"    {v:35s}: unique={s.nunique()}, null={s.isna().sum()}, "
                  f"vals={sorted(s.dropna().unique()[:8].tolist())}")

# 6-4. 학생-보호자 ID 매칭 & 탈락 불일치 분석
print(f"\n  [ 학생-보호자 ID 매칭 및 탈락 불일치 ]")
# 학생 완전응답자 ID
s_completer_ids = set(df[df['waves_completed'] == 5]['설문번호'])
# 보호자 완전응답자 ID (fin_parent_wide_5y 기준)
try:
    dp_wide = pd.read_csv(PARENT_WIDE_PATH, low_memory=False, encoding='utf-8-sig')
    p_completer_ids = set(dp_wide['설문번호'])
    both_complete   = s_completer_ids & p_completer_ids
    s_only_complete = s_completer_ids - p_completer_ids
    p_only_complete = p_completer_ids - s_completer_ids

    print(f"    학생 5파 완전응답  : {len(s_completer_ids):,}명")
    print(f"    보호자 5파 완전응답: {len(p_completer_ids):,}명")
    print(f"    양쪽 모두 완전응답 : {len(both_complete):,}명  ← 병합 분석 최대 표본")
    print(f"    학생만 완전응답    : {len(s_only_complete):,}명  (보호자 탈락)")
    print(f"    보호자만 완전응답  : {len(p_only_complete):,}명  (학생 탈락)")
    print(f"\n  ※ 학생-보호자 병합 분석 시 유효 N = {len(both_complete):,}명 "
          f"(학생 단독 CCA 대비 -{len(s_only_complete)}명)")
except FileNotFoundError:
    print(f"    [fin_parent_wide_5y.csv 없음 — 먼저 01_data_cleaning_pipeline.py 실행 필요]")

# 6-5. 파별 탈락율 비교: 학생 vs 보호자
print(f"\n  [ 파별 탈락율 비교 ]")
print(f"  {'파':>4}  {'학생 유지율':>12}  {'보호자 유지율':>14}  {'차이':>6}")
total_s = len(df)
total_p = len(parent_raw.get('w1', pd.DataFrame()))
for w in ['w2', 'w3', 'w4', 'w5']:
    s_n = df[f'responded_{w}'].sum() if f'responded_{w}' in df.columns else 0
    p_n = len(parent_raw[w]) if w in parent_raw else 0
    s_rate = s_n / total_s * 100
    p_rate = p_n / total_p * 100 if total_p > 0 else 0
    diff = p_rate - s_rate
    print(f"  {w:>4}  {s_rate:>11.1f}%  {p_rate:>13.1f}%  {diff:>+6.1f}%p")

print("\n" + "=" * 65)
print("구조 확인 완료. 전처리 단계로 진행 가능.")
print("=" * 65)
print("""
전처리 우선순위 요약:
  1. 학생 단독 분석   → 07_preprocessing.py (CCA N=3,986)
  2. 보호자 단독 분석 → fin_parent_wide_5y 기반 (N=3,922)
  3. 학생+보호자 병합 → 설문번호 join, 유효 N=3,922 이하 확인 후 진행
""")

"""
보호자 R 스크립트에서 value labels 추출 + 통합 codebook 생성
================================================================
- 보호자: cp949 R 스크립트 파싱 → C{n} 컬럼 ↔ 한글 변수명 ↔ 응답값 라벨 매핑
- 학생: wide CSV에서 변수별 응답값 분포 자동 산출
- 산출물: parent_value_labels.csv, student_value_distribution.csv
"""
import os, re
import pandas as pd

from pathlib import Path
BASE = Path(__file__).resolve().parents[2]   # repo root
OUT = os.path.join(BASE, "output_cleaning")
os.makedirs(OUT, exist_ok=True)

YEARS = [2019, 2020, 2021, 2022, 2023]
WAVES = [1, 2, 3, 4, 5]


# ---------- (1) 보호자 R 스크립트 파싱 ----------
# 패턴 예시:
#   mdis$V2<- recode_factor(mdis$V2, '1'="서울")
RECODE_RE = re.compile(r"mdis\$V(\d+)\s*<-\s*recode_factor\([^,]+,\s*'(\d+)'\s*=\s*\"(.+?)\"\s*\)")


def parse_r_value_labels(path):
    """R 스크립트 → {V_index: {code: label}} 반환"""
    with open(path, 'rb') as f:
        txt = f.read().decode('cp949', errors='replace')
    out = {}
    for m in RECODE_RE.finditer(txt):
        v_idx = int(m.group(1))
        code = m.group(2)
        label = m.group(3).strip()
        out.setdefault(v_idx, {})[code] = label
    return out


def get_parent_var_names(year):
    """해당 연도 보호자 CSV의 컬럼 순서 반환 (V1=설문번호 ... V_n)"""
    fp = os.path.join(BASE, "보호자_20260506_46302_데이터", f"{year}_보호자_20260506_46302.csv")
    df = pd.read_csv(fp, encoding='cp949', nrows=0)
    return df.columns.tolist()


def build_parent_codebook():
    rows = []
    for y, w in zip(YEARS, WAVES):
        r_path = os.path.join(BASE, "보호자_20260506_46302_r", f"{y}_보호자_20260506_46302.R")
        labels = parse_r_value_labels(r_path)
        cols = get_parent_var_names(y)
        # V1 = 첫 번째 컬럼 = 설문번호
        for i, varname in enumerate(cols, start=1):
            mapping = labels.get(i, {})
            if mapping:
                vtype = "범주형"
                resp = "; ".join([f"{k}={v}" for k, v in sorted(mapping.items(), key=lambda x: int(x[0]))])
            else:
                vtype = "수치/식별자"
                resp = ""
            rows.append({
                "차시": w,
                "연도": y,
                "변수순번(V)": i,
                "변수명": varname,
                "변수명_wide": f"{varname}_w{w}" if varname != "설문번호" else "설문번호",
                "응답유형": vtype,
                "응답값(코드=라벨)": resp,
                "고유코드수": len(mapping),
            })
    return pd.DataFrame(rows)


# ---------- (2) 학생 wide 데이터 응답값 분포 자동 산출 ----------
def build_student_distribution():
    fp = os.path.join(BASE, "2019-23_student_merged_wide_format.csv")
    df = pd.read_csv(fp, encoding='cp949', low_memory=False)
    rows = []
    for c in df.columns:
        s = df[c]
        m = re.search(r"_w(\d)$", c)
        wave = int(m.group(1)) if m else None
        base = re.sub(r"_w\d$", "", c) if wave else c
        nun = s.nunique(dropna=True)
        if nun <= 15:  # 범주형으로 추정
            vc = s.value_counts(dropna=False).sort_index()
            resp = "; ".join([f"{k}({v})" for k, v in vc.items() if pd.notna(k)])
            vtype = "범주형(추정)"
        else:
            try:
                desc = s.describe()
                resp = f"min={desc.get('min'):.1f}; max={desc.get('max'):.1f}; mean={desc.get('mean'):.2f}"
            except Exception:
                resp = ""
            vtype = "수치형(추정)"
        rows.append({
            "변수명_wide": c,
            "변수명(base)": base,
            "차시(wave)": wave,
            "응답유형": vtype,
            "고유값수": nun,
            "결측수": int(s.isna().sum()),
            "유효응답수": int(s.notna().sum()),
            "응답분포(상위/요약)": resp,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("[1/2] 보호자 codebook 생성")
    par_cb = build_parent_codebook()
    par_cb.to_csv(os.path.join(OUT, "parent_value_labels.csv"), index=False, encoding="utf-8-sig")
    print(f"  rows: {len(par_cb)}, saved")

    print("[2/2] 학생 응답값 분포 생성")
    stu_dist = build_student_distribution()
    stu_dist.to_csv(os.path.join(OUT, "student_value_distribution.csv"), index=False, encoding="utf-8-sig")
    print(f"  rows: {len(stu_dist)}, saved")

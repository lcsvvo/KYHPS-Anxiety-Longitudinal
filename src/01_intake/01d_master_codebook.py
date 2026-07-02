"""
KYHPS 통합 마스터 코드북(Excel) + fin_ 데이터 최종 검증
==========================================================
시트 구성:
1) Overview          - 정제 요약·작업 절차
2) 한계_및_검토       - Selection Bias 등 확장 디스커션
3) 학생_코드북        - 학생 변수 1,073개의 변수명·응답유형·분포·라벨추정
4) 보호자_코드북      - 보호자 변수 168개의 변수명·응답값(코드=라벨)
5) 단조성_검사결과    - 평생 흡연/음주 변수별 불일치/재코딩 건수
6) ID_5년완전응답     - 학생/보호자/공통 ID 리스트
"""
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from pathlib import Path
BASE = Path(__file__).resolve().parents[2]   # repo root
OUT = os.path.join(BASE, "output_cleaning")

# 데이터 로드
stu_dist = pd.read_csv(os.path.join(OUT, "student_value_distribution.csv"))
par_cb = pd.read_csv(os.path.join(OUT, "parent_value_labels.csv"))
id_stu = pd.read_csv(os.path.join(OUT, "ID_list_student_5y.csv"))
id_par = pd.read_csv(os.path.join(OUT, "ID_list_parent_5y.csv"))
id_com = pd.read_csv(os.path.join(OUT, "ID_list_common_5y.csv"))

# Phase2 재코딩 결과 (이전 파이프라인 출력)
phase2 = pd.DataFrame([
    ["일반담배(궐련)_평생 흡연 경험(모금 기준)", 5, "1,2,3,4,5",  24,   24],
    ["일반담배(궐련)_평생 흡연 경험(개비 기준)", 5, "1,2,3,4,5",  13,   14],
    ["액상형_평생 흡연 여부(모금 기준)",          5, "1,2,3,4,5",  20,   20],
    ["궐련형_평생 흡연 경험(모금 기준)",          5, "1,2,3,4,5",  13,   16],
    ["궐련형_평생 흡연 경험(개비 기준)",          5, "1,2,3,4,5",   5,    5],
    ["평생 음주 경험(모금 기준)",                  5, "1,2,3,4,5", 1169, 2312],
    ["평생 음주 경험(잔 기준)",                    5, "1,2,3,4,5",  434,  716],
    ["평생담배제품사용경험률",                      4, "1,2,3,4",     40,   59],
], columns=["변수명(base)", "차시수", "차시컬럼", "불일치_subject수", "재코딩_셀단위건수"])

# ---------- 스타일 ----------
THIN = Side(border_style="thin", color="999999")
BORDER = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
HEAD_FILL = PatternFill("solid", start_color="305496")
SUB_FILL = PatternFill("solid", start_color="D9E1F2")
HEAD_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=11)
TITLE_FONT = Font(name="Arial", bold=True, size=14)
SECTION_FONT = Font(name="Arial", bold=True, size=12)
BODY_FONT = Font(name="Arial", size=10)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="top", wrap_text=True)


def style_header_row(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEAD_FILL
        cell.font = HEAD_FONT
        cell.alignment = CENTER
        cell.border = BORDER


def style_body_range(ws, r1, r2, ncols, align=CENTER):
    for r in range(r1, r2 + 1):
        for c in range(1, ncols + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = BODY_FONT
            cell.alignment = align
            cell.border = BORDER


def autosize_ws(ws, max_w=50):
    widths = {}
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is None:
                continue
            try:
                col_idx = cell.column
            except Exception:
                continue
            length = max(len(line) for line in str(cell.value).split("\n"))
            widths[col_idx] = max(widths.get(col_idx, 10), length + 2)
    for ci, w in widths.items():
        ws.column_dimensions[get_column_letter(ci)].width = min(w, max_w)


def write_df(ws, df, start_row=1):
    for j, col in enumerate(df.columns):
        ws.cell(row=start_row, column=1 + j, value=col)
    style_header_row(ws, start_row, len(df.columns))
    for i, row in enumerate(df.itertuples(index=False), start=1):
        for j, v in enumerate(row):
            ws.cell(row=start_row + i, column=1 + j,
                    value=(v if (pd.notna(v) if not isinstance(v, str) else True) else None))
    style_body_range(ws, start_row + 1, start_row + len(df), len(df.columns), align=LEFT)


# ---------- Workbook ----------
wb = Workbook()

# Sheet 1: Overview
ws = wb.active
ws.title = "1_Overview"
ws["A1"] = "KYHPS 5개년(2019~2023) 패널 정제 마스터 코드북"
ws["A1"].font = TITLE_FONT
ws.merge_cells("A1:H1")
ws["A1"].alignment = CENTER

ws["A3"] = "[데이터 정제 요약]"
ws["A3"].font = SECTION_FONT

phase1_rows = [
    ["대상", "전체(w1)", "w2", "w3", "w4", "w5", "5년 완전응답", "Retention(%)"],
    ["학생", 5051, 4702, 4438, 4409, 4243, len(id_stu), round(100 * len(id_stu) / 5051, 2)],
    ["보호자", 5051, 4689, 4424, 4388, 4182, len(id_par), round(100 * len(id_par) / 5051, 2)],
    ["공통(학생∩보호자)", "-", "-", "-", "-", "-", len(id_com), round(100 * len(id_com) / 5051, 2)],
]
for i, row in enumerate(phase1_rows):
    for j, v in enumerate(row):
        ws.cell(row=5 + i, column=1 + j, value=v)
style_header_row(ws, 5, 8)
style_body_range(ws, 6, 8, 8, CENTER)

ws["A11"] = "[작업 절차 요약]"
ws["A11"].font = SECTION_FONT
proc = [
    "1. 학생 wide 데이터(5,051×1,073) 직접 로드, 보호자 yearly CSV → wide(5,051×164) 자동 병합",
    "2. Phase 1: 차시별 응답 여부 플래그 산출 → 5년 완전응답자 추출",
    "3. Phase 2: 평생 경험형 변수 단조성 강제 재코딩 (한 번이라도 1=있음 → 이후 모두 1)",
    "4. Phase 3: fin_ 접두사 데이터 저장 + 코드북·ID 리스트 산출",
    "5. 보호자 R 스크립트(cp949) 파싱 → 변수별 응답값 라벨 사전 추출",
    "6. 학생 변수는 raw 분포 자동 산출 (코딩북 PDF 미파싱; 라벨은 통계집 PDF 참조 권장)",
]
for i, p in enumerate(proc):
    c = ws.cell(row=12 + i, column=1, value=p)
    c.font = BODY_FONT
    ws.merge_cells(start_row=12 + i, start_column=1, end_row=12 + i, end_column=8)

ws["A20"] = "[산출 파일 안내]"
ws["A20"].font = SECTION_FONT
files = [
    ("fin_student_wide_5y.csv", "5년 완전응답 학생 패널(3,986×1,073), Phase2 재코딩 적용"),
    ("fin_parent_wide_5y.csv", "5년 완전응답 보호자 패널(3,922×164)"),
    ("ID_list_student_5y.csv", "학생 5년완전 응답 설문번호"),
    ("ID_list_parent_5y.csv", "보호자 5년완전 응답 설문번호"),
    ("ID_list_common_5y.csv", "학생∩보호자 5년완전 공통 설문번호 (페어 분석용 N=3,922)"),
    ("parent_value_labels.csv", "보호자 변수별 응답값 라벨(코드=라벨) 사전"),
    ("student_value_distribution.csv", "학생 변수별 응답값 분포 자동 산출표"),
    ("KYHPS_마스터_코드북.xlsx", "본 통합 보고서(현재 파일)"),
]
ws.cell(row=21, column=1, value="파일명")
ws.cell(row=21, column=2, value="설명")
style_header_row(ws, 21, 2)
for i, (fn, desc) in enumerate(files):
    ws.cell(row=22 + i, column=1, value=fn)
    ws.cell(row=22 + i, column=2, value=desc)
style_body_range(ws, 22, 22 + len(files) - 1, 2, LEFT)

autosize_ws(ws)

# Sheet 2: 한계 및 검토
ws = wb.create_sheet("2_한계_및_검토")
ws["A1"] = "데이터 정제·분석상의 한계 및 추가 검토 필요사항"
ws["A1"].font = TITLE_FONT
ws.merge_cells("A1:B1")

sections = [
    ("[1] 선택 편향(Selection Bias)", [
        "• 1차 표본 5,051명 대비 5년 완전응답 학생 3,986명(78.92%), 보호자 3,922명(77.65%) — 약 22% 중도탈락",
        "• 탈락 패턴이 무작위(MCAR)인지 무작위 결측(MAR)인지 검정 필요 — Little's MCAR test 권장",
        "• 가설: 흡연·음주 고위험·저성취·저소득 가구일수록 탈락률 ↑ → 결과의 과소추정 가능성",
        "• 대응 방안: (1) 탈락 vs 잔류 베이스라인 특성 비교(t-test/χ²) (2) 역확률가중(IPW) 적용 (3) 다중대체(MICE) 민감도 분석",
    ]),
    ("[2] 평생 경험 변수의 응답 역전(논리적 불일치)", [
        "• 평생 음주 경험(모금) 단일 변수에서 1,169명·2,312셀 재코딩 — 전체 완전응답자(3,986)의 약 29%",
        "• 원인 추정: (a) 응답자 회상 편향 (b) 설문 문항/지시문 변경 (c) 응답 거부·임의응답",
        "• 보수적 접근: 한 번이라도 '있음(1)' → 이후 모두 1 강제(현 적용)",
        "• 대안 접근: (a) 첫 '있음' 발생 차시 이전을 결측 처리 후 다중대체 (b) 'last-observation-carried-forward'와 비교 민감도",
        "• 흡연 변수 vs 음주 변수의 불일치 빈도 차이 → 음주 회상 신뢰도 낮음을 시사",
    ]),
    ("[3] 변수의 시간 가변성(Time-Variance) 식별", [
        "• 시간 불변(time-invariant): 설문번호, 시도코드, 학교담당자 설문참여번호, 학부모 성별 — 차시 간 일관성 점검 권장",
        "• 단조 비감소: 평생 경험 변수, 학년, 신장(성장기) — 단조성 위반 시 재코딩 또는 결측 처리",
        "• 양방향 가변: 가구 음주자/흡연자 유무, 부모 맞벌이, 가구 경제상태 — 패널 모형의 time-varying covariate로 모델링",
    ]),
    ("[4] 가중치 적용", [
        "• 보호자 데이터: w1~w2는 '종단면 가중치', w3 이후 '횡단면 가중치'로 명칭 변경 — 분석 목적에 맞춰 선택 필요",
        "• 학생 데이터: '종단면 가중치_w1~w5' + '유한모집단보정계수_w1~w5' 동시 존재 — 종단 분석 시 종단면 가중치 사용",
        "• 복합표본 설계 변수: 시도코드(strata), 군집(cluster), 종단면 가중치를 statsmodels의 SurveyDesign 또는 R의 survey 패키지로 처리",
    ]),
    ("[5] 변수명 일관성·코딩 변경", [
        "• 일부 변수는 차시별 신설/삭제(예: 평생담배제품사용경험률은 w1~w4만 존재, 평생 천식/알레르기비염 의사진단은 w5만 존재)",
        "• 차시별 컬럼 수: w1=190, w2=203, w3=223, w4=223, w5=233 — 신규 도입 변수의 결측 처리 주의",
    ]),
    ("[6] 응답값 라벨 출처 한계", [
        "• 보호자: R 스크립트(recode_factor) 파싱으로 정확한 응답값 라벨 확보(168개 변수)",
        "• 학생: R/SPS 스크립트 미제공 → wide CSV의 응답 분포로부터 자동 추정 (정확한 라벨은 통계집 PDF 참조)",
        "• 권장: 통계집 PDF(2019-20, 2021)의 코드북 섹션을 OCR하여 학생 변수 라벨 사전 보강",
    ]),
    ("[7] 결측치 처리 정책", [
        "• 본 정제는 'Complete Case Analysis(완전관찰자 분석)' 기준 — 5년 미응답자 전원 제외",
        "• 한계: 통계적 검정력 ↓, 일반화 가능성 ↓ — Sensitivity로 MICE 다중대체 비교 결과 제시 필요",
        "• 보호자 wide-format 결합 시 outer join → 결측 셀이 추가 발생 가능 (특정 차시 미응답자)",
    ]),
    ("[8] Discussion 작성 권장 포인트", [
        "• 'Why Complete Case?': 인과 추론을 위한 시간 흐름 보존 + 측정 오차 최소화",
        "• 'Limitations': 위 [1]~[7] 항목 + 자기보고식 측정 한계",
        "• 'Sensitivity Analysis': MICE/LOCF/IPW 결과 대비 본 분석 결과의 robustness 보고",
    ]),
]

r = 3
for title, items in sections:
    ws.cell(row=r, column=1, value=title).font = SECTION_FONT
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
    r += 1
    for it in items:
        ws.cell(row=r, column=1, value=it).font = BODY_FONT
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        ws.cell(row=r, column=1).alignment = LEFT
        r += 1
    r += 1

ws.column_dimensions["A"].width = 100

# Sheet 3: 학생 코드북
ws = wb.create_sheet("3_학생_코드북")
write_df(ws, stu_dist, start_row=1)
autosize_ws(ws, max_w=60)
ws.freeze_panes = "A2"

# Sheet 4: 보호자 코드북
ws = wb.create_sheet("4_보호자_코드북")
write_df(ws, par_cb, start_row=1)
autosize_ws(ws, max_w=80)
ws.freeze_panes = "A2"

# Sheet 5: 단조성 검사
ws = wb.create_sheet("5_단조성_검사")
ws["A1"] = "[Phase 2] 평생 경험 변수 단조성 검사·재코딩 결과"
ws["A1"].font = SECTION_FONT
ws.merge_cells("A1:E1")
write_df(ws, phase2, start_row=3)
sum_row = 3 + len(phase2) + 1
ws.cell(row=sum_row, column=1, value="합계").font = Font(name="Arial", bold=True)
ws.cell(row=sum_row, column=4, value=f"=SUM(D4:D{sum_row-1})")
ws.cell(row=sum_row, column=5, value=f"=SUM(E4:E{sum_row-1})")
style_body_range(ws, sum_row, sum_row, 5)

ws.cell(row=sum_row + 2, column=1,
        value="재코딩 로직: 한 번이라도 '있음(1)' → 이후 모든 차시를 '있음(1)'로 강제 (NaN 유지)").font = BODY_FONT
ws.merge_cells(start_row=sum_row + 2, start_column=1, end_row=sum_row + 2, end_column=5)
autosize_ws(ws)

# Sheet 6: ID 리스트
ws = wb.create_sheet("6_ID_5년완전응답")
ws.cell(row=1, column=1, value="학생 5년완전")
ws.cell(row=1, column=2, value="보호자 5년완전")
ws.cell(row=1, column=3, value="공통(학생∩보호자)")
style_header_row(ws, 1, 3)
n_max = max(len(id_stu), len(id_par), len(id_com))
for i in range(n_max):
    if i < len(id_stu):
        ws.cell(row=2 + i, column=1, value=id_stu.iloc[i, 0])
    if i < len(id_par):
        ws.cell(row=2 + i, column=2, value=id_par.iloc[i, 0])
    if i < len(id_com):
        ws.cell(row=2 + i, column=3, value=id_com.iloc[i, 0])
for col in ["A", "B", "C"]:
    ws.column_dimensions[col].width = 22
ws.freeze_panes = "A2"

# 저장
out_path = os.path.join(OUT, "KYHPS_마스터_코드북.xlsx")
wb.save(out_path)
print("saved:", out_path)

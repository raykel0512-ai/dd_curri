"""
parser.py — 교육과정 엑셀 파일 파싱 모듈
단위배당표 / 교과배정표를 읽어 구조화된 데이터로 변환
"""
import pandas as pd
from io import BytesIO

# ── 단위배당표 컬럼 맵 ─────────────────────────────────────────────────────────
# 헤더 구조 (R4 기준):
# col7=1학년1학기, col9=1학년2학기
# col11=2학년세무회계1학기, col13=세무회계2학기
# col15=관세무역1학기,      col17=관세무역2학기
# col19=세무행정1학기,      col21=세무행정2학기
# col23=3학년세무회계1학기, col25=세무회계2학기
# col27=관세무역1학기,      col29=관세무역2학기
# col31=세무행정1학기,      col33=세무행정2학기
COL_MAP = [
    (7,  "1학년", "공통",    "1학기"),
    (9,  "1학년", "공통",    "2학기"),
    (11, "2학년", "세무회계", "1학기"),
    (13, "2학년", "세무회계", "2학기"),
    (15, "2학년", "관세무역", "1학기"),
    (17, "2학년", "관세무역", "2학기"),
    (19, "2학년", "세무행정", "1학기"),
    (21, "2학년", "세무행정", "2학기"),
    (23, "3학년", "세무회계", "1학기"),
    (25, "3학년", "세무회계", "2학기"),
    (27, "3학년", "관세무역", "1학기"),
    (29, "3학년", "관세무역", "2학기"),
    (31, "3학년", "세무행정", "1학기"),
    (33, "3학년", "세무행정", "2학기"),
]

# 과목명 키워드 → 교과(과) 매핑
DEPT_KEYWORD_MAP = {
    "공통국어": "국어과", "문학": "국어과", "화법": "국어과", "독서": "국어과",
    "공통수학": "수학과", "대수": "수학과", "수학I": "수학과", "수학II": "수학과",
    "확률": "수학과", "미적분": "수학과",
    "공통영어": "영어과", "영어I": "영어과", "영어II": "영어과", "토익": "영어과",
    "커뮤니케이션": "영어과", "비즈니스영어": "영어과", "상과지원": "영어과",
    "한국사": "사회과", "통합사회": "사회과",
    "통합과학": "과학과",
    "체육": "예체능과", "스포츠": "예체능과", "음악": "예체능과", "미술": "예체능과",
    "회계": "상업과", "세무": "상업과", "상업": "상업과", "금융": "상업과",
    "무역": "상업과", "기업": "상업과", "사무": "상업과", "컴퓨터": "상업과",
    "프로그래밍": "상업과", "빅데이터": "상업과", "예산": "상업과",
    "수출입": "상업과", "원산지": "상업과", "관세": "상업과", "국제": "상업과",
    "중급": "상업과", "성공적인": "상업과", "노동": "상업과", "직무": "상업과",
    "디지털": "상업과", "컴일": "상업과",
}


def _g(rv, i, default=""):
    """행 값 안전 추출"""
    if i < len(rv) and pd.notna(rv[i]):
        return str(rv[i]).strip().replace("\n", "").replace("\xa0", "")
    return default


def _float(s):
    try:
        return float(str(s).split()[0])
    except Exception:
        return 0.0


def guess_dept(subject_name):
    for kw, dept in DEPT_KEYWORD_MAP.items():
        if kw in subject_name:
            return dept
    return "기타"


# ── 단위배당표 파싱 ────────────────────────────────────────────────────────────
def _parse_sheet(df, entry_year):
    subjects = []
    current_area = None
    current_group = None
    skip_words = {"교과", "과목", "학년", "보통", "전문", "창의", "이수",
                  "학기", "영역", "구분", "비고", "nan", ""}

    for idx, row in df.iterrows():
        if idx < 5:
            continue
        rv = list(row)

        area = _g(rv, 0)
        group = _g(rv, 1)
        name = _g(rv, 4)

        if area and not any(x in area for x in ["소계", "학점", "합계", "교과", "보통", "전문", "창의", "이수"]):
            current_area = area
        if group and group not in {"보통 교과 (군)", "전문 교과 구분"}:
            current_group = group

        if not name or name in skip_words or len(name) < 2:
            continue

        std = _float(_g(rv, 5)) if _g(rv, 5) else 0
        op = _float(_g(rv, 6)) if _g(rv, 6) else 0
        if std == 0 and op == 0:
            continue

        schedule = {}
        for col, grade, track, sem in COL_MAP:
            val_str = _g(rv, col)
            if not val_str:
                continue
            v = _float(val_str)
            if v > 0:
                schedule[f"{grade}|{track}|{sem}"] = int(v)

        if schedule:
            subjects.append({
                "entry_year": entry_year,
                "area": (current_area or "기타").replace("\n", ""),
                "group": (current_group or "").replace("\n", ""),
                "name": name,
                "std_credits": int(std),
                "op_credits": int(op),
                "schedule": schedule,
            })

    return subjects


def parse_curriculum_file(file_obj):
    """단위배당표 xlsx → 과목 리스트"""
    content = file_obj.read() if hasattr(file_obj, "read") else open(file_obj, "rb").read()
    sheets = pd.read_excel(BytesIO(content), sheet_name=None, header=None)

    sheet_map = {}
    for name in sheets.keys():
        if "2026" in name:
            sheet_map[2026] = name
        elif "2025" in name:
            sheet_map[2025] = name
        elif "2024" in name:
            sheet_map[2024] = name

    all_subjects = []
    for entry_year, sheet_name in sorted(sheet_map.items()):
        subs = _parse_sheet(sheets[sheet_name], entry_year)
        all_subjects.extend(subs)

    return all_subjects


# ── 교과배정표 파싱 ────────────────────────────────────────────────────────────
def _parse_alloc_sheet(df, school_year):
    teachers = []
    current_dept = "미분류"
    current_group = {"dept": "미분류", "subject_names": [], "total_hours": 0, "teachers": []}
    in_teacher_section = False

    for idx, row in df.iterrows():
        if idx < 2:
            continue
        rv = list(row)
        col0 = _g(rv, 0)
        col1 = _g(rv, 1)
        col2 = _g(rv, 2)

        is_subject = (not col1 or col1 == "nan") and col2 and col2 not in {"nan", "0", "1", "2", "3", "4", "5", "6", "7", "8"}
        is_teacher = bool(col1) and col1 != "nan"

        if is_subject:
            if in_teacher_section:
                in_teacher_section = False

            try:
                grand = float(rv[28]) if pd.notna(rv[28]) else 0
            except Exception:
                grand = 0

            guessed = guess_dept(col2)
            if grand > 0:
                current_dept = guessed
                current_group = {
                    "dept": guessed,
                    "subject_names": [col2],
                    "total_hours": int(grand),
                    "teachers": [],
                }
            else:
                current_group["subject_names"].append(col2)

        elif is_teacher:
            in_teacher_section = True
            try:
                total = float(rv[28]) if pd.notna(rv[28]) else 0
            except Exception:
                total = 0

            notes = " ".join(
                _g(rv, i) for i in range(29, 36)
                if _g(rv, i) and _g(rv, i) not in {"nan", "0", "1"}
            ).strip()
            is_temp = col1 in {"기간제", "강사", "원어민", "시간강사", "정교사", "순회교사"}

            if total > 0:
                teachers.append({
                    "name": col1,
                    "dept": current_dept,
                    "school_year": school_year,
                    "total_credits": int(total),
                    "notes": notes,
                    "is_temp": is_temp,
                    "subject_group": current_group["subject_names"][0] if current_group["subject_names"] else "",
                })
                current_group["teachers"].append(col1)

    return teachers


def parse_allocation_file(file_obj):
    """교과배정표 xlsx → (교사 dict, 교과군 dict)"""
    content = file_obj.read() if hasattr(file_obj, "read") else open(file_obj, "rb").read()
    sheets = pd.read_excel(BytesIO(content), sheet_name=None, header=None)

    teachers_by_year = {}
    dept_groups_by_year = {}

    for sheet_name, df in sheets.items():
        try:
            year = int(sheet_name)
        except ValueError:
            continue
        if 2025 <= year <= 2028:
            teachers_by_year[str(year)] = _parse_alloc_sheet(df, year)
            dept_groups_by_year[str(year)] = []   # 필요 시 확장

    return teachers_by_year, dept_groups_by_year


# ── 연도별 운영 현황 ───────────────────────────────────────────────────────────
def build_yearly_view(school_year, curriculum):
    grade_map = {0: "1학년", 1: "2학년", 2: "3학년"}
    items = []
    seen = set()

    for sub in curriculum:
        diff = school_year - sub["entry_year"]
        grade = grade_map.get(diff)
        if not grade:
            continue

        tracks = {}
        total = 0
        for key, credits in sub["schedule"].items():
            parts = key.split("|")
            if len(parts) != 3:
                continue
            g, track, sem = parts
            if g == grade:
                tk = f"{track}_{sem}"
                tracks[tk] = credits
                total += credits

        if tracks:
            uid = f"{sub['entry_year']}_{sub['name']}_{grade}"
            if uid not in seen:
                seen.add(uid)
                items.append({
                    "name": sub["name"],
                    "group": sub.get("group", ""),
                    "area": sub.get("area", ""),
                    "grade": grade,
                    "entry_year": sub["entry_year"],
                    "tracks": tracks,
                    "weekly_credits": total,
                })

    return items


# ── 2027 가이드 ───────────────────────────────────────────────────────────────
def build_guidance_2027(curriculum):
    items = []
    for sub in curriculum:
        for key, credits in sub["schedule"].items():
            parts = key.split("|")
            if len(parts) != 3:
                continue
            g, track, sem = parts
            if (sub["entry_year"] == 2025 and g == "3학년") or \
               (sub["entry_year"] == 2026 and g == "2학년"):
                items.append({
                    "name": sub["name"],
                    "grade": g,
                    "cohort": f"{sub['entry_year']}입학",
                    "entry_year": sub["entry_year"],
                    "group": sub.get("group", ""),
                    "area": sub.get("area", ""),
                    "track": track,
                    "sem": sem,
                    "credits": credits,
                })
    return items

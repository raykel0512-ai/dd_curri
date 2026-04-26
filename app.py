# v1.0 - 대동세무고 교육과정 관리 시스템
import streamlit as st
import pandas as pd
import json
from pathlib import Path
import io

from parser import parse_curriculum_file, parse_allocation_file, build_yearly_view, build_guidance_2027
from storage import load_edits, save_edits

st.set_page_config(
    page_title="대동세무고 교육과정 관리",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 전체 배경 */
.stApp { background-color: #0d1117; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

/* 사이드바 */
section[data-testid="stSidebar"] { background-color: #161b24; border-right: 1px solid #2a3448; }
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

/* 헤더 */
h1, h2, h3 { color: #e2e8f0 !important; font-weight: 700; }
h1 { font-size: 1.4rem !important; }
h2 { font-size: 1.1rem !important; border-bottom: 1px solid #2a3448; padding-bottom: 6px; }
h3 { font-size: 0.95rem !important; color: #94a3b8 !important; }

/* 카드형 컨테이너 */
div[data-testid="stVerticalBlock"] > div[style] { border-radius: 10px; }

/* 메트릭 */
div[data-testid="stMetric"] {
    background: #192030; border: 1px solid #2a3448;
    border-radius: 8px; padding: 12px 16px;
}
div[data-testid="stMetricLabel"] p { color: #94a3b8 !important; font-size: 0.75rem !important; }
div[data-testid="stMetricValue"] { color: #e2e8f0 !important; font-size: 1.6rem !important; }

/* 데이터프레임 */
.stDataFrame { border: 1px solid #2a3448; border-radius: 8px; overflow: hidden; }
iframe[title="st_aggrid"] { border-radius: 8px; }

/* 탭 */
div[data-testid="stTabs"] button {
    color: #94a3b8 !important; font-size: 0.82rem;
    border-bottom: 2px solid transparent !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #3b82f6 !important; border-bottom-color: #3b82f6 !important;
}

/* 버튼 */
.stButton > button {
    background: #1e2535; border: 1px solid #2a3448;
    color: #e2e8f0; border-radius: 6px; font-size: 0.82rem;
}
.stButton > button:hover { border-color: #3b82f6; color: #3b82f6; }

/* info / success / warning 박스 */
div[data-testid="stAlert"] { border-radius: 8px; font-size: 0.82rem; }

/* selectbox, multiselect */
div[data-baseweb="select"] > div { background-color: #1e2535 !important; border-color: #2a3448 !important; }

/* 텍스트 */
p, li, span { color: #e2e8f0; }
.stMarkdown p { font-size: 0.85rem; color: #94a3b8; }

/* 태그 뱃지 */
.badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 0.72rem; font-weight: 600; line-height: 1.4;
}
.badge-blue { background: rgba(59,130,246,.15); color: #60a5fa; }
.badge-green { background: rgba(34,197,94,.15); color: #4ade80; }
.badge-yellow { background: rgba(234,179,8,.15); color: #facc15; }
.badge-orange { background: rgba(249,115,22,.15); color: #fb923c; }
.badge-red { background: rgba(239,68,68,.15); color: #f87171; }
.badge-gray { background: rgba(100,116,139,.15); color: #94a3b8; }
.badge-purple { background: rgba(99,102,241,.15); color: #a5b4fc; }
</style>
""", unsafe_allow_html=True)

# ── 세션 상태 초기화 ──────────────────────────────────────────────────────────
if "curriculum" not in st.session_state:
    st.session_state.curriculum = None
if "teachers" not in st.session_state:
    st.session_state.teachers = None
if "dept_groups" not in st.session_state:
    st.session_state.dept_groups = None
if "yearly_view" not in st.session_state:
    st.session_state.yearly_view = None
if "guidance" not in st.session_state:
    st.session_state.guidance = None
if "edits" not in st.session_state:
    st.session_state.edits = load_edits()

# ── 사이드바 ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📚 대동세무고\n### 교육과정 관리 시스템")
    st.markdown("---")

    st.markdown("#### 📂 데이터 불러오기")
    st.caption("엑셀 파일을 업로드하거나 저장된 데이터를 사용합니다.")

    curr_file = st.file_uploader(
        "단위배당표 (교육과정)",
        type=["xlsx"],
        key="curr_upload",
        help="2026학년도 통합 교육과정 단위배당표 xlsx"
    )
    alloc_file = st.file_uploader(
        "교과배정표 (교사)",
        type=["xlsx"],
        key="alloc_upload",
        help="교과배정표 연습 xlsx"
    )

    if st.button("🔄 데이터 파싱", type="primary", use_container_width=True):
        if curr_file and alloc_file:
            with st.spinner("파싱 중..."):
                try:
                    curriculum = parse_curriculum_file(curr_file)
                    teachers, dept_groups = parse_allocation_file(alloc_file)
                    yearly_view = {
                        str(sy): build_yearly_view(sy, curriculum)
                        for sy in [2025, 2026, 2027]
                    }
                    guidance = build_guidance_2027(curriculum)

                    st.session_state.curriculum = curriculum
                    st.session_state.teachers = teachers
                    st.session_state.dept_groups = dept_groups
                    st.session_state.yearly_view = yearly_view
                    st.session_state.guidance = guidance
                    st.success(f"✅ 파싱 완료!\n과목 {len(curriculum)}개 · 교사 {sum(len(v) for v in teachers.values())}명")
                except Exception as e:
                    st.error(f"파싱 오류: {e}")
        else:
            st.warning("두 파일 모두 업로드해주세요.")

    # 기본 데이터 로드 (파일 없을 때)
    default_path = Path(__file__).parent / "data" / "curriculum_data.json"
    if st.session_state.curriculum is None and default_path.exists():
        with open(default_path, encoding="utf-8") as f:
            d = json.load(f)
        st.session_state.curriculum = d.get("curriculum", [])
        st.session_state.teachers = d.get("teachers", {})
        st.session_state.dept_groups = d.get("dept_groups", {})
        st.session_state.yearly_view = d.get("yearly_view", {})
        st.session_state.guidance = d.get("guidance_2027", [])

    st.markdown("---")
    st.markdown("#### ⚙️ 학년도 선택")
    school_year = st.selectbox(
        "", [2025, 2026, 2027], index=1,
        format_func=lambda y: f"{y}학년도",
        key="school_year"
    )

    if st.session_state.curriculum:
        st.markdown("---")
        st.markdown("#### 💾 저장")
        if st.button("변경사항 저장", use_container_width=True):
            save_edits(st.session_state.edits)
            st.success("저장 완료!")

        # CSV 내보내기
        edits = st.session_state.edits
        cross_rows = edits.get("cross_teaching", {}).get(str(school_year), [])
        if cross_rows:
            df_export = pd.DataFrame(cross_rows)
            csv_buf = io.StringIO()
            df_export.to_csv(csv_buf, index=False, encoding="utf-8-sig")
            st.download_button(
                "📥 상치교과 CSV 다운로드",
                data=csv_buf.getvalue().encode("utf-8-sig"),
                file_name=f"상치교과_{school_year}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    st.markdown("---")
    st.caption("대동세무고등학교 교육과정 관리 시스템 v1.0")

# ── 데이터 없을 때 안내 ────────────────────────────────────────────────────────
if st.session_state.curriculum is None:
    st.title("📚 대동세무고 교육과정 관리 시스템")
    st.info("👈 사이드바에서 엑셀 파일 두 개를 업로드하고 **데이터 파싱** 버튼을 눌러주세요.")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **필요한 파일:**
        - 📄 단위배당표 (2026학년도 통합 교육과정)
        - 📄 교과배정표 (2025~2028 연습본)
        """)
    with col2:
        st.markdown("""
        **주요 기능:**
        - 📅 연도별 운영 과목 현황
        - 📚 입학연도별 교육과정 편성표
        - 👩‍🏫 교사 수급 분석
        - 🔄 상치교과 관리 (수기 편집·저장)
        - 🗺️ 2027학년도 편성 가이드
        """)
    st.stop()

# ── 메인 탭 ──────────────────────────────────────────────────────────────────
SY = str(school_year)
curriculum = st.session_state.curriculum
teachers_all = st.session_state.teachers or {}
dept_groups_all = st.session_state.dept_groups or {}
yearly_view_all = st.session_state.yearly_view or {}
guidance = st.session_state.guidance or []
edits = st.session_state.edits

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📅 연도별 운영 현황",
    "📚 교육과정 편성표",
    "👩‍🏫 교사 수급 분석",
    "🔄 상치교과 관리",
    "🗺️ 2027 편성 가이드",
])

# ════════════════════════════════════════════════════════════════
# TAB 1: 연도별 운영 현황
# ════════════════════════════════════════════════════════════════
with tab1:
    st.markdown(f"## {school_year}학년도 운영 현황")
    items = yearly_view_all.get(SY, [])

    if not items:
        st.warning("해당 학년도 데이터가 없습니다.")
    else:
        g1 = [i for i in items if i["grade"] == "1학년"]
        g2 = [i for i in items if i["grade"] == "2학년"]
        g3 = [i for i in items if i["grade"] == "3학년"]
        total_ch = sum(i["weekly_credits"] for i in items)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("총 운영 과목", f"{len(items)}개")
        c2.metric("1학년 과목", f"{len(g1)}개", help=f"{school_year}입학")
        c3.metric("2학년 과목", f"{len(g2)}개", help=f"{school_year-1}입학")
        c4.metric("3학년 과목", f"{len(g3)}개", help=f"{school_year-2}입학")
        c5.metric("주간 총학점", f"{total_ch}")

        st.markdown("---")

        # 필터
        col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
        with col_f1:
            grade_filter = st.selectbox("학년 필터", ["전체", "1학년", "2학년", "3학년"], key="yf_grade")
        with col_f2:
            area_filter = st.selectbox("교과 유형", ["전체", "보통교과", "전문교과"], key="yf_area")
        with col_f3:
            search = st.text_input("과목명 검색", placeholder="예: 국어, 세무 …", key="yf_search")

        filtered = items
        if grade_filter != "전체":
            filtered = [i for i in filtered if i["grade"] == grade_filter]
        if area_filter == "보통교과":
            filtered = [i for i in filtered if not any(x in i["area"] for x in ["전문", "전공", "고시"])]
        elif area_filter == "전문교과":
            filtered = [i for i in filtered if any(x in i["area"] for x in ["전문", "전공", "고시"])]
        if search:
            filtered = [i for i in filtered if search in i["name"] or search in (i["group"] or "")]

        TRACKS = ["세무회계", "관세무역", "세무행정"]

        for grade in ["1학년", "2학년", "3학년"]:
            grade_items = [i for i in filtered if i["grade"] == grade]
            if not grade_items:
                continue
            grade_colors = {"1학년": "🔵", "2학년": "🟢", "3학년": "🟠"}
            st.markdown(f"### {grade_colors[grade]} {grade} ({len(grade_items)}과목)")

            rows = []
            is_common = (grade == "1학년")
            for item in grade_items:
                t = item["tracks"]
                row = {
                    "교과군": item["group"] or "-",
                    "과목명": item["name"],
                    "입학년": str(item["entry_year"]),
                }
                if is_common:
                    row["1학기"] = t.get("공통_1학기", "")
                    row["2학기"] = t.get("공통_2학기", "")
                    row["비고"] = "(전학급 공통)"
                else:
                    for tr in TRACKS:
                        row[f"{tr[:2]} 1학기"] = t.get(f"{tr}_1학기", "") or ""
                        row[f"{tr[:2]} 2학기"] = t.get(f"{tr}_2학기", "") or ""
                row["주간학점"] = item["weekly_credits"]
                rows.append(row)

            df = pd.DataFrame(rows)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "주간학점": st.column_config.ProgressColumn(
                        "주간학점", min_value=0, max_value=40, format="%d"
                    )
                }
            )

# ════════════════════════════════════════════════════════════════
# TAB 2: 교육과정 편성표
# ════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("## 교육과정 편성표")
    st.caption("입학년도별 전체 교육과정 — 1학기/2학기 분리 표시")

    col_f1, col_f2 = st.columns([3, 4])
    with col_f1:
        entry_filter = st.multiselect(
            "입학년도", [2024, 2025, 2026],
            default=[2024, 2025, 2026],
            format_func=lambda y: f"{y}입학 (현 고{2026-y+1})"
        )
    with col_f2:
        curr_search = st.text_input("과목명/교과군 검색", placeholder="국어, 세무, 회계 …", key="curr_search")

    filtered_curr = [s for s in curriculum if s["entry_year"] in entry_filter]
    if curr_search:
        filtered_curr = [s for s in filtered_curr if curr_search in s["name"] or curr_search in (s["group"] or "")]

    SCHED_COLS = [
        ("1학년", "공통", "1학기"), ("1학년", "공통", "2학기"),
        ("2학년", "세무회계", "1학기"), ("2학년", "세무회계", "2학기"),
        ("2학년", "관세무역", "1학기"), ("2학년", "관세무역", "2학기"),
        ("2학년", "세무행정", "1학기"), ("2학년", "세무행정", "2학기"),
        ("3학년", "세무회계", "1학기"), ("3학년", "세무회계", "2학기"),
        ("3학년", "관세무역", "1학기"), ("3학년", "관세무역", "2학기"),
        ("3학년", "세무행정", "1학기"), ("3학년", "세무행정", "2학기"),
    ]

    rows = []
    for s in filtered_curr:
        sch = s["schedule"]
        row = {
            "입학": str(s["entry_year"]),
            "교과영역": (s["area"] or "").replace("\n", ""),
            "교과군": s["group"] or "-",
            "과목명": s["name"],
            "기준": s["std_credits"],
            "운영": s["op_credits"],
        }
        for grade, track, sem in SCHED_COLS:
            k = f"{grade}|{track}|{sem}"
            v = sch.get(k, "")
            col_label = f"{grade[:1]}학년 {track[:2]} {sem[:1]}학기"
            row[col_label] = v if v else ""
        rows.append(row)

    if rows:
        df_curr = pd.DataFrame(rows)
        st.dataframe(df_curr, use_container_width=True, hide_index=True)
        st.caption(f"총 {len(rows)}개 과목")
    else:
        st.info("조건에 맞는 과목이 없습니다.")

# ════════════════════════════════════════════════════════════════
# TAB 3: 교사 수급 분석
# ════════════════════════════════════════════════════════════════
with tab3:
    st.markdown(f"## {school_year}학년도 교사 수급 분석")

    teachers = teachers_all.get(SY, [])
    dept_groups = dept_groups_all.get(SY, [])

    real_t = [t for t in teachers if not t["is_temp"] and t["total_credits"] > 0]
    temp_t = [t for t in teachers if t["is_temp"] and t["total_credits"] > 0]
    avg_load = round(sum(t["total_credits"] for t in real_t) / len(real_t)) if real_t else 0
    over_t = [t for t in real_t if t["total_credits"] > 18]
    under_t = [t for t in real_t if t["total_credits"] < 14]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("정규 교사", f"{len(real_t)}명")
    c2.metric("기간제·강사", f"{len(temp_t)}명")
    c3.metric("평균 시수", f"{avg_load}시간")
    c4.metric("시수 초과 (18+)", f"{len(over_t)}명",
              delta="주의" if over_t else None,
              delta_color="inverse" if over_t else "off")
    c5.metric("시수 부족 (-14)", f"{len(under_t)}명",
              delta="확인필요" if under_t else None,
              delta_color="inverse" if under_t else "off")

    if over_t:
        st.warning(f"⚠️ 시수 초과 우려: {', '.join(t['name'] for t in over_t)}")
    crossed = [t for t in real_t if t.get("notes") and len(t["notes"]) > 2]
    if crossed:
        st.warning(f"🔄 상치교과 주의: {', '.join(t['name']+'('+t['notes'][:30]+')' for t in crossed)}")

    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 📊 교과별 현황")
        dept_map = {}
        for t in teachers:
            if t["total_credits"] > 0:
                d = t["dept"]
                if d not in dept_map:
                    dept_map[d] = {"real": [], "temp": [], "total_load": 0}
                if t["is_temp"]:
                    dept_map[d]["temp"].append(t)
                else:
                    dept_map[d]["real"].append(t)
                dept_map[d]["total_load"] += t["total_credits"]

        dept_rows = []
        for dept, info in dept_map.items():
            if not dept or dept == "미분류":
                continue
            avg2 = round(info["total_load"] / len(info["real"])) if info["real"] else 0
            status = "⚠️ 초과" if avg2 > 18 else ("✅ 적정" if avg2 >= 14 else "🔶 부족")
            dept_rows.append({
                "교과(과)": dept,
                "정규": len(info["real"]),
                "기간제": len(info["temp"]),
                "총 시수": info["total_load"],
                "인당 평균": avg2,
                "상태": status,
            })
        if dept_rows:
            st.dataframe(pd.DataFrame(dept_rows), use_container_width=True, hide_index=True)

    with col_right:
        st.markdown("### 👩‍🏫 교사별 시수")
        dept_options = ["전체"] + sorted(set(t["dept"] for t in teachers if t["dept"] and t["dept"] != "미분류"))
        dept_sel = st.selectbox("교과 필터", dept_options, key="dept_sel")
        teacher_search = st.text_input("교사명 검색", placeholder="이름 입력", key="t_search")

        t_filtered = [t for t in teachers if t["total_credits"] > 0]
        if dept_sel != "전체":
            t_filtered = [t for t in t_filtered if t["dept"] == dept_sel]
        if teacher_search:
            t_filtered = [t for t in t_filtered if teacher_search in t["name"]]

        t_rows = []
        for t in t_filtered:
            load = t["total_credits"]
            status = "⚠️ 초과" if load > 18 else ("✅ 적정" if load >= 14 else "🔶 부족")
            t_rows.append({
                "교사명": t["name"] + (" (기간제)" if t["is_temp"] else ""),
                "교과(과)": t["dept"],
                "시수": load,
                "상태": status,
            })
        if t_rows:
            st.dataframe(
                pd.DataFrame(t_rows),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "시수": st.column_config.ProgressColumn(
                        "시수", min_value=0, max_value=22, format="%d"
                    )
                }
            )

# ════════════════════════════════════════════════════════════════
# TAB 4: 상치교과 관리
# ════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("## 🔄 상치교과 관리")
    st.caption("수기로 편집하고 저장합니다. 사이드바의 저장 버튼으로 JSON 파일에 기록됩니다.")

    cross_yr = st.selectbox("학년도", [2025, 2026, 2027, 2028],
                             index=1, format_func=lambda y: f"{y}학년도", key="cross_yr")
    cross_key = str(cross_yr)

    # 초기화: 교과배정표 notes에서 자동 생성
    if "cross_teaching" not in edits:
        edits["cross_teaching"] = {}
    if cross_key not in edits["cross_teaching"]:
        auto_rows = []
        for t in teachers_all.get(cross_key, []):
            if t.get("notes") and len(t["notes"]) > 2 and not t["is_temp"]:
                auto_rows.append({
                    "교사명": t["name"],
                    "소속교과": t["dept"],
                    "상치담당과목": t["notes"],
                    "학년": "",
                    "학기": "",
                    "시수": "",
                    "메모": "",
                })
        edits["cross_teaching"][cross_key] = auto_rows if auto_rows else [
            {"교사명": "", "소속교과": "", "상치담당과목": "", "학년": "", "학기": "", "시수": "", "메모": ""}
        ]

    st.info("✏️ 아래 표를 직접 클릭해서 편집할 수 있습니다.")

    cross_df = pd.DataFrame(edits["cross_teaching"][cross_key])
    edited_df = st.data_editor(
        cross_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "교사명": st.column_config.TextColumn("교사명", width="small"),
            "소속교과": st.column_config.SelectboxColumn(
                "소속교과", width="small",
                options=["국어과", "수학과", "영어과", "사회과", "과학과", "예체능과", "상업과", "기타"]
            ),
            "상치담당과목": st.column_config.TextColumn("상치담당과목"),
            "학년": st.column_config.SelectboxColumn("학년", width="small", options=["", "1학년", "2학년", "3학년"]),
            "학기": st.column_config.SelectboxColumn("학기", width="small", options=["", "1학기", "2학기", "연간"]),
            "시수": st.column_config.NumberColumn("시수", width="small", min_value=0, max_value=20),
            "메모": st.column_config.TextColumn("메모"),
        },
        key=f"cross_editor_{cross_key}"
    )
    edits["cross_teaching"][cross_key] = edited_df.to_dict("records")
    st.session_state.edits = edits

    st.markdown("---")
    st.markdown("### 📝 교원 배치 메모")
    if "teacher_memos" not in edits:
        edits["teacher_memos"] = {}
    memo = st.text_area(
        f"{cross_yr}학년도 메모",
        value=edits["teacher_memos"].get(cross_key, ""),
        height=150,
        placeholder="학년도별 교원 배치 특이사항, 협의 내용 등을 자유롭게 기록하세요.",
        key=f"memo_{cross_key}"
    )
    edits["teacher_memos"][cross_key] = memo
    st.session_state.edits = edits

# ════════════════════════════════════════════════════════════════
# TAB 5: 2027 편성 가이드
# ════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("## 🗺️ 2027학년도 교육과정 편성 가이드")
    st.info("📌 2027학년도 구성: **2025입학 고3** + **2026입학 고2** + **2027입학 고1(신규 편성 필요)**")

    g3_subs = list(set(g["name"] for g in guidance if g["grade"] == "3학년"))
    g2_subs = list(set(g["name"] for g in guidance if g["grade"] == "2학년"))
    groups = list(set(g["group"] for g in guidance))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("고3 예상 과목", f"{len(g3_subs)}개", help="2025입학 기준")
    c2.metric("고2 예상 과목", f"{len(g2_subs)}개", help="2026입학 기준")
    c3.metric("교과군", f"{len(groups)}종")
    c4.metric("고1 신규 편성", "필요", help="2027입학 교육과정")

    st.markdown("---")
    col_cl, col_note = st.columns(2)

    with col_cl:
        st.markdown("### ✅ 편성 체크리스트")
        if "checklist" not in edits:
            edits["checklist"] = [
                {"done": True,  "text": "2025입학 3학년 교육과정 확정"},
                {"done": True,  "text": "2026입학 2학년 교육과정 확정"},
                {"done": False, "text": "2027입학 1학년 교육과정 신규 편성"},
                {"done": False, "text": "2027학년도 교사 수급 계획 수립"},
                {"done": False, "text": "기간제·강사 필요 인원 파악"},
                {"done": False, "text": "상치교과 배정 계획 확인"},
                {"done": False, "text": "3학년 선택과목(코스형) 최종 확정"},
                {"done": False, "text": "총 이수학점 적법성 검토 (192학점)"},
            ]

        for i, item in enumerate(edits["checklist"]):
            checked = st.checkbox(item["text"], value=item["done"], key=f"chk_{i}")
            edits["checklist"][i]["done"] = checked

        new_item = st.text_input("새 항목 추가", key="new_chk", placeholder="항목 입력 후 Enter")
        if new_item:
            edits["checklist"].append({"done": False, "text": new_item})
            st.rerun()
        st.session_state.edits = edits

    with col_note:
        st.markdown("### ⚠️ 주의사항 및 권고")
        st.warning("영어과 수업시수 증가 추세 — 상치교과 또는 추가 배치 검토 필요")
        st.warning("과학과 기간제 운영 중 — 2027 정규교사 확보 여부 확인")
        st.info("3학년 코스형(택1) 과목은 수강 인원에 따라 통합/분리 여부 결정")
        st.info("2027 신입생 교육과정은 2026입학 구조를 베이스로 검토 권장")

    st.markdown("---")
    st.markdown("### 📋 예상 운영 과목 상세 (고2·고3)")

    grade_sel = st.radio("학년 필터", ["전체", "3학년 (2025입학)", "2학년 (2026입학)"],
                          horizontal=True, key="guide_grade")

    filtered_g = guidance
    if "3학년" in grade_sel:
        filtered_g = [g for g in guidance if g["grade"] == "3학년"]
    elif "2학년" in grade_sel:
        filtered_g = [g for g in guidance if g["grade"] == "2학년"]

    if filtered_g:
        df_g = pd.DataFrame([{
            "학년": g["grade"],
            "코호트": g["cohort"],
            "교과군": g["group"] or "-",
            "과목명": g["name"],
            "학과/트랙": g["track"],
            "학기": g["sem"],
            "학점": g["credits"],
        } for g in filtered_g])
        st.dataframe(df_g, use_container_width=True, hide_index=True)
        st.caption(f"총 {len(filtered_g)}건")
    else:
        st.info("데이터 없음")

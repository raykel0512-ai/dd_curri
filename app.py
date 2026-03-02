import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="교과 시수 배정 시스템", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 1. 데이터 불러오기 및 정제 ---
@st.cache_data(ttl=10)
def load_and_clean_data():
    try:
        curr = conn.read(worksheet="curriculum_data")
        tech = conn.read(worksheet="teacher_data")
        
        curr.columns = curr.columns.str.strip()
        tech.columns = tech.columns.str.strip()
        
        # [핵심 수정] 모든 열의 데이터 타입을 안전하게 고정
        curr['학년'] = curr['학년'].astype(str).replace('nan', '')
        curr['교과군'] = curr['교과군'].fillna('').astype(str)
        curr['교과명'] = curr['교과명'].fillna('').astype(str)
        curr['주당시수'] = pd.to_numeric(curr['주당시수'], errors='coerce').fillna(0)
        curr['분반수'] = pd.to_numeric(curr['분반수'], errors='coerce').fillna(8)
        
        tech['성함'] = tech['성함'].fillna('').astype(str)
        tech['담당교과군'] = tech['담당교과군'].fillna('').astype(str)
        tech['배정시수'] = pd.to_numeric(tech['배정시수'], errors='coerce').fillna(0)
        
        return curr, tech
    except Exception as e:
        return None, None

# 세션 상태 초기화
if 'curr_df' not in st.session_state or 'tech_df' not in st.session_state:
    c_raw, t_raw = load_and_clean_data()
    st.session_state.curr_df = c_raw if c_raw is not None else pd.DataFrame(columns=['학년', '교과군', '교과명', '구분', '주당시수', '분반수', '비고'])
    st.session_state.tech_df = t_raw if t_raw is not None else pd.DataFrame(columns=['성함', '담당교과군', '배정시수', '비고'])

# --- 2. 실시간 계산용 안전 함수 ---
def get_safe_calculation_data():
    c = st.session_state.curr_df.copy()
    t = st.session_state.tech_df.copy()
    # 계산 직전 다시 한번 숫자 변환 (에디터 입력값 대응)
    c['주당시수'] = pd.to_numeric(c['주당시수'], errors='coerce').fillna(0)
    c['분반수'] = pd.to_numeric(c['분반수'], errors='coerce').fillna(8)
    t['배정시수'] = pd.to_numeric(t['배정시수'], errors='coerce').fillna(0)
    # 학년 열을 문자열로 통일 (contains 에러 방지)
    c['학년'] = c['학년'].astype(str)
    return c, t

st.title("🏫 학교 교과 시수 관리 시스템")

# --- 사이드바 요약 ---
with st.sidebar:
    st.header("📊 학교 시수 요약")
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    calc_curr, calc_tech = get_safe_calculation_data()

    # 교과 총 필요 시수 (주당시수 * 8학급)
    academic_need = (calc_curr['주당시수'] * 8).sum() 
    hr_fixed_need = 2 * 24 # 담임/부담임 고정분
    
    total_need = academic_need + hr_fixed_need
    total_sup = calc_tech['배정시수'].sum()
    
    st.metric("교과 필요 시수 합계", f"{int(academic_need)}H")
    st.metric("담임/부담임 시수 (고정)", f"{int(hr_fixed_need)}H")
    st.metric("교원 공급 시수 (52명)", f"{int(total_sup)}H")
    st.metric("전체 시수 균형", f"{int(total_sup - total_need)}H", delta=int(total_sup - total_need))

# --- 메인 탭 ---
tab1, tab2, tab3 = st.tabs(["📚 교과 편제(32H 검증)", "👨‍🏫 교원 배정(12~16H)", "⚖️ 교과군별 분석"])

with tab1:
    st.subheader("1. 학년별 교과 편제 (목표: 32H)")
    c_eval, _ = get_safe_calculation_data()
    cols = st.columns(3)
    for i, g in enumerate(["1", "2", "3"]):
        # [수정된 부분] 열을 문자열로 바꾼 후 검색하여 AttributeError 방지
        g_sum = c_eval[c_eval['학년'].str.contains(g, na=False)]['주당시수'].sum()
        if g_sum == 32:
            cols[i].success(f"✅ {g}학년: {int(g_sum)}/32H")
        else:
            cols[i].warning(f"⚠️ {g}학년: {int(g_sum)}/32H")

    st.session_state.curr_df = st.data_editor(st.session_state.curr_df, num_rows="dynamic", use_container_width=True, key="edit_curr")

with tab2:
    st.subheader("2. 교원별 개인 시수 관리")
    _, t_eval = get_safe_calculation_data()
    invalid = t_eval[(t_eval['배정시수'] < 12) | (t_eval['배정시수'] > 16)]
    if not invalid.empty:
        st.error(f"⚠️ 시수 범위(12-16H) 미달/초과자 존재")
    st.session_state.tech_df = st.data_editor(st.session_state.tech_df, num_rows="dynamic", use_container_width=True, key="edit_tech")

with tab3:
    st.subheader("3. 교과군별 과부족 분석")
    c_f, t_f = get_safe_calculation_data()
    if not c_f.empty and not t_f.empty:
        demand = c_f.groupby('교과군')['주당시수'].sum() * 8
        demand = demand.reset_index().rename(columns={'주당시수': '필요시수'})
        supply = t_f.groupby('담당교과군')['배정시수'].sum().reset_index()
        supply.columns = ['교과군', '공급시수']
        
        report = pd.merge(demand, supply, on='교과군', how='outer').fillna(0)
        report['과부족'] = report['공급시수'] - report['필요시수']
        st.dataframe(report.style.background_gradient(subset=['과부족'], cmap='RdYlGn'), use_container_width=True)

# --- 저장 ---
st.divider()
if st.button("💾 모든 변경사항 구글 시트에 최종 저장", use_container_width=True):
    try:
        conn.update(worksheet="curriculum_data", data=st.session_state.curr_df)
        conn.update(worksheet="teacher_data", data=st.session_state.tech_df)
        st.cache_data.clear()
        st.success("✅ 저장 완료!")
        st.balloons()
    except Exception as e:
        st.error(f"저장 오류: {e}")

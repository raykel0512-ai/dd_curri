import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="교과 시수 배정 시스템", layout="wide")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        curr = conn.read(worksheet="curriculum_data")
        tech = conn.read(worksheet="teacher_data")
        
        # 열 이름 공백 제거
        curr.columns = curr.columns.str.strip()
        tech.columns = tech.columns.str.strip()
        
        return curr, tech
    except Exception as e:
        return None, None

# 데이터 초기화 로직 (오류 방지)
if 'curr_df' not in st.session_state or 'tech_df' not in st.session_state:
    c_raw, t_raw = load_data()
    st.session_state.curr_df = c_raw if c_raw is not None else pd.DataFrame(columns=['학년', '교과군', '교과명', '주당시수', '비고'])
    st.session_state.tech_df = t_raw if t_raw is not None else pd.DataFrame(columns=['성함', '담당교과군', '배정시수', '비고'])

# --- 데이터 안전 변환 함수 ---
def get_safe_df(df, col_name):
    """특정 열을 강제로 숫자로 변환한 카피본 반환"""
    temp_df = df.copy()
    if col_name in temp_df.columns:
        temp_df[col_name] = pd.to_numeric(temp_df[col_name], errors='coerce').fillna(0)
    return temp_df

st.title("🏫 학교 교과 시수 매칭 시스템 (32H 기준)")

# --- 사이드바: 계산 로직 강화 ---
with st.sidebar:
    st.header("📊 학교 시수 요약")
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    
    # 계산용 안전 데이터 생성
    safe_curr = get_safe_df(st.session_state.curr_df, '주당시수')
    safe_tech = get_safe_df(st.session_state.tech_df, '배정시수')

    # 교과 필요 시수 (32H * 24학급)
    # 학년별로 32시간을 다 채웠을 때 768시간이 됩니다.
    academic_need = safe_curr['주당시수'].sum() * 8
    
    # 담임/부담임 고정 시수 (2H * 24학급)
    hr_fixed_need = 2 * 24 
    
    total_need = academic_need + hr_fixed_need
    total_sup = safe_tech['배정시수'].sum()
    
    st.metric("교과 필요 시수 합계", f"{int(academic_need)}H")
    st.metric("담임/부담임 시수 (고정)", f"{int(hr_fixed_need)}H")
    st.metric("교원 공급 시수 (52명)", f"{int(total_sup)}H")
    
    diff = total_sup - total_need
    st.metric("전체 시수 균형", f"{int(diff)}H", delta=int(diff))

# --- 메인 화면 탭 ---
tab1, tab2, tab3 = st.tabs(["📚 교과 편제(32H 검증)", "👨‍🏫 교원 배정(12~16H)", "⚖️ 교과군별 분석"])

with tab1:
    st.subheader("1. 학년별 교과 편제 (목표: 학년별 32H)")
    
    # 학년별 검증 표시
    cols = st.columns(3)
    curr_eval = get_safe_df(st.session_state.curr_df, '주당시수')
    for i, g in enumerate(["1", "2", "3"]):
        g_sum = curr_eval[curr_eval['학년'].astype(str) == g]['주당시수'].sum()
        if g_sum == 32:
            cols[i].success(f"✅ {g}학년: {int(g_sum)}/32H")
        else:
            cols[i].warning(f"⚠️ {g}학년: {int(g_sum)}/32H")

    # 데이터 에디터
    st.session_state.curr_df = st.data_editor(st.session_state.curr_df, num_rows="dynamic", use_container_width=True, key="edit_curr")

with tab2:
    st.subheader("2. 교원별 개인 시수 관리")
    tech_eval = get_safe_df(st.session_state.tech_df, '배정시수')
    
    invalid = tech_eval[(tech_eval['배정시수'] < 12) | (tech_eval['배정시수'] > 16)]
    if not invalid.empty:
        st.error(f"⚠️ 시수 범위(12-16H) 미달/초과자 존재")
        
    st.session_state.tech_df = st.data_editor(st.session_state.tech_df, num_rows="dynamic", use_container_width=True, key="edit_tech")

with tab3:
    st.subheader("3. 교과군별 과부족 분석")
    
    if not st.session_state.curr_df.empty and not st.session_state.tech_df.empty:
        # 안전한 계산용 데이터 사용
        c_final = get_safe_df(st.session_state.curr_df, '주당시수')
        t_final = get_safe_df(st.session_state.tech_df, '배정시수')
        
        # 수요 (교과군별 주당시수합 * 8)
        demand = c_final.groupby('교과군')['주당시수'].sum() * 8
        demand = demand.reset_index().rename(columns={'주당시수': '필요시수'})
        
        # 공급 (교과군별 배정시수합)
        supply = t_final.groupby('담당교과군')['배정시수'].sum().reset_index()
        supply.columns = ['교과군', '공급시수']
        
        # 분석표 결합
        report = pd.merge(demand, supply, on='교과군', how='outer').fillna(0)
        report['과부족'] = report['공급시수'] - report['필요시수']
        
        def color_diff(val):
            if val < 0: return 'background-color: #ffcccc'
            if val > 0: return 'background-color: #ccffcc'
            return ''
            
        st.dataframe(report.style.applymap(color_diff, subset=['과부족']), use_container_width=True)
    else:
        st.info("데이터를 입력하면 분석표가 나타납니다.")

# --- 저장 ---
st.divider()
if st.button("💾 모든 변경사항 구글 시트에 최종 저장", use_container_width=True):
    try:
        conn.update(worksheet="curriculum_data", data=st.session_state.curr_df)
        conn.update(worksheet="teacher_data", data=st.session_state.tech_df)
        st.cache_data.clear()
        st.success("✅ 저장이 완료되었습니다!")
        st.balloons()
    except Exception as e:
        st.error(f"저장 오류: {e}")

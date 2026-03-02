import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="시수 조절 도우미", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# 1. 데이터 로드 및 전처리 함수
@st.cache_data(ttl=60) # 할당량 문제를 위해 1분간 캐시
def get_data():
    try:
        curr = conn.read(worksheet="curriculum_data")
        tech = conn.read(worksheet="teacher_data")
        
        # [중요] 열 이름의 앞뒤 공백을 강제로 제거합니다.
        if curr is not None: curr.columns = curr.columns.str.strip()
        if tech is not None: tech.columns = tech.columns.str.strip()
        
        return curr, tech
    except Exception as e:
        st.error(f"시트 읽기 오류: {e}")
        return None, None

# 2. 세션 상태 초기화
if 'curr_df' not in st.session_state or 'tech_df' not in st.session_state:
    c, t = get_data()
    st.session_state.curr_df = c if c is not None else pd.DataFrame(columns=['학년', '교과명', '주당시수', '비고'])
    st.session_state.tech_df = t if t is not None else pd.DataFrame(columns=['성함', '담당교과', '배정시수', '비고'])

st.title("🏫 학교 교원 시수 관리 시스템")

# --- 진단 도구 (문제가 생기면 이 부분을 확인하세요) ---
with st.expander("🔍 연결 상태 및 열 이름 확인 (문제가 있을 때만 열어보세요)"):
    st.write("현재 '교육과정' 시트 열 이름:", list(st.session_state.curr_df.columns))
    st.write("현재 '교원명단' 시트 열 이름:", list(st.session_state.tech_df.columns))
    if st.button("♻️ 세션 강제 초기화 (데이터가 꼬였을 때 클릭)"):
        st.cache_data.clear()
        del st.session_state.curr_df
        del st.session_state.tech_df
        st.rerun()

# --- 사이드바 및 계산 ---
with st.sidebar:
    st.header("⚙️ 요약")
    
    # 에러 방지를 위한 안전한 합계 계산 함수
    def safe_sum(df, col_name):
        if col_name in df.columns:
            return pd.to_numeric(df[col_name], errors='coerce').sum()
        return 0

    total_need = safe_sum(st.session_state.curr_df, '주당시수') * 8
    total_sup = safe_sum(st.session_state.tech_df, '배정시수')
    
    st.metric("총 필요 시수 (24학급)", f"{total_need}H")
    st.metric("교원 공급 시수 (52명)", f"{total_sup}H")
    if st.button("🔄 시트에서 새로고침"):
        st.cache_data.clear()
        c, t = get_data()
        st.session_state.curr_df = c
        st.session_state.tech_df = t
        st.rerun()

# --- 메인 화면 ---
tab1, tab2, tab3 = st.tabs(["📚 교육과정 설정", "👨‍🏫 교원 명단 관리", "⚖️ 시수 과부족 분석"])

with tab1:
    st.session_state.curr_df = st.data_editor(st.session_state.curr_df, num_rows="dynamic", use_container_width=True, key="ed_curr")

with tab2:
    st.session_state.tech_df = st.data_editor(st.session_state.tech_df, num_rows="dynamic", use_container_width=True, key="ed_tech")

with tab3:
    st.subheader("📊 과부족 분석")
    c = st.session_state.curr_df
    t = st.session_state.tech_df
    
    # 필수 열이 모두 있을 때만 분석 실행
    if '교과명' in c.columns and '주당시수' in c.columns and '담당교과' in t.columns and '배정시수' in t.columns:
        demand = c.groupby('교과명')['주당시수'].sum() * 8
        demand = demand.reset_index().rename(columns={'주당시수': '필요시수'})
        
        supply = t.groupby('담당교과')['배정시수'].sum()
        supply = supply.reset_index().rename(columns={'배정시수': '공급시수', '담당교과': '교과명'})
        
        result = pd.merge(demand, supply, on='교과명', how='outer').fillna(0)
        result['과부족'] = result['공급시수'] - result['필요시수']
        st.dataframe(result, use_container_width=True)
    else:
        st.warning("분석을 위한 열 이름(교과명, 주당시수, 담당교과, 배정시수)을 확인해주세요.")

# --- 저장 ---
st.divider()
if st.button("💾 구글 시트에 최종 저장", use_container_width=True):
    try:
        conn.update(worksheet="curriculum_data", data=st.session_state.curr_df)
        conn.update(worksheet="teacher_data", data=st.session_state.tech_df)
        st.cache_data.clear()
        st.success("저장 성공!")
    except Exception as e:
        st.error(f"저장 실패: {e}")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="시수 조절 도우미", layout="wide")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 불러오기 함수 (캐시 적용)
# ttl=600은 600초(10분) 동안 동일한 데이터를 구글 시트에서 다시 읽지 않고 메모리에서 가져옵니다.
@st.cache_data(ttl=600)
def get_cached_data():
    try:
        curr = conn.read(worksheet="curriculum_data")
        tech = conn.read(worksheet="teacher_data")
        return curr, tech
    except Exception as e:
        return None, None

# 세션 상태(Session State)를 이용해 편집 중인 데이터를 관리합니다.
if 'curr_df' not in st.session_state or 'tech_df' not in st.session_state:
    c, t = get_cached_data()
    st.session_state.curr_df = c if c is not None else pd.DataFrame(columns=['학년', '교과명', '주당시수', '비고'])
    st.session_state.tech_df = t if t is not None else pd.DataFrame(columns=['성함', '담당교과', '배정시수', '비고'])

st.title("🏫 학교 교원 시수 관리 시스템")

# 사이드바 제어 도구
with st.sidebar:
    st.header("⚙️ 도구")
    if st.button("🔄 구글 시트에서 새로고침"):
        # 캐시를 삭제하고 다시 불러옵니다.
        st.cache_data.clear()
        c, t = get_cached_data()
        st.session_state.curr_df = c
        st.session_state.tech_df = t
        st.rerun()
    
    st.divider()
    # 전체 요약 정보
    total_need = st.session_state.curr_df['주당시수'].sum() * 8 if not st.session_state.curr_df.empty else 0
    total_sup = st.session_state.tech_df['배정시수'].sum() if not st.session_state.tech_df.empty else 0
    st.metric("총 필요 시수 (24학급)", f"{total_need}H")
    st.metric("교원 공급 시수 (52명)", f"{total_sup}H")

# --- 메인 화면 탭 ---
tab1, tab2, tab3 = st.tabs(["📚 교육과정 설정", "👨‍🏫 교원 명단 관리", "⚖️ 시수 과부족 분석"])

with tab1:
    st.subheader("1. 학년별 교육과정 시수")
    # 편집기에서 수정한 내용을 세션 상태에 즉시 반영
    edited_curr = st.data_editor(st.session_state.curr_df, num_rows="dynamic", use_container_width=True, key="ed_curr")
    st.session_state.curr_df = edited_curr

with tab2:
    st.subheader("2. 교원별 배정 시수")
    edited_tech = st.data_editor(st.session_state.tech_df, num_rows="dynamic", use_container_width=True, key="ed_tech")
    st.session_state.tech_df = edited_tech

with tab3:
    st.subheader("3. 교과별 수요 vs 공급 분석")
    if not st.session_state.curr_df.empty and not st.session_state.tech_df.empty:
        # 분석 로직 (중복 호출 방지를 위해 로컬 데이터 사용)
        demand = st.session_state.curr_df.groupby('교과명')['주당시수'].sum() * 8
        demand = demand.reset_index().rename(columns={'주당시수': '필요시수'})
        
        supply = st.session_state.tech_df.groupby('담당교과')['배정시수'].sum()
        supply = supply.reset_index().rename(columns={'배정시수': '공급시수', '담당교과': '교과명'})
        
        result = pd.merge(demand, supply, on='교과명', how='outer').fillna(0)
        result['과부족'] = result['공급시수'] - result['필요시수']
        
        def color_diff(val):
            if val < 0: return 'background-color: #ffdddd'
            if val > 0: return 'background-color: #ddffdd'
            return ''
        st.dataframe(result.style.applymap(color_diff, subset=['과부족']), use_container_width=True)
    else:
        st.info("데이터를 입력하면 분석 결과가 표시됩니다.")

# --- 저장 버튼 ---
st.divider()
if st.button("💾 모든 변경사항 구글 시트에 저장하기", use_container_width=True):
    try:
        with st.spinner("구글 시트에 저장 중... (이 작업은 API를 사용합니다)"):
            conn.update(worksheet="curriculum_data", data=st.session_state.curr_df)
            conn.update(worksheet="teacher_data", data=st.session_state.tech_df)
            # 저장 후 캐시 갱신
            st.cache_data.clear()
            st.success("✅ 저장 완료!")
            st.balloons()
    except Exception as e:
        if "429" in str(e):
            st.error("🚨 구글 API 호출 제한에 도달했습니다. 1분만 기다렸다가 다시 시도해주세요.")
        else:
            st.error(f"저장 중 오류 발생: {e}")

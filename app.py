import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="교원 시수 세밀 조절기", layout="wide")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def get_master_data():
    try:
        # 교육과정 배당표(uploaded_data 또는 curriculum_data)
        curr = conn.read(worksheet="curriculum_data")
        # 교원 명단
        tech = conn.read(worksheet="teacher_data")
        
        curr.columns = curr.columns.str.strip()
        tech.columns = tech.columns.str.strip()
        
        # 주당시수 숫자형 변환
        curr['주당시수'] = pd.to_numeric(curr['주당시수'], errors='coerce').fillna(0)
        tech['배정시수'] = pd.to_numeric(tech['배정시수'], errors='coerce').fillna(0)
        
        return curr, tech
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None, None

# 데이터 초기화
c_raw, t_raw = get_master_data()
if 'curr_df' not in st.session_state: st.session_state.curr_df = c_raw
if 'tech_df' not in st.session_state: st.session_state.tech_df = t_raw

st.title("🏫 세밀한 교원 시수 배정 시스템")

# --- [사이드바] 기본 설정 ---
with st.sidebar:
    st.header("⚙️ 기본 설정")
    num_classes = st.number_input("기본 학급 수 (공통과목용)", value=8)
    if st.button("🔄 시트 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

# --- [메인] 탭 구성 ---
tab1, tab2, tab3 = st.tabs(["📋 교육과정 마스터", "👨‍🏫 교원 배정 관리", "📊 시수 분석 보고서"])

with tab1:
    st.subheader("1. 교육과정 편제 및 분반 설정")
    st.write("선택과목의 경우 '분반 수'를 실제 개설되는 반 수에 맞게 수정하세요.")
    
    # 필수/선택 구분을 위해 '분반수' 열이 없다면 추가
    if '분반수' not in st.session_state.curr_df.columns:
        st.session_state.curr_df['분반수'] = num_classes
    
    # 에디터 호출
    edited_curr = st.data_editor(
        st.session_state.curr_df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "주당시수": st.column_config.NumberColumn(format="%d H"),
            "분반수": st.column_config.NumberColumn(help="선택과목은 실제 개설 반 수를 입력하세요.")
        }
    )
    st.session_state.curr_df = edited_curr

with tab2:
    st.subheader("2. 교원별 담당 교과 및 시수")
    # 교과군(국어, 수학 등)을 선택할 수 있도록 구성
    edited_tech = st.data_editor(st.session_state.tech_df, num_rows="dynamic", use_container_width=True)
    st.session_state.tech_df = edited_tech

with tab3:
    st.subheader("3. 최종 시수 과부족 분석")
    
    # 로직: (교과별 주당시수 * 분반수) 합산 vs (교사별 배정시수) 합산
    # 1. 수요 계산
    curr = st.session_state.curr_df.copy()
    curr['총소요시수'] = curr['주당시수'] * curr['분반수']
    
    # 교과군으로 묶기 위해 '교과명'에서 공통 키워드 추출 (예: 공통국어 -> 국어)
    # 실제 업무에선 시트에 '교과군' 열을 따로 두는 것이 가장 정확합니다.
    st.info("💡 팁: '국어', '수학' 등 교과군별로 합산하여 분석합니다.")
    
    demand_sum = curr.groupby('교과명')['총소요시수'].sum().reset_index()
    
    # 2. 공급 계산
    supply_sum = st.session_state.tech_df.groupby('담당교과')['배정시수'].sum().reset_index()
    supply_sum.columns = ['교과명', '공급시수']
    
    # 3. 비교 데이터프레임 생성
    analysis = pd.merge(demand_sum, supply_sum, on='교과명', how='outer').fillna(0)
    analysis['과부족'] = analysis['공급시수'] - analysis['총소요시수']
    
    # 시각화
    def color_status(val):
        if val < 0: return 'background-color: #ffcccc'
        if val > 0: return 'background-color: #ccffcc'
        return ''

    st.table(analysis.style.applymap(color_status, subset=['과부족']))

# --- [저장] ---
if st.button("💾 변경사항 구글 시트에 최종 저장"):
    conn.update(worksheet="curriculum_data", data=st.session_state.curr_df)
    conn.update(worksheet="teacher_data", data=st.session_state.tech_df)
    st.success("저장되었습니다!")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np

st.set_page_config(page_title="교과 시수 배정 시스템", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 1. 데이터 불러오기 및 정제 함수 ---
@st.cache_data(ttl=10) # 짧은 캐시로 API 할당량 보호
def load_and_clean_data():
    try:
        curr = conn.read(worksheet="curriculum_data")
        tech = conn.read(worksheet="teacher_data")
        
        # 열 이름 공백 제거
        curr.columns = curr.columns.str.strip()
        tech.columns = tech.columns.str.strip()
        
        # [데이터 정제] None 또는 NaN 값을 적절한 기본값으로 채우기
        # 교육과정 시트 정제
        curr['학년'] = curr['학년'].fillna('').astype(str)
        curr['교과군'] = curr['교과군'].fillna('')
        curr['교과명'] = curr['교과명'].fillna('')
        curr['구분'] = curr['구분'].fillna('')
        curr['주당시수'] = pd.to_numeric(curr['주당시수'], errors='coerce').fillna(0)
        curr['분반수'] = pd.to_numeric(curr['분반수'], errors='coerce').fillna(8) # 기본 8학급
        curr['비고'] = curr['비고'].fillna('')

        # 교원 명단 시트 정제
        tech['성함'] = tech['성함'].fillna('')
        tech['담당교과군'] = tech['담당교과군'].fillna('')
        tech['배정시수'] = pd.to_numeric(tech['배정시수'], errors='coerce').fillna(0)
        tech['비고'] = tech['비고'].fillna('')
        
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
    # 현재 세션에 있는 데이터를 복사해서 계산용 숫자로 변환
    c = st.session_state.curr_df.copy()
    t = st.session_state.tech_df.copy()
    c['주당시수'] = pd.to_numeric(c['주당시수'], errors='coerce').fillna(0)
    c['분반수'] = pd.to_numeric(c['분반수'], errors='coerce').fillna(8)
    t['배정시수'] = pd.to_numeric(t['배정시수'], errors='coerce').fillna(0)
    return c, t

st.title("🏫 학교 교과 시수 관리 (32H + 담임2H 체제)")

# --- 사이드바 요약 현황 ---
with st.sidebar:
    st.header("📊 학교 시수 요약")
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    
    calc_curr, calc_tech = get_safe_calculation_data()

    # 교과 총 시수 (주당시수 * 8학급) - 사용자가 분반수를 따로 안 써도 8로 계산됨
    academic_need = (calc_curr['주당시수'] * 8).sum() 
    # 담임/부담임 고정 시수 (2H * 24학급)
    hr_fixed_need = 2 * 24 
    
    total_need = academic_need + hr_fixed_need
    total_sup = calc_tech['배정시수'].sum()
    
    st.metric("교과 필요 시수 합계", f"{int(academic_need)}H")
    st.metric("담임/부담임 시수 (고정)", f"{int(hr_fixed_need)}H")
    st.metric("교원 공급 시수 (52명)", f"{int(total_sup)}H")
    
    diff = total_sup - total_need
    st.metric("전체 시수 균형", f"{int(diff)}H", delta=int(diff))

# --- 메인 화면 탭 ---
tab1, tab2, tab3 = st.tabs(["📚 교과 편제(32H 검증)", "👨‍🏫 교원 배정(12~16H)", "⚖️ 교과군별 분석"])

with tab1:
    st.subheader("1. 학년별 교과 편제 (목표: 32H)")
    calc_curr, _ = get_safe_calculation_data()
    cols = st.columns(3)
    for i, g in enumerate(["1", "2", "3"]):
        g_sum = calc_curr[calc_curr['학년'].str.contains(g, na=False)]['주당시수'].sum()
        if g_sum == 32:
            cols[i].success(f"✅ {g}학년: {int(g_sum)}/32H")
        else:
            cols[i].warning(f"⚠️ {g}학년: {int(g_sum)}/32H")

    # 데이터 에디터 (None 방지를 위해 fillna 처리된 데이터 제공)
    st.session_state.curr_df = st.data_editor(st.session_state.curr_df.fillna(''), num_rows="dynamic", use_container_width=True, key="edit_curr")

with tab2:
    st.subheader("2. 교원별 개인 시수 관리")
    calc_curr, calc_tech = get_safe_calculation_data()
    invalid = calc_tech[(calc_tech['배정시수'] < 12) | (calc_tech['배정시수'] > 16)]
    if not invalid.empty:
        st.error(f"⚠️ 시수 범위(12-16H) 미달/초과자 존재")
        
    st.session_state.tech_df = st.data_editor(st.session_state.tech_df.fillna(''), num_rows="dynamic", use_container_width=True, key="edit_tech")

with tab3:
    st.subheader("3. 교과군별 과부족 분석")
    c_final, t_final = get_safe_calculation_data()
    
    if not c_final.empty and not t_final.empty:
        # 수요 (교과군별 주당시수합 * 8)
        demand = c_final.groupby('교과군')['주당시수'].sum() * 8
        demand = demand.reset_index().rename(columns={'주당시수': '필요시수'})
        
        # 공급 (교과군별 배정시수합)
        supply = t_final.groupby('담당교과군')['배정시수'].sum().reset_index()
        supply.columns = ['교과군', '공급시수']
        
        # 분석표 결합
        report = pd.merge(demand, supply, on='교과군', how='outer').fillna(0)
        report['과부족'] = report['공급시수'] - report['필요시수']
        
        st.dataframe(report.style.background_gradient(subset=['과부족'], cmap='RdYlGn'), use_container_width=True)
    else:
        st.info("데이터를 입력하면 분석표가 나타납니다.")

# --- 저장 ---
st.divider()
if st.button("💾 모든 변경사항 구글 시트에 최종 저장", use_container_width=True):
    try:
        # 저장 시에는 다시 판다스의 NaN 형태로 변환하여 구글 시트의 빈 칸으로 저장되게 함
        conn.update(worksheet="curriculum_data", data=st.session_state.curr_df)
        conn.update(worksheet="teacher_data", data=st.session_state.tech_df)
        st.cache_data.clear()
        st.success("✅ 저장 완료!")
        st.balloons()
    except Exception as e:
        st.error(f"저장 오류: {e}")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="교과 시수 배정 시스템 (32H)", layout="wide")

# 1. 구글 시트 연결 및 데이터 로드
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        curr = conn.read(worksheet="curriculum_data")
        tech = conn.read(worksheet="teacher_data")
        curr.columns = curr.columns.str.strip()
        tech.columns = tech.columns.str.strip()
        curr['주당시수'] = pd.to_numeric(curr['주당시수'], errors='coerce').fillna(0)
        tech['배정시수'] = pd.to_numeric(tech['배정시수'], errors='coerce').fillna(0)
        return curr, tech
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None, None

# 데이터 초기화
c_raw, t_raw = load_data()
if 'curr_df' not in st.session_state: st.session_state.curr_df = c_raw
if 'tech_df' not in st.session_state: st.session_state.tech_df = t_raw

st.title("🏫 학교 교과 시수 매칭 시스템 (학급당 32H 기준)")
st.info("💡 학급당 총 34시간 중 **담임/부담임 시수(2H)**를 제외한 **교과 시수 합계 32시간**을 맞추는 모드입니다.")

# --- 사이드바: 전체 요약 ---
with st.sidebar:
    st.header("📊 학교 시수 요약")
    if st.button("🔄 시트 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    # 전체 교과 필요 시수 (학년별 교과시수합 32H * 8학급)
    # 만약 시트에 담임/부담임 시수를 넣지 않았다면 32H가 기준이 됩니다.
    academic_need = st.session_state.curr_df['주당시수'].sum() * 8
    # 담임/부담임 고정 시수 (2H * 24학급 = 48H)
    hr_fixed_need = 2 * 24 
    
    total_need = academic_need + hr_fixed_need
    total_sup = st.session_state.tech_df['배정시수'].sum()
    
    st.metric("교과 필요 시수 (32H*24)", f"{int(academic_need)}H")
    st.metric("담임/부담임 시수 (2H*24)", f"{int(hr_fixed_need)}H")
    st.metric("총 공급 시수 (52명)", f"{int(total_sup)}H")
    st.metric("전체 시수 균형", f"{int(total_sup - total_need)}H", delta=int(total_sup - total_need))

# --- 메인 화면 ---
tab1, tab2, tab3 = st.tabs(["📚 교과 편제(32H 검증)", "👨‍🏫 교원 배정(12~16H)", "⚖️ 교과군별 분석"])

with tab1:
    st.subheader("1. 학년별 교과 편제표 (목표: 학년별 32시간)")
    
    # 학년별 시수 합계 체크 (목표 32)
    cols = st.columns(3)
    for i, g in enumerate(["1", "2", "3"]):
        # 학년 컬럼이 숫자일 수도, 문자열일 수도 있으므로 처리
        grade_data = st.session_state.curr_df[st.session_state.curr_df['학년'].astype(str) == g]
        g_sum = grade_data['주당시수'].sum()
        
        if g_sum == 32:
            cols[i].success(f"✅ {g}학년: {g_sum}/32H 완료")
        else:
            cols[i].warning(f"⚠️ {g}학년: {g_sum}/32H (차이: {int(g_sum-32)}H)")
            
    st.session_state.curr_df = st.data_editor(st.session_state.curr_df, num_rows="dynamic", use_container_width=True, key="edit_curr")

with tab2:
    st.subheader("2. 교원별 개인 시수 관리")
    st.write("선생님들의 배정 시수에 **담임/부담임 시수(각 1H)**가 포함되어 있는지 확인 후 입력하세요.")
    
    # 개인별 시수 적정성 체크 (12~16H)
    invalid = st.session_state.tech_df[(st.session_state.tech_df['배정시수'] < 12) | (st.session_state.tech_df['배정시수'] > 16)]
    if not invalid.empty:
        st.error(f"⚠️ 적정 시수(12-16H) 미달/초과자: {', '.join(invalid['성함'].astype(str).tolist())}")
        
    st.session_state.tech_df = st.data_editor(st.session_state.tech_df, num_rows="dynamic", use_container_width=True, key="edit_tech")

with tab3:
    st.subheader("3. 교과군별 최종 과부족 분석")
    
    # 1) 수요: 교과군별 (주당시수 합 * 8)
    demand = st.session_state.curr_df.groupby('교과군')['주당시수'].sum() * 8
    demand = demand.reset_index().rename(columns={'주당시수': '필요시수'})
    
    # 2) 공급: 교과군별 (배정시수 합)
    supply = st.session_state.tech_df.groupby('담당교과군')['배정시수'].sum().reset_index()
    supply.columns = ['교과군', '공급시수']
    
    # 3) 병합 및 계산
    report = pd.merge(demand, supply, on='교과군', how='outer').fillna(0)
    report['과부족'] = report['공급시수'] - report['필요시수']
    
    # 스타일링
    def color_result(val):
        if val < 0: return 'background-color: #ffcccc'
        if val > 0: return 'background-color: #ccffcc'
        return ''
    
    st.dataframe(report.style.applymap(color_result, subset=['과부족']), use_container_width=True)
    
    # 부족 교과군 강조
    shortage = report[report['과부족'] < 0]
    if not shortage.empty:
        for _, row in shortage.iterrows():
            st.warning(f"🚩 **{row['교과군']}** 교과군에 {abs(int(row['과부족']))}시간이 더 필요합니다.")

# --- 저장 ---
st.divider()
if st.button("💾 변경사항 구글 시트에 최종 저장", use_container_width=True):
    try:
        conn.update(worksheet="curriculum_data", data=st.session_state.curr_df)
        conn.update(worksheet="teacher_data", data=st.session_state.tech_df)
        st.cache_data.clear()
        st.success("✅ 저장이 완료되었습니다!")
        st.balloons()
    except Exception as e:
        st.error(f"저장 중 오류 발생: {e}")

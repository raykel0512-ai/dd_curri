import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="학교 시수 관리 시스템", layout="wide")

st.title("🏫 2024학년도 시수 배정 시뮬레이터")
st.info("8학급 체제 (학년별 34시간) / 교원 52명 기준")

# 1. 구글 시트 연결 설정
# (실제 배포 시에는 .streamlit/secrets.toml에 시트 주소를 넣어야 합니다)
url = "여러분의_구글_시트_공유_링크" 

conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 불러오기 함수
def load_data():
    curr_df = conn.read(worksheet="curriculum_data")
    tech_df = conn.read(worksheet="teacher_data")
    return curr_df, tech_df

curr_df, tech_df = load_data()

# --- 사이드바: 전체 현황 요약 ---
st.sidebar.header("📊 전체 요약")
total_required_hours = curr_df['주당시수'].sum() * 8 # 각 학년별 34시간 * 8학급 기준
total_supplied_hours = tech_df['배정시수'].sum()

st.sidebar.metric("필요 총 시수 (24학급)", f"{total_required_hours} 시간")
st.sidebar.metric("교사 배정 총 시수 (52명)", f"{total_supplied_hours} 시간")
st.sidebar.write(f"**차이:** {total_supplied_hours - total_required_hours} 시간")

# --- 메인 화면 탭 ---
tab1, tab2, tab3 = st.tabs(["📚 교육과정(수요)", "👨‍🏫 교원 명단(공급)", "⚖️ 시수 과부족 분석"])

with tab1:
    st.subheader("학년별 교육과정 설정")
    st.write("각 학년별 시수의 합이 34시간이 되어야 합니다.")
    
    # 학년별 합계 체크
    for grade in ["1학년", "2학년", "3학년"]:
        grade_sum = curr_df[curr_df['학년'] == grade]['주당시수'].sum()
        if grade_sum != 34:
            st.warning(f"⚠️ {grade}: 현재 {grade_sum}시간 (목표 34시간까지 {34-grade_sum}시간 남음)")
        else:
            st.success(f"✅ {grade}: 34시간 충족")
            
    edited_curr = st.data_editor(curr_df, num_rows="dynamic", key="curr_editor")

with tab2:
    st.subheader("교원 명단 및 개인별 시수")
    st.write("선생님별 담당 교과와 시수(12~16시간)를 조정하세요.")
    
    # 시수 범위 체크 (12~16시간)
    out_of_range = tech_df[(tech_df['배정시수'] < 12) | (tech_df['배정시수'] > 16)]
    if not out_of_range.empty:
        st.error(f"⚠️ 시수 범위(12-16)를 벗어난 분이 {len(out_of_range)}명 있습니다.")
    
    edited_tech = st.data_editor(tech_df, num_rows="dynamic", key="tech_editor")

with tab3:
    st.subheader("교과별 수요 vs 공급 분석")
    
    # 1. 교과별 필요 총 시수 (교육과정 시수 * 8학급)
    curr_summary = curr_df.groupby('교과명')['주당시수'].sum() * 8
    curr_summary = curr_summary.reset_index().rename(columns={'주당시수': '필요시수'})
    
    # 2. 교과별 공급 총 시수 (교사별 시수 합계)
    tech_summary = tech_df.groupby('담당교과')['배정시수'].sum()
    tech_summary = tech_summary.reset_index().rename(columns={'배정시수': '확보시수', '담당교과': '교과명'})
    
    # 3. 데이터 병합 분석
    analysis_df = pd.merge(curr_summary, tech_summary, on='교과명', how='outer').fillna(0)
    analysis_df['과부족'] = analysis_df['확보시수'] - analysis_df['필요시수']
    
    st.dataframe(analysis_df, use_container_width=True)
    
    # 시각화 알림
    for _, row in analysis_df.iterrows():
        if row['과부족'] < 0:
            st.error(f"[{row['교과명']}] {abs(row['과부족'])}시간 부족 (교사 추가 배정 필요)")
        elif row['과부족'] > 0:
            st.info(f"[{row['교과명']}] {row['과부족']}시간 남음")

# 저장 버튼
if st.button("💾 변경사항 구글 시트에 저장하기"):
    conn.update(worksheet="curriculum_data", data=edited_curr)
    conn.update(worksheet="teacher_data", data=edited_tech)
    st.success("구글 시트에 성공적으로 저장되었습니다!")

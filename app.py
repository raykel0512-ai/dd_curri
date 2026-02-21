import streamlit as st
import pandas as pd

st.set_page_config(page_title="학교 시수 조절 도우미", layout="wide")

st.title("🏫 학교 교원 시수 조절 프로토타입")
st.write("학년별 시수와 교원 정보를 입력하여 적정 시수를 맞춰보세요.")

# 사이드바 - 메뉴 선택
menu = st.sidebar.selectbox("메뉴", ["교육과정 입력", "교원 명단 관리", "시수 배정 및 분석"])

# 데이터 초기화 (세션 상태 저장)
if 'curriculum' not in st.session_state:
    st.session_state.curriculum = pd.DataFrame(columns=['학년', '교과', '학급수', '주당시수'])
if 'teachers' not in st.session_state:
    st.session_state.teachers = pd.DataFrame(columns=['성함', '교과', '희망시수'])

# --- 1. 교육과정 입력 ---
if menu == "교육과정 입력":
    st.header("1. 학년별 교육과정 시수 입력")
    with st.form("curr_form"):
        col1, col2, col3, col4 = st.columns(4)
        grade = col1.selectbox("학년", ["1학년", "2학년", "3학년"])
        subject = col2.text_input("교과명 (예: 수학)")
        num_classes = col3.number_input("학급 수", min_value=1, value=10)
        hours_per_week = col4.number_input("주당 시수", min_value=0.5, value=4.0, step=0.5)
        submit = st.form_submit_button("추가하기")
        
        if submit:
            new_data = pd.DataFrame([[grade, subject, num_classes, hours_per_week]], 
                                    columns=['학년', '교과', '학급수', '주당시수'])
            st.session_state.curriculum = pd.concat([st.session_state.curriculum, new_data], ignore_index=True)

    st.dataframe(st.session_state.curriculum, use_container_width=True)
    if st.button("데이터 초기화"):
        st.session_state.curriculum = pd.DataFrame(columns=['학년', '교과', '학급수', '주당시수'])

# --- 2. 교원 명단 관리 ---
elif menu == "교원 명단 관리":
    st.header("2. 교원 명단 및 정보 입력")
    with st.form("teacher_form"):
        col1, col2, col3 = st.columns(3)
        t_name = col1.text_input("선생님 성함")
        t_subject = col2.text_input("담당 교과")
        t_hours = col3.number_input("주당 배정 가능 시수", min_value=1, value=18)
        t_submit = st.form_submit_button("교사 추가")
        
        if t_submit:
            new_teacher = pd.DataFrame([[t_name, t_subject, t_hours]], 
                                       columns=['성함', '교과', '희망시수'])
            st.session_state.teachers = pd.concat([st.session_state.teachers, new_teacher], ignore_index=True)
            
    st.dataframe(st.session_state.teachers, use_container_width=True)

# --- 3. 시수 배정 및 분석 ---
elif menu == "시수 배정 및 분석":
    st.header("3. 교과별 시수 과부족 분석")
    
    if not st.session_state.curriculum.empty and not st.session_state.teachers.empty:
        # 교과별 필요 총 시수 계산
        curr = st.session_state.curriculum.copy()
        curr['총필요시수'] = curr['학급수'] * curr['주당시수']
        needed_hours = curr.groupby('교과')['총필요시수'].sum().reset_index()
        
        # 교과별 교사 공급 시수 계산
        tech = st.session_state.teachers.copy()
        supplied_hours = tech.groupby('교과')['희망시수'].sum().reset_index()
        
        # 병합 및 분석
        analysis = pd.merge(needed_hours, supplied_hours, on='교과', how='outer').fillna(0)
        analysis['과부족'] = analysis['희망시수'] - analysis['총필요시수']
        
        st.subheader("교과별 요약")
        st.dataframe(analysis, use_container_width=True)
        
        for index, row in analysis.iterrows():
            if row['과부족'] < 0:
                st.error(f"⚠️ {row['교과']} 교과에 {-row['과부족']}시간이 부족합니다.")
            elif row['과부족'] > 0:
                st.info(f"✅ {row['교과']} 교과에 {row['과부족']}시간 여유가 있습니다.")
    else:
        st.warning("교육과정과 교원 명단을 먼저 입력해주세요.")

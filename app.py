import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="학교 시수 조절 도우미", layout="wide")

# 1. 구글 시트 연결 (서비스 계정 방식 자동 인식)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # worksheet 이름이 시트 하단 탭 이름과 정확히 일치해야 합니다.
        curr_df = conn.read(worksheet="curriculum_data")
        tech_df = conn.read(worksheet="teacher_data")
        return curr_df, tech_df
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류 발생: {e}")
        return pd.DataFrame(), pd.DataFrame()

curr_df, tech_df = load_data()

st.title("🏫 학교 교원 시수 관리 시스템")

if curr_df.empty or tech_df.empty:
    st.warning("구글 시트에서 데이터를 불러올 수 없습니다. 시트 이름과 공유 설정을 확인해주세요.")
else:
    # --- 사이드바: 전체 요약 현황 ---
    st.sidebar.header("📊 실시간 배정 현황")
    
    # 학년별 8학급 기준 계산
    total_required = curr_df['주당시수'].sum() * 8 
    total_supplied = tech_df['배정시수'].sum()
    
    st.sidebar.metric("총 필요 시수 (24학급)", f"{total_required}H")
    st.sidebar.metric("교사 확보 시수 (52명)", f"{total_supplied}H")
    
    diff = total_supplied - total_required
    st.sidebar.metric("시수 과부족", f"{diff}H", delta=int(diff))

    # --- 메인 화면 탭 구성 ---
    tab1, tab2, tab3 = st.tabs(["📋 교육과정 입력", "👥 교원 명단 관리", "📈 시수 분석 리포트"])

    with tab1:
        st.subheader("학년별 교육과정 시수 (각 학년 합계 34시간)")
        edited_curr = st.data_editor(curr_df, num_rows="dynamic", use_container_width=True, key="curr_edit")
        
        # 학년별 합계 검사
        for grade in ["1학년", "2학년", "3학년"]:
            g_sum = edited_curr[edited_curr['학년'] == grade]['주당시수'].sum()
            if g_sum != 34:
                st.error(f"⚠️ {grade} 합계: {g_sum}H (목표: 34H)")
            else:
                st.success(f"✅ {grade} 합계: 34H 충족")

    with tab2:
        st.subheader("교원별 담당 교과 및 시수 (12~16시간)")
        edited_tech = st.data_editor(tech_df, num_rows="dynamic", use_container_width=True, key="tech_edit")
        
        # 개인별 시수 적정성 검사
        invalid_tech = edited_tech[(edited_tech['배정시수'] < 12) | (edited_tech['배정시수'] > 16)]
        if not invalid_tech.empty:
            st.warning(f"⚠️ 시수 범위를 벗어난 교사: {', '.join(invalid_tech['성함'].tolist())}")

    with tab3:
        st.subheader("교과별 수요/공급 분석")
        # 분석 로직
        needed = curr_df.groupby('교과명')['주당시수'].sum() * 8
        supplied = tech_df.groupby('담당교과')['배정시수'].sum()
        
        analysis = pd.DataFrame({'필요': needed, '공급': supplied}).fillna(0)
        analysis['차이'] = analysis['공급'] - analysis['필요']
        
        st.dataframe(analysis.style.highlight_min(subset=['차이'], color='#ffaaaa'), use_container_width=True)

    # 저장 버튼
    if st.button("💾 변경사항을 구글 시트에 저장"):
        try:
            conn.update(worksheet="curriculum_data", data=edited_curr)
            conn.update(worksheet="teacher_data", data=edited_tech)
            st.toast("구글 시트에 성공적으로 저장되었습니다!", icon="✅")
        except Exception as e:
            st.error(f"저장 중 오류 발생: {e}")

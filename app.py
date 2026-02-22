import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="디버깅 모드", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🔧 시스템 연결 상세 점검")

# 1. 시트 탭 이름이 정확한지 확인하는 과정
try:
    # 탭 이름을 지정하지 않고 첫 번째 탭을 무조건 가져와봅니다.
    df_test = conn.read(ttl=0)
    st.success("✅ 첫 번째 탭 연결 성공!")
    st.write("첫 번째 탭의 데이터 샘플:", df_test.head())
    
    # 만약 데이터가 아예 없으면 (헤더도 없으면) empty로 취급됩니다.
    if df_test.empty:
        st.warning("⚠️ 시트에 데이터가 아예 없습니다. 첫 줄에 '학년', '교과명', '주당시수'라고 적으셨나요?")
except Exception as e:
    st.error(f"❌ 첫 번째 탭 불러오기 실패: {e}")

st.divider()

# 2. 특정 탭 이름으로 불러오기 시도
def check_tab(tab_name):
    try:
        df = conn.read(worksheet=tab_name, ttl=0)
        st.write(f"📊 '{tab_name}' 탭 불러오기 성공! (행 개수: {len(df)})")
        return df
    except Exception as e:
        st.error(f"❌ '{tab_name}' 탭을 찾는 데 실패했습니다. 에러 메시지: {e}")
        return None

curr_df = check_tab("curriculum_data")
tech_df = check_tab("teacher_data")

if curr_df is not None and tech_df is not None:
    st.balloons()
    st.success("모든 연결이 확인되었습니다! 이제 원래 코드를 사용하셔도 됩니다.")

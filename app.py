import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("연결 테스트")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # worksheet 이름을 넣지 말고 시도해봅니다 (첫 번째 탭을 가져옴)
    df = conn.read() 
    st.write("연결 성공! 데이터 샘플:")
    st.dataframe(df)
except Exception as e:
    st.error("연결 실패")
    st.exception(e)

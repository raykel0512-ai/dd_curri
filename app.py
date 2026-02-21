import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="학교 시수 조절 도우미", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 1. 시트 이름을 지정하지 않고 첫 번째 탭을 읽어옵니다.
        # 이렇게 해서 데이터가 불러와진다면 연결은 성공한 것입니다.
        curr_df = conn.read(ttl=0) # 첫 번째 시트 읽기
        
        # 2. 만약 두 번째 탭을 읽어야 한다면 아래와 같이 worksheet 이름을 명시해야 합니다.
        # 현재는 디버깅을 위해 에러가 나지 않도록 빈 데이터프레임을 일단 설정합니다.
        tech_df = pd.DataFrame() 
        
        # 실제 운영시에는 아래 주석을 풀고 탭 이름을 정확히 넣어야 합니다.
        # tech_df = conn.read(worksheet="teacher_data", ttl=0)
        
        return curr_df, tech_df
    except Exception as e:
        st.error(f"데이터 연결 오류 상세: {e}")
        return pd.DataFrame(), pd.DataFrame()

curr_df, tech_df = load_data()

st.title("🏫 시수 관리 시스템 연결 테스트")

if not curr_df.empty:
    st.success("✅ 첫 번째 탭 데이터를 성공적으로 불러왔습니다!")
    st.subheader("불러온 데이터 미리보기")
    st.dataframe(curr_df.head())
else:
    st.error("❌ 데이터를 불러오지 못했습니다. 아래 체크리스트를 확인하세요.")
    st.write("1. 구글 시트 공유 설정에 서비스 계정 이메일이 추가되었나요?")
    st.code("lecturer-calc@gen-lang-client-0580250011.iam.gserviceaccount.com")
    st.write("2. Secrets에 입력한 spreadsheet 주소가 정확한가요?")

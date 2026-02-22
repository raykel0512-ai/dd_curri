import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="시수 조절 도우미", layout="wide")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # ttl=0을 사용하여 캐시를 방지하고 항상 최신 데이터를 불러옵니다.
    curr = conn.read(worksheet="curriculum_data", ttl=0)
    tech = conn.read(worksheet="teacher_data", ttl=0)
    return curr, tech

# 데이터 불러오기
try:
    curr_df, tech_df = load_data()
    # 데이터가 아예 없을 경우를 대비해 빈 데이터프레임 구조 생성
    if curr_df is None or curr_df.empty:
        curr_df = pd.DataFrame(columns=['학년', '교과명', '주당시수', '비고'])
    if tech_df is None or tech_df.empty:
        tech_df = pd.DataFrame(columns=['성함', '담당교과', '배정시수', '비고'])
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

st.title("🏫 학교 교원 시수 관리 시스템")
st.info("💡 탭에서 내용을 수정하신 후, 하단의 '저장' 버튼을 눌러야 구글 시트에 반영됩니다.")

# --- 메인 화면 탭 구성 ---
tab1, tab2, tab3 = st.tabs(["📚 교육과정 설정", "👨‍🏫 교원 명단 관리", "⚖️ 시수 과부족 분석"])

with tab1:
    st.subheader("1. 학년별 교육과정 (학년별 34시간 기준)")
    
    # 학년별 시수 합계 계산 및 표시
    c1, c2, c3 = st.columns(3)
    grades = ["1학년", "2학년", "3학년"]
    cols = [c1, c2, c3]
    
    for i, g in enumerate(grades):
        # 데이터가 있을 때만 계산
        if not curr_df.empty and '학년' in curr_df.columns and '주당시수' in curr_df.columns:
            sum_val = curr_df[curr_df['학년'] == g]['주당시수'].sum()
            if sum_val == 34:
                cols[i].success(f"✅ {g}: {sum_val}H")
            else:
                cols[i].warning(f"⚠️ {g}: {sum_val}H (목표: 34H)")
        else:
            cols[i].write(f"{g}: 데이터 없음")

    # 데이터 수정 에디터
    edited_curr = st.data_editor(curr_df, num_rows="dynamic", use_container_width=True, key="curr_edit")

with tab2:
    st.subheader("2. 교원별 배정 시수 (12~16시간 기준)")
    
    # 시수 범위 체크 및 경고
    if not tech_df.empty and '배정시수' in tech_df.columns:
        invalid_tech = tech_df[(tech_df['배정시수'] < 12) | (tech_df['배정시수'] > 16)]
        if not invalid_tech.empty:
            st.error(f"⚠️ 시수 범위를 벗어난 분 ({len(invalid_tech)}명): {', '.join(invalid_tech['성함'].fillna('이름없음').tolist())}")
    
    # 데이터 수정 에디터
    edited_tech = st.data_editor(tech_df, num_rows="dynamic", use_container_width=True, key="tech_edit")

with tab3:
    st.subheader("3. 교과별 수요 vs 공급 분석 (8학급 기준)")
    
    if not edited_curr.empty and not edited_tech.empty:
        # 수요 계산 (교육과정 시수 * 8학급)
        demand = edited_curr.groupby('교과명')['주당시수'].sum() * 8
        demand = demand.reset_index().rename(columns={'주당시수': '필요시수'})
        
        # 공급 계산 (교사별 배정 시수 합계)
        supply = edited_tech.groupby('담당교과')['배정시수'].sum()
        supply = supply.reset_index().rename(columns={'배정시수': '공급시수', '담당교과': '교과명'})
        
        # 결과 합치기
        result = pd.merge(demand, supply, on='교과명', how='outer').fillna(0)
        result['과부족'] = result['공급시수'] - result['필요시수']
        
        # 스타일링 함수
        def color_diff(val):
            if val < 0: return 'background-color: #ffdddd'
            if val > 0: return 'background-color: #ddffdd'
            return ''
            
        st.dataframe(result.style.applymap(color_diff, subset=['과부족']), use_container_width=True)
        
        # 총계 요약
        total_need = result['필요시수'].sum()
        total_sup = result['공급시수'].sum()
        st.write(f"**전체 요약:** 필요 {total_need}H / 공급 {total_sup}H (차이: {total_sup - total_need}H)")
    else:
        st.info("분석을 위해 교육과정과 교원 명단에 데이터를 입력해주세요.")

# --- 저장 버튼 ---
st.divider()
if st.button("💾 모든 변경사항 구글 시트에 저장하기", use_container_width=True):
    try:
        with st.spinner("구글 시트에 저장 중..."):
            conn.update(worksheet="curriculum_data", data=edited_curr)
            conn.update(worksheet="teacher_data", data=edited_tech)
            st.success("✅ 저장 완료! 구글 시트가 업데이트되었습니다.")
            st.balloons()
    except Exception as e:
        st.error(f"저장 중 오류가 발생했습니다: {e}")

# 사이드바에 새로고침 버튼 추가
if st.sidebar.button("🔄 데이터 새로고침 (Refresh)"):
    st.rerun()

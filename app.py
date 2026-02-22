import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="시수 조절 도우미", layout="wide")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # 시트에서 데이터 불러오기 (캐시를 0으로 설정해 실시간 반영 유도)
    curr_df = conn.read(worksheet="curriculum_data", ttl=0)
    tech_df = conn.read(worksheet="teacher_data", ttl=0)
    return curr_df, tech_df

# 데이터 로드
curr_df, tech_df = load_data()

st.title("🏫 학교 교원 시수 조절 시스템")
st.markdown(f"**현재 설정:** 학년별 8학급(총 24학급) | 학급당 34시간 | 교원 52명")

if curr_df.empty or tech_df.empty:
    st.error("데이터를 불러오지 못했습니다. 구글 시트의 탭 이름(curriculum_data, teacher_data)을 확인해주세요.")
else:
    # --- 사이드바: 전체 요약 현황 ---
    st.sidebar.header("📊 실시간 전체 현황")
    
    # 총 필요 시수 계산: (학년별 주당 시수 합계) * 8학급
    total_needed_hours = curr_df['주당시수'].sum() * 8
    # 총 공급 시수 계산: 교사별 배정 시수 합계
    total_supplied_hours = tech_df['배정시수'].sum()
    
    st.sidebar.metric("총 필요 시수 (24학급)", f"{total_needed_hours}H")
    st.sidebar.metric("교원 공급 시수 (52명)", f"{total_supplied_hours}H")
    
    diff = total_supplied_hours - total_needed_hours
    if diff == 0:
        st.sidebar.success("✅ 시수 균형이 완벽합니다!")
    elif diff > 0:
        st.sidebar.info(f"💡 {int(diff)}시간이 남습니다.")
    else:
        st.sidebar.error(f"⚠️ {int(abs(diff))}시간이 부족합니다.")

    # --- 메인 화면 탭 구성 ---
    tab1, tab2, tab3 = st.tabs(["📚 교육과정(수요)", "👨‍🏫 교원 명단(공급)", "⚖️ 시수 과부족 분석"])

    with tab1:
        st.subheader("1. 학년별 교육과정 시수 설정")
        st.info("각 학급은 주당 34시간의 수업을 듣습니다. 아래 시수 합계가 34가 되는지 확인하세요.")
        
        # 학년별 합계 검사 및 표시
        cols = st.columns(3)
        for i, grade in enumerate(["1학년", "2학년", "3학년"]):
            g_sum = curr_df[curr_df['학년'] == grade]['주당시수'].sum()
            if g_sum == 34:
                cols[i].success(f"✅ {grade}: {g_sum}/34")
            else:
                cols[i].error(f"⚠️ {grade}: {g_sum}/34")
        
        # 데이터 에디터
        edited_curr = st.data_editor(curr_df, num_rows="dynamic", use_container_width=True, key="curr_editor")

    with tab2:
        st.subheader("2. 교원별 담당 교과 및 시수 배정")
        st.info("선생님별 적정 시수는 12~16시간입니다.")
        
        # 시수 범위 체크 함수
        def highlight_hours(val):
            color = 'red' if val < 12 or val > 16 else 'black'
            return f'color: {color}'

        # 데이터 에디터 (배정 시수 범위 밖이면 빨간색으로 표시하고 싶지만, editor에선 제약이 있어 아래에 경고 표시)
        edited_tech = st.data_editor(tech_df, num_rows="dynamic", use_container_width=True, key="tech_editor")
        
        invalid_list = edited_tech[(edited_tech['배정시수'] < 12) | (edited_tech['배정시수'] > 16)]['성함'].tolist()
        if invalid_list:
            st.warning(f"⚠️ 시수 범위(12-16H)를 벗어난 분: {', '.join(invalid_list)}")

    with tab3:
        st.subheader("3. 교과별 수요 vs 공급 결과")
        
        # 분석 로직
        # 1) 교과별 필요 시수 (시수 * 8학급)
        needed_by_sub = curr_df.groupby('교과명')['주당시수'].sum() * 8
        needed_by_sub = needed_by_sub.reset_index().rename(columns={'주당시수': '필요시수'})
        
        # 2) 교과별 공급 시수 (선생님들의 합계)
        supplied_by_sub = edited_tech.groupby('담당교과')['배정시수'].sum()
        supplied_by_sub = supplied_by_sub.reset_index().rename(columns={'배정시수': '공급시수', '담당교과': '교과명'})
        
        # 3) 병합
        analysis_df = pd.merge(needed_by_sub, supplied_by_sub, on='교과명', how='outer').fillna(0)
        analysis_df['과부족'] = analysis_df['공급시수'] - analysis_df['필요시수']
        
        # 테이블 스타일링
        def color_diff(val):
            if val < 0: return 'background-color: #ffcccc' # 부족 (빨강)
            if val > 0: return 'background-color: #ccffcc' # 남음 (초록)
            return ''

        st.dataframe(analysis_df.style.applymap(color_diff, subset=['과부족']), use_container_width=True)
        
        # 요약 리포트
        st.markdown("#### 🚩 집중 점검 항목")
        shortage = analysis_df[analysis_df['과부족'] < 0]
        if not shortage.empty:
            for _, row in shortage.iterrows():
                st.error(f"**{row['교과명']}**: {abs(row['과부족'])}시간이 더 필요합니다. 선생님을 더 배정하거나 시수를 높여야 합니다.")
        else:
            st.success("모든 교과의 최소 필요 시수가 충족되었습니다.")

    # --- 저장 기능 ---
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    if col2.button("💾 변경사항 구글 시트에 최종 저장", use_container_width=True):
        try:
            conn.update(worksheet="curriculum_data", data=edited_curr)
            conn.update(worksheet="teacher_data", data=edited_tech)
            st.balloons()
            st.success("구글 시트에 성공적으로 저장되었습니다! 모든 선생님이 업데이트된 내용을 보실 수 있습니다.")
        except Exception as e:
            st.error(f"저장 중 오류 발생: {e}")

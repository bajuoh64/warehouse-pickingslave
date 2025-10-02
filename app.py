import streamlit as st
import pandas as pd
import math

st.set_page_config(layout="wide")

# 앱 제목
st.title("Warehouse Picking MVP")

# 세션 상태 초기화
if "progress" not in st.session_state:
    st.session_state.progress = {}
if "current_index" not in st.session_state:
    st.session_state.current_index = {}

# 왼쪽 설정
st.sidebar.header("설정")
num_pickers = st.sidebar.number_input("인원수", min_value=1, max_value=20, value=1, step=1)
uploaded_file = st.sidebar.file_uploader("파일 선택 (엑셀 .xlsx)", type=["xlsx"])

if st.sidebar.button("Clear Data", type="primary"):
    st.session_state.progress = {}
    st.session_state.current_index = {}
    st.rerun()

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    total_items = len(df)

    # 인원별 분배
    items_per_picker = math.ceil(total_items / num_pickers)
    spans = [(i * items_per_picker, min((i + 1) * items_per_picker, total_items) - 1) for i in range(num_pickers)]

    tabs = st.tabs([f"피커 {i+1}" for i in range(num_pickers)])

    for tab, (picker_id, (s, e)) in zip(tabs, enumerate(spans, start=1)):
        with tab:
            if s > e:
                st.warning("배정 없음")
                continue

            # 세션 상태 준비
            if picker_id not in st.session_state.current_index:
                st.session_state.current_index[picker_id] = s
                st.session_state.progress[picker_id] = [False] * (e - s + 1)

            cur_idx = st.session_state.current_index[picker_id]

            # 현재 진행률
            done_count = sum(st.session_state.progress[picker_id])
            total_count = e - s + 1
            percent = int((done_count / total_count) * 100)

            st.subheader(f"피커 {picker_id} 진행률: {done_count}/{total_count} ({percent}%)")
            st.progress(percent / 100)

            if s <= cur_idx <= e:
                row = df.iloc[cur_idx]

                st.markdown(
                    f"""
                    <div style="background-color:black;color:white;padding:10px;font-size:18px;">
                        <b>피커 #{picker_id} : 항목 {cur_idx-s+1}/{total_count}</b><br>
                        <span style="color:lime;">다음 로케이션: {df.iloc[cur_idx+1]['로케이션'] if cur_idx < e else '없음'}</span><br>
                        현재 로케이션: {row['로케이션']}<br>
                        <span>사이즈: {row['사이즈']} · <span style="color:red;">수량: {row['주문수량']}</span></span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <div style="background-color:#FFD580;padding:8px;">
                        바코드(5): {str(row['스타일명']).split(',')[0].replace('[','')} |
                        색상명: {row['색상명']}
                    </div>
                    <div style="background-color:#FFF2A1;padding:8px;">
                        스타일명: {str(row['스타일명']).split(']')[-1]}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # OK 버튼
                if st.button("OK", key=f"ok_{picker_id}"):
                    st.session_state.progress[picker_id][cur_idx-s] = True
                    if cur_idx < e:
                        st.session_state.current_index[picker_id] += 1
                    st.rerun()

                # 이동 버튼들
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("Previous", key=f"prev_{picker_id}") and cur_idx > s:
                        st.session_state.current_index[picker_id] -= 1
                        st.rerun()
                with col2:
                    if st.button("Next", key=f"next_{picker_id}") and cur_idx < e:
                        st.session_state.current_index[picker_id] += 1
                        st.rerun()
                with col3:
                    if st.button("First in Category", key=f"first_{picker_id}"):
                        st.session_state.current_index[picker_id] = s
                        st.rerun()
                with col4:
                    if st.button("Last in Category", key=f"last_{picker_id}"):
                        st.session_state.current_index[picker_id] = e
                        st.rerun()

            else:
                st.success("모든 배정 완료 🎉")
else:
    st.info("좌측에서 인원수 선택 후 엑셀 파일을 업로드하세요.")

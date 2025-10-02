import streamlit as st
import pandas as pd
import math

# ✅ 1) 페이지/모바일 기본 세팅(단 한 번만!)
st.set_page_config(
    page_title="Warehouse Picking MVP",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ✅ 2) 터치/가독성 개선 스타일
st.markdown("""
<style>
.block-container {padding-top: 0.8rem;}
.stButton > button {padding: 12px 18px; font-size: 18px;}
.stSelectbox, .stNumberInput, .stFileUploader {font-size: 16px;}
.stDataFrame, .element-container {width: 100%;}
</style>
""", unsafe_allow_html=True)

st.title("Warehouse Picking MVP")

# ✅ 3) 세션 상태 초기화
if "progress" not in st.session_state:
    st.session_state.progress = {}          # {picker_id: [True/False, ...]}
if "current_index" not in st.session_state:
    st.session_state.current_index = {}     # {picker_id: 현재 인덱스}
# 모바일 빠른설정용 기본 키
st.session_state.setdefault("num_pickers", 5)
st.session_state.setdefault("uploaded_file", None)

# ✅ 4) 모바일에서도 바로 보이도록 본문에 빠른 설정 제공
with st.expander("📱 모바일 빠른 설정", expanded=True):
    st.session_state["num_pickers"] = st.number_input(
        "인원수", min_value=1, value=st.session_state["num_pickers"], step=1, key="num_pickers_main"
    )
    st.session_state["uploaded_file"] = st.file_uploader(
        "파일 선택 (.xlsx)", type=["xlsx"], key="uploaded_file_main"
    )

# ✅ 5) 사이드바(PC용)도 그대로 유지
st.sidebar.header("설정")
num_pickers_sidebar = st.sidebar.number_input(
    "인원수", min_value=1, max_value=20, value=st.session_state["num_pickers"], step=1, key="num_pickers_sidebar"
)
uploaded_file_sidebar = st.sidebar.file_uploader("파일 선택 (엑셀 .xlsx)", type=["xlsx"], key="uploaded_file_sidebar")

# ✅ 6) 값 통합(모바일/사이드바 중 '마지막으로 입력된 값' 우선)
#   - 파일은 둘 중 하나라도 있으면 사용
effective_num_pickers = st.session_state.get("num_pickers", num_pickers_sidebar)
effective_uploaded = st.session_state.get("uploaded_file") or uploaded_file_sidebar

# Clear Data 버튼
if st.sidebar.button("Clear Data", type="primary"):
    st.session_state.progress = {}
    st.session_state.current_index = {}
    st.session_state["uploaded_file"] = None
    st.session_state["num_pickers"] = 5
    st.rerun()

# ✅ 7) 본문 안내 (파일 없을 때)
if effective_uploaded is None:
    st.info("좌측 상단 ≡ 를 눌러 사이드바를 열거나, 위의 **모바일 빠른 설정**에서 인원수 설정 후 **엑셀(.xlsx)** 파일을 업로드하세요.")
    st.stop()

# ✅ 8) 엑셀 읽기
try:
    df = pd.read_excel(effective_uploaded, engine="openpyxl")
except Exception as e:
    st.error(f"엑셀을 읽는 중 오류가 발생했습니다: {e}")
    st.stop()

# 기대 컬럼: 로케이션, 주문수량, 사이즈, 스타일명, 색상명, 스타일
missing = [c for c in ["로케이션","주문수량","사이즈","스타일명","색상명"] if c not in df.columns]
if missing:
    st.error(f"다음 컬럼이 누락되어 있습니다: {', '.join(missing)}")
    st.stop()

# ✅ 9) 인원별 분배
total_items = len(df)
num_pickers = int(effective_num_pickers)
items_per_picker = math.ceil(total_items / num_pickers) if num_pickers else total_items
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

        # 진행률
        done_count = sum(st.session_state.progress[picker_id])
        total_count = e - s + 1
        percent = int((done_count / total_count) * 100) if total_count else 100
        st.subheader(f"피커 {picker_id} 진행률: {done_count}/{total_count} ({percent}%)")
        st.progress(percent / 100)

        if s <= cur_idx <= e:
            row = df.iloc[cur_idx]
            next_loc = df.iloc[cur_idx+1]["로케이션"] if cur_idx < e else "없음"

            # 상단 정보 카드
            st.markdown(
                f"""
                <div style="background-color:black;color:white;padding:10px;font-size:18px;border-radius:8px;">
                    <b>피커 #{picker_id} : 항목 {cur_idx-s+1}/{total_count}</b><br>
                    <span style="color:lime;">다음 로케이션: {next_loc}</span><br>
                    현재 로케이션: {row['로케이션']}<br>
                    <span>사이즈: {row['사이즈']} · <span style="color:red;">수량: {row['주문수량']}</span></span>
                </div>
                """,
                unsafe_allow_html=True
            )

            # 바코드/색상, 스타일명 카드
            barcode_5 = str(row["스타일명"]).split(",")[0].replace("[","")  # [84785,BLACK ...] → 84785
            style_name = str(row["스타일명"]).split("]")[-1].strip()

            st.markdown(
                f"""
                <div style="background-color:#FFD580;padding:10px;border-radius:8px;margin-top:8px;">
                    바코드(5): {barcode_5}  |  색상명: {row['색상명']}
                </div>
                <div style="background-color:#FFF2A1;padding:10px;border-radius:8px;margin-top:6px;">
                    스타일명: {style_name}
                </div>
                """,
                unsafe_allow_html=True
            )

            # OK 버튼
            if st.button("OK", key=f"ok_{picker_id}"):
                st.session_state.progress[picker_id][cur_idx - s] = True
                if cur_idx < e:
                    st.session_state.current_index[picker_id] += 1
                st.rerun()

            # 이동 버튼들
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("Previous", key=f"prev_{picker_id}") and cur_idx > s:
                    st.session_state.current_index[picker_id] -= 1
                    st.rerun()
            with c2:
                if st.button("Next", key=f"next_{picker_id}") and cur_idx < e:
                    st.session_state.current_index[picker_id] += 1
                    st.rerun()
            with c3:
                if st.button("First in Category", key=f"first_{picker_id}"):
                    st.session_state.current_index[picker_id] = s
                    st.rerun()
            with c4:
                if st.button("Last in Category", key=f"last_{picker_id}"):
                    st.session_state.current_index[picker_id] = e
                    st.rerun()
        else:
            st.success("모든 배정 완료 🎉")

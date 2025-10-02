import streamlit as st

# ---------------------------
# 페이지 기본 설정
# ---------------------------
st.set_page_config(
    page_title="Warehouse Picking MVP",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------
# 스타일 (CSS)
# ---------------------------
st.markdown("""
<style>
.block-container { padding-top: 0.8rem; }

/* 카드 스타일 */
.picker-card {
  background: linear-gradient(160deg, #0f172a 0%, #111827 60%);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 8px 22px rgba(0,0,0,.35);
  margin-top: 10px;
}

/* 텍스트 */
.hint { color:#9CA3AF; font-size:0.92rem; }
.value { color:#F9FAFB; font-size:1.06rem; font-weight:700; }
.progress { color:#E5E7EB; font-size:1.02rem; font-weight:800; }

/* 노란 박스 */
.badge {
  background:#fcd34d22;
  border:1px solid #f59e0b55;
  border-radius:12px;
  padding:10px 12px;
  margin-top:8px;
}
.badge .hint { color:#F59E0B; font-weight:800; }

/* 버튼 공통 */
.stButton > button {
  width: 100%;
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 16px;
  font-weight: 800;
}
.ok-btn { background:#22c55e !important; color:#0b1117 !important; }
.nav-btn { background:#1f2937 !important; color:#E5E7EB !important; }
.util-btn{ background:#111827 !important; color:#9CA3AF !important; border:1px solid #374151 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# 더미 데이터 (실제 로직 연결 필요)
# ---------------------------
item = {
    "picker_idx": 1,
    "current_idx": 1,
    "total_cnt": 14,
    "current_location": "CC",
    "next_location": "1FC0604",
    "size": "OS",
    "qty": 7,
    "barcode5": "41303",
    "color": "MULTI",
    "style": "DEUS X HELINOX TACITAL TABLE M"
}

# ---------------------------
# 상단 진행 상태
# ---------------------------
st.markdown(
    f"<div class='progress'>피커 #{item['picker_idx']} : 항목 {item['current_idx']}/{item['total_cnt']}</div>",
    unsafe_allow_html=True
)

# ---------------------------
# 상세 카드
# ---------------------------
st.markdown("<div class='picker-card'>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown("<div class='hint'>현재 로케이션</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='value'>{item['current_location']}</div>", unsafe_allow_html=True)
with c2:
    st.markdown("<div class='hint'>다음제품 로케이션</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='value'>{item['next_location']}</div>", unsafe_allow_html=True)

c3, c4 = st.columns(2)
with c3:
    st.markdown("<div class='hint'>사이즈</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='value'>{item['size']}</div>", unsafe_allow_html=True)
with c4:
    st.markdown("<div class='hint'>수량</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='value'>{item['qty']}</div>", unsafe_allow_html=True)

st.markdown(f"<div class='badge'><div class='hint'>바코드 5자리</div><div class='value'>{item['barcode5']}</div></div>", unsafe_allow_html=True)
st.markdown(f"<div class='badge'><div class='hint'>컬러명</div><div class='value'>{item['color']}</div></div>", unsafe_allow_html=True)
st.markdown(f"<div class='badge'><div class='hint'>스타일명</div><div class='value'>{item['style']}</div></div>", unsafe_allow_html=True)

# ---------------------------
# 버튼 레이아웃 (요청한 배치)
# ---------------------------

# 1) OK (가운데 단독)
ok_L, ok_C, ok_R = st.columns([1,2,1])
with ok_C:
    if st.button("OK", key="ok_btn"):
        st.toast("OK 처리 완료")

# 2) Previous | Next
row2_L, row2_R = st.columns(2)
with row2_L:
    if st.button("Previous", key="prev_btn"):
        st.toast("이전 항목으로 이동")
with row2_R:
    if st.button("Next", key="next_btn"):
        st.toast("다음 항목으로 이동")

# 3) First in Category | Last in Category
row3_L, row3_R = st.columns(2)
with row3_L:
    if st.button("First in Category", key="first_cat_btn"):
        st.toast("카테고리 처음으로 이동")
with row3_R:
    if st.button("Last in Category", key="last_cat_btn"):
        st.toast("카테고리 마지막으로 이동")

# 4) Clear Data (가운데 단독)
clr_L, clr_C, clr_R = st.columns([1,2,1])
with clr_C:
    if st.button("Clear Data", key="clear_btn"):
        st.toast("데이터 초기화 완료")

st.markdown("</div>", unsafe_allow_html=True)

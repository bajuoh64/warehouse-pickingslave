import streamlit as st

# ✅ 페이지 설정
st.set_page_config(
    page_title="Warehouse Picking MVP",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ✅ 글로벌 스타일
st.markdown("""
<style>
/* 본문 여백 */
.block-container {padding-top: 0.8rem;}

/* 공통 카드 */
.picker-card {
  background: linear-gradient(160deg, #0f172a 0%, #111827 60%);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 18px;
  padding: 16px 16px 10px 16px;
  box-shadow: 0 6px 18px rgba(0,0,0,.35);
  margin-top: 10px;
}

/* 라벨/값 */
.label {font-size: 0.92rem; color: #9CA3AF; letter-spacing:.2px;}
.value {font-size: 1.05rem; color: #F9FAFB; font-weight: 600;}
.progress-title {font-size: 1.02rem; color: #E5E7EB; font-weight: 700;}

/* 버튼 */
.stButton > button {
  width: 100%;
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 16px;
  font-weight: 700;
}
button.ok-btn { background: #22c55e !important; color: #0a0f14 !important; }
button.nav-btn { background: #1f2937 !important; color: #E5E7EB !important; }
button.util-btn{ background: #111827 !important; color: #9CA3AF !important; border:1px solid #374151 !important; }

/* 배지 박스 */
.badge {
  background: #fcd34d22;
  border: 1px solid #f59e0b55;
  border-radius: 12px;
  padding: 10px 12px;
  margin-top: 6px;
}
.badge .label { color: #F59E0B; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ==============================
# 📊 더미 데이터 (실제 로직 연결하면 됨)
# ==============================
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

# ==============================
# 📍 상단 진행 정보
# ==============================
st.markdown(
    f"<div class='progress-title'>피커 #{item['picker_idx']} : 항목 {item['current_idx']}/{item['total_cnt']}</div>",
    unsafe_allow_html=True
)

# ==============================
# 📦 메인 카드
# ==============================
st.markdown("<div class='picker-card'>", unsafe_allow_html=True)

# ── 위치 정보
colA, colB = st.columns(2)
with colA:
    st.markdown("<div class='label'>현재 로케이션</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='value'>{item['current_location']}</div>", unsafe_allow_html=True)
with colB:
    st.markdown("<div class='label'>다음제품 로케이션</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='value'>{item['next_location']}</div>", unsafe_allow_html=True)

# ── 사이즈 / 수량
colC, colD = st.columns(2)
with colC:
    st.markdown("<div class='label'>사이즈</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='value'>{item['size']}</div>", unsafe_allow_html=True)
with colD:
    st.markdown("<div class='label'>수량</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='value'>{item['qty']}</div>", unsafe_allow_html=True)

# ── 바코드 / 컬러 / 스타일
st.markdown(
    f"""
    <div class='badge'>
      <div class='label'>바코드 5자리</div>
      <div class='value'>{item['barcode5']}</div>
    </div>
    """, unsafe_allow_html=True
)
st.markdown(
    f"""
    <div class='badge'>
      <div class='label'>컬러명</div>
      <div class='value'>{item['color']}</div>
    </div>
    """, unsafe_allow_html=True
)
st.markdown(
    f"""
    <div class='badge'>
      <div class='label'>스타일명</div>
      <div class='value'>{item['style']}</div>
    </div>
    """, unsafe_allow_html=True
)

# ── OK 버튼
ok_col = st.columns(1)[0]
with ok_col:
    if st.button("OK !", key="ok_btn"):
        st.toast("OK 처리 완료")

st.markdown("</div>", unsafe_allow_html=True)  # /picker-card

# ==============================
# 🔀 네비게이션 버튼
# ==============================
nav1, nav2 = st.columns(2)
with nav1:
    if st.button("Previous", key="prev"): st.toast("이전 항목 이동")
with nav2:
    if st.button("Next", key="next"): st.toast("다음 항목 이동")

cat1, cat2 = st.columns(2)
with cat1:
    if st.button("Last in Category", key="last_cat"): st.toast("카테고리 마지막으로 이동")
with cat2:
    if st.button("First in Category", key="first_cat"): st.toast("카테고리 처음으로 이동")

# ==============================
# 🧹 유틸 버튼
# ==============================
if st.button("Clear Data", key="clear"):
    st.toast("데이터 초기화 완료")

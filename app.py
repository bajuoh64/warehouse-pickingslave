import streamlit as st

# ---------------------------
# Page Setup
# ---------------------------
st.set_page_config(
    page_title="Warehouse Picking MVP",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------
# CSS Styles
# ---------------------------
st.markdown("""
<style>
.stButton > button {
    width: 100%;
    height: 60px;
    border-radius: 14px;
    font-size: 22px;
    font-weight: 800;
    margin-top: 8px;
}

/* 버튼 컬러 */
button:has(span:contains("OK")) {
    background: #facc15 !important; color:#111827 !important;
}
button:has(span:contains("Previous")) {
    background: #111827 !important; color:#f9fafb !important;
}
button:has(span:contains("Next")) {
    background: #2563eb !important; color:#ffffff !important;
}
button:has(span:contains("First in Category")),
button:has(span:contains("Last in Category")) {
    background: #111827 !important; color:#f9fafb !important;
}
button:has(span:contains("Clear Data")) {
    background: #fca5a5 !important; border:2px solid #ef4444 !important;
    color:#7f1d1d !important;
}

/* 가운데 정렬 전용 컨테이너 */
.center-row { display:flex; justify-content:center; }
.center-col { width: 70%; }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Dummy Data (실제 데이터 연결 부분)
# ---------------------------
item = {
    "slot": "021",
    "green_code": "2LV041",
    "sku": "2LW010",
    "size": "L",
    "qty": 1,
    "badge": "46201,CORAL",
    "title": "OBEY INTERNATIONAL SEOUL OVERDYED SS OB25SSTSS02837001"
}

# ---------------------------
# Main Info Card (간단 버전)
# ---------------------------
st.markdown(f"### 슬롯: {item['slot']}   |   코드: {item['green_code']}")
st.markdown(f"## **{item['sku']}**")
st.markdown(f"사이즈: {item['size']}   |   수량: {item['qty']}")
st.markdown(f"**{item['badge']}**")
st.markdown(item["title"])

# ---------------------------
# Buttons Layout (4줄 구조)
# ---------------------------

# 1️⃣ OK (첫 줄 중앙)
col1, col2, col3 = st.columns([1,2,1])
with col2:
    ok = st.button("OK")
if ok: st.toast("OK 처리 완료")

# 2️⃣ Previous | Next (두번째 줄)
c2_1, c2_2 = st.columns(2)
with c2_1:
    prev = st.button("Previous")
with c2_2:
    nxt = st.button("Next")
if prev: st.toast("이전 항목으로 이동")
if nxt: st.toast("다음 항목으로 이동")

# 3️⃣ First in Category | Last in Category (세번째 줄)
c3_1, c3_2 = st.columns(2)
with c3_1:
    fic = st.button("First in Category")
with c3_2:
    lic = st.button("Last in Category")
if fic: st.toast("카테고리 처음으로 이동")
if lic: st.toast("카테고리 마지막으로 이동")

# 4️⃣ Clear Data (네번째 줄 중앙)
col4_1, col4_2, col4_3 = st.columns([1,2,1])
with col4_2:
    clear = st.button("Clear Data")
if clear: st.toast("데이터 초기화 완료")

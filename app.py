import streamlit as st
from datetime import datetime

# =========================
# Page Setup
# =========================
st.set_page_config(
    page_title="Warehouse Picking MVP",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================
# Global Styles (CSS)
# =========================
st.markdown("""
<style>
/* 페이지 여백 및 기본 폰트 크기 */
.block-container { padding-top: 0.6rem; }

/* 상단 시간 */
.now-time { font-size: 1.35rem; font-weight: 800; }

/* 상단 컨트롤 */
.top-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 10px 12px;
  margin-bottom: 8px;
}

/* 피커 숫자 버튼(세그먼트 느낌) */
.segment {
  display:inline-flex; gap:12px; align-items:center;
}
.segment .seg {
  width:64px; height:64px;
  border-radius:16px;
  border:1px solid #e5e7eb;
  background:#f8fafc;
  display:flex; align-items:center; justify-content:center;
  font-size:20px; font-weight:800; color:#111827;
  box-shadow: 0 2px 4px rgba(0,0,0,.06) inset;
}
.segment .seg.active {
  background:#22c55e; color:#fff; border-color:#16a34a;
  box-shadow: 0 0 0 3px #bbf7d0 inset;
}

/* 메인 카드 */
.main-card {
  background:#fff;
  border:1px solid #e5e7eb;
  border-radius:18px;
  padding:16px;
  margin-top:8px;
  box-shadow: 0 8px 22px rgba(0,0,0,.06);
}

/* 헤더 바 (검정 021) */
.slot-bar {
  background:#111827;
  color:#f9fafb;
  border-radius:10px;
  padding:8px 14px;
  font-size:32px; font-weight:900;
  text-align:center;
  letter-spacing:2px;
}

/* 우상단 그린 라벨 */
.green-tag {
  position: absolute;
  right: 16px;
  top: 52px;
  font-weight: 900;
  color: #16a34a;
  font-size: 48px;
}

/* 큰 SKU 코드 */
.big-sku {
  font-size: 96px;
  line-height: 1.0;
  font-weight: 900;
  color:#1f2937;
  letter-spacing: 4px;
  margin: 16px 0 4px 0;
}

/* 사이즈/수량 */
.meta-row { display:flex; align-items:center; gap:24px; }
.meta-lbl { font-size: 32px; font-weight: 800; color:#111827; }
.meta-size { font-size: 40px; font-weight: 900; color:#111827; }
.meta-qty  { font-size: 40px; font-weight: 900; color:#ef4444; }

/* 베이지 배지 */
.badge {
  background:#fde8d9;
  border:1px solid #f3b58a;
  border-radius:14px;
  padding:12px 16px;
  font-size:28px; font-weight:900; color:#111827;
  display:inline-block;
}

/* 제품 타이틀(여러 줄) */
.title {
  margin-top: 10px;
  font-size: 28px;
  line-height: 1.25;
  font-weight: 800;
  letter-spacing: .5px;
  color:#1f2937;
}

/* 버튼 공통스타일(기본: 회색) */
.stButton > button {
  width: 100%;
  height: 60px;
  border-radius: 18px;
  font-size: 22px;
  font-weight: 900;
  border: 1px solid #e5e7eb;
  background: #1f2937;
  color: #f9fafb;
  box-shadow: 0 4px 10px rgba(0,0,0,.05);
}

/* 행 간격 */
.row-gap { margin-top: 12px; }

/* 가운데 단독 버튼 위치 보정용 래퍼 */
.center-row { display:flex; justify-content:center; }
.center-col { width: 72%; }

/* ---- JS에서 라벨로 컬러 덮어쓸 예정 ---- */
</style>
""", unsafe_allow_html=True)

# =========================
# Session State
# =========================
if "picker_count" not in st.session_state:
    st.session_state.picker_count = 3
if "active_picker" not in st.session_state:
    st.session_state.active_picker = 2  # 예시 화면처럼 2번 선택

# =========================
# Top: 현재 시간 + 인원수 + 파일선택 + 피커 세그먼트
# =========================
st.markdown(f"<div class='now-time'>{datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)

with st.container():
    with st.form("top_controls", clear_on_submit=False):
        colA, colB = st.columns([2,6])
        with colA:
            head = st.text_input("인원수:", value=str(st.session_state.picker_count))
        with colB:
            file = st.file_uploader("파일 선택", type=["xlsx", "csv"], label_visibility="visible")
        submitted = st.form_submit_button("적용")
        if submitted:
            try:
                st.session_state.picker_count = int(head.strip())
            except:
                st.warning("인원수는 숫자로 입력해주세요.")

    # 피커 선택 (1~N)
    seg_cols = st.columns(st.session_state.picker_count)
    for i in range(st.session_state.picker_count):
        idx = i + 1
        with seg_cols[i]:
            # 라운드 스퀘어 스타일을 위해 HTML 세그먼트 + 클릭은 버튼으로 처리
            st.markdown(
                f"<div class='segment'><div class='seg {'active' if st.session_state.active_picker==idx else ''}'>{idx}</div></div>",
                unsafe_allow_html=True
            )
            if st.button(f"select_picker_{idx}", key=f"seg_btn_{idx}", help=f"{idx}번 피커 선택", use_container_width=True):
                st.session_state.active_picker = idx
            # 버튼 라벨은 숨기기 (CSS로 숨기는 대신 text-indent)
            st.markdown("""
            <style>
            button[kind="secondary"][data-testid^="baseButton-secondary"] { text-indent:-9999px; height:0; padding:0; margin:0; border:none; box-shadow:none; }
            </style>
            """, unsafe_allow_html=True)

# =========================
# Demo 데이터 (실데이터 바인딩 위치)
# =========================
data = {
    "slot":"021",
    "green_code":"2LV041",
    "sku":"2LW010",
    "size":"L",
    "qty":1,
    "badge":"46201,CORAL",
    "title_lines":[
        "OBEY INTERNATIONAL",
        "SEOUL OVERDYED SS",
        "OB25SSTS SSO2837001"
    ]
}

# =========================
# Main Card
# =========================
st.markdown("<div class='main-card'>", unsafe_allow_html=True)

# 검정 슬롯바 & 그린 태그
st.markdown(f"<div class='slot-bar'>{data['slot']}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='green-tag'>{data['green_code']}</div>", unsafe_allow_html=True)

# 큰 SKU 코드
st.markdown(f"<div class='big-sku'>{data['sku']}</div>", unsafe_allow_html=True)

# 사이즈 / 수량
st.markdown(
    f"<div class='meta-row'><div class='meta-lbl'> </div>"
    f"<div class='meta-size'>{data['size']}</div>"
    f"<div class='meta-lbl'> </div>"
    f"<div class='meta-qty'>{data['qty']}</div></div>",
    unsafe_allow_html=True
)

# 베이지 배지
st.markdown(f"<div class='badge'>{data['badge']}</div>", unsafe_allow_html=True)

# 제품 타이틀
st.markdown("<div class='title'>" + "<br/>".join(data["title_lines"]) + "</div>", unsafe_allow_html=True)

# =========================
# Buttons (레이아웃)
# =========================

# 1) OK (가운데 단독)
st.markdown("<div class='row-gap center-row'><div class='center-col'>", unsafe_allow_html=True)
ok_clicked = st.button("OK", key="ok_btn")
st.markdown("</div></div>", unsafe_allow_html=True)

# 2) Previous | Next
prev_col, next_col = st.columns(2)
with prev_col:
    prev_clicked = st.button("Previous", key="prev_btn")
with next_col:
    next_clicked = st.button("Next", key="next_btn")

# 3) First in Category | Last in Category
first_col, last_col = st.columns(2)
with first_col:
    first_clicked = st.button("First in Category", key="first_cat_btn")
with last_col:
    last_clicked = st.button("Last in Category", key="last_cat_btn")

# 4) Clear Data (가운데 단독)
st.markdown("<div class='row-gap center-row'><div class='center-col'>", unsafe_allow_html=True)
clear_clicked = st.button("Clear Data", key="clear_btn")
st.markdown("</div></div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # /main-card

# =========================
# Actions (토스트 예시)
# =========================
if ok_clicked: st.toast("OK 처리 완료")
if prev_clicked: st.toast("이전 항목으로 이동")
if next_clicked: st.toast("다음 항목으로 이동")
if first_clicked: st.toast("카테고리 처음으로 이동")
if last_clicked: st.toast("카테고리 마지막으로 이동")
if clear_clicked: st.toast("데이터 초기화 완료")

# =========================
# Button Color Patches (JS)
# - 버튼 라벨 텍스트로 DOM을 찾아 색상/모양 입힘
# =========================
st.markdown("""
<script>
const patch = () => {
  const btns = Array.from(window.parent.document.querySelectorAll('button'));
  const byLabel = (txt) => btns.find(b => (b.innerText || '').trim() === txt);

  const ok = byLabel('OK');
  if (ok) {
    ok.style.background = '#facc15';
    ok.style.color = '#111827';
    ok.style.border = '1px solid #eab308';
    ok.style.height = '72px';
    ok.style.fontSize = '26px';
    ok.style.borderRadius = '22px';
  }
  const prev = byLabel('Previous');
  if (prev) {
    prev.style.background = '#111827';
    prev.style.color = '#f9fafb';
  }
  const next = byLabel('Next');
  if (next) {
    next.style.background = '#2563eb';
    next.style.color = '#ffffff';
  }
  const fic = byLabel('First in Category');
  if (fic) {
    fic.style.background = '#111827';
    fic.style.color = '#f9fafb';
  }
  const lic = byLabel('Last in Category');
  if (lic) {
    lic.style.background = '#111827';
    lic.style.color = '#f9fafb';
  }
  const clr = byLabel('Clear Data');
  if (clr) {
    clr.style.background = '#fca5a5';
    clr.style.border = '2px solid #ef4444';
    clr.style.color = '#7f1d1d';
    clr.style.height = '72px';
    clr.style.fontSize = '28px';
    clr.style.borderRadius = '22px';
  }
};
// 처음 및 짧은 지연 후 재시도(스트림릿 렌더링 타이밍 대응)
setTimeout(patch, 50);
setTimeout(patch, 250);
setTimeout(patch, 600);
</script>
""", unsafe_allow_html=True)

import streamlit as st
from datetime import datetime
import math

# =========================
# Page
# =========================
st.set_page_config(
    page_title="Warehouse Picking MVP",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================
# Init session state
# =========================
if "picker_count" not in st.session_state:
    st.session_state.picker_count = 3
if "active_picker" not in st.session_state:
    st.session_state.active_picker = 2

# =========================
# CSS (샘플 색/형태 매칭)
# =========================
st.markdown("""
<style>
.block-container { padding-top: 0.6rem; }

/* 현재 시간 */
.now-time { font-size: 1.35rem; font-weight: 800; }

/* 세그먼트 박스 표시용 */
.segment { display:inline-flex; gap:12px; align-items:center; }
.segment .seg {
  width:64px; height:64px;
  border-radius:16px;
  border:1px solid #e5e7eb;
  background:#f8fafc;
  display:flex; align-items:center; justify-content:center;
  font-size:20px; font-weight:800; color:#111827;
  box-shadow: 0 2px 4px rgba(0,0,0,.06) inset;
  margin-bottom: 6px;
}
.segment .seg.active {
  background:#22c55e; color:#fff; border-color:#16a34a;
  box-shadow: 0 0 0 3px #bbf7d0 inset;
}

/* 메인 카드 */
.main-card {
  position: relative;
  background:#fff;
  border:1px solid #e5e7eb;
  border-radius:18px;
  padding:16px;
  margin-top:8px;
  box-shadow: 0 8px 22px rgba(0,0,0,.06);
}

/* 검정 슬롯바(021) */
.slot-bar {
  background:#111827; color:#f9fafb;
  border-radius:10px; padding:8px 14px;
  font-size:32px; font-weight:900; text-align:center; letter-spacing:2px;
}

/* 우상단 초록 코드 */
.green-tag {
  position:absolute; right:16px; top:52px;
  font-weight:900; color:#16a34a; font-size:48px;
}

/* 큰 SKU */
.big-sku {
  font-size: 96px; line-height: 1.0; font-weight: 900;
  color:#1f2937; letter-spacing: 4px; margin: 16px 0 8px 0;
}

/* 사이즈/수량 라인 */
.meta-row { display:flex; align-items:center; gap:24px; }
.meta-size { font-size: 40px; font-weight: 900; color:#111827; }
.meta-qty  { font-size: 40px; font-weight: 900; color:#ef4444; }  /* 빨강 수량 */

/* 베이지 배지 */
.badge {
  background:#fde8d9;
  border:1px solid #f3b58a;
  border-radius:14px;
  padding:12px 16px;
  font-size:28px; font-weight:900; color:#111827;
  display:inline-block; margin-top:8px;
}

/* 제품 타이틀(여러 줄 굵게) */
.title {
  margin-top: 10px;
  font-size: 28px; line-height: 1.25;
  font-weight: 800; letter-spacing: .5px; color:#1f2937;
}

/* 버튼 기본(레이아웃용) */
.stButton > button {
  width: 100%; height: 60px;
  border-radius: 18px; font-size: 22px; font-weight: 900;
  border: 1px solid #e5e7eb;
  background: #1f2937; color: #f9fafb;   /* 기본 회색(검정톤) */
  box-shadow: 0 4px 10px rgba(0,0,0,.05);
}

/* 가운데 단독 버튼 폭 */
.center-row { display:flex; justify-content:center; }
.center-col { width: 72%; }

.row-gap { margin-top: 12px; }

/* 숨김 버튼(세그먼트 클릭 처리용)의 시각적 노출 제거 */
.hide-btn button { text-indent:-9999px; height:0; padding:0; margin:0; border:none; box-shadow:none; }
</style>
""", unsafe_allow_html=True)

# =========================
# Helpers
# =========================
def render_picker_segments(count: int, active: int):
    """3개씩 끊어서 세그먼트 표시 + 클릭 버튼."""
    rows = math.ceil(count / 3)
    idx = 1
    for _ in range(rows):
        cols = st.columns(min(3, count - (idx-1)))
        for c in cols:
            with c:
                st.markdown(
                    f"<div class='segment'><div class='seg {'active' if idx==active else ''}'>{idx}</div></div>",
                    unsafe_allow_html=True
                )
                # 클릭용 숨김 버튼
                with st.container():
                    st.markdown("<div class='hide-btn'>", unsafe_allow_html=True)
                    if st.button(f"select_{idx}", key=f"seg_btn_{idx}"):
                        st.session_state.active_picker = idx
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            idx += 1
            if idx > count:
                break

# =========================
# Top: 시간 / 인원수 / 파일 / 피커
# =========================
st.markdown(f"<div class='now-time'>{datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)

top1, top2 = st.columns([2,6])
with top1:
    # ✅ 인원수 변경 즉시 반영 + rerun
    new_count = st.number_input(
        "인원수:",
        min_value=1,
        max_value=24,
        step=1,
        value=st.session_state.picker_count,
        key="picker_count_input",
    )
    if int(new_count) != st.session_state.picker_count:
        st.session_state.picker_count = int(new_count)
        if st.session_state.active_picker > st.session_state.picker_count:
            st.session_state.active_picker = st.session_state.picker_count
        st.rerun()

with top2:
    st.file_uploader("파일 선택", type=["xlsx","csv"])

# 피커 세그먼트 렌더
render_picker_segments(st.session_state.picker_count, st.session_state.active_picker)

# =========================
# Demo 데이터 (실데이터로 교체 지점)
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
        "OB25SSTSS02837001"
    ]
}

# =========================
# Main Card
# =========================
st.markdown("<div class='main-card'>", unsafe_allow_html=True)
st.markdown(f"<div class='slot-bar'>{data['slot']}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='green-tag'>{data['green_code']}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='big-sku'>{data['sku']}</div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='meta-row'><div class='meta-size'>{data['size']}</div>"
    f"<div class='meta-qty'>{data['qty']}</div></div>",
    unsafe_allow_html=True
)
st.markdown(f"<div class='badge'>{data['badge']}</div>", unsafe_allow_html=True)
st.markdown("<div class='title'>" + "<br/>".join(data["title_lines"]) + "</div>", unsafe_allow_html=True)

# =========================
# Buttons (4줄 레이아웃)
# =========================
# 1) OK (첫줄 중앙)
st.markdown("<div class='row-gap center-row'><div class='center-col'>", unsafe_allow_html=True)
ok_clicked = st.button("OK", key="ok_btn")
st.markdown("</div></div>", unsafe_allow_html=True)

# 2) Previous | Next (둘째줄)
prev_col, next_col = st.columns(2)
with prev_col:
    prev_clicked = st.button("Previous", key="prev_btn")
with next_col:
    next_clicked = st.button("Next", key="next_btn")

# 3) First in Category | Last in Category (셋째줄)
first_col, last_col = st.columns(2)
with first_col:
    first_clicked = st.button("First in Category", key="first_cat_btn")
with last_col:
    last_clicked = st.button("Last in Category", key="last_cat_btn")

# 4) Clear Data (넷째줄 중앙)
st.markdown("<div class='row-gap center-row'><div class='center-col'>", unsafe_allow_html=True)
clear_clicked = st.button("Clear Data", key="clear_btn")
st.markdown("</div></div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # /main-card

# =========================
# 클릭 동작(데모)
# =========================
if ok_clicked: st.toast("OK 처리 완료")
if prev_clicked: st.toast("이전 항목으로 이동")
if next_clicked: st.toast("다음 항목으로 이동")
if first_clicked: st.toast("카테고리 처음으로 이동")
if last_clicked: st.toast("카테고리 마지막으로 이동")
if clear_clicked: st.toast("데이터 초기화 완료")

# =========================
# 버튼 색상 패치(JS) — 라벨 기준으로 색 덮어쓰기
# =========================
st.markdown("""
<script>
const patch = () => {
  const btns = Array.from(window.parent.document.querySelectorAll('button'));
  const byText = (t) => btns.find(b => (b.innerText || '').trim() === t);

  const ok = byText('OK');
  if (ok) {
    ok.style.background = '#facc15';   /* 노랑 */
    ok.style.color = '#111827';
    ok.style.border = '1px solid #eab308';
    ok.style.height = '72px';
    ok.style.fontSize = '26px';
    ok.style.borderRadius = '22px';
  }
  const prev = byText('Previous');
  if (prev) {
    prev.style.background = '#111827'; /* 검정 */
    prev.style.color = '#f9fafb';
  }
  const next = byText('Next');
  if (next) {
    next.style.background = '#2563eb'; /* 파랑 */
    next.style.color = '#ffffff';
  }
  const fic = byText('First in Category');
  if (fic) {
    fic.style.background = '#111827';  /* 검정 */
    fic.style.color = '#f9fafb';
  }
  const lic = byText('Last in Category');
  if (lic) {
    lic.style.background = '#111827';  /* 검정 */
    lic.style.color = '#f9fafb';
  }
  const clr = byText('Clear Data');
  if (clr) {
    clr.style.background = '#fca5a5';  /* 연빨강 */
    clr.style.border = '2px solid #ef4444'; /* 진빨강 테두리 */
    clr.style.color = '#7f1d1d';
    clr.style.height = '72px';
    clr.style.fontSize = '28px';
    clr.style.borderRadius = '22px';
  }
};
setTimeout(patch, 60);
setTimeout(patch, 250);
setTimeout(patch, 600);
</script>
""", unsafe_allow_html=True)

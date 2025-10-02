import streamlit as st
import pandas as pd
from datetime import datetime
import math

# =============== 페이지 설정 ===============
st.set_page_config(
    page_title="Warehouse Picking MVP",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="📦"
)

# =============== CSS (화이트 배경 + 완료 시 흐리게 표시) ===============
st.markdown("""
<style>
html, body, [class*="css"]  {
    background-color: #ffffff !important;
    color: #111827 !important;
    font-family: "Helvetica Neue", sans-serif;
}

/* 현재 시간 */
.now-time { font-size: 1.35rem; font-weight: 800; color:#111827; }

/* 메인 카드 */
.main-card {
  position: relative;
  background:#fff;
  border:2px solid #e5e7eb;
  border-radius:18px;
  padding:16px;
  margin-top:8px;
  box-shadow: 0 6px 18px rgba(0,0,0,.08);
}
.main-card.done {
  background:#f3f4f6 !important;   /* 회색 배경 */
  color:#9ca3af !important;        /* 흐린 글씨 */
}

/* DONE 리본 */
.ribbon {
  position:absolute; top:10px; right:-25px;
  transform: rotate(45deg);
  background:#9ca3af; color:#fff;
  padding:4px 40px; font-size:14px; font-weight:800;
  box-shadow:0 2px 6px rgba(0,0,0,.15);
}

/* 슬롯바 / 코드 / SKU */
.slot-bar { background:#111827; color:#f9fafb; border-radius:10px; padding:8px 14px;
  font-size:32px; font-weight:900; text-align:center; }
.green-tag { position:absolute; right:16px; top:52px; font-weight:900; color:#16a34a; font-size:44px; }
.big-sku { font-size:92px; font-weight:900; color:#1f2937; margin:16px 0 8px 0; }

/* 사이즈/수량 */
.meta-row { display:flex; align-items:center; gap:24px; }
.meta-size { font-size:38px; font-weight:900; color:#1f2937; }
.meta-qty  { font-size:38px; font-weight:900; color:#dc2626; }

/* 배지/타이틀 */
.badge { background:#fde8d9; border:1px solid #fca5a5; border-radius:14px; padding:10px 14px;
  font-size:26px; font-weight:800; color:#1f2937; display:inline-block; margin-top:8px; }
.title { margin-top:10px; font-size:26px; line-height:1.25; font-weight:800; color:#111827; }

/* 버튼 */
.stButton > button {
  width:100%; height:60px; border-radius:18px; font-size:22px; font-weight:900;
  border:1px solid #e5e7eb; background:#1f2937; color:#f9fafb;
}
.center-row { display:flex; justify-content:center; }
.center-col { width:72%; }
.row-gap { margin-top:12px; }

</style>
""", unsafe_allow_html=True)

# =============== 세션 상태 초기화 ===============
def init_state():
    ss = st.session_state
    ss.setdefault("picker_count", 3)
    ss.setdefault("active_picker", 1)
    ss.setdefault("picker_idx_in_group", 0)
    ss.setdefault("df_norm", None)
    ss.setdefault("groups", {})
init_state()

# =============== 예시 데이터 변환 함수 ===============
def normalize_columns(df):
    out = pd.DataFrame()
    out["slot"]       = df.iloc[:,0].astype(str)
    out["green_code"] = df.iloc[:,1].astype(str)
    out["sku"]        = df.iloc[:,2].astype(str)
    out["size"]       = df.iloc[:,3].astype(str)
    out["qty"]        = pd.to_numeric(df.iloc[:,4], errors="coerce").fillna(1).astype(int)
    out["barcode5"]   = df.iloc[:,5].astype(str) if df.shape[1] > 5 else ""
    out["color"]      = df.iloc[:,6].astype(str) if df.shape[1] > 6 else ""
    out["style_name"] = df.iloc[:,7].astype(str) if df.shape[1] > 7 else out["sku"]
    out["category"]   = out["style_name"]
    out["picker"]     = None
    out["done"]       = False
    return out

def build_groups(df, picker_count):
    df = df.copy()
    df["picker"] = (pd.RangeIndex(0,len(df)) % picker_count) + 1
    groups = {i: df.index[df["picker"]==i].tolist() for i in range(1, picker_count+1)}
    return df, groups

def get_current_row():
    ss = st.session_state
    g = ss.groups.get(ss.active_picker, [])
    if not g: return None
    idx = max(0, min(ss.picker_idx_in_group, len(g)-1))
    return ss.df_norm.loc[g[idx]]

# =============== 상단 UI ===============
st.markdown(f"<div class='now-time'>{datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)

col1, col2 = st.columns([2,6])
with col1:
    st.session_state.picker_count = st.number_input("인원수:", 1, 50, st.session_state.picker_count)
with col2:
    uploaded = st.file_uploader("피킹 파일 업로드 (.xlsx/.csv)", type=["xlsx","csv"])
    if uploaded is not None:
        if uploaded.name.endswith(".csv"):
            df_raw = pd.read_csv(uploaded)
        else:
            df_raw = pd.read_excel(uploaded)
        st.session_state.df_norm = normalize_columns(df_raw)
        st.session_state.df_norm, st.session_state.groups = build_groups(st.session_state.df_norm, st.session_state.picker_count)
        st.session_state.picker_idx_in_group = 0

# 진행도
if st.session_state.df_norm is not None:
    g = st.session_state.groups.get(st.session_state.active_picker, [])
    if g:
        done_cnt = int(st.session_state.df_norm.loc[g,"done"].sum())
        total = len(g)
        st.progress(done_cnt/total, text=f"진행도 {done_cnt}/{total}")
    else:
        st.info("현재 피커에게 할당된 아이템 없음")

# =============== 메인 카드 (완료 시 흐리게) ===============
row = get_current_row()
if row is None:
    st.warning("표시할 데이터 없음")
else:
    done = row["done"]
    card_class = "main-card done" if done else "main-card"
    st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)

    if done:
        st.markdown("<div class='ribbon'>DONE</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='slot-bar'>{row['slot']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='green-tag'>{row['green_code']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='big-sku'>{row['sku']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='meta-row'><div class='meta-size'>{row['size']}</div><div class='meta-qty'>{row['qty']}</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='badge'>{row['barcode5']},{row['color']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='title'>{row['style_name']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =============== 버튼 ===============
st.markdown("<div class='row-gap center-row'><div class='center-col'>", unsafe_allow_html=True)
ok = st.button("OK")
st.markdown("</div></div>", unsafe_allow_html=True)

c1,c2 = st.columns(2)
with c1: prev = st.button("Previous")
with c2: nxt = st.button("Next")

c3,c4 = st.columns(2)
with c3: first = st.button("First in Category")
with c4: last = st.button("Last in Category")

st.markdown("<div class='row-gap center-row'><div class='center-col'>", unsafe_allow_html=True)
clear = st.button("Clear Data")
st.markdown("</div></div>", unsafe_allow_html=True)

# =============== 동작 로직 ===============
if st.session_state.df_norm is not None:
    g = st.session_state.groups.get(st.session_state.active_picker, [])
    if g:
        cur = st.session_state.picker_idx_in_group
        cur = max(0,min(cur,len(g)-1))
        idx = g[cur]

        if ok:
            st.session_state.df_norm.at[idx,"done"] = True
            st.session_state.picker_idx_in_group = min(cur+1,len(g)-1)
            st.rerun()
        if prev:
            st.session_state.picker_idx_in_group = max(cur-1,0); st.rerun()
        if nxt:
            st.session_state.picker_idx_in_group = min(cur+1,len(g)-1); st.rerun()
        if first or last:
            cat = row["category"]
            same = [i for i,j in enumerate(g) if st.session_state.df_norm.loc[j,"category"]==cat]
            if same:
                st.session_state.picker_idx_in_group = same[0] if first else same[-1]
                st.rerun()

if clear:
    st.session_state.df_norm = None
    st.session_state.groups = {}
    st.session_state.picker_count = 3
    st.session_state.active_picker = 1
    st.session_state.picker_idx_in_group = 0
    st.experimental_rerun()

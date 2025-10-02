import streamlit as st
import pandas as pd
from datetime import datetime
import math

# ---------------- Page ----------------
st.set_page_config(page_title="Warehouse Picking MVP", layout="wide", initial_sidebar_state="collapsed", page_icon="📦")

# ---------------- State ----------------
def _init():
    ss = st.session_state
    ss.setdefault("picker_count", 3)
    ss.setdefault("active_picker", 1)
    ss.setdefault("picker_idx", 0)
    ss.setdefault("df", None)         # normalized df
    ss.setdefault("groups", {})       # picker -> list[index]
    ss.setdefault("uploader_key", 0)  # reset file uploader
_init()

# ---------------- Data helpers ----------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """엑셀 0~7열 기준으로 단순 매핑. 파일 포맷이 바뀌면 여기만 조정하면 됨."""
    out = pd.DataFrame(index=df.index)
    def col(i, default=""):
        return df.iloc[:, i].astype(str) if df.shape[1] > i else default
    out["slot"]       = col(0)                  # 021
    out["green"]      = col(1)                  # 2LV041 (다음 로케이션)
    out["sku"]        = col(2)                  # 2LW010
    out["size"]       = col(3)                  # L
    out["qty"]        = pd.to_numeric(df.iloc[:,4], errors="coerce").fillna(1).astype(int) if df.shape[1] > 4 else 1
    out["barcode5"]   = col(5, "")              # 46201
    out["color"]      = col(6, "")              # CORAL
    out["style_name"] = col(7, "")              # 제품명
    out["category"]   = out["style_name"].where(out["style_name"].str.strip()!="", other=out["sku"])
    out["done"]       = False
    return out

def build_groups(df: pd.DataFrame, n: int):
    df = df.copy()
    df["picker"] = (pd.RangeIndex(0, len(df)) % n) + 1
    groups = {i: df.index[df["picker"] == i].tolist() for i in range(1, n+1)}
    return df, groups

def current_row():
    ss = st.session_state
    g = ss.groups.get(ss.active_picker, [])
    if not g: return None
    i = max(0, min(ss.picker_idx, len(g)-1))
    return ss.df.loc[g[i]]

def move(step: int):
    ss = st.session_state
    g = ss.groups.get(ss.active_picker, [])
    if not g: return
    i, n = ss.picker_idx, len(g)
    ss.picker_idx = max(0, min(i+step, n-1))

# ---------------- Styles ----------------
st.markdown("""
<style>
/* 상단 */
.now { font-size: 1.35rem; font-weight: 800; }

/* 피커 세그먼트(라운드 스퀘어) */
.segbar { display:flex; gap:14px; flex-wrap:wrap; }
.segbtn {
  width:72px; height:72px; border-radius:18px;
  border:2px solid #d1d5db; background:#f8fafc;
  font-weight:900; font-size:22px; color:#111827;
  box-shadow: 0 2px 4px rgba(0,0,0,.06) inset;
}
.segbtn.active { background:#22c55e; border-color:#16a34a; color:#ffffff; }

/* 메인 카드 */
.card {
  position:relative; background:#ffffff; border:1px solid #e5e7eb; border-radius:20px;
  padding:16px; box-shadow:0 10px 24px rgba(0,0,0,.08);
}
.slotbar { background:#111827; color:#f9fafb; border-radius:12px; text-align:center;
  font-weight:900; font-size:34px; padding:10px 14px; letter-spacing:2px; }
.greentag { position:absolute; right:16px; top:64px; color:#16a34a; font-weight:900; font-size:52px; }
.sku { font-size:110px; line-height:1; font-weight:900; letter-spacing:4px; color:#1f2937; margin:18px 0 8px 0; }
.row-sq { display:flex; align-items:center; justify-content:space-between; padding:6px 6px 2px 6px; }
.size { font-size:48px; font-weight:900; color:#1f2937; }
.qty { font-size:48px; font-weight:900; color:#ef4444; } /* 빨강 1 */

.badge { background:#fde8d9; border:1px solid #f3b58a; color:#111827; font-weight:900;
  font-size:32px; padding:12px 18px; border-radius:16px; text-align:center; margin:10px auto; width:100%; }
.title { margin-top:12px; font-size:32px; line-height:1.2; font-weight:900; text-align:center; color:#1f2937;
  word-break:break-word; overflow-wrap:anywhere; }

/* 버튼 레이아웃 */
.stButton > button { width:100%; height:64px; border-radius:20px; font-weight:900; font-size:24px; border:1px solid #e5e7eb; }
#ok-wrap  button{ background:#facc15; color:#111827; border-color:#eab308; height:86px; font-size:32px; }
#prev-wrap button{ background:#111827; color:#f9fafb; }
#next-wrap button{ background:#2563eb; color:#ffffff; }
#fic-wrap button, #lic-wrap button{ background:#111827; color:#f9fafb; }
#clear-wrap button{ background:#fca5a5; color:#7f1d1d; border:2px solid #ef4444; height:90px; font-size:36px; }

/* 간격 */
.center { display:flex; justify-content:center; }
.w70 { width:72%; }
.mt8 { margin-top:12px; }
</style>
""", unsafe_allow_html=True)

# ---------------- Top bar ----------------
st.markdown(f"<div class='now'>{datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)
c1, c2 = st.columns([3,7], vertical_alignment="bottom")
with c1:
    new_cnt = st.number_input("인원수:", min_value=1, max_value=50, step=1, value=st.session_state.picker_count)
with c2:
    up = st.file_uploader("파일 선택", type=["xlsx","csv"], key=f"uploader_{st.session_state.uploader_key}")
    if up is not None:
        raw = pd.read_csv(up) if up.name.lower().endswith(".csv") else pd.read_excel(up)
        st.session_state.df = normalize_columns(raw)
        st.session_state.df, st.session_state.groups = build_groups(st.session_state.df, st.session_state.picker_count)
        st.session_state.picker_idx = 0

# 인원수 변경 즉시 반영
if int(new_cnt) != st.session_state.picker_count:
    st.session_state.picker_count = int(new_cnt)
    if st.session_state.df is not None:
        st.session_state.df, st.session_state.groups = build_groups(st.session_state.df, st.session_state.picker_count)
    if st.session_state.active_picker > st.session_state.picker_count:
        st.session_state.active_picker = st.session_state.picker_count
    st.session_state.picker_idx = 0
    st.rerun()

# ---------------- Picker segment buttons ----------------
st.markdown("<div class='segbar'>", unsafe_allow_html=True)
for i in range(1, st.session_state.picker_count+1):
    cols = st.columns(1)
    with cols[0]:
        label = f"{i}"
        btn = st.button(label, key=f"seg_{i}", help=f"{i}번 피커", type="secondary")
        # 버튼 색상은 CSS에서 설정하므로 여기선 active 표시만 처리
        if i == st.session_state.active_picker:
            st.markdown(f"""
            <style>
            /* nth-of-type를 이용해서 i번째 버튼 활성색 입힘 */
            .segbar .stButton:nth-of-type({i}) > button {{ background:#22c55e !important; color:#ffffff !important; border-color:#16a34a !important; }}
            </style>
            """, unsafe_allow_html=True)
        if btn:
            st.session_state.active_picker = i
            st.session_state.picker_idx = 0
            st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Progress (선택 피커 기준) ----------------
if st.session_state.df is not None:
    g = st.session_state.groups.get(st.session_state.active_picker, [])
    done = int(st.session_state.df.loc[g, "done"].sum()) if g else 0
    total = len(g)
    st.progress((done/total) if total else 0.0, text=f"진행도 {done}/{total}")
else:
    st.info("피킹 파일을 업로드하면 진행도와 항목이 표시됩니다.")

# ---------------- Main card ----------------
row = current_row()
st.markdown("<div class='card'>", unsafe_allow_html=True)
if row is None:
    st.warning("현재 피커에 할당된 항목이 없습니다.")
else:
    # 상단 슬롯바 + 우상단 그린 태그
    st.markdown(f"<div class='slotbar'>{row['slot'] or ''}</div>", unsafe_allow_html=True)
    if str(row['green']).strip():
        st.markdown(f"<div class='greentag'>{row['green']}</div>", unsafe_allow_html=True)

    # 대형 SKU
    st.markdown(f"<div class='sku'>{row['sku'] or ''}</div>", unsafe_allow_html=True)

    # 좌: 사이즈 / 우: 수량
    st.markdown(
        f"<div class='row-sq'><div class='size'>{row['size'] or ''}</div>"
        f"<div class='qty'>{int(row['qty']) if str(row['qty']).isdigit() else ''}</div></div>",
        unsafe_allow_html=True
    )

    # 베이지 배지 (바코드, 색상 — 중앙 굵게)
    badge_text = ",".join([x for x in [str(row['barcode5']).strip(), str(row['color']).strip()] if x])
    st.markdown(f"<div class='badge'><b>{badge_text}</b></div>", unsafe_allow_html=True)

    # 제품명(중앙, 굵게 2~3줄)
    title = (row["style_name"] or "").strip()
    st.markdown(f"<div class='title'>{title}</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Buttons (4 rows) ----------------
# 1) OK
st.markdown("<div class='center mt8'><div class='w70' id='ok-wrap'>", unsafe_allow_html=True)
ok = st.button("OK", key="ok_btn")
st.markdown("</div></div>", unsafe_allow_html=True)

# 2) Previous | Next
c2l, c2r = st.columns(2)
with c2l:
    st.markdown("<div id='prev-wrap'>", unsafe_allow_html=True)
    prev = st.button("Previous", key="prev_btn")
    st.markdown("</div>", unsafe_allow_html=True)
with c2r:
    st.markdown("<div id='next-wrap'>", unsafe_allow_html=True)
    nxt  = st.button("Next", key="next_btn")
    st.markdown("</div>", unsafe_allow_html=True)

# 3) First/Last in Category
c3l, c3r = st.columns(2)
with c3l:
    st.markdown("<div id='fic-wrap'>", unsafe_allow_html=True)
    fic = st.button("First in Category", key="fic_btn")
    st.markdown("</div>", unsafe_allow_html=True)
with c3r:
    st.markdown("<div id='lic-wrap'>", unsafe_allow_html=True)
    lic = st.button("Last in Category", key="lic_btn")
    st.markdown("</div>", unsafe_allow_html=True)

# 4) Clear Data (넓은 레드 바 형태)
st.markdown("<div class='center mt8'><div class='w70' id='clear-wrap'>", unsafe_allow_html=True)
clear = st.button("Clear Data", key="clear_btn")
st.markdown("</div></div>", unsafe_allow_html=True)

# ---------------- Actions ----------------
if st.session_state.df is not None:
    g = st.session_state.groups.get(st.session_state.active_picker, [])
    if g:
        idx_in = max(0, min(st.session_state.picker_idx, len(g)-1))
        st.session_state.picker_idx = idx_in
        row_idx = g[idx_in]

        if ok:
            st.session_state.df.at[row_idx, "done"] = True
            move(+1)
            st.rerun()
        if prev:
            move(-1); st.rerun()
        if nxt:
            move(+1); st.rerun()
        if fic or lic:
            cat = str(st.session_state.df.loc[row_idx, "category"])
            same = [k for k, rid in enumerate(g) if str(st.session_state.df.loc[rid, "category"]) == cat]
            if same:
                st.session_state.picker_idx = same[0] if fic else same[-1]
                st.rerun()

# Clear Data: 파일 삭제, 인원수 초기화, 대기상태
if clear:
    st.session_state.df = None
    st.session_state.groups = {}
    st.session_state.picker_count = 3
    st.session_state.active_picker = 1
    st.session_state.picker_idx = 0
    st.session_state.uploader_key += 1
    st.rerun()

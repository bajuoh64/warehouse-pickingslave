import streamlit as st
import pandas as pd
from datetime import datetime
import math

# ===================== Page Config =====================
st.set_page_config(
    page_title="Warehouse Picking MVP",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="📦",
)

# ===================== Session Init =====================
def _init_state():
    ss = st.session_state
    ss.setdefault("picker_count", 3)
    ss.setdefault("active_picker", 1)
    ss.setdefault("picker_idx_in_group", 0)
    ss.setdefault("df_norm", None)
    ss.setdefault("groups", {})
    ss.setdefault("file_uploader_key", 0)  # 업로드 리셋용
    ss.setdefault("skip_done", True)
_init_state()

# ===================== Helpers =====================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    간단한 열 위치 기준 정규화(현장 파일 형식에 맞춰 0~7열 사용).
    필요하면 여기만 커스터마이즈하면 됨.
    """
    out = pd.DataFrame(index=df.index)
    def col(i, fallback=""):
        return df.iloc[:, i].astype(str) if df.shape[1] > i else fallback

    out["slot"]       = col(0)
    out["green_code"] = col(1)
    out["sku"]        = col(2)
    out["size"]       = col(3)
    out["qty"]        = pd.to_numeric(df.iloc[:,4], errors="coerce").fillna(1).astype(int) if df.shape[1] > 4 else 1
    out["barcode5"]   = col(5, "")
    out["color"]      = col(6, "")
    out["style_name"] = col(7, "")
    out["category"]   = out["style_name"].where(out["style_name"].str.strip()!="", other=out["sku"])
    out["picker"]     = None
    out["done"]       = False
    return out

def build_groups(df_norm: pd.DataFrame, picker_count: int):
    df = df_norm.copy()
    df["picker"] = (pd.RangeIndex(0, len(df)) % picker_count) + 1  # 라운드로빈
    groups = {i: df.index[df["picker"]==i].tolist() for i in range(1, picker_count+1)}
    return df, groups

def current_series():
    ss = st.session_state
    g = ss.groups.get(ss.active_picker, [])
    if not g:
        return None
    i = max(0, min(ss.picker_idx_in_group, len(g)-1))
    return ss.df_norm.loc[g[i]]

def move_index(step: int):
    ss = st.session_state
    g = ss.groups.get(ss.active_picker, [])
    if not g:
        return
    i, n = ss.picker_idx_in_group, len(g)
    j = max(0, min(i + step, n-1))
    if ss.skip_done:
        # 미완료 항목으로 이동
        direction = 1 if step >= 0 else -1
        k = i
        visited = set()
        while 0 <= k < n and k not in visited:
            visited.add(k)
            k = max(0, min(k + direction, n-1))
            if not ss.df_norm.loc[g[k], "done"]:
                j = k
                break
    ss.picker_idx_in_group = j

# ===================== Light Theme / Mobile-friendly CSS =====================
st.markdown("""
<style>
:root { color-scheme: only light; }
body, .stApp, .block-container { background: #ffffff !important; }

/* 타이포(가독성 업) */
* { -webkit-font-smoothing: antialiased; }
.now-time { font-size: 1.35rem; font-weight: 800; color:#0f172a; }

/* 세그먼트 버튼(사파리 호환: 단순 div + 실제 st.button 숨김) */
.segment { display:inline-flex; gap:12px; }
.segment .seg {
  width:60px; height:60px; border-radius:16px; border:2px solid #d1d5db;
  background:#f8fafc; display:flex; align-items:center; justify-content:center;
  font-size:20px; font-weight:800; color:#1f2937;
}
.segment .seg.active { background:#2563eb; color:#fff; border-color:#1d4ed8; }

/* 메인 카드 */
.card { position: relative; background:#fff; border:2px solid #e5e7eb; border-radius:18px; padding:16px; box-shadow:0 6px 18px rgba(0,0,0,.08); }
.card.done { background:#f3f4f6; color:#9ca3af; border-color:#e5e7eb; }
.ribbon { position:absolute; top:10px; right:-25px; transform:rotate(45deg); background:#9ca3af; color:#fff; padding:4px 40px; font-size:14px; font-weight:800; }

/* 주요 텍스트 색상 */
.slot { background:#111827; color:#f9fafb; border-radius:10px; padding:8px 14px; font-size:32px; font-weight:900; text-align:center; }
.green { position:absolute; right:16px; top:52px; font-weight:900; color:#16a34a; font-size:42px; }
.sku { font-size:92px; line-height:1.0; font-weight:900; color:#111827; letter-spacing:4px; margin:16px 0 6px 0; }
.meta { display:flex; gap:24px; align-items:center; }
.size { font-size:38px; font-weight:900; color:#111827; }
.qty { font-size:38px; font-weight:900; color:#dc2626; }
.badge { display:inline-block; background:#fde8d9; border:1px solid #fca5a5; border-radius:14px; padding:10px 14px; font-size:26px; font-weight:800; color:#111827; margin-top:8px; }
.title { margin-top:10px; font-size:26px; line-height:1.25; font-weight:800; color:#0f172a; }

/* 버튼(사파리 호환: 각 래퍼 id로 직접 스타일링) */
.stButton > button { width:100%; height:58px; border-radius:18px; font-size:22px; font-weight:900; border:1px solid #e5e7eb; }
#ok-wrap button      { background:#facc15; color:#111827; border-color:#eab308; height:68px; }
#prev-wrap button    { background:#111827; color:#f9fafb; }
#next-wrap button    { background:#2563eb; color:#ffffff; }
#fic-wrap button, #lic-wrap button { background:#111827; color:#f9fafb; }
#clear-wrap button   { background:#fca5a5; color:#7f1d1d; border:2px solid #ef4444; height:68px; font-size:24px; }

/* 레이아웃 헬퍼 */
.center-row { display:flex; justify-content:center; }
.center-col { width:72%; }
.row-gap { margin-top:12px; }
.subtle { color:#475569; font-size:0.92rem; }
</style>
""", unsafe_allow_html=True)

# ===================== Top: time / count / file =====================
st.markdown(f"<div class='now-time'>{datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)

# --- 인원수 변경 콜백 (사파리 대응: on_change로 즉시 반영) ---
def _on_count_change():
    ss = st.session_state
    ss.picker_count = int(st.session_state._picker_input_val)
    if ss.df_norm is not None:
        ss.df_norm, ss.groups = build_groups(ss.df_norm, ss.picker_count)
    if ss.active_picker > ss.picker_count:
        ss.active_picker = ss.picker_count
    ss.picker_idx_in_group = 0
    st.rerun()

left, right = st.columns([2,6])
with left:
    st.number_input(
        "인원수:",
        min_value=1, max_value=50, step=1,
        value=st.session_state.picker_count,
        key="_picker_input_val",
        on_change=_on_count_change,
    )
with right:
    uploaded = st.file_uploader(
        "피킹 파일 업로드 (.xlsx/.csv)",
        type=["xlsx","csv"],
        key=f"uploader_{st.session_state.file_uploader_key}"
    )
    if uploaded is not None:
        if uploaded.name.lower().endswith(".csv"):
            df_raw = pd.read_csv(uploaded)
        else:
            df_raw = pd.read_excel(uploaded)
        st.session_state.df_norm = normalize_columns(df_raw)
        st.session_state.df_norm, st.session_state.groups = build_groups(st.session_state.df_norm, st.session_state.picker_count)
        st.session_state.picker_idx_in_group = 0
        st.rerun()

# ===================== Picker Segments =====================
def render_segments():
    count = st.session_state.picker_count
    rows = math.ceil(count/3)
    idx = 1
    for _ in range(rows):
        cols = st.columns(min(3, count-(idx-1)))
        for c in cols:
            with c:
                active = (idx == st.session_state.active_picker)
                st.markdown(f"<div class='segment'><div class='seg {'active' if active else ''}'>{idx}</div></div>", unsafe_allow_html=True)
                if st.button(" ", key=f"seg_{idx}"):  # 표시 없는 버튼(터치 영역)
                    st.session_state.active_picker = idx
                    st.session_state.picker_idx_in_group = 0
                    st.rerun()
            idx += 1
            if idx > count:
                break

render_segments()

# ===================== Progress =====================
if st.session_state.df_norm is not None:
    g = st.session_state.groups.get(st.session_state.active_picker, [])
    done_cnt = int(st.session_state.df_norm.loc[g, "done"].sum()) if g else 0
    total = len(g)
    st.progress((done_cnt/total) if total else 0.0, text=f"진행도 {done_cnt}/{total}")
else:
    st.markdown("<div class='subtle'>진행도: 파일 업로드 전까지는 ? 상태</div>", unsafe_allow_html=True)

# ===================== Main Card =====================
row = current_series()

if row is None:
    st.warning("표시할 데이터가 없습니다. 파일을 업로드하거나 다른 피커를 선택하세요.")
else:
    done = bool(row["done"])
    card_cls = "card done" if done else "card"
    st.markdown(f"<div class='{card_cls}'>", unsafe_allow_html=True)
    if done:
        st.markdown("<div class='ribbon'>DONE</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='slot'>{row['slot']}</div>", unsafe_allow_html=True)
    if str(row['green_code']).strip():
        st.markdown(f"<div class='green'>{row['green_code']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sku'>{row['sku']}</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='meta'><div class='size'>{row['size'] or '?'}</div>"
        f"<div class='qty'>{int(row['qty']) if str(row['qty']).isdigit() else '?'}</div></div>",
        unsafe_allow_html=True
    )
    badge_text = f"{row['barcode5']},{row['color']}".strip(",")
    st.markdown(f"<div class='badge'>{badge_text or '?'}</div>", unsafe_allow_html=True)
    title_text = (row['style_name'] or "?")
    st.markdown(f"<div class='title'>{title_text}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ===================== Buttons (Safari-safe Styling via wrappers) =====================
# 1) OK
st.markdown("<div class='row-gap center-row'><div class='center-col' id='ok-wrap'>", unsafe_allow_html=True)
ok = st.button("OK", key="ok_btn")
st.markdown("</div></div>", unsafe_allow_html=True)
# 2) Prev / Next
c1, c2 = st.columns(2)
with c1:
    st.markdown("<div id='prev-wrap'>", unsafe_allow_html=True)
    prev = st.button("Previous", key="prev_btn")
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown("<div id='next-wrap'>", unsafe_allow_html=True)
    nxt = st.button("Next", key="next_btn")
    st.markdown("</div>", unsafe_allow_html=True)
# 3) First / Last in Category
c3, c4 = st.columns(2)
with c3:
    st.markdown("<div id='fic-wrap'>", unsafe_allow_html=True)
    fic = st.button("First in Category", key="first_cat_btn")
    st.markdown("</div>", unsafe_allow_html=True)
with c4:
    st.markdown("<div id='lic-wrap'>", unsafe_allow_html=True)
    lic = st.button("Last in Category", key="last_cat_btn")
    st.markdown("</div>", unsafe_allow_html=True)
# 4) Clear Data
st.markdown("<div class='row-gap center-row'><div class='center-col' id='clear-wrap'>", unsafe_allow_html=True)
clear = st.button("Clear Data", key="clear_btn")
st.markdown("</div></div>", unsafe_allow_html=True)

# ===================== Actions =====================
if st.session_state.df_norm is not None:
    g = st.session_state.groups.get(st.session_state.active_picker, [])
    if g:
        i = max(0, min(st.session_state.picker_idx_in_group, len(g)-1))
        st.session_state.picker_idx_in_group = i
        row_idx = g[i]

        if ok:
            st.session_state.df_norm.at[row_idx, "done"] = True
            move_index(+1)
            st.rerun()
        if prev:
            move_index(-1); st.rerun()
        if nxt:
            move_index(+1); st.rerun()
        if fic or lic:
            cur_cat = str(st.session_state.df_norm.loc[row_idx, "category"])
            same = [k for k, ridx in enumerate(g) if str(st.session_state.df_norm.loc[ridx, "category"]) == cur_cat]
            if same:
                st.session_state.picker_idx_in_group = same[0] if fic else same[-1]
                st.rerun()

# ===================== Clear Data =====================
if clear:
    st.session_state.df_norm = None
    st.session_state.groups = {}
    st.session_state.picker_count = 3
    st.session_state.active_picker = 1
    st.session_state.picker_idx_in_group = 0
    st.session_state.file_uploader_key += 1  # 업로더 위젯 리셋
    st.rerun()

import streamlit as st
import pandas as pd
from datetime import datetime
import math

# ---------------- Page ----------------
st.set_page_config(page_title="Warehouse Picking MVP", layout="wide", initial_sidebar_state="collapsed")

# ---------------- State ----------------
def _init():
    ss = st.session_state
    ss.setdefault("picker_count", 3)
    ss.setdefault("active_picker", 1)
    ss.setdefault("df", None)            # normalized df
    ss.setdefault("groups", {})          # {picker: [row_index,...]}
    ss.setdefault("pos", {})             # {picker: current_position}
    ss.setdefault("uploader_key", 0)     # reset file uploader
    ss.setdefault("skip_done", True)     # OK 시 완료건 건너뛰기
_init()

# ---------------- Helpers ----------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """엑셀 0~7열을 표준 컬럼으로 매핑 (포맷 바뀌면 여기 조정)."""
    out = pd.DataFrame(index=df.index)
    def col(i, default=""):
        return df.iloc[:, i].astype(str) if df.shape[1] > i else default
    out["slot"]       = col(0)
    out["green"]      = col(1)
    out["sku"]        = col(2)
    out["size"]       = col(3)
    out["qty"]        = pd.to_numeric(df.iloc[:,4], errors="coerce").fillna(1).astype(int) if df.shape[1] > 4 else 1
    out["barcode5"]   = col(5, "")
    out["color"]      = col(6, "")
    out["style_name"] = col(7, "")
    out["category"]   = out["style_name"].where(out["style_name"].str.strip()!="", other=out["sku"])
    out["done"]       = False
    return out

def build_groups(df: pd.DataFrame, n: int):
    df = df.copy()
    df["picker"] = (pd.RangeIndex(0, len(df)) % n) + 1   # 라운드로빈
    groups = {i: df.index[df["picker"]==i].tolist() for i in range(1, n+1)}
    return df, groups

def ensure_pos_for_all_pickers():
    """피커별 커서(pos) 누락 시 0으로 채움."""
    ss = st.session_state
    for p in range(1, ss.picker_count+1):
        if p not in ss.pos:
            ss.pos[p] = 0
        # 현재 피커의 커서가 그룹 범위를 넘지 않도록 보정
        g = ss.groups.get(p, [])
        if g:
            ss.pos[p] = max(0, min(ss.pos[p], len(g)-1))
        else:
            ss.pos[p] = 0

def current_row():
    ss = st.session_state
    g = ss.groups.get(ss.active_picker, [])
    if not g: return None, None, 0
    i = ss.pos.get(ss.active_picker, 0)
    i = max(0, min(i, len(g)-1))
    return ss.df.loc[g[i]], g, i

def move(step: int, prefer_unfinished=True):
    ss = st.session_state
    row, g, i = current_row()
    if not g: return
    n = len(g)
    j = max(0, min(i + step, n-1))
    if prefer_unfinished:
        direction = 1 if step >= 0 else -1
        k = i
        visited = set()
        # 현재 위치에서 한 칸씩 이동하며 미완료 찾기
        while 0 <= k < n and k not in visited:
            visited.add(k)
            k = max(0, min(k + direction, n-1))
            if not ss.df.loc[g[k], "done"]:
                j = k
                break
    ss.pos[ss.active_picker] = j

# ---------------- Styles (가독성 고정 색상) ----------------
st.markdown("""
<style>
.now { font-size: 22px; font-weight: 800; color:#111111; }

.segbar { display:flex; gap:12px; flex-wrap:wrap; }
.stButton > button.btn-seg {
  width:68px; height:68px; border-radius:16px; border:2px solid #d1d5db;
  background:#f7fafc; color:#111111; font-weight:900; font-size:20px;
}
.stButton > button.btn-seg-active {
  width:68px; height:68px; border-radius:16px; border:2px solid #16a34a;
  background:#22c55e; color:#ffffff; font-weight:900; font-size:20px;
}

.card { position:relative; background:#ffffff; border:1px solid #e5e7eb;
  border-radius:18px; padding:16px; box-shadow:0 8px 20px rgba(0,0,0,.08); }
.slotbar { background:#111111; color:#ffffff; border-radius:10px; text-align:center; font-weight:900; font-size:34px; padding:8px 14px; }
.greentag { position:absolute; right:16px; top:64px; color:#138a21; font-weight:900; font-size:50px; }
.sku { font-size:108px; line-height:1; font-weight:900; letter-spacing:4px; color:#111111; margin:16px 0 10px; }
.row-sq { display:flex; align-items:center; justify-content:space-between; padding:4px 2px; }
.size { font-size:46px; font-weight:900; color:#111111; }
.qty { font-size:46px; font-weight:900; color:#e11d48; } /* 강한 빨강 */

.badge { background:#fde8d9; border:1px solid #f3b58a; color:#111111; font-weight:900;
  font-size:30px; padding:12px 16px; border-radius:14px; text-align:center; margin:10px 0; }
.title { margin-top:8px; font-size:30px; line-height:1.18; font-weight:900; text-align:center; color:#111111;
  word-break:break-word; overflow-wrap:anywhere; }

.stButton > button { width:100%; height:64px; border-radius:18px; font-weight:900; font-size:24px; border:1px solid #e5e7eb; }
#ok-wrap button  { background:#facc15; color:#111111; border-color:#eab308; height:84px; font-size:32px; }
#prev-wrap button{ background:#111111; color:#ffffff; }
#next-wrap button{ background:#2563eb; color:#ffffff; }
#fic-wrap button, #lic-wrap button { background:#111111; color:#ffffff; }
#clear-wrap button{ background:#fca5a5; color:#7f1d1d; border:2px solid #ef4444; height:88px; font-size:34px; }

.center { display:flex; justify-content:center; }
.w70 { width:72%; }
.mt12 { margin-top:12px; }
</style>
""", unsafe_allow_html=True)

# ---------------- Top ----------------
st.markdown(f"<div class='now'>{datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)
c1, c2 = st.columns([3,7], vertical_alignment="bottom")
with c1:
    new_cnt = st.number_input("인원수:", min_value=1, max_value=50, value=st.session_state.picker_count, step=1)
with c2:
    up = st.file_uploader("피킹 파일 업로드 (.xlsx/.csv)", type=["xlsx","csv"], key=f"uploader_{st.session_state.uploader_key}")
    if up is not None:
        raw = pd.read_csv(up) if up.name.lower().endswith(".csv") else pd.read_excel(up)
        st.session_state.df = normalize_columns(raw)
        st.session_state.df, st.session_state.groups = build_groups(st.session_state.df, st.session_state.picker_count)
        st.session_state.pos = {}  # 새 파일이므로 커서 초기화
        ensure_pos_for_all_pickers()
        st.rerun()

# 인원수 변경 → 그룹/커서 재설정
if int(new_cnt) != st.session_state.picker_count:
    st.session_state.picker_count = int(new_cnt)
    if st.session_state.df is not None:
        st.session_state.df, st.session_state.groups = build_groups(st.session_state.df, st.session_state.picker_count)
    ensure_pos_for_all_pickers()
    if st.session_state.active_picker > st.session_state.picker_count:
        st.session_state.active_picker = st.session_state.picker_count
    st.rerun()

# ---------------- Picker segments ----------------
st.markdown("<div class='segbar'>", unsafe_allow_html=True)
for i in range(1, st.session_state.picker_count+1):
    cls = "btn-seg-active" if i == st.session_state.active_picker else "btn-seg"
    if st.button(str(i), key=f"seg_{i}", type="secondary", help=f"{i}번 피커",
                 use_container_width=False):
        st.session_state.active_picker = i
        ensure_pos_for_all_pickers()
        st.rerun()
    # 마지막 렌더된 버튼을 강제로 클래스로 스타일링
    st.markdown(f"<style>.stButton[data-testid='baseButton-secondary']:last-child > button {{}}</style>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Progress ----------------
if st.session_state.df is not None:
    g = st.session_state.groups.get(st.session_state.active_picker, [])
    done_cnt = int(st.session_state.df.loc[g, "done"].sum()) if g else 0
    total = len(g)
    st.progress((done_cnt/total) if total else 0.0, text=f"진행도 {done_cnt}/{total}")
else:
    st.info("엑셀/CSV를 업로드하면 항목이 표시됩니다.")

# ---------------- Main card ----------------
row, g, pos = current_row()
st.markdown("<div class='card'>", unsafe_allow_html=True)
if row is None:
    st.warning("현재 피커에 할당된 항목이 없습니다.")
else:
    st.markdown(f"<div class='slotbar'>{row['slot'] or ''}</div>", unsafe_allow_html=True)
    if str(row["green"]).strip():
        st.markdown(f"<div class='Greentag greentag'>{row['green']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sku'>{row['sku'] or ''}</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='row-sq'><div class='size'>{row['size'] or ''}</div>"
        f"<div class='qty'>{int(row['qty']) if str(row['qty']).isdigit() else ''}</div></div>",
        unsafe_allow_html=True
    )
    badge_text = ",".join([x for x in [str(row['barcode5']).strip(), str(row['color']).strip()] if x])
    st.markdown(f"<div class='badge'><b>{badge_text}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='title'>{(row['style_name'] or '').strip()}</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Buttons (4 rows) ----------------
# 1) OK
st.markdown("<div class='center mt12'><div class='w70' id='ok-wrap'>", unsafe_allow_html=True)
ok = st.button("OK", key="ok_btn")
st.markdown("</div></div>", unsafe_allow_html=True)

# 2) Prev/Next
c2l, c2r = st.columns(2)
with c2l:
    st.markdown("<div id='prev-wrap'>", unsafe_allow_html=True)
    prev = st.button("Previous", key="prev_btn")
    st.markdown("</div>", unsafe_allow_html=True)
with c2r:
    st.markdown("<div id='next-wrap'>", unsafe_allow_html=True)
    nxt = st.button("Next", key="next_btn")
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

# 4) Clear Data
st.markdown("<div class='center mt12'><div class='w70' id='clear-wrap'>", unsafe_allow_html=True)
clear = st.button("Clear Data", key="clear_btn")
st.markdown("</div></div>", unsafe_allow_html=True)

# ---------------- Actions ----------------
if st.session_state.df is not None and g:
    cur_row_index = g[pos]

    if ok:
        # 완료 표시 후 다음(미완료 우선)으로 이동
        st.session_state.df.at[cur_row_index, "done"] = True
        move(+1, prefer_unfinished=st.session_state.skip_done)
        st.rerun()

    if prev:
        move(-1, prefer_unfinished=False); st.rerun()

    if nxt:
        move(+1, prefer_unfinished=False); st.rerun()

    if fic or lic:
        cat = str(st.session_state.df.loc[cur_row_index, "category"])
        same = [k for k, rid in enumerate(g) if str(st.session_state.df.loc[rid, "category"]) == cat]
        if same:
            st.session_state.pos[st.session_state.active_picker] = same[0] if fic else same[-1]
            st.rerun()

# Clear Data: 파일 삭제/인원수 초기화/대기
if clear:
    st.session_state.df = None
    st.session_state.groups = {}
    st.session_state.pos = {}
    st.session_state.picker_count = 3
    st.session_state.active_picker = 1
    st.session_state.uploader_key += 1
    st.rerun()

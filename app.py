import streamlit as st
import pandas as pd
from datetime import datetime
import math, io, textwrap

# =========================
# Page
# =========================
st.set_page_config(
    page_title="Warehouse Picking MVP",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================
# Session Init
# =========================
def _init_state():
    ss = st.session_state
    ss.setdefault("picker_count", 3)
    ss.setdefault("active_picker", 1)
    ss.setdefault("df", None)                      # 업로드한 원본 DF
    ss.setdefault("file_sig", None)                # 파일 변경 감지용
    ss.setdefault("map", {})                       # 컬럼 매핑
    ss.setdefault("indices_by_picker", {})         # {picker: [row_index, ...]}
    ss.setdefault("cursor_by_picker", {})          # {picker: 0-based}
    ss.setdefault("ok_set", set())                 # {(row_index)}
    ss.setdefault("category_field", None)          # 카테고리 기준 필드명

_init_state()

# =========================
# CSS (색/배치 UI 샘플과 매칭)
# =========================
st.markdown("""
<style>
.block-container { padding-top: 0.6rem; }
.now-time { font-size: 1.35rem; font-weight: 800; }
.segment { display:inline-flex; gap:12px; align-items:center; }
.segment .seg {
  width:64px; height:64px; border-radius:16px; border:1px solid #e5e7eb;
  background:#f8fafc; display:flex; align-items:center; justify-content:center;
  font-size:20px; font-weight:800; color:#111827; box-shadow: 0 2px 4px rgba(0,0,0,.06) inset; margin-bottom:6px;
}
.segment .seg.active {
  background:#22c55e; color:#fff; border-color:#16a34a; box-shadow: 0 0 0 3px #bbf7d0 inset;
}
.main-card { position:relative; background:#fff; border:1px solid #e5e7eb; border-radius:18px; padding:16px; margin-top:8px; box-shadow: 0 8px 22px rgba(0,0,0,.06);}
.slot-bar { background:#111827; color:#f9fafb; border-radius:10px; padding:8px 14px; font-size:32px; font-weight:900; text-align:center; letter-spacing:2px;}
.green-tag { position:absolute; right:16px; top:52px; font-weight:900; color:#16a34a; font-size:48px;}
.big-sku { font-size:96px; line-height:1.0; font-weight:900; color:#1f2937; letter-spacing:4px; margin:16px 0 8px 0;}
.meta-row { display:flex; align-items:center; gap:24px; }
.meta-size { font-size:40px; font-weight:900; color:#111827; }
.meta-qty  { font-size:40px; font-weight:900; color:#ef4444; }
.badge { background:#fde8d9; border:1px solid #f3b58a; border-radius:14px; padding:12px 16px; font-size:28px; font-weight:900; color:#111827; display:inline-block; margin-top:8px;}
.title { margin-top:10px; font-size:28px; line-height:1.25; font-weight:800; letter-spacing:.5px; color:#1f2937; }
.stButton > button { width:100%; height:60px; border-radius:18px; font-size:22px; font-weight:900; border:1px solid #e5e7eb; background:#1f2937; color:#f9fafb; box-shadow:0 4px 10px rgba(0,0,0,.05); }
.center-row { display:flex; justify-content:center; }
.center-col { width:72%; }
.row-gap { margin-top:12px; }
.hide-btn button { text-indent:-9999px; height:0; padding:0; margin:0; border:none; box-shadow:none; }
.small { font-size:.9rem; color:#6b7280; }
</style>
""", unsafe_allow_html=True)

# =========================
# Utils
# =========================
COMMON_MAP = {
    "slot":    ["슬롯","slot","표시","표지","번호","seq","순번","slot_no","slot id"],
    "loc":     ["location","로케이션","loc","bin","shelf","rack","자리","위치"],
    "sku":     ["sku","스타일","style","품번","상품코드","제품코드","item","code"],
    "size":    ["size","사이즈"],
    "qty":     ["qty","quantity","수량","수"],
    "barcode": ["barcode","바코드","ean","upc"],
    "color":   ["color","컬러","색상"],
    "title":   ["title","상품명","스타일명","품명","name","product","설명","description"],
}

def _guess_column(df, candidates):
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        for c_low, orig in cols_lower.items():
            if cand in c_low:
                return orig
    return None

def guess_map(df: pd.DataFrame):
    m = {}
    for k, cands in COMMON_MAP.items():
        col = _guess_column(df, cands)
        if col: m[k] = col
    # 합성 배지용: 없으면 None으로 남겨둠
    return m

def assign_round_robin(n_items: int, picker_count: int):
    d = {i+1: [] for i in range(picker_count)}
    for i in range(n_items):
        d[(i % picker_count)+1].append(i)
    return d

def ensure_assignment():
    ss = st.session_state
    if ss.df is None: 
        ss.indices_by_picker = {}
        return
    n = len(ss.df)
    ss.indices_by_picker = assign_round_robin(n, ss.picker_count)
    # 커서 초기화/보정
    for p, idxs in ss.indices_by_picker.items():
        ss.cursor_by_picker.setdefault(p, 0)
        if not idxs: 
            ss.cursor_by_picker[p] = 0
        else:
            ss.cursor_by_picker[p] = min(ss.cursor_by_picker[p], max(0, len(idxs)-1))
    if ss.active_picker > ss.picker_count:
        ss.active_picker = ss.picker_count

def set_file(df: pd.DataFrame, file_sig: str):
    ss = st.session_state
    ss.df = df.reset_index(drop=True)
    ss.file_sig = file_sig
    ss.map = guess_map(ss.df)
    ss.ok_set = set()
    ss.cursor_by_picker = {}
    ensure_assignment()

def current_row_index():
    ss = st.session_state
    idxs = ss.indices_by_picker.get(ss.active_picker, [])
    if not idxs: return None
    return idxs[ss.cursor_by_picker.get(ss.active_picker, 0)]

def goto_prev():
    ss = st.session_state
    idxs = ss.indices_by_picker.get(ss.active_picker, [])
    if not idxs: return
    cur = ss.cursor_by_picker.get(ss.active_picker, 0)
    ss.cursor_by_picker[ss.active_picker] = (cur - 1) % len(idxs)
    st.rerun()

def goto_next():
    ss = st.session_state
    idxs = ss.indices_by_picker.get(ss.active_picker, [])
    if not idxs: return
    cur = ss.cursor_by_picker.get(ss.active_picker, 0)
    ss.cursor_by_picker[ss.active_picker] = (cur + 1) % len(idxs)
    st.rerun()

def goto_first_in_category():
    ss = st.session_state
    idxs = ss.indices_by_picker.get(ss.active_picker, [])
    if not idxs or not ss.category_field: return
    df = ss.df; cur_i = current_row_index()
    if cur_i is None: return
    key = df.loc[cur_i, ss.category_field]
    for k, ridx in enumerate(idxs):
        if df.loc[ridx, ss.category_field] == key:
            ss.cursor_by_picker[ss.active_picker] = k
            break
    st.rerun()

def goto_last_in_category():
    ss = st.session_state
    idxs = ss.indices_by_picker.get(ss.active_picker, [])
    if not idxs or not ss.category_field: return
    df = ss.df; cur_i = current_row_index()
    if cur_i is None: return
    key = df.loc[cur_i, ss.category_field]
    last_k = None
    for k, ridx in enumerate(idxs):
        if df.loc[ridx, ss.category_field] == key:
            last_k = k
    if last_k is not None:
        ss.cursor_by_picker[ss.active_picker] = last_k
    st.rerun()

def mark_ok():
    i = current_row_index()
    if i is not None:
        st.session_state.ok_set.add(i)
        goto_next()

def clear_data():
    ss = st.session_state
    ss.ok_set = set()
    for p in ss.cursor_by_picker: ss.cursor_by_picker[p] = 0
    st.rerun()

def wrap_title(text, width=26, max_lines=3):
    if not isinstance(text,str): text = str(text)
    lines = textwrap.wrap(text, width=width)
    return lines[:max_lines]

# =========================
# Top: 시간 / 인원수 / 파일 / 피커
# =========================
st.markdown(f"<div class='now-time'>{datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)

top1, top2 = st.columns([2,6])
with top1:
    # 인원수 변경 -> 즉시 재배정 + rerun
    new_count = st.number_input("인원수:", 1, 50, value=st.session_state.picker_count, step=1)
    if new_count != st.session_state.picker_count:
        st.session_state.picker_count = int(new_count)
        ensure_assignment()
        st.rerun()

with top2:
    upl = st.file_uploader("파일 선택", type=["xlsx","csv"])
    if upl is not None:
        sig = f"{upl.name}-{upl.size}"
        if sig != st.session_state.file_sig:
            # 파일 로드
            if upl.name.lower().endswith(".csv"):
                df = pd.read_csv(upl)
            else:
                # openpyxl 필요
                data = upl.read()
                df = pd.read_excel(io.BytesIO(data))
            set_file(df, sig)
            st.success(f"파일 로드됨: {upl.name} (행 {len(df)})")

# 피커 번호(세그먼트)
rows = math.ceil(st.session_state.picker_count / 3)
idx = 1
for _ in range(rows):
    cols = st.columns(min(3, st.session_state.picker_count - (idx-1)))
    for c in cols:
        with c:
            st.markdown(
                f"<div class='segment'><div class='seg {'active' if idx==st.session_state.active_picker else ''}'>{idx}</div></div>",
                unsafe_allow_html=True
            )
            with st.container():
                st.markdown("<div class='hide-btn'>", unsafe_allow_html=True)
                if st.button(f"select_{idx}", key=f"seg_btn_{idx}"):
                    st.session_state.active_picker = idx
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        idx += 1
        if idx > st.session_state.picker_count:
            break

# 매핑/카테고리 선택 (자동 추정 + 수정 가능)
if st.session_state.df is not None:
    df = st.session_state.df
    auto = st.session_state.map.copy()

    st.markdown("<div class='small'>필요하면 컬럼 매핑과 카테고리 기준을 조정하세요.</div>", unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        auto["slot"] = st.selectbox("슬롯/표시", [None]+list(df.columns), index=[None]+list(df.columns).index(auto.get("slot"))+1 if auto.get("slot") in df.columns else 0)
        auto["loc"]  = st.selectbox("로케이션", [None]+list(df.columns), index=[None]+list(df.columns).index(auto.get("loc"))+1 if auto.get("loc") in df.columns else 0)
    with c2:
        auto["sku"]  = st.selectbox("SKU/스타일코드", [None]+list(df.columns), index=[None]+list(df.columns).index(auto.get("sku"))+1 if auto.get("sku") in df.columns else 0)
        auto["size"] = st.selectbox("사이즈", [None]+list(df.columns), index=[None]+list(df.columns).index(auto.get("size"))+1 if auto.get("size") in df.columns else 0)
    with c3:
        auto["qty"]  = st.selectbox("수량", [None]+list(df.columns), index=[None]+list(df.columns).index(auto.get("qty"))+1 if auto.get("qty") in df.columns else 0)
        auto["barcode"] = st.selectbox("바코드", [None]+list(df.columns), index=[None]+list(df.columns).index(auto.get("barcode"))+1 if auto.get("barcode") in df.columns else 0)
    with c4:
        auto["color"] = st.selectbox("색상", [None]+list(df.columns), index=[None]+list(df.columns).index(auto.get("color"))+1 if auto.get("color") in df.columns else 0)
        auto["title"] = st.selectbox("상품명/설명", [None]+list(df.columns), index=[None]+list(df.columns).index(auto.get("title"))+1 if auto.get("title") in df.columns else 0)

    st.session_state.map = auto
    # 카테고리 기준 (기본: SKU 있으면 SKU, 없으면 로케이션)
    default_cat = auto.get("sku") or auto.get("loc")
    st.session_state.category_field = st.selectbox("카테고리 기준", [None]+list(df.columns), index=[None]+list(df.columns).index(default_cat)+1 if default_cat in df.columns else 0)

# =========================
# Main Card (현재 아이템 표시)
# =========================
ensure_assignment()
cur_idx = current_row_index()

def get_val(row, key, default=""):
    col = st.session_state.map.get(key)
    if col and col in row.index:
        return row[col]
    return default

if st.session_state.df is None or cur_idx is None:
    st.info("엑셀/CSV를 업로드하면 이 영역에 피킹 대상이 표시됩니다.")
else:
    row = st.session_state.df.loc[cur_idx]
    slot  = str(get_val(row,"slot",""))
    loc   = str(get_val(row,"loc",""))
    sku   = str(get_val(row,"sku",""))
    size  = str(get_val(row,"size",""))
    qty   = int(get_val(row,"qty",1)) if pd.notna(get_val(row,"qty",1)) else 1
    barcode = str(get_val(row,"barcode",""))
    color = str(get_val(row,"color",""))
    title_txt = str(get_val(row,"title",""))

    badge = ", ".join([v for v in [barcode, color] if v and v != "nan"])
    lines = wrap_title(title_txt, width=26, max_lines=3)
    title_lines = "<br/>".join(lines) if lines else ""

    # 카드
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='slot-bar'>{slot or '&nbsp;'}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='green-tag'>{loc or '&nbsp;'}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='big-sku'>{sku or '&nbsp;'}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='meta-row'><div class='meta-size'>{size or ''}</div><div class='meta-qty'>{qty}</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='badge'>{badge or '&nbsp;'}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='title'>{title_lines}</div>", unsafe_allow_html=True)

    # 진행률
    idxs = st.session_state.indices_by_picker.get(st.session_state.active_picker, [])
    cur_pos = (st.session_state.cursor_by_picker.get(st.session_state.active_picker,0) + 1) if idxs else 0
    st.caption(f"피커 {st.session_state.active_picker} 진행률: {cur_pos}/{len(idxs)} (완료 {len([i for i in idxs if i in st.session_state.ok_set])})")

    # 버튼 4줄
    st.markdown("<div class='row-gap center-row'><div class='center-col'>", unsafe_allow_html=True)
    ok_clicked = st.button("OK", key="ok_btn")
    st.markdown("</div></div>", unsafe_allow_html=True)

    prev_col, next_col = st.columns(2)
    with prev_col:
        prev_clicked = st.button("Previous", key="prev_btn")
    with next_col:
        next_clicked = st.button("Next", key="next_btn")

    first_col, last_col = st.columns(2)
    with first_col:
        first_clicked = st.button("First in Category", key="first_cat_btn")
    with last_col:
        last_clicked = st.button("Last in Category", key="last_cat_btn")

    st.markdown("<div class='row-gap center-row'><div class='center-col'>", unsafe_allow_html=True)
    clear_clicked = st.button("Clear Data", key="clear_btn")
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # /main-card

    # 동작
    if ok_clicked:   mark_ok()
    if prev_clicked: goto_prev()
    if next_clicked: goto_next()
    if first_clicked: goto_first_in_category()
    if last_clicked:  goto_last_in_category()
    if clear_clicked: clear_data()

# =========================
# 버튼 색상 패치(JS)
# =========================
st.markdown("""
<script>
const patch = () => {
  const btns = Array.from(window.parent.document.querySelectorAll('button'));
  const byText = (t) => btns.find(b => (b.innerText || '').trim() === t);

  const ok = byText('OK');
  if (ok) { ok.style.background='#facc15'; ok.style.color='#111827'; ok.style.border='1px solid #eab308'; ok.style.height='72px'; ok.style.fontSize='26px'; ok.style.borderRadius='22px'; }
  const prev = byText('Previous'); if (prev){ prev.style.background='#111827'; prev.style.color='#f9fafb'; }
  const next = byText('Next');     if (next){ next.style.background='#2563eb'; next.style.color='#ffffff'; }
  const fic = byText('First in Category'); if (fic){ fic.style.background='#111827'; fic.style.color='#f9fafb'; }
  const lic = byText('Last in Category');  if (lic){ lic.style.background='#111827'; lic.style.color='#f9fafb'; }
  const clr = byText('Clear Data'); if (clr){ clr.style.background='#fca5a5'; clr.style.border='2px solid #ef4444'; clr.style.color='#7f1d1d'; clr.style.height='72px'; clr.style.fontSize='28px'; clr.style.borderRadius='22px'; }
};
setTimeout(patch, 80); setTimeout(patch, 250); setTimeout(patch, 600);
</script>
""", unsafe_allow_html=True)

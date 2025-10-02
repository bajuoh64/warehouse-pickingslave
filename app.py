import streamlit as st
import pandas as pd
from datetime import datetime
import re
import math

# ---------------- Page ----------------
st.set_page_config(page_title="Warehouse Picking MVP", layout="wide", initial_sidebar_state="collapsed")

# ---------------- Session ----------------
def init():
    ss = st.session_state
    ss.setdefault("picker_count", 3)
    ss.setdefault("active_picker", 1)
    ss.setdefault("idx", {})                 # {picker: cursor}
    ss.setdefault("df", None)                # normalized df
    ss.setdefault("groups", {})              # {picker: [rowidx,...]}
    ss.setdefault("uploader_key", 0)         # reset uploader
init()

# ---------------- CSS (고대비/가독성) ----------------
st.markdown("""
<style>
.now { font-size:22px; font-weight:800; color:#111; }

/* 피커 버튼 */
.segbar { display:flex; gap:12px; flex-wrap:wrap; }
.stButton > button.seg { width:64px; height:64px; border-radius:16px; border:2px solid #d1d5db;
  background:#f8fafc; color:#111; font-weight:900; font-size:20px; }
.stButton > button.seg.active { background:#16a34a; border-color:#15803d; color:#fff; }

/* 카드 */
.card { position:relative; background:#fff; border:1px solid #e5e7eb; border-radius:18px; padding:16px; box-shadow:0 8px 20px rgba(0,0,0,.08); }
.slotbar { background:#111; color:#fff; border-radius:10px; text-align:center; font-weight:900; font-size:34px; padding:8px 14px; }
.greentag { position:absolute; right:16px; top:64px; color:#15803d; font-weight:900; font-size:50px; }
.sku { font-size:108px; line-height:1; font-weight:900; letter-spacing:4px; color:#111; margin:16px 0 10px; }
.row-sq { display:flex; align-items:center; justify-content:space-between; padding:6px 2px; }
.size { font-size:46px; font-weight:900; color:#111; }
.qty  { font-size:46px; font-weight:900; color:#e11d48; }  /* 강한 빨강 */
.badge { background:#fde8d9; border:1px solid #f3b58a; color:#111; font-weight:900; font-size:30px;
  padding:12px 16px; border-radius:14px; text-align:center; margin:10px 0; }
.title { margin-top:8px; font-size:30px; line-height:1.18; font-weight:900; text-align:center; color:#111;
  word-break:break-word; overflow-wrap:anywhere; }

/* 버튼들 */
.stButton > button { width:100%; height:64px; border-radius:18px; font-weight:900; font-size:24px; border:1px solid #e5e7eb; }
#ok-wrap button  { background:#facc15; color:#111; border-color:#eab308; height:84px; font-size:32px; }
#prev-wrap button{ background:#111; color:#fff; }
#next-wrap button{ background:#2563eb; color:#fff; }
#fic-wrap button, #lic-wrap button { background:#111; color:#fff; }
#clear-wrap button{ background:#fca5a5; color:#7f1d1d; border:2px solid #ef4444; height:88px; font-size:34px; }

.center { display:flex; justify-content:center; }
.w70 { width:72%; }
.mt12 { margin-top:12px; }
.subtle { color:#475569; font-size:.92rem; }
</style>
""", unsafe_allow_html=True)

# ---------------- Column mapping (헤더 자동매핑) ----------------
CAND = {
    "slot":     ["slot","슬롯","순번","번호","오더","order","no"],
    "nextloc":  ["nextlocation","다음로케이션","다음 로케이션","다음","next"],
    "loc":      ["location","현재로케이션","현재 로케이션","로케이션","sku","상품코드","코드","품번","품목코드"],
    "size":     ["size","사이즈"],
    "qty":      ["qty","quantity","수량","주문수량","수량합"],
    "barcode":  ["barcode","바코드","바코드5","바코드(5)","ean"],
    "color":    ["color","색상","색상명","컬러"],
    "style":    ["style","스타일","스타일명","상품명","품명","name","title","productname"],
    "picker":   ["picker","피커","담당","담당자"],
    "category": ["category","카테고리","분류","군","라인"]
}
def _norm(s): return re.sub(r'[\s_]+','',str(s).lower())
def _pick(df, keys):
    cols = {_norm(c): c for c in df.columns}
    # exact
    for w in keys:
        k = _norm(w)
        if k in cols: return cols[k]
    # contains
    for w in keys:
        k = _norm(w)
        for nk, orig in cols.items():
            if k in nk: return orig
    return None

def normalize_by_header(df: pd.DataFrame) -> pd.DataFrame:
    g = {k:_pick(df, v) for k,v in CAND.items()}
    out = pd.DataFrame(index=df.index)
    # 필드 채우기
    out["slot"]       = (df[g["slot"]].astype(str) if g["slot"] else pd.RangeIndex(1,len(df)+1).astype(str))
    out["green"]      = (df[g["nextloc"]].astype(str) if g["nextloc"] else "")
    out["sku"]        = (df[g["loc"]].astype(str) if g["loc"] else (df[g["barcode"]].astype(str) if g["barcode"] else ""))
    out["size"]       = (df[g["size"]].astype(str) if g["size"] else "")
    out["qty"]        = (pd.to_numeric(df[g["qty"]], errors="coerce").fillna(1).astype(int) if g["qty"] else 1)
    if g["barcode"]:
        bc = df[g["barcode"]].astype(str).str.replace(r"\D","",regex=True)
        out["barcode5"] = bc.str[-5:].fillna("")
    else:
        bc = out["sku"].str.replace(r"\D","",regex=True)
        out["barcode5"] = bc.str[-5:].fillna("")
    out["color"]      = (df[g["color"]].astype(str) if g["color"] else "")
    out["style_name"] = (df[g["style"]].astype(str) if g["style"] else out["sku"])
    out["category"]   = (df[g["category"]].astype(str) if g["category"] else out["style_name"].where(out["style_name"].str.strip()!="", other=out["sku"]))
    # picker(있으면 사용)
    if g["picker"]:
        p = pd.to_numeric(df[g["picker"]], errors="coerce").astype('Int64')
        out["picker"] = p
    else:
        out["picker"] = pd.NA
    out["done"] = False
    return out

def build_groups(df: pd.DataFrame, n: int):
    df = df.copy()
    if df["picker"].isna().all():
        df["picker"] = (pd.RangeIndex(0,len(df)) % n) + 1
    else:
        df["picker"] = df["picker"].fillna(1).astype(int).clip(lower=1, upper=n)
    groups = {i: df.index[df["picker"]==i].tolist() for i in range(1, n+1)}
    return df, groups

def ensure_idx_all():
    ss = st.session_state
    for p in range(1, ss.picker_count+1):
        if p not in ss.idx: ss.idx[p] = 0
        g = ss.groups.get(p, [])
        ss.idx[p] = 0 if not g else max(0, min(ss.idx[p], len(g)-1))

def current_tuple():
    ss = st.session_state
    g = ss.groups.get(ss.active_picker, [])
    if not g: return None, [], 0
    i = ss.idx.get(ss.active_picker, 0)
    i = max(0, min(i, len(g)-1))
    return ss.df.loc[g[i]], g, i

def move(step: int, prefer_unfinished=True):
    ss = st.session_state
    row, g, i = current_tuple()
    if not g: return
    n = len(g); j = max(0, min(i+step, n-1))
    if prefer_unfinished:
        dir_ = 1 if step>=0 else -1
        k = i
        for _ in range(n-1):
            k = max(0, min(k+dir_, n-1))
            if not ss.df.loc[g[k], "done"]:
                j = k; break
    ss.idx[ss.active_picker] = j

# ---------------- Top ----------------
st.markdown(f"<div class='now'>{datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)

# 인원수 on_change 콜백
def on_count_change():
    ss = st.session_state
    ss.picker_count = int(st.session_state._picker_input)
    if ss.df is not None:
        ss.df, ss.groups = build_groups(ss.df, ss.picker_count)
    ensure_idx_all()
    if ss.active_picker > ss.picker_count:
        ss.active_picker = ss.picker_count
    st.rerun()

c1, c2 = st.columns([3,7], vertical_alignment="bottom")
with c1:
    st.number_input("인원수:", min_value=1, max_value=50, step=1,
                    value=st.session_state.picker_count, key="_picker_input",
                    on_change=on_count_change)
with c2:
    up = st.file_uploader("피킹 파일 업로드 (.xlsx/.csv)", type=["xlsx","csv"],
                          key=f"uploader_{st.session_state.uploader_key}")
    if up is not None:
        raw = pd.read_csv(up) if up.name.lower().endswith(".csv") else pd.read_excel(up)
        st.session_state.df = normalize_by_header(raw)
        st.session_state.df, st.session_state.groups = build_groups(st.session_state.df, st.session_state.picker_count)
        st.session_state.idx = {}
        ensure_idx_all()
        st.rerun()

# ---------------- Picker Segments ----------------
st.markdown("<div class='segbar'>", unsafe_allow_html=True)
for i in range(1, st.session_state.picker_count+1):
    # active 스타일은 class 가 붙지 않으므로, 현재 버튼을 두 가지 스타일로 구분
    label = str(i)
    if st.button(label, key=f"seg_{i}", help=f"{i}번 피커", type="secondary"):
        st.session_state.active_picker = i
        ensure_idx_all()
        st.rerun()
    # 활성 버튼 색 입히기(nth-of-type로 현재 index 지정)
st.markdown(f"""
<style>
.segbar .stButton:nth-of-type({st.session_state.active_picker}) > button {{
  background:#16a34a !important; color:#fff !important; border-color:#15803d !important;
}}
.segbar .stButton > button {{ width:64px; height:64px; border-radius:16px; border:2px solid #d1d5db;
  background:#f8fafc; color:#111; font-weight:900; font-size:20px; }}
</style>
""", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Progress ----------------
if st.session_state.df is not None:
    g = st.session_state.groups.get(st.session_state.active_picker, [])
    done_cnt = int(st.session_state.df.loc[g,"done"].sum()) if g else 0
    total = len(g)
    st.progress((done_cnt/total) if total else 0.0, text=f"진행도 {done_cnt}/{total}")
else:
    st.info("엑셀/CSV 업로드 후 시작하세요.")

# ---------------- Main Card ----------------
row, g, cur = current_tuple()
st.markdown("<div class='card'>", unsafe_allow_html=True)
if row is None:
    st.warning("현재 피커에 할당된 항목이 없습니다.")
else:
    st.markdown(f"<div class='slotbar'>{row['slot'] or ''}</div>", unsafe_allow_html=True)
    if str(row["green"]).strip():
        st.markdown(f"<div class='greentag'>{row['green']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sku'>{row['sku'] or ''}</div>", unsafe_allow_html=True)
    qty_txt = int(row['qty']) if str(row['qty']).isdigit() else ""
    st.markdown(f"<div class='row-sq'><div class='size'>{row['size'] or ''}</div><div class='qty'>{qty_txt}</div></div>", unsafe_allow_html=True)
    badge = ",".join([x for x in [str(row['barcode5']).strip(), str(row['color']).strip()] if x])
    st.markdown(f"<div class='badge'><b>{badge}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='title'>{(row['style_name'] or '').strip()}</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Buttons ----------------
st.markdown("<div class='center mt12'><div class='w70' id='ok-wrap'>", unsafe_allow_html=True)
ok = st.button("OK", key="ok_btn")
st.markdown("</div></div>", unsafe_allow_html=True)

c2l, c2r = st.columns(2)
with c2l:
    st.markdown("<div id='prev-wrap'>", unsafe_allow_html=True)
    prev = st.button("Previous", key="prev_btn"); st.markdown("</div>", unsafe_allow_html=True)
with c2r:
    st.markdown("<div id='next-wrap'>", unsafe_allow_html=True)
    nxt  = st.button("Next", key="next_btn");  st.markdown("</div>", unsafe_allow_html=True)

c3l, c3r = st.columns(2)
with c3l:
    st.markdown("<div id='fic-wrap'>", unsafe_allow_html=True)
    fic = st.button("First in Category", key="fic_btn"); st.markdown("</div>", unsafe_allow_html=True)
with c3r:
    st.markdown("<div id='lic-wrap'>", unsafe_allow_html=True)
    lic = st.button("Last in Category", key="lic_btn");  st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='center mt12'><div class='w70' id='clear-wrap'>", unsafe_allow_html=True)
clear = st.button("Clear Data", key="clear_btn")
st.markdown("</div></div>", unsafe_allow_html=True)

# ---------------- Actions ----------------
if st.session_state.df is not None and g:
    ridx = g[cur]
    if ok:
        st.session_state.df.at[ridx, "done"] = True
        move(+1, prefer_unfinished=True)
        st.rerun()
    if prev:
        move(-1, prefer_unfinished=False); st.rerun()
    if nxt:
        move(+1, prefer_unfinished=False); st.rerun()
    if fic or lic:
        cat = str(st.session_state.df.loc[ridx, "category"])
        same = [k for k, r in enumerate(g) if str(st.session_state.df.loc[r, "category"]) == cat]
        if same:
            st.session_state.idx[st.session_state.active_picker] = same[0] if fic else same[-1]
            st.rerun()

# ---------------- Clear Data ----------------
if clear:
    st.session_state.df = None
    st.session_state.groups = {}
    st.session_state.idx = {}
    st.session_state.picker_count = 3
    st.session_state.active_picker = 1
    st.session_state.uploader_key += 1
    st.rerun()

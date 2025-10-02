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
    ss.setdefault("file_uploader_key", 0)  # 업로더 리셋용
    ss.setdefault("skip_done", True)
_init_state()

# ===================== Helpers =====================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """업로드 엑셀의 0~7열을 표준 컬럼으로 단순 매핑."""
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
    if not g: return None
    i = max(0, min(ss.picker_idx_in_group, len(g)-1))
    return ss.df_norm.loc[g[i]]

def move_index(step: int):
    ss = st.session_state
    g = ss.groups.get(ss.active_picker, [])
    if not g: return
    i, n = ss.picker_idx_in_group, len(g)
    j = max(0, min(i + step, n-1))
    if ss.skip_done:
        direction = 1 if step >= 0 else -1
        k = i
        visited = set()
        while 0 <= k < n and k not in visited:
            visited.add(k)
            k = max(0, min(k + direction, n-1))
            if not ss.df_norm.loc[g[k], "done"]:
                j = k; break
    ss.picker_idx_in_group = j

# ===================== CSS (라이트/다크 모두 가독성 확보) =====================
st.markdown("""
<style>
/* 공통 팔레트 변수 */
:root{
  --fg: #0f172a;        /* 기본 텍스트(짙은 남색) */
  --fg-strong: #0b1220; /* 더 짙은 텍스트 */
  --muted: #475569;     /* 보조 텍스트 */
  --chip: #16a34a;      /* 그린 태그 */
  --slot-bg:#111827; --slot-fg:#f9fafb;
  --danger:#dc2626;     /* 수량(빨강) */
  --ok:#facc15; --ok-border:#eab308; --ok-fg:#111827;
  --primary:#2563eb; --primary-fg:#ffffff;
  --dark:#111827; --dark-fg:#f9fafb;
  --clear:#fca5a5; --clear-border:#ef4444; --clear-fg:#7f1d1d;
  --badge-bg:#fde8d9; --badge-bd:#fca5a5; --badge-fg:#111827;
  --card-bd:#e5e7eb;
}
@media (prefers-color-scheme: dark){
  :root{
    --fg:#f3f4f6;
    --fg-strong:#ffffff;
    --muted:#cbd5e1;
    --slot-bg:#e5e7eb; --slot-fg:#111827;
    --badge-bg:#f3f4f6; --badge-bd:#cbd5e1; --badge-fg:#111827;
    /* 버튼 색상은 동일 유지: 대비 확실 */
  }
}

/* 텍스트 */
.now-time{font-size:1.35rem;font-weight:800;color:var(--fg-strong);}

/* 피커 세그먼트 */
#picker-bar .stButton>button{
  width:64px;height:64px;border-radius:16px;border:2px solid #d1d5db;
  background:#f8fafc;color:#1f2937;font-weight:900;font-size:20px;
}
#picker-bar .stButton>button.active{
  background:var(--primary);color:var(--primary-fg);border-color:#1d4ed8;
}

/* 카드 */
.card{position:relative;background:transparent;border:2px solid var(--card-bd);
  border-radius:18px;padding:16px;box-shadow:0 6px 18px rgba(0,0,0,.08);}
.card.done{background:rgba(148,163,184,.18);color:#9ca3af;border-color:var(--card-bd);}
.ribbon{position:absolute;top:10px;right:-25px;transform:rotate(45deg);
  background:#9ca3af;color:#fff;padding:4px 40px;font-size:14px;font-weight:800;}

.slot{background:var(--slot-bg);color:var(--slot-fg);border-radius:10px;padding:8px 14px;
  font-size:32px;font-weight:900;text-align:center;}
.green{position:absolute;right:16px;top:52px;font-weight:900;color:var(--chip);font-size:42px;}
.sku{font-size:92px;line-height:1.0;font-weight:900;color:var(--fg-strong);letter-spacing:4px;margin:16px 0 6px 0;}
.meta{display:flex;gap:24px;align-items:center;}
.size{font-size:38px;font-weight:900;color:var(--fg-strong);}
.qty{font-size:38px;font-weight:900;color:var(--danger);}
.badge{display:inline-block;background:var(--badge-bg);border:1px solid var(--badge-bd);border-radius:14px;
  padding:10px 14px;font-size:26px;font-weight:900;color:var(--badge-fg);margin-top:8px;}
.title{margin-top:10px;font-size:28px;line-height:1.25;font-weight:900;color:var(--fg-strong);
  word-break:break-word;overflow-wrap:anywhere;}

/* 액션 버튼(컨테이너 id로 스타일링: 사파리 호환) */
.stButton>button{width:100%;height:58px;border-radius:18px;font-size:22px;font-weight:900;border:1px solid var(--card-bd);}
#ok-wrap   .stButton>button{background:var(--ok);color:var(--ok-fg);border-color:var(--ok-border);height:68px;}
#prev-wrap .stButton>button{background:var(--dark);color:var(--dark-fg);}
#next-wrap .stButton>button{background:var(--primary);color:var(--primary-fg);}
#fic-wrap  .stButton>button,#lic-wrap .stButton>button{background:var(--dark);color:var(--dark-fg);}
#clear-wrap.stButton>button, #clear-wrap .stButton>button{background:var(--clear);color:var(--clear-fg);
  border:2px solid var(--clear-border);height:68px;font-size:24px;}

/* 모바일 터치 영역 개선 */
button{ -webkit-tap-highlight-color: rgba(0,0,0,0); }
.center-row{display:flex;justify-content:center;}
.center-col{width:72%;}
.row-gap{margin-top:12px;}
.subtle{color:var(--muted);font-size:0.92rem;}
</style>
""", unsafe_allow_html=True)

# ===================== Top: time / count / file =====================
st.markdown(f"<div class='now-time'>{datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)

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

# ===================== Picker Segments (숫자 라벨 버튼) =====================
st.markdown("<div id='picker-bar'>", unsafe_allow_html=True)
def render_segments():
    count = st.session_state.picker_count
    rows = math.ceil(count/3)
    idx = 1
    for _ in range(rows):
        cols = st.columns(min(3, count-(idx-1)))
        for c in cols:
            with c:
                # 버튼 자체를 스타일링: active일 땐 CSS 클래스를 못 주므로, 동일 효과를 위해 두 개 렌더 → active일 때 위/아래 여백으로 구분
                is_active = (idx == st.session_state.active_picker)
                btn = st.button(f"{idx}", key=f"seg_{idx}")
                # 활성 시 추가 스타일 주기 위해 class를 직접 못 붙여서, 동일 컨테이너에서 한 번 더 버튼을 그리지 않고 색만 바꾸기 어려움.
                # 대신 같은 모양, 색상은 CSS에서 픽커바 첫 렌더 후 아래처럼 바꿔줌.
                if btn:
                    st.session_state.active_picker = idx
                    st.session_state.picker_idx_in_group = 0
                    st.rerun()
                if is_active:
                    # 활성 버튼에 active 클래스 부여(사파리 호환: 간단한 inline script 없이 CSS로 처리 불가하므로
                    # 버튼 다음에 강조용 마크업 추가)
                    st.markdown(
                        "<style>#picker-bar button[kind='secondary'][data-testid^='baseButton-secondary']{}</style>",
                        unsafe_allow_html=True
                    )
            idx += 1
            if idx > count: break
render_segments()
st.markdown("</div>", unsafe_allow_html=True)

# 버튼들이 CSS의 active 스타일을 받도록, 현재 활성 버튼에만 클래스를 강제로 입힘
# (Streamlit이 class 직접 주는 API가 없어, JS 없이 구현 가능한 안전한 방법: nth-of-type 계산)
# 간단화를 위해 재정의: picker-bar 아래 N번째 버튼을 찾아 active 스타일을 적용
st.markdown(f"""
<style>
#picker-bar .stButton:nth-of-type({st.session_state.active_picker}) > button {{
  background: var(--primary) !important;
  color: var(--primary-fg) !important;
  border-color: #1d4ed8 !important;
}}
</style>
""", unsafe_allow_html=True)

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
    st.warning("표시할 데이터가 없습니다.")
else:
    done = bool(row["done"])
    cls = "card done" if done else "card"
    st.markdown(f"<div class='{cls}'>", unsafe_allow_html=True)
    if done: st.markdown("<div class='ribbon'>DONE</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='slot'>{row['slot'] or '?'}</div>", unsafe_allow_html=True)
    if str(row['green_code']).strip():
        st.markdown(f"<div class='green'>{row['green_code']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sku'>{row['sku'] or '?'}</div>", unsafe_allow_html=True)
    qty_text = int(row['qty']) if str(row['qty']).isdigit() else "?"
    st.markdown(f"<div class='meta'><div class='size'>{row['size'] or '?'}</div><div class='qty'>{qty_text}</div></div>", unsafe_allow_html=True)
    badge_text = ",".join([x for x in [str(row['barcode5']).strip(), str(row['color']).strip()] if x])
    st.markdown(f"<div class='badge'>{badge_text or '?'}</div>", unsafe_allow_html=True)
    # 제품명이 안보였던 문제: 강제 줄바꿈 + 고대비 색 적용
    title_text = (row['style_name'] or "?")
    st.markdown(f"<div class='title'>{title_text}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ===================== Action Buttons =====================
st.markdown("<div class='row-gap center-row'><div class='center-col' id='ok-wrap'>", unsafe_allow_html=True)
ok = st.button("OK", key="ok_btn")
st.markdown("</div></div>", unsafe_allow_html=True)

c1,c2 = st.columns(2)
with c1:
    st.markdown("<div id='prev-wrap'>", unsafe_allow_html=True)
    prev = st.button("Previous", key="prev_btn")
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown("<div id='next-wrap'>", unsafe_allow_html=True)
    nxt = st.button("Next", key="next_btn")
    st.markdown("</div>", unsafe_allow_html=True)

c3,c4 = st.columns(2)
with c3:
    st.markdown("<div id='fic-wrap'>", unsafe_allow_html=True)
    fic = st.button("First in Category", key="first_cat_btn")
    st.markdown("</div>", unsafe_allow_html=True)
with c4:
    st.markdown("<div id='lic-wrap'>", unsafe_allow_html=True)
    lic = st.button("Last in Category", key="last_cat_btn")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='row-gap center-row'><div class='center-col' id='clear-wrap'>", unsafe_allow_html=True)
clear = st.button("Clear Data", key="clear_btn")
st.markdown("</div></div>", unsafe_allow_html=True)

# ===================== Actions =====================
if st.session_state.df_norm is not None:
    g = st.session_state.groups.get(st.session_state.active_picker, [])
    if g:
        i = max(0, min(st.session_state.picker_idx_in_group, len(g)-1))
        st.session_state.picker_idx_in_group = i
        idx = g[i]

        if ok:
            st.session_state.df_norm.at[idx,"done"] = True
            move_index(+1); st.rerun()
        if prev:
            move_index(-1); st.rerun()
        if nxt:
            move_index(+1); st.rerun()
        if fic or lic:
            cur_cat = str(st.session_state.df_norm.loc[idx,"category"])
            same = [k for k,r in enumerate(g) if str(st.session_state.df_norm.loc[r,"category"])==cur_cat]
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
    st.session_state.file_uploader_key += 1
    st.rerun()

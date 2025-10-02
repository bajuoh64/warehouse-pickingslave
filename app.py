import streamlit as st
import pandas as pd
from datetime import datetime
import math
import re

# =========================
# Page
# =========================
st.set_page_config(
    page_title="Warehouse Picking MVP",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================
# CSS (샘플 색/형태 매칭)
# =========================
st.markdown("""
<style>
.block-container { padding-top: 0.6rem; }

/* 현재 시간 */
.now-time { font-size: 1.35rem; font-weight: 800; }

/* 세그먼트 박스 */
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

/* 상태 리본 */
.small-hint { color:#6b7280; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

# =========================
# Session State
# =========================
def init_state():
    ss = st.session_state
    ss.setdefault("picker_count", 3)
    ss.setdefault("active_picker", 1)
    ss.setdefault("picker_idx_in_group", 0)  # 현재 피커에서 몇번째 아이템인지
    ss.setdefault("df_raw", None)            # 원본 DF
    ss.setdefault("df_norm", None)           # 정규화 DF (표준 컬럼)
    ss.setdefault("groups", {})              # 피커별 인덱스 리스트
    ss.setdefault("category_col", None)      # 카테고리 판별에 사용할 컬럼명
init_state()

# =========================
# Excel → 표준컬럼 매핑
# =========================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # 공백/소문자 정규화용
    def norm(s): return re.sub(r'[\s_]+','',str(s).lower())

    colmap = {norm(c): c for c in df.columns}

    def pick(*cands):
        for c in cands:
            k = norm(c)
            # 직접 이름이 있을 때
            for nk, orig in colmap.items():
                if nk == k:
                    return orig
            # 포함 매칭(느슨하게)
            for nk, orig in colmap.items():
                if k in nk:
                    return orig
        return None

    # 후보군들(한국어/영문 혼합)
    c_slot   = pick('slot','슬롯','순번','번호','오더','order')
    c_loc    = pick('location','로케이션','현재로케이션','현재 로케이션','현위치','sku','상품코드','코드')
    c_next   = pick('nextlocation','다음로케이션','다음 로케이션','다음','next')
    c_size   = pick('size','사이즈')
    c_qty    = pick('qty','quantity','수량','수량합','주문수량')
    c_bar    = pick('barcode','바코드','바코드5','바코드(5)')  # 가능하면 5자리 컬럼
    c_color  = pick('color','색상','색상명','컬러')
    c_style  = pick('style','스타일','스타일명','상품명','품명','name','title')
    c_picker = pick('picker','피커','담당','담당자')

    out = pd.DataFrame()
    out['slot']         = df[c_slot].astype(str) if c_slot else pd.RangeIndex(1, len(df)+1).astype(str)
    out['green_code']   = df[c_next].astype(str) if c_next else ''
    out['sku']          = df[c_loc].astype(str) if c_loc else (df[c_bar].astype(str) if c_bar else '')
    out['size']         = df[c_size].astype(str) if c_size else ''
    out['qty']          = pd.to_numeric(df[c_qty], errors='coerce').fillna(1).astype(int) if c_qty else 1
    # 바코드 5자리 추출
    if c_bar:
        bc = df[c_bar].astype(str).str.replace(r'\D','', regex=True)
        out['barcode5'] = bc.str[-5:].fillna('')
    else:
        # 바코드 없으면 sku의 끝 5자리를 추정(숫자만)
        bc = out['sku'].str.replace(r'\D','', regex=True)
        out['barcode5'] = bc.str[-5:].fillna('')

    out['color']        = df[c_color].astype(str) if c_color else ''
    out['style_name']   = df[c_style].astype(str) if c_style else out['sku']

    # 카테고리는 스타일명 우선, 없으면 sku
    out['category']     = out['style_name'].where(out['style_name'].str.strip()!='', other=out['sku'])

    # 피커(엑셀에 있으면 사용)
    if c_picker:
        tmp = pd.to_numeric(df[c_picker], errors='coerce').fillna(1).astype(int)
        out['picker'] = tmp.clip(lower=1)  # 상한은 나중에 인원수로 클립
    else:
        out['picker'] = None  # 나중에 동적 분배

    return out

# =========================
# 피커 분배 및 그룹핑
# =========================
def build_groups(df_norm: pd.DataFrame, picker_count: int):
    df = df_norm.copy()
    # 엑셀에 picker가 없으면, 인덱스 기준 라운드로빈 분배
    if df['picker'].isna().all():
        df['picker'] = (pd.RangeIndex(0, len(df)) % picker_count) + 1
    else:
        # 엑셀에 있던 값이 인원수보다 크면 잘라냄
        df['picker'] = df['picker'].clip(upper=picker_count)

    groups = {i: df.index[df['picker']==i].tolist() for i in range(1, picker_count+1)}
    return df, groups

# =========================
# 현재 피커에서 n번째 아이템 가져오기
# =========================
def get_current_row(ss) -> pd.Series | None:
    g = ss.groups.get(ss.active_picker, [])
    if not g:
        return None
    idx = max(0, min(ss.picker_idx_in_group, len(g)-1))
    return ss.df_norm.loc[g[idx]]

# =========================
# UI: 상단 (시간/인원수/파일/피커)
# =========================
st.markdown(f"<div class='now-time'>{datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)

left, right = st.columns([2,6])
with left:
    new_count = st.number_input(
        "인원수:",
        min_value=1, max_value=30, step=1,
        value=st.session_state.picker_count,
        key="picker_count_input",
    )

with right:
    uploaded = st.file_uploader("파일 선택 (.xlsx / .csv)", type=["xlsx","csv"])
    if uploaded is not None:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df_raw = pd.read_csv(uploaded)
            else:
                df_raw = pd.read_excel(uploaded, engine="openpyxl")
            st.session_state.df_raw = df_raw
            st.session_state.df_norm = normalize_columns(df_raw)
        except Exception as e:
            st.error(f"파일 읽는 중 오류: {e}")
            st.stop()

# 인원수 반영 → 그룹 재구성
if int(new_count) != st.session_state.picker_count:
    st.session_state.picker_count = int(new_count)
    # active_picker가 범위를 벗어나면 보정
    if st.session_state.active_picker > st.session_state.picker_count:
        st.session_state.active_picker = st.session_state.picker_count
    # 파일 기반이면 재그룹
    if st.session_state.df_norm is not None:
        st.session_state.df_norm, st.session_state.groups = build_groups(
            st.session_state.df_norm, st.session_state.picker_count
        )
        st.session_state.picker_idx_in_group = 0
    st.rerun()

# 파일이 있으면 그룹핑, 없으면 비활성
if st.session_state.df_norm is not None and not st.session_state.groups:
    st.session_state.df_norm, st.session_state.groups = build_groups(
        st.session_state.df_norm, st.session_state.picker_count
    )

# 피커 세그먼트 표시
def render_segments():
    count = st.session_state.picker_count
    rows = math.ceil(count / 3)
    idx = 1
    for _ in range(rows):
        cols = st.columns(min(3, count - (idx-1)))
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
                        st.session_state.picker_idx_in_group = 0
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            idx += 1
            if idx > count:
                break

render_segments()

# 상태 안내
if st.session_state.df_norm is not None:
    total = len(st.session_state.df_norm)
    gsize = len(st.session_state.groups.get(st.session_state.active_picker, []))
    st.markdown(f"<div class='small-hint'>파일 행수: {total} · 피커 {st.session_state.active_picker}/{st.session_state.picker_count} 담당 {gsize}건</div>", unsafe_allow_html=True)
else:
    st.info("엑셀 또는 CSV 파일을 업로드하면 피킹 리스트가 여기에 표시됩니다.")

# =========================
# 메인 카드 (현재 행 표시)
# =========================
row = get_current_row(st.session_state)

st.markdown("<div class='main-card'>", unsafe_allow_html=True)

if row is None:
    st.warning("현재 피커에게 할당된 아이템이 없습니다.")
else:
    # 화면 바인딩
    slot       = str(row.get('slot',''))
    green_code = str(row.get('green_code',''))
    sku        = str(row.get('sku',''))
    size       = str(row.get('size',''))
    qty        = int(row.get('qty',1))
    badge      = f"{str(row.get('barcode5',''))},{str(row.get('color',''))}".strip(',')  # '46201,CORAL'
    style_name = str(row.get('style_name',''))

    st.markdown(f"<div class='slot-bar'>{slot}</div>", unsafe_allow_html=True)
    if green_code:
        st.markdown(f"<div class='green-tag'>{green_code}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='big-sku'>{sku}</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='meta-row'><div class='meta-size'>{size}</div>"
        f"<div class='meta-qty'>{qty}</div></div>",
        unsafe_allow_html=True
    )
    if badge:
        st.markdown(f"<div class='badge'>{badge}</div>", unsafe_allow_html=True)
    # 스타일명은 2~3줄로 보이도록 적당히 끊어주기
    def wrap_title(s, width=26):
        words, lines, cur = s.split(), [], ""
        for w in words:
            if len(cur)+len(w)+1 > width:
                lines.append(cur.strip()); cur = w
            else:
                cur += " " + w
        if cur.strip(): lines.append(cur.strip())
        return lines[:3]
    title_lines = wrap_title(style_name, width=28)
    st.markdown("<div class='title'>" + "<br/>".join(title_lines) + "</div>", unsafe_allow_html=True)

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
# 동작 로직
# =========================
if st.session_state.df_norm is not None:
    g = st.session_state.groups.get(st.session_state.active_picker, [])
    n = len(g)
    if n > 0:
        cur_i = st.session_state.picker_idx_in_group

        # OK = 다음으로 이동(+ 완료 체크는 필요시 DF에 컬럼 추가해 저장 가능)
        if ok_clicked:
            st.session_state.picker_idx_in_group = min(cur_i + 1, n-1)
            st.rerun()

        if prev_clicked:
            st.session_state.picker_idx_in_group = max(cur_i - 1, 0)
            st.rerun()

        if next_clicked:
            st.session_state.picker_idx_in_group = min(cur_i + 1, n-1)
            st.rerun()

        # 카테고리 기준 이동 (style_name 우선, 없으면 sku)
        if first_clicked or last_clicked:
            cat_col = 'category'
            cur_row = st.session_state.df_norm.loc[g[cur_i]]
            cur_cat = cur_row.get(cat_col, "")
            # 해당 피커 그룹 내에서 같은 카테고리의 범위를 찾는다
            same = [i for i, ridx in enumerate(g)
                    if str(st.session_state.df_norm.loc[ridx].get(cat_col,"")) == str(cur_cat)]
            if same:
                st.session_state.picker_idx_in_group = same[0] if first_clicked else same[-1]
                st.rerun()

        if clear_clicked:
            st.session_state.picker_idx_in_group = 0
            st.rerun()
    else:
        if any([ok_clicked, prev_clicked, next_clicked, first_clicked, last_clicked, clear_clicked]):
            st.toast("현재 피커에게 할당된 항목이 없습니다.")

# =========================
# 버튼 색상 패치(JS)
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

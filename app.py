
# -*- coding: utf-8 -*-
import re
import io
import math
import pandas as pd
import streamlit as st

# -------------------------------------------------------------
# 피킹 최적화 웹 애플리케이션 (Streamlit · Python) — 최종본 v1.2 (indent fix)
# -------------------------------------------------------------

st.set_page_config(page_title="피킹 최적화 웹앱 v1.2", layout="centered")

# --------------- 유틸 ---------------
def key_of(obj_keys, candidates):
    """다국어/여러 변형 헤더 후보 중 매칭되는 실제 키 반환"""
    for raw in obj_keys:
        k = str(raw).lower().replace(' ', '')
        if k in candidates:
            return raw
    return None

def split_barcode_color(value):
    """'78681,BLACK/WHITE' → (barcode5='78681', color='BLACK/WHITE')"""
    s = str(value or '').strip()
    if not s:
        return {'barcode5': '', 'color': ''}
    m = re.match(r'^(\d{5})[,\-\s]*(.+)$', s)
    if m:
        return {'barcode5': m.group(1), 'color': m.group(2).strip()}
    if re.match(r'^\d{5}$', s):
        return {'barcode5': s, 'color': ''}
    return {'barcode5': '', 'color': s}

def split_style(value):
    """'[41303,MULTI]DEUS ...' → (styleCode='41303', styleName='DEUS ...')"""
    s = str(value or '').strip()
    if not s:
        return {'styleCode': '', 'styleName': ''}
    m = re.match(r'^\[(\d+)[^\]]*\](.*)$', s)
    if m:
        return {'styleCode': m.group(1), 'styleName': m.group(2).strip()}
    return {'styleCode': '', 'styleName': s}

def get_zone(location):
    """로케이션 코드에서 3~4자리 접두 구역 추출 (예: 1FC12 → 1FC, 3MH-07 → 3MH)"""
    s = str(location or '').upper().strip()
    if not s:
        return ''
    m = re.match(r'^[A-Z0-9]{3,4}', s)
    return m.group(0) if m else s

# 마스터 동선표 (예시). 실제 창고 동선에 맞게 커스터마이즈 가능
MASTER_ORDER = [
    '1FA', '1FB', '1FC', '1FD', '1FE', '1FF', '1FG', '1FH',
    'CC',
    '2MA', '2MB', '2MC', '2MD', '2ME',
    '3MA', '3MB', '3MC', '3MD', '3ME', '3MF', '3MG', '3MH',
    'DECK', 'ACC', 'ETC'
]

def sort_key(row):
    zone = row.get('zone', '')
    base = MASTER_ORDER.index(zone) if zone in MASTER_ORDER else 999
    loc = str(row.get('location', '')).upper()
    return f"{base:03d}-{loc:>15}"

# --------------- 데이터 파싱 ---------------
def parse_dataframe(df: pd.DataFrame):
    """업로드된 DF를 표준 컬럼으로 정리"""
    cols = list(df.columns)
    k_location = key_of(cols, {'location','로케이션','bin','shelf','loc','위치'})
    k_qty      = key_of(cols, {'qty','수량','quantity'})
    k_size     = key_of(cols, {'size','사이즈'})
    k_color    = key_of(cols, {'색상명','colorname','color','색상'})
    k_style    = key_of(cols, {'스타일명','stylename','product','제품명','name'})
    k_barcode  = key_of(cols, {'barcode','바코드','upc','ean'})

    out = []
    for i, r in df.iterrows():
        location = str(r.get(k_location, '')).strip()
        qty      = str(r.get(k_qty, '1')).strip() or '1'
        size     = str(r.get(k_size, '')).strip()

        bc_color = split_barcode_color(r.get(k_color, ''))
        color    = bc_color['color']
        barcode5 = bc_color['barcode5']

        st_info   = split_style(r.get(k_style, ''))
        styleCode = st_info['styleCode']
        styleName = st_info['styleName']

        raw_bar   = str(r.get(k_barcode, '')).strip()
        if raw_bar:
            m = re.search(r'(\d{5})', raw_bar)
            if m:
                barcode5 = m.group(1)

        out.append({
            'id': int(i),
            'location': location,
            'qty': qty,
            'size': size,
            'color': color,
            'barcode5': barcode5,
            'styleCode': styleCode,
            'styleName': styleName,
            'zone': get_zone(location),
        })
    return out

def distribute(sorted_rows, n_pickers):
    """정렬된 리스트를 N명에게 구간 분할로 균등 분배"""
    n = max(1, min(6, int(n_pickers or 1)))
    per = math.ceil(len(sorted_rows) / n) if len(sorted_rows) else 0
    packs = [sorted_rows[i*per:(i+1)*per] for i in range(n)]
    return packs

# --------------- 세션 상태 초기화 ---------------
if 'raw_rows' not in st.session_state:
    st.session_state.raw_rows = []
if 'sorted_rows' not in st.session_state:
    st.session_state.sorted_rows = []
if 'pickers' not in st.session_state:
    st.session_state.pickers = 1
if 'started' not in st.session_state:
    st.session_state.started = False
if 'picker_no' not in st.session_state:
    st.session_state.picker_no = 1
if 'packs' not in st.session_state:
    st.session_state.packs = []
if 'progress' not in st.session_state:
    st.session_state.progress = {}  # {1: {'idx':0,'done_ids':set()}, ...}

# --------------- 메인/설정 화면 ---------------
def render_setup():
    st.title('📦 피킹 최적화 웹앱 v1.2')

    up = st.file_uploader('엑셀(xlsx) 또는 CSV 업로드', type=['xlsx','xls','csv'])
    if up is not None:
        try:
            if up.name.lower().endswith('.csv'):
                df = pd.read_csv(up, dtype=str, keep_default_na=False)
            else:
                df = pd.read_excel(up, dtype=str, engine='openpyxl')
            parsed = parse_dataframe(df)
            st.session_state.raw_rows = parsed
            st.session_state.started = False
            st.success(f"{len(parsed)}개 항목을 불러왔습니다.")
        except Exception as e:
            st.error(f"파일 파싱 중 오류: {e}")

    st.write('---')
    st.subheader('작업자 수 선택')
    cols = st.columns(6)
    for i, n in enumerate([1, 2, 3, 4, 5, 6]):
        with cols[i]:
            clicked = st.button(
                f"{n}",
                use_container_width=True,
                type=('primary' if st.session_state.pickers == n else 'secondary')
            )
            if clicked:
                st.session_state.pickers = n
                if st.session_state.picker_no > n:
                    st.session_state.picker_no = n

#     ---- 피커 번호 선택 라인 (indent 안정화) ----
    st.markdown('**피커 번호 선택:**')
    pick_buttons = st.columns(st.session_state.pickers)
    for i in range(st.session_state.pickers):
        with pick_buttons[i]:
            b = st.button(
                f"#{i+1}",
                use_container_width=True,
                type=('primary' if st.session_state.picker_no == i + 1 else 'secondary')
            )
            if b:
                st.session_state.picker_no = i + 1

    st.write('---')
    c1, c2 = st.columns(2)
    with c1:
        start = st.button(
            '피킹 시작하기',
            type='primary',
            use_container_width=True,
            disabled=(len(st.session_state.raw_rows) == 0)
        )
    with c2:
        clear = st.button('Clear Data', use_container_width=True)

    if start:
        sorted_rows = sorted(st.session_state.raw_rows, key=sort_key)
        st.session_state.sorted_rows = sorted_rows
        packs = distribute(sorted_rows, st.session_state.pickers)
        st.session_state.packs = packs
        st.session_state.progress = {
            p: {'idx': 0, 'done_ids': set()}
            for p in range(1, st.session_state.pickers + 1)
        }
        st.session_state.started = True

    if clear:
        st.session_state.raw_rows = []
        st.session_state.sorted_rows = []
        st.session_state.pickers = 1
        st.session_state.started = False
        st.session_state.picker_no = 1
        st.session_state.packs = []
        st.session_state.progress = {}
        st.experimental_rerun()

    if len(st.session_state.raw_rows):
        st.caption('미리보기 (상위 10개)')
        st.dataframe(pd.DataFrame(st.session_state.raw_rows).head(10))

# --------------- 진행 화면 ---------------
def render_running():
    pno = st.session_state.picker_no
    packs = st.session_state.packs
    my_list = packs[pno - 1] if packs and len(packs) >= pno else []
    prog = st.session_state.progress.get(pno, {'idx': 0, 'done_ids': set()})
    idx = min(max(0, prog['idx']), max(0, len(my_list) - 1)) if my_list else 0
    current = my_list[idx] if my_list else None
    next_item = my_list[idx + 1] if my_list and idx + 1 < len(my_list) else None

    done_count = sum(1 for r in my_list if r['id'] in prog['done_ids'])
    total = len(my_list)
    pct = int(round((done_count / total) * 100)) if total else 0

    st.title(f"피커 #{pno} · {done_count}/{total} ({pct}%)")
    st.progress(pct / 100 if total else 0.0)

    box = st.container()
    with box:
        st.markdown(f"**다음 제품 로케이션**: :green[{next_item.get('location', '-') if next_item else '-'}]")
        st.markdown(f"### {current.get('location', '-') if current else '-'}")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**사이즈**: {current.get('size', '-') if current else '-'}")
        with c2:
            st.markdown(f"**수량**: :red[{current.get('qty', '1') if current else '1'}]")

        st.markdown("> 바코드 5자리 / 컬러")
        st.info(
            f"바코드: `{current.get('barcode5', '') if current else ''}`\n컬러: **{current.get('color', '-') if current else '-'}**"
        )

        st.caption(
            f"스타일명: {current.get('styleName', '-') if current else '-'}" +
            (f"  (코드 {current.get('styleCode', '')})" if current and current.get('styleCode') else '')
        )

    st.write('')
    ok = st.button('OK! ✅', type='primary', use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        prev = st.button('Previous', use_container_width=True)
    with c2:
        nxt = st.button('Next', use_container_width=True)
    c3, c4 = st.columns(2)
    with c3:
        first_cat = st.button('First in Category', use_container_width=True)
    with c4:
        last_cat = st.button('Last in Category', use_container_width=True)

    def jump_to(i):
        i = max(0, min(i, max(0, len(my_list) - 1)))
        st.session_state.progress[pno]['idx'] = i

    if ok and current:
        st.session_state.progress[pno]['done_ids'].add(current['id'])
        jump_to(idx + 1)
        st.experimental_rerun()

    if prev:
        jump_to(idx - 1)
        st.experimental_rerun()

    if nxt:
        jump_to(idx + 1)
        st.experimental_rerun()

    if first_cat and current:
        cat = current['zone']
        for i, r in enumerate(my_list):
            if r['zone'] == cat:
                jump_to(i)
                st.experimental_rerun()
                break

    if last_cat and current:
        cat = current['zone']
        for i in range(len(my_list) - 1, -1, -1):
            if my_list[i]['zone'] == cat:
                jump_to(i)
                st.experimental_rerun()
                break

    st.write('---')
    if st.button('초기화 및 나가기', help='모든 데이터를 초기화합니다.'):
        st.session_state.raw_rows = []
        st.session_state.sorted_rows = []
        st.session_state.pickers = 1
        st.session_state.started = False
        st.session_state.picker_no = 1
        st.session_state.packs = []
        st.session_state.progress = {}
        st.experimental_rerun()

# --------------- 라우팅 ---------------
if not st.session_state.started:
    render_setup()
else:
    render_running()


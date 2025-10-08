# -*- coding: utf-8 -*-
import re
import io
import math
import pandas as pd
import streamlit as st

# -------------------------------------------------------------
# 피킹 최적화 웹 애플리케이션 (Streamlit · Python) — 최종본 v1.3
# 변경사항:
# - UI 흐름 개선: '피커 번호 선택' UI를 설정 화면에서 진행 화면으로 이동
# - 코드 가독성 및 안정성 개선
# -------------------------------------------------------------

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="피킹 최적화 웹앱 v1.3", layout="centered")

# --- 유틸리티 함수들 ---
def key_of(obj_keys, candidates):
    for raw in obj_keys:
        k = str(raw).lower().replace(' ', '')
        if k in candidates:
            return raw
    return None

def split_barcode_color(value):
    s = str(value or '').strip()
    if not s: return {'barcode5': '', 'color': ''}
    m = re.match(r'^(\d{5})[,\-\s]*(.+)$', s)
    if m: return {'barcode5': m.group(1), 'color': m.group(2).strip()}
    if re.match(r'^\d{5}$', s): return {'barcode5': s, 'color': ''}
    return {'barcode5': '', 'color': s}

def split_style(value):
    s = str(value or '').strip()
    if not s: return {'styleCode': '', 'styleName': ''}
    m = re.match(r'^\[(\d+)[^\]]*\](.*)$', s)
    if m: return {'styleCode': m.group(1), 'styleName': m.group(2).strip()}
    return {'styleCode': '', 'styleName': s}

def get_zone(location):
    s = str(location or '').upper().strip()
    if not s: return ''
    m = re.match(r'^[A-Z0-9]{3,4}', s)
    return m.group(0) if m else s

# --- 핵심 데이터 및 로직 ---
MASTER_ORDER = [
    'CC', '1FC', '2LD', '2LE', '2LF', '2LG', '2LH', '2LN', '2LQ', '2LS',
    '2LT', '2LU', '2RA', '2RB', '2RD', '2RE', '2RF', '2RH', '2RI', '2RJ',
    '2RK', '2RM', '2RN', '2RP', '2RQ', '2RR', '2RS', '2RT', '2RU', '2RV',
    '3LA', '3LB', '3LD', '3LE', '3LF', '3LH', '3LN', '3LQ', '3LS', '3LT', '3LU',
    '3FC', '3MH', 'W3F', 'W3G'
] # 실제 '완벽한 동선' 순서대로 로케이션 '구역(zone)'을 정의합니다.

def sort_key(row):
    zone = row.get('zone', '')
    # MASTER_ORDER에 있는 구역 순서 + 같은 구역 내에서는 로케이션 코드 전체로 정렬
    base = MASTER_ORDER.index(zone) if zone in MASTER_ORDER else 999
    loc = str(row.get('location', '')).upper()
    return f"{base:03d}-{loc}"

def parse_dataframe(df: pd.DataFrame):
    cols = list(df.columns)
    k_location = key_of(cols, {'location','로케이션','bin','shelf','loc','위치'})
    k_qty = key_of(cols, {'qty','수량','quantity', '주문수량'})
    k_size = key_of(cols, {'size','사이즈'})
    k_color = key_of(cols, {'색상명','colorname','color','색상'})
    k_style = key_of(cols, {'스타일명','stylename','product','제품명','name'})
    k_barcode = key_of(cols, {'barcode','바코드','upc','ean'})

    out = []
    for i, r in df.iterrows():
        location = str(r.get(k_location, '')).strip()
        if not location: continue # 로케이션 없으면 무시

        out.append({
            'id': int(i),
            'location': location,
            'qty': str(r.get(k_qty, '1')).strip() or '1',
            'size': str(r.get(k_size, '')).strip(),
            **split_barcode_color(r.get(k_color, '')),
            **split_style(r.get(k_style, '')),
            'zone': get_zone(location),
        })
    return out

def distribute(sorted_rows, n_pickers):
    n = max(1, min(6, int(n_pickers or 1)))
    per = math.ceil(len(sorted_rows) / n) if len(sorted_rows) else 0
    packs = [sorted_rows[i*per:(i+1)*per] for i in range(n)]
    return packs

# --- 세션 상태 관리 (앱의 기억 저장소) ---
if 'started' not in st.session_state:
    st.session_state.started = False
if 'raw_rows' not in st.session_state:
    st.session_state.raw_rows = []
if 'pickers' not in st.session_state:
    st.session_state.pickers = 1
if 'picker_no' not in st.session_state:
    st.session_state.picker_no = 1
if 'packs' not in st.session_state:
    st.session_state.packs = []
if 'progress' not in st.session_state:
    st.session_state.progress = {}

# --- 화면 1: 설정 및 업로드 ---
def render_setup():
    st.title('📦 피킹 최적화 웹앱 v1.3')

    uploaded_file = st.file_uploader('엑셀(xlsx) 또는 CSV 업로드', type=['xlsx','xls','csv'])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.lower().endswith('.csv'):
                df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
            else:
                df = pd.read_excel(uploaded_file, dtype=str, engine='openpyxl')
            
            st.session_state.raw_rows = parse_dataframe(df)
            st.session_state.started = False
            st.success(f"{len(st.session_state.raw_rows)}개 항목을 성공적으로 불러왔습니다.")
        except Exception as e:
            st.error(f"파일 처리 중 오류가 발생했습니다: {e}")

    st.divider()
    st.subheader('작업자 수를 선택하세요')
    cols = st.columns(6)
    for i in range(6):
        n = i + 1
        if cols[i].button(f"{n}명", use_container_width=True, type=('primary' if st.session_state.pickers == n else 'secondary')):
            st.session_state.pickers = n

    st.divider()
    
    c1, c2 = st.columns(2)
    if c1.button('피킹 시작하기', type='primary', use_container_width=True, disabled=(not st.session_state.raw_rows)):
        sorted_rows = sorted(st.session_state.raw_rows, key=sort_key)
        st.session_state.packs = distribute(sorted_rows, st.session_state.pickers)
        st.session_state.progress = {p + 1: {'idx': 0, 'done_ids': set()} for p in range(st.session_state.pickers)}
        st.session_state.picker_no = 1
        st.session_state.started = True
        st.rerun()

    if c2.button('데이터 초기화', use_container_width=True):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

# --- 화면 2: 피킹 진행 ---
def render_running():
    pno = st.session_state.picker_no
    my_list = st.session_state.packs[pno - 1] if len(st.session_state.packs) >= pno else []
    prog = st.session_state.progress.get(pno, {'idx': 0, 'done_ids': set()})
    idx = prog.get('idx', 0)
    
    # 현재 아이템, 다음 아이템 결정
    current = my_list[idx] if idx < len(my_list) else None
    next_item = my_list[idx + 1] if idx + 1 < len(my_list) else None

    done_count = len(prog.get('done_ids', set()))
    total = len(my_list)
    pct = int(round((done_count / total) * 100)) if total else 0

    st.title(f"피커 #{pno}")
    st.progress(pct / 100, text=f"{done_count} / {total} ({pct}%)")

    # [수정됨] 다른 피커 화면으로 전환하는 UI
    if st.session_state.pickers > 1:
        st.subheader("다른 작업자 화면 보기")
        cols = st.columns(st.session_state.pickers)
        for i in range(st.session_state.pickers):
            if cols[i].button(f"피커 #{i+1}", use_container_width=True, type=('primary' if pno == i + 1 else 'secondary')):
                st.session_state.picker_no = i + 1
                st.rerun()
        st.divider()


    if current:
        st.markdown(f"**다음 로케이션**: :green[{next_item['location'] if next_item else '없음'}]")
        st.header(current['location'])
        
        c1, c2 = st.columns(2)
        c1.metric("사이즈", current['size'] or '-')
        c2.metric("수량", current['qty'])

        with st.container(border=True):
            st.markdown(f"**컬러:** {current['color'] or '-'}")
            st.markdown(f"**바코드 5자리:** `{current['barcode5'] or '-'}`")
        
        st.caption(f"스타일명: {current['styleName'] or '-'}" + (f" (코드: {current['styleCode']})" if current['styleCode'] else ""))

    else:
        st.success("🎉 이 피커의 모든 작업이 완료되었습니다!")

    st.divider()

    # --- 버튼 로직 ---
    def jump_to(new_index):
        st.session_state.progress[pno]['idx'] = max(0, min(new_index, len(my_list) - 1))

    if st.button('OK! ✅', type='primary', use_container_width=True, disabled=not current):
        prog['done_ids'].add(current['id'])
        jump_to(idx + 1)
        st.rerun()

    c1, c2 = st.columns(2)
    if c1.button('◀ Previous', use_container_width=True):
        jump_to(idx - 1)
        st.rerun()
    if c2.button('Next ▶', use_container_width=True):
        jump_to(idx + 1)
        st.rerun()

    c3, c4 = st.columns(2)
    if c3.button('First in Category', use_container_width=True, disabled=not current):
        cat = current['zone']
        for i, r in enumerate(my_list):
            if r['zone'] == cat:
                jump_to(i); st.rerun(); break
    if c4.button('Last in Category', use_container_width=True, disabled=not current):
        cat = current['zone']
        for i in range(len(my_list) - 1, -1, -1):
            if my_list[i]['zone'] == cat:
                jump_to(i); st.rerun(); break

    st.divider()
    if st.button('↩️ 초기화 및 나가기'):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

# --- 화면 라우팅 ---
if st.session_state.started:
    render_running()
else:
    render_setup()

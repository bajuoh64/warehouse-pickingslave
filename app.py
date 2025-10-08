# -*- coding: utf-8 -*-
# -------------------------------------------------------------
# 피킹 최적화 웹 애플리케이션 (Streamlit · Python) — 최종본 v1.4
# 변경사항:
# - 모든 import 구문을 함수 안으로 이동시켜 Cold Start 속도 극대화
# - NameError 해결 및 코드 안정성 강화
# -------------------------------------------------------------

import streamlit as st

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="피킹 최적화 웹앱 v1.4", layout="centered")

# --- 유틸리티 함수들 (모든 import는 함수 내부로 이동) ---

def key_of(obj_keys, candidates):
    for raw in obj_keys:
        k = str(raw).lower().replace(' ', '')
        if k in candidates:
            return raw
    return None

def split_barcode_color(value):
    import re
    s = str(value or '').strip()
    if not s: return {'barcode5': '', 'color': ''}
    m = re.match(r'^(\d{5})[,\-\s]*(.+)$', s)
    if m: return {'barcode5': m.group(1), 'color': m.group(2).strip()}
    if re.match(r'^\d{5}$', s): return {'barcode5': s, 'color': ''}
    return {'barcode5': '', 'color': s}

def split_style(value):
    import re
    s = str(value or '').strip()
    if not s: return {'styleCode': '', 'styleName': ''}
    m = re.match(r'^\[(\d+)[^\]]*\](.*)$', s)
    if m: return {'styleCode': m.group(1), 'styleName': m.group(2).strip()}
    return {'styleCode': '', 'styleName': s}

def get_zone(location):
    import re
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
]

def sort_key(row):
    zone = row.get('zone', '')
    base = MASTER_ORDER.index(zone) if zone in MASTER_ORDER else 999
    loc = str(row.get('location', '')).upper()
    return f"{base:03d}-{loc}"

#수정해야함

def parse_dataframe(df):
    """
    업로드된 DF를 표준 컬럼으로 정리
    (규칙 확정: 바코드는 '스타일명'의 2번째 글자부터 6글자 중 숫자 5자리)
    """
    import re
    out = []
    cols = list(df.columns)
    
    # 모든 가능한 헤더 이름을 찾습니다.
    k_location = key_of(cols, {'location','로케이션','bin','shelf','loc','위치'})
    k_qty = key_of(cols, {'qty','수량','quantity', '주문수량'})
    k_size = key_of(cols, {'size','사이즈'})
    k_color = key_of(cols, {'색상명','colorname','color','색상'})
    k_style = key_of(cols, {'스타일명','stylename','product','제품명','name'})

    for i, r in df.iterrows():
        location = str(r.get(k_location, '')).strip()
        if not location: continue

        # 1단계: '스타일명' 원본 데이터를 가져옵니다.
        style_original = str(r.get(k_style, ''))
        
        # 2단계: 바코드 추출 (사용자님이 알려주신 규칙 적용!)
        barcode5 = ''
        if len(style_original) > 1:
            # 2번째 글자부터 6글자를 잘라냅니다. (=MID(..., 2, 6))
            mid_text = style_original[1:7] 
            # 그 안에서 연속된 숫자 5자리를 찾습니다.
            m = re.search(r'(\d{5})', mid_text)
            if m:
                barcode5 = m.group(1)

        # 3단계: 바코드를 제외한 순수 '스타일명'과 '품번'을 분리합니다.
        style_info = split_style(style_original)
        styleName = style_info['styleName']
        # 바코드를 찾았다면, 그것을 최종 품번(styleCode)으로 사용합니다.
        styleCode = barcode5 if barcode5 else style_info['styleCode']

        # 4단계: '색상명'에서 컬러만 가져옵니다.
        color_info = split_barcode_color(r.get(k_color, ''))
        color = color_info['color']
        
        out.append({
            'id': int(i),
            'location': location,
            'qty': str(r.get(k_qty, '1')).strip() or '1',
            'size': str(r.get(k_size, '')).strip(),
            'color': color,
            'barcode5': barcode5, # <-- 여기에 최종 추출된 바코드가 들어갑니다!
            'styleCode': styleCode,
            'styleName': styleName,
            'zone': get_zone(location),
        })
    return out
    
#수정할 부분 끝

def distribute(sorted_rows, n_pickers):
    import math
    n = max(1, min(6, int(n_pickers or 1)))
    per = math.ceil(len(sorted_rows) / n) if len(sorted_rows) else 0
    packs = [sorted_rows[i*per:(i+1)*per] for i in range(n)]
    return packs

# --- 세션 상태 관리 ---
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
    st.title('📦 피킹 최적화 웹앱 v1.4')

    uploaded_file = st.file_uploader('엑셀(xlsx) 또는 CSV 업로드', type=['xlsx','xls','csv'])
    if uploaded_file is not None:
        try:
            import pandas as pd
            if uploaded_file.name.lower().endswith('.csv'):
                df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
            else:
                df = pd.read_excel(uploaded_file, dtype=str, engine='openpyxl')
            
            st.session_state.raw_rows = parse_dataframe(df)
            st.session_state.started = False
            st.success(f"{len(st.session_state.raw_rows)}개 항목을 성공적으로 불러왔습니다.")
        except Exception as e:
            st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
    # (이하 render_setup 함수의 나머지 부분은 이전과 동일합니다)
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
    
    current = my_list[idx] if idx < len(my_list) else None
    next_item = my_list[idx + 1] if idx + 1 < len(my_list) else None

    done_count = len(prog.get('done_ids', set()))
    total = len(my_list)
    pct = int(round((done_count / total) * 100)) if total else 0

    st.title(f"피커 #{pno}")
    st.progress(pct / 100, text=f"{done_count} / {total} ({pct}%)")

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

    def jump_to(new_index):
        st.session_state.progress[pno]['idx'] = max(0, min(new_index, len(my_list) - 1))

    is_done = current and current['id'] in prog.get('done_ids', set())

    # --- [최종 수정] 버튼 로직: HTML 직접 삽입 방식으로 변경 ---
    
    # 1. OK / 완료 취소 버튼 그리기 (이전과 동일)
    if is_done:
        ok_clicked = st.button('완료 취소 ↩️', type='secondary', use_container_width=True)
    else:
        ok_clicked = st.button('OK! ✅', type='primary', use_container_width=True, disabled=not current)

    # 2. 나머지 버튼들을 HTML로 직접 그리기
    # 버튼 클릭을 감지하기 위해 Streamlit의 쿼리 파라미터를 사용합니다.
    st.write(
        """
        <style>
            .btn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px; }
            .btn-grid button { width: 100%; }
        </style>
        <div class="btn-grid">
            <a href="?action=prev" target="_self"><button class="st-emotion-cache-70003y e1nzilvr2">◀ Previous</button></a>
            <a href="?action=next" target="_self"><button class="st-emotion-cache-70003y e1nzilvr2">Next ▶</button></a>
        </div>
        <div class="btn-grid">
            <a href="?action=first_cat" target="_self"><button class="st-emotion-cache-70003y e1nzilvr2">First in Category</button></a>
            <a href="?action=last_cat" target="_self"><button class="st-emotion-cache-70003y e1nzilvr2">Last in Category</button></a>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 3. URL의 쿼리 파라미터를 읽어와서 어떤 버튼이 눌렸는지 확인하고 동작 처리
    query_params = st.query_params
    action = query_params.get("action")

    if action:
        st.query_params.clear() # 처리 후 파라미터 즉시 제거
        if action == "prev":
            jump_to(idx - 1); st.rerun()
        elif action == "next":
            jump_to(idx + 1); st.rerun()
        elif action == "first_cat" and current:
            cat = current['zone']
            for i, r in enumerate(my_list):
                if r['zone'] == cat:
                    jump_to(i); st.rerun(); break
        elif action == "last_cat" and current:
            cat = current['zone']
            for i in range(len(my_list) - 1, -1, -1):
                if my_list[i]['zone'] == cat:
                    jump_to(i); st.rerun(); break

    if ok_clicked and current:
        if is_done:
            prog['done_ids'].remove(current['id'])
        else:
            prog['done_ids'].add(current['id'])
            jump_to(idx + 1)
        st.rerun()

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

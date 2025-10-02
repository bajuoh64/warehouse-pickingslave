import streamlit as st
import pandas as pd
import math

# 1) 페이지/모바일 기본 세팅
st.set_page_config(
    page_title="Warehouse Picking",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2) 전역 스타일 (색/타이포/버튼/고정바)
st.markdown("""
<style>
:root{
  --bg0:#0b1020;
  --bg1:#111827;
  --bg2:#1e293b;
  --card:#0f172a;
  --ok:#16a34a;
  --warn:#f59e0b;
  --note:#fff7bf;
  --accent:#22c55e;
  --err:#ef4444;
}
html,body,[class*="View"]{background:#0a0d17}
.block-container{padding-top:0.8rem; max-width:1200px}
h1,h2,h3,h4{letter-spacing:.2px}
.stButton > button{padding:12px 18px; font-size:18px; border-radius:12px}
div[role="tablist"] *{font-size:16px}
.stDataFrame, .element-container{width:100%}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;background:#111827;color:#fff;font-size:12px}
.kbd{font-family:ui-monospace,Menlo,monospace;background:#0b1222;color:#fff;padding:2px 8px;border-radius:8px}
.card{background:linear-gradient(135deg,#0b1020,#1e293b);color:#fff;padding:14px;border-radius:14px}
.card b{font-weight:800}
.info1{background:#FFD580;color:#111;padding:10px;border-radius:10px}
.info2{background:#FFF2A1;color:#111;padding:10px;border-radius:10px}
.footerbar{position:sticky;bottom:8px;z-index:999;background:transparent}
.footerbar .btn{width:100%;padding:12px 0;border:none;border-radius:12px;color:#fff;font-weight:800}
.btn-first,.btn-last{background:#6b7280}
.btn-prev{background:#475569}
.btn-next{background:#3b82f6}
.btn-ok{background:var(--ok)}
.progress-wrap{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.progress-text{color:#cbd5e1;font-weight:700}
</style>
""", unsafe_allow_html=True)

# 3) 세션 상태
st.session_state.setdefault("progress", {})       # {picker_id: [True/False,...]}
st.session_state.setdefault("current_index", {})  # {picker_id: absolute_idx}
st.session_state.setdefault("num_pickers", 5)
st.session_state.setdefault("uploaded_file", None)

st.title("Warehouse Picking")

# 4) 본문 상단: 모바일 빠른 설정
with st.expander("📱 모바일 빠른 설정", expanded=True):
    st.session_state["num_pickers"] = st.number_input(
        "인원수", min_value=1, value=st.session_state["num_pickers"], step=1, key="num_pickers_main"
    )
    st.session_state["uploaded_file"] = st.file_uploader(
        "파일 선택 (.xlsx)", type=["xlsx"], key="uploaded_file_main"
    )

# 5) 사이드바(PC용)
st.sidebar.header("설정")
num_pickers_sidebar = st.sidebar.number_input(
    "인원수", min_value=1, max_value=50, value=st.session_state["num_pickers"], step=1, key="num_pickers_sidebar"
)
uploaded_file_sidebar = st.sidebar.file_uploader("파일 선택 (엑셀 .xlsx)", type=["xlsx"], key="uploaded_file_sidebar")

if st.sidebar.button("Clear Data", type="primary"):
    st.session_state["progress"] = {}
    st.session_state["current_index"] = {}
    st.session_state["uploaded_file"] = None
    st.session_state["num_pickers"] = 5
    st.rerun()

# 6) 값 통합(모바일/사이드바 중 입력된 값 우선)
num_pickers = int(st.session_state.get("num_pickers", num_pickers_sidebar))
uploaded = st.session_state.get("uploaded_file") or uploaded_file_sidebar

# 7) 업로드 안내
if uploaded is None:
    st.info("좌측 상단 ≡ 를 눌러 사이드바를 열거나, 위의 **모바일 빠른 설정**에서 인원수 설정 후 **엑셀(.xlsx)** 파일을 업로드하세요.")
    st.stop()

# 8) 데이터 읽기
try:
    df = pd.read_excel(uploaded, engine="openpyxl")
except Exception as e:
    st.error(f"엑셀을 읽는 중 오류가 발생했습니다: {e}")
    st.stop()

# 필수 컬럼 검증
required_cols = ["로케이션", "주문수량", "사이즈", "스타일명", "색상명"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"다음 컬럼이 누락되어 있습니다: {', '.join(missing)}")
    st.stop()

# 9) 분배
total_items = len(df)
items_per_picker = math.ceil(total_items / num_pickers) if num_pickers else total_items
spans = [(i * items_per_picker, min((i + 1) * items_per_picker, total_items) - 1) for i in range(num_pickers)]

# 탭 라벨에 진행률 포함
labels = []
for i,(s,e) in enumerate(spans, start=1):
    if e < s:
        labels.append(f"피커 {i} (0%)")
        continue
    total = e - s + 1
    done = sum(st.session_state["progress"].get(i, [False]*total))
    pct = int((done/total)*100) if total else 0
    labels.append(f"피커 {i} ({pct}%)")

tabs = st.tabs(labels)

# 10) 피커 탭 UI
for tab, (picker_id, (s, e)) in zip(tabs, enumerate(spans, start=1)):
    with tab:
        if e < s:
            st.warning("배정 없음")
            continue

        # 상태 준비
        if picker_id not in st.session_state["current_index"]:
            st.session_state["current_index"][picker_id] = s
            st.session_state["progress"][picker_id] = [False] * (e - s + 1)

        cur_idx = st.session_state["current_index"][picker_id]
        cur_idx = max(s, min(e, cur_idx))  # 안전 범위
        done_list = st.session_state["progress"][picker_id]
        total_count = e - s + 1
        done_count = sum(done_list)
        percent = int((done_count / total_count) * 100) if total_count else 100

        # 진행 헤더 + 바
        st.markdown(
            f"""
            <div class="progress-wrap">
              <div class="progress-text">피커 {picker_id} 진행률 : {done_count}/{total_count} ({percent}%)</div>
              <div class="badge">현재 {cur_idx - s + 1} / {total_count}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.progress(percent/100)

        # 현재/다음
        row = df.iloc[cur_idx]
        next_loc = df.iloc[cur_idx+1]["로케이션"] if cur_idx < e else "없음"

        # 상단 상태 카드
        st.markdown(
            f"""
            <div class="card">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <div style="font-weight:800;font-size:18px">피커 #{picker_id}
                  <span class="badge">{cur_idx - s + 1}/{total_count}</span>
                </div>
                <div style="font-weight:800">{percent}%</div>
              </div>
              <div style="margin-top:6px">
                <span style="color:var(--accent);font-weight:800">다음 로케이션</span> :
                <span class="kbd">{next_loc}</span>
              </div>
              <div style="margin-top:4px">
                <span>현재 로케이션</span> :
                <span class="kbd" style="font-size:18px">{row['로케이션']}</span>
              </div>
              <div style="margin-top:4px">
                사이즈 : <b>{row['사이즈']}</b>
                &nbsp;·&nbsp; 수량 : <b style="color:#f87171">{row['주문수량']}</b>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 바코드/색상 + 스타일 카드
        # 스타일명 예: [84785,BLACK GARMENT DYED]W COLLINS ...
        style_raw = str(row["스타일명"])
        barcode_5 = style_raw.split(",")[0].replace("[", "").strip() if "[" in style_raw else ""
        style_actual = style_raw.split("]")[-1].strip() if "]" in style_raw else style_raw

        st.markdown(
            f"""
            <div class="info1" style="margin-top:10px">
              <b>바코드(5)</b> : {barcode_5}
              &nbsp;&nbsp;|&nbsp;&nbsp; <b>색상명</b> : {row['색상명']}
            </div>
            <div class="info2" style="margin-top:6px">
              <b>스타일명</b> : {style_actual}
            </div>
            """,
            unsafe_allow_html=True
        )

        # 하단 고정 버튼 바
        done_now = done_list[cur_idx - s]

        st.markdown('<div class="footerbar">', unsafe_allow_html=True)
        c1,c2,c3,c4,c5 = st.columns([1,1.2,1.6,1.2,1])

        with c1:
            if st.button("First", key=f"first_{picker_id}"):
                st.session_state["current_index"][picker_id] = s
                st.rerun()
        with c2:
            if st.button("Previous", key=f"prev_{picker_id}") and cur_idx > s:
                st.session_state["current_index"][picker_id] -= 1
                st.rerun()
        with c3:
            ok_label = "완료됨" if done_now else "OK"
            ok_help = "현재 항목 완료로 표시하고 다음으로 이동" if not done_now else "이미 완료됨"
            if st.button(ok_label, key=f"ok_{picker_id}", help=ok_help):
                st.session_state["progress"][picker_id][cur_idx - s] = True
                if cur_idx < e:
                    st.session_state["current_index"][picker_id] += 1
                st.rerun()
        with c4:
            if st.button("Next", key=f"next_{picker_id}") and cur_idx < e:
                st.session_state["current_index"][picker_id] += 1
                st.rerun()
        with c5:
            if st.button("Last", key=f"last_{picker_id}"):
                st.session_state["current_index"][picker_id] = e
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        # (선택) 진행 리스트
        with st.expander("배정 리스트 / 진행 상태", expanded=False):
            vis = df.loc[s:e, ["로케이션","주문수량","사이즈","스타일명"]].copy()
            vis.insert(0, "#", range(1, len(vis)+1))
            vis["상태"] = [
                "완료" if (s+i) < s+len(done_list) and done_list[i] else
                ("현재" if (s+i) == cur_idx else "대기")
                for i in range(len(vis))
            ]
            st.dataframe(vis, use_container_width=True)

# 끝

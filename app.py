import React, { useEffect, useMemo, useRef, useState } from "react";
# ✅ 피킹 최적화 웹 애플리케이션 v1.2 — 단일 파일 React 컴포넌트
# 요구사항 반영:
# - 엑셀(xlsx) / CSV 업로드 → JSON 변환 (xlsx 라이브러리)
# - '색상명'에서 바코드/컬러 분리, '스타일명'에서 품번/스타일명 분리
# - 마스터 정렬 기준표(완벽한 동선)로 정렬 후 N명 균등 분배
# - 피커별 화면: 다음 로케이션(녹색, 미리보기) / 현재 로케이션(크게) / 사이즈·수량(수량은 빨간색)
# - 바코드 5자리/컬러명: 노란색 박스, 컬러명 강조
# - 스타일명(제품명) 표시
# - 제어 버튼: [OK!] / [Previous] [Next] / [First in Category] [Last in Category]
# - 메인(설정) 화면: 업로드, 인원 선택(1~6), 시작, Clear Data
# - 진행 상태: 로컬 저장(LocalStorage). 피커 번호는 URL 쿼리 ?picker=1 로 접속해도 설정됨.
# - iPhone Safari 고려: 큰 터치 타겟, 시스템 폰트, 헤더 고정, 3D Touch 이슈 회피.

# ⚠️ 주의: 이 파일은 ChatGPT Canvas 미리보기 기준으로 작성되었습니다. 빌드 환경에서는
#   `npm install xlsx` 후 사용하세요. (Canvas에서는 가정상 사용 가능)
import * as XLSX from "xlsx";

export default function App() {
  // --------- 전역 상태 ---------
  const [rawRows, setRawRows] = useState([]); // 업로드 직후 원본(정렬 전)
  const [sortedRows, setSortedRows] = useState([]); // 마스터 동선 정렬 후
  const [pickers, setPickers] = useState(1); // 인원 수
  const [started, setStarted] = useState(false); // 피킹 시작 여부

  // 피커 선택(메인/진행 화면 공통). URL ?picker=1 우선, 없으면 state 사용
  const [pickerNo, setPickerNo] = useState(1);

  // 피커별 진행 인덱스와 완료 상태 (로컬)
  const [progressByPicker, setProgressByPicker] = useState({}); // {1:{idx:0, doneIds:Set([...])}, ...}

  const fileInputRef = useRef(null);

  // --------- LocalStorage Load ---------
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("pick_opt_v12_state") || "null");
      if (saved) {
        setRawRows(saved.rawRows || []);
        setSortedRows(saved.sortedRows || []);
        setPickers(saved.pickers || 1);
        setStarted(!!saved.started);
        setProgressByPicker(reviveProgress(saved.progressByPicker || {}));
        if (saved.pickerNo) setPickerNo(saved.pickerNo);
      }
    } catch {}
  }, []);

  // URL 쿼리에서 picker= 추출
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const p = Number(params.get("picker"));
    if (p && p >= 1 && p <= 6) setPickerNo(p);
  }, []);

  // --------- LocalStorage Save ---------
  useEffect(() => {
    try {
      localStorage.setItem(
        "pick_opt_v12_state",
        JSON.stringify({
          rawRows,
          sortedRows,
          pickers,
          started,
          pickerNo,
          progressByPicker: serializeProgress(progressByPicker),
        })
      );
    } catch {}
  }, [rawRows, sortedRows, pickers, started, pickerNo, progressByPicker]);

  // --------- 마스터 정렬 기준표 (동선) ---------
  // 예시: 로케이션 접두/구역을 순서로 나열. 실제 창고 동선에 맞게 자유롭게 수정 가능.
  const MASTER_ORDER = useMemo(
    () => [
      // 1층
      "1FA", "1FB", "1FC", "1FD", "1FE", "1FF", "1FG", "1FH",
      // CC(카운터/캐시 근처)
      "CC",
      // 2층
      "2MA", "2MB", "2MC", "2MD", "2ME",
      // 3층 일반
      "3MA", "3MB", "3MC", "3MD", "3ME", "3MF", "3MG", "3MH",
      // DECK / 악세사리 / 기타
      "DECK", "ACC", "ETC"
    ],
    []
  );

  // 로케이션에서 카테고리/구역 키 추출
  function getZone(loc) {
    const s = String(loc || "").toUpperCase();
    // 접두 3~4자 추출 (예: 1FC12 → 1FC, 3MH-07 → 3MH)
    const m = s.match(/^[A-Z0-9]{3,4}/);
    return m ? m[0] : s || "";
  }

  // 마스터 정렬용 키 생성
  function sortKeyByMaster(row) {
    const z = getZone(row.location);
    const base = MASTER_ORDER.indexOf(z);
    const rank = base === -1 ? 999 : base; // 목록에 없으면 뒤로
    // 같은 구역 내에서는 로케이션 코드의 숫자/문자 기준으로 2차 정렬
    return `${String(rank).padStart(3, "0")}-${String(row.location || "").padStart(10, "0")}`;
  }

  // --------- 엑셀/CSV 파서 ---------
  function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    const isXlsx = /\.xlsx?$/i.test(file.name);

    reader.onload = () => {
      try {
        let rows = [];
        if (isXlsx) {
          const wb = XLSX.read(reader.result, { type: "array" });
          const ws = wb.Sheets[wb.SheetNames[0]];
          rows = XLSX.utils.sheet_to_json(ws, { defval: "" });
        } else {
          // CSV
          const text = new TextDecoder("utf-8").decode(reader.result);
          rows = parseCSV(text);
        }
        const normalized = rows.map((r, i) => normalizeRow(r, i));
        setRawRows(normalized);
        setStarted(false);
      } catch (err) {
        alert("파일 파싱 중 오류가 발생했습니다.\n" + err.message);
      }
    };

    if (isXlsx) reader.readAsArrayBuffer(file);
    else reader.readAsArrayBuffer(file); // CSV도 ArrayBuffer로 받아 수동 디코딩
  }

  // 헤더 키 정규화 유틸
  function keyOf(obj, candidates) {
    const keys = Object.keys(obj);
    for (const raw of keys) {
      const k = String(raw).toLowerCase().replace(/\s+/g, "");
      if (candidates.includes(k)) return raw; // 원본 키 반환
    }
    return null;
  }

  // '색상명' → "78681,BLACK/WHITE" 형식 파싱
  function splitBarcodeColor(v) {
    const s = String(v || "").trim();
    if (!s) return { color: "", barcode5: "" };
    // 앞 5자리 숫자 + 콤마 + 컬러명 패턴 우선
    const m = s.match(/^(\d{5})[,\-\s]*(.+)$/);
    if (m) return { barcode5: m[1], color: m[2].trim() };
    // 숫자 5자리만 있는 경우
    if (/^\d{5}$/.test(s)) return { barcode5: s, color: "" };
    // 컬러명만 있는 경우
    return { barcode5: "", color: s };
  }

  // '스타일명' → "[41303,MULTI]DEUS ..." 형식 파싱
  function splitStyle(v) {
    const s = String(v || "").trim();
    if (!s) return { styleCode: "", styleName: "" };
    const m = s.match(/^\[(\d+)[^\]]*\](.*)$/);
    if (m) return { styleCode: m[1], styleName: m[2].trim() };
    return { styleCode: "", styleName: s };
  }

  function normalizeRow(r, i) {
    // 다양한 헤더 대응 (한국어/영어 혼용)
    const kLocation = keyOf(r, ["location", "로케이션", "bin", "shelf", "loc", "위치"]);
    const kQty = keyOf(r, ["qty", "수량", "quantity"]);
    const kSize = keyOf(r, ["size", "사이즈"]);
    const kColorName = keyOf(r, ["색상명", "colorname", "color", "색상"]);
    const kStyleName = keyOf(r, ["스타일명", "stylename", "product", "제품명", "name"]);
    const kBarcode = keyOf(r, ["barcode", "바코드", "upc", "ean"]);

    const location = (r[kLocation] ?? "").toString().trim();
    const qty = String(r[kQty] ?? "1").toString().trim() || "1";
    const size = (r[kSize] ?? "").toString().trim();

    // 색상명에서 바코드5/컬러 분리 (없으면 별도로 바코드 컬럼 사용)
    const { barcode5: bc5_from_color, color } = splitBarcodeColor(r[kColorName]);
    let barcode5 = bc5_from_color;

    // 스타일명에서 품번/스타일명 분리
    const { styleCode, styleName } = splitStyle(r[kStyleName]);

    // 별도 바코드 컬럼이 있으면 우선 사용 → 5자리만 취득
    const rawBarcode = (r[kBarcode] ?? "").toString().trim();
    if (rawBarcode) {
      const m = rawBarcode.match(/(\d{5})/);
      if (m) barcode5 = m[1];
    }

    return {
      id: i,
      location,
      qty,
      size,
      color,
      barcode5,
      styleCode,
      styleName,
      // 구역 키
      zone: getZone(location),
    };
  }

  // CSV 파싱 (간단 처리)
  function parseCSV(text) {
    const lines = text.split(/\r?\n/).filter((l) => l.trim().length);
    if (!lines.length) return [];
    const headers = splitCSVLine(lines[0]);
    const rows = [];
    for (let i = 1; i < lines.length; i++) {
      const cols = splitCSVLine(lines[i]);
      const row = {};
      headers.forEach((h, idx) => (row[h] = cols[idx] ?? ""));
      rows.push(row);
    }
    return rows;
  }

  function splitCSVLine(line) {
    const out = [];
    let cur = "";
    let q = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"') {
        if (q && line[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          q = !q;
        }
      } else if (ch === "," && !q) {
        out.push(cur);
        cur = "";
      } else {
        cur += ch;
      }
    }
    out.push(cur);
    return out;
  }

  // --------- 시작: 정렬 & 분배 ---------
  const distributed = useMemo(() => {
    if (!rawRows.length) return [];
    // 마스터 정렬
    const sorted = [...rawRows].sort((a, b) => (sortKeyByMaster(a) < sortKeyByMaster(b) ? -1 : 1));
    setSortedRows(sorted);

    // N명 균등 분배 (라운드로빈 대신 구간 나누기 — 동선 끊김 최소화)
    const n = Math.max(1, Math.min(6, pickers || 1));
    const per = Math.ceil(sorted.length / n);
    const packs = Array.from({ length: n }, (_, i) => sorted.slice(i * per, (i + 1) * per));
    return packs;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rawRows, pickers, started]);

  // 현재 피커의 리스트
  const myList = useMemo(() => {
    if (!distributed.length) return [];
    const idx = Math.max(1, Math.min(pickers, pickerNo)) - 1;
    return distributed[idx] || [];
  }, [distributed, pickers, pickerNo]);

  const myProg = progressByPicker[pickerNo] || { idx: 0, doneIds: new Set() };
  const myIdx = Math.max(0, Math.min((myList.length || 1) - 1, myProg.idx || 0));
  const current = myList[myIdx] || null;
  const nextItem = myList[myIdx + 1] || null;

  const doneCount = myList.filter((r) => myProg.doneIds?.has?.(r.id)).length;

  // --------- 이벤트 핸들러 ---------
  function startPicking() {
    if (!rawRows.length) return alert("파일을 먼저 업로드하세요.");
    if (!pickers) return alert("작업자 수를 선택하세요.");
    // 진행 상태 초기화
    const init = {};
    for (let p = 1; p <= pickers; p++) init[p] = { idx: 0, doneIds: new Set() };
    setProgressByPicker(init);
    setStarted(true);
  }

  function markOk() {
    if (!current) return;
    const next = cloneProgress(progressByPicker);
    const me = next[pickerNo] || { idx: 0, doneIds: new Set() };
    me.doneIds.add(current.id);
    me.idx = Math.min(myIdx + 1, Math.max(0, myList.length - 1));
    next[pickerNo] = me;
    setProgressByPicker(next);
    // 모바일 진동
    if (navigator.vibrate) navigator.vibrate(30);
  }

  function goPrev() {
    const next = cloneProgress(progressByPicker);
    const me = next[pickerNo] || { idx: 0, doneIds: new Set() };
    me.idx = Math.max(0, myIdx - 1);
    next[pickerNo] = me;
    setProgressByPicker(next);
  }

  function goNext() {
    const next = cloneProgress(progressByPicker);
    const me = next[pickerNo] || { idx: 0, doneIds: new Set() };
    me.idx = Math.min(myIdx + 1, Math.max(0, myList.length - 1));
    next[pickerNo] = me;
    setProgressByPicker(next);
  }

  function jumpFirstInCategory() {
    if (!current) return;
    const cat = current.zone;
    const pos = myList.findIndex((r) => r.zone === cat);
    if (pos >= 0) jumpTo(pos);
  }

  function jumpLastInCategory() {
    if (!current) return;
    const cat = current.zone;
    // 뒤에서 찾기
    for (let i = myList.length - 1; i >= 0; i--) {
      if (myList[i].zone === cat) return jumpTo(i);
    }
  }

  function jumpTo(i) {
    const next = cloneProgress(progressByPicker);
    const me = next[pickerNo] || { idx: 0, doneIds: new Set() };
    me.idx = Math.max(0, Math.min(i, Math.max(0, myList.length - 1)));
    next[pickerNo] = me;
    setProgressByPicker(next);
  }

  function clearData() {
    if (!confirm("모든 데이터를 초기화하고 시작 화면으로 돌아갈까요?")) return;
    setRawRows([]);
    setSortedRows([]);
    setPickers(1);
    setStarted(false);
    setProgressByPicker({});
  }

  function onPickersButton(n) {
    setPickers(n);
    if (pickerNo > n) setPickerNo(n);
  }

  // --------- 렌더 ---------
  if (!started) {
    return (
      <div className="min-h-screen bg-white text-gray-900">
        <Header title="피킹 최적화 웹앱 v1.2" />
        <main className="mx-auto max-w-xl px-4 py-6">
          <div className="rounded-2xl border shadow-sm p-5">
            <h2 className="text-lg font-bold mb-3">파일 업로드</h2>
            <div className="flex items-center gap-2">
              <button
                className="btn-secondary"
                onClick={() => fileInputRef.current?.click()}
              >파일 선택</button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls,.csv"
                className="hidden"
                onChange={handleFile}
              />
              <span className="text-sm text-gray-600 truncate">
                {rawRows.length ? `${rawRows.length}개 항목 로드됨` : "xlsx 또는 csv 파일을 선택하세요"}
              </span>
            </div>

            <div className="h-px bg-gray-200 my-5" />

            <h2 className="text-lg font-bold mb-2">작업자 수 선택</h2>
            <div className="grid grid-cols-6 gap-2">
              {[1, 2, 3, 4, 5, 6].map((n) => (
                <button key={n} className={`btn-number ${pickers === n ? "active" : ""}`} onClick={() => onPickersButton(n)}>
                  {n}
                </button>
              ))}
            </div>

            <div className="mt-3 text-sm text-gray-600">
              피커 번호 선택: 
              {[...Array(pickers)].map((_, i) => (
                <button
                  key={i}
                  className={`ml-2 underline ${pickerNo === i + 1 ? "font-bold" : ""}`}
                  onClick={() => setPickerNo(i + 1)}
                >#{i + 1}</button>
              ))}
              <span className="ml-2 text-gray-500">(또는 URL에 ?picker={"<번호>"})</span>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-2">
              <button className="btn-primary" onClick={startPicking} disabled={!rawRows.length}>피킹 시작하기</button>
              <button className="btn-ghost" onClick={clearData}>Clear Data</button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // 진행 화면
  const total = myList.length;
  const progressPct = total ? Math.round((doneCount / total) * 100) : 0;

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <Header title={`피커 #${pickerNo} · ${doneCount}/${total} (${progressPct}%)`} />
      <main className="mx-auto max-w-xl px-4 py-6">
        <div className="rounded-2xl border shadow-sm p-5">
          {/* 다음 로케이션 미리보기 */}
          <div className="text-sm font-medium text-emerald-600 mb-2">
            다음 제품 로케이션: {nextItem?.location || "-"}
          </div>

          {/* 현재 로케이션 크게 */}
          <div className="text-3xl font-extrabold tracking-tight mb-1 break-words">
            {current?.location || "-"}
          </div>

          {/* 사이즈/수량 */}
          <div className="text-base mb-3">
            <span className="font-medium">사이즈</span>: {current?.size || "-"}
            <span className="inline-block w-3" />
            <span className="font-medium">수량</span>: <span className="text-red-600 font-bold">{current?.qty || "1"}</span>
          </div>

          {/* 노란 박스: 바코드5/컬러명 (컬러 강조) */}
          <div className="rounded-xl border bg-yellow-100 px-3 py-2 mb-3">
            <div className="text-sm">바코드 5자리: <span className="font-mono font-bold tracking-wide">{current?.barcode5 || ""}</span></div>
            <div className="text-base font-bold">컬러: {current?.color || "-"}</div>
          </div>

          {/* 스타일명 */}
          <div className="text-sm text-gray-700 mb-3">
            <span className="font-medium">스타일명</span>: {current?.styleName || "-"}
            {current?.styleCode ? <span className="text-gray-500">  (코드 {current.styleCode})</span> : null}
          </div>

          {/* 버튼들 */}
          <div className="grid grid-cols-1 gap-2 mb-2">
            <button className="btn-primary h-14 text-lg" onClick={markOk}>OK!</button>
          </div>
          <div className="grid grid-cols-2 gap-2 mb-2">
            <button className="btn-secondary" onClick={goPrev}>Previous</button>
            <button className="btn-secondary" onClick={goNext}>Next</button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button className="btn-ghost" onClick={jumpFirstInCategory}>First in Category</button>
            <button className="btn-ghost" onClick={jumpLastInCategory}>Last in Category</button>
          </div>
        </div>

        <div className="mt-4 text-center">
          <button className="text-sm text-gray-600 underline" onClick={clearData}>초기화 및 나가기</button>
        </div>
      </main>

      {/* 간단 스타일 */}
      <style>{`
        * { -webkit-tap-highlight-color: transparent; }
        .btn-primary { background:#111; color:#fff; border-radius:14px; padding:12px 16px; font-weight:700; border:1px solid #111; }
        .btn-primary:active { transform: translateY(1px); }
        .btn-secondary { background:#fff; color:#111; border-radius:14px; padding:12px 16px; font-weight:700; border:1px solid #d1d5db; }
        .btn-secondary:active { transform: translateY(1px); }
        .btn-ghost { background:#fff; color:#111; border-radius:14px; padding:12px 16px; font-weight:600; border:1px dashed #d1d5db; }
        .btn-number { border-radius:12px; padding:10px 0; border:1px solid #d1d5db; font-weight:700; background:#fff; }
        .btn-number.active { background:#111; color:#fff; border-color:#111; }
        header.sticky { position:sticky; top:0; background:rgba(255,255,255,.92); backdrop-filter: saturate(180%) blur(6px); border-bottom:1px solid #e5e7eb; z-index:10; }
      `}</style>
    </div>
  );
}

function Header({ title }) {
  return (
    <header className="sticky">
      <div className="mx-auto max-w-xl px-4 py-3 flex items-center justify-between">
        <div className="text-lg font-bold">📦 Picking</div>
        <div className="text-sm text-gray-700">{title}</div>
      </div>
    </header>
  );
}

// --------- 진행 상태 직렬화 유틸 ---------
function serializeProgress(obj) {
  const out = {};
  for (const k of Object.keys(obj)) {
    out[k] = { idx: obj[k].idx || 0, doneIds: Array.from(obj[k].doneIds || []) };
  }
  return out;
}
function reviveProgress(obj) {
  const out = {};
  for (const k of Object.keys(obj)) {
    out[k] = { idx: obj[k].idx || 0, doneIds: new Set(obj[k].doneIds || []) };
  }
  return out;
}
function cloneProgress(obj) {
  const out = {};
  for (const k of Object.keys(obj)) {
    out[k] = { idx: obj[k].idx, doneIds: new Set(obj[k].doneIds) };
  }
  return out;
}

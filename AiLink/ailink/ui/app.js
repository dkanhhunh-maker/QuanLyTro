/* AiLink — giao diện. Chỉ vẽ và gửi lệnh; mọi việc chạy nằm trong lõi Python. */
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const clone = o => JSON.parse(JSON.stringify(o));
const NODE_W = 196, PORT_Y0 = 21.5, PORT_DY = 18;
const TT = {cho: "chờ", dang_chay: "đang chạy", xong: "xong", loi: "lỗi", bo_qua: "bỏ qua", cho_duyet: "chờ anh duyệt"};
const TT_LAN = {moi: "mới", dang_chay: "đang chạy", xong: "xong", loi: "có lỗi", cho_duyet: "chờ duyệt", can_xem: "cần xem", dung_chi_phi: "dừng vì chạm trần chi phí"};
const KHONG_VAO = new Set(["bat_dau", "hen_gio"]);
const MOI = new Set(["bao_cao_ai", "kiem_duyet", "tom_tat", "phan_loai", "phan_tich_doi_thu", "tra_loi_binh_luan"]);

let META = {}, NHOM = {}, KENH = [], DOI = {}, CAI_DAT = {}, DS_SO_DO = [];
let flow = null, flowSrc = null;           // sơ đồ đang mở
let run = null;                             // {id, st, dang_chay}
let rt = {};                                // trạng thái chạy theo node id
let sel = null;                             // {kind:'node',id} | {kind:'wire',i}
let z = 1;

async function api(path, body) {
  const opt = body === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json", "X-AiLink": "1"}, body: JSON.stringify(body)};
  const r = await fetch(path, opt);
  return r.json();
}
function toast(msg, kind = "") {
  const t = $("#toast");
  t.textContent = Array.isArray(msg) ? msg.join("\n") : msg;
  t.className = "toast " + kind; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => t.hidden = true, kind === "loi" ? 9000 : 3500);
}

/* ================= chủ đề ================= */
function apDungChuDe() {
  const v = $("#chu-de").value;
  let t = v;
  if (v === "tu_dong") { const h = new Date().getHours(); t = h >= 6 && h < 18 ? "studio" : "neon"; }
  document.documentElement.dataset.theme = t;
}
$("#chu-de").onchange = () => {
  try { localStorage.setItem("ailink_chu_de", $("#chu-de").value); } catch (e) {}
  api("/api/cai_dat", {chu_de: $("#chu-de").value});
  apDungChuDe(); veDay();
};
setInterval(apDungChuDe, 600000);

/* ================= tab ================= */
function moTab(t) {
  $$(".tab").forEach(b => b.setAttribute("aria-selected", b.dataset.tab === t));
  $$(".page").forEach(p => p.hidden = p.id !== "p-" + t);
  if (t === "duyet") taiDuyet();
  if (t === "kenh") veKenh();
  if (t === "lich_su") taiLichSu();
  if (t === "doi_ai") veDoiAI();
  if (t === "cai_dat") veCaiDat();
  if (t === "so_do") veTatCa();
}
$$(".tab").forEach(b => b.onclick = () => moTab(b.dataset.tab));

/* ================= bảng node ================= */
function veBangNode() {
  const q = $("#tim-node").value.trim().toLowerCase();
  let h = "";
  for (const [k, g] of Object.entries(NHOM)) {
    const ds = Object.values(META).filter(n => n.nhom === k && (!q || (n.ten + " " + n.loai + " " + n.mo_ta + " " + n.vi_du).toLowerCase().includes(q)));
    if (!ds.length) continue;
    h += `<div class="pal-group"><h4><span class="pal-dot" style="background:var(--g-${g.mau})"></span>${esc(g.ten)}</h4>`;
    for (const n of ds)
      h += `<div class="pal-item" draggable="true" data-loai="${n.loai}" title="${esc(n.mo_ta + "\n\nVí dụ: " + n.vi_du)}"><span class="nm">${esc(n.ten)}</span>${MOI.has(n.loai) ? '<span class="tag moi">mới</span>' : ""}${n.gia_lap ? '<span class="tag">giả lập</span>' : ""}</div>`;
    h += "</div>";
  }
  $("#ds-node").innerHTML = h || '<p class="muted">Không thấy node nào.</p>';
}
$("#tim-node").oninput = veBangNode;
$("#ds-node").addEventListener("dragstart", e => { const it = e.target.closest(".pal-item"); if (it) e.dataTransfer.setData("text/ailink", it.dataset.loai); });
$("#ds-node").addEventListener("click", e => { const it = e.target.closest(".pal-item"); if (it) themNode(it.dataset.loai); });
$("#cv-wrap").addEventListener("dragover", e => e.preventDefault());
$("#cv-wrap").addEventListener("drop", e => {
  const loai = e.dataTransfer.getData("text/ailink"); if (!loai) return;
  e.preventDefault(); const p = toaDo(e); themNode(loai, p.x - 90, p.y - 15);
});

function idMoi(loai) {
  let base = loai.replace(/^_+/, ""), id = base, i = 2;
  while (flow.nodes.some(n => n.id === id)) id = base + "_" + (i++);
  return id;
}
function themNode(loai, x, y) {
  if (!flow) return;
  if (x === undefined) {
    const w = $("#cv-wrap");
    x = (w.scrollLeft + w.clientWidth / 2) / z - 98; y = (w.scrollTop + w.clientHeight / 2) / z - 40;
  }
  const n = {id: idMoi(loai), loai, cai_dat: clone(META[loai].cai_dat_mau || {}), vi_tri: [Math.round(x), Math.round(y)]};
  flow.nodes.push(n);
  sel = {kind: "node", id: n.id};
  veTatCa();
}

/* ================= sơ đồ ================= */
function congRa(n) {
  if (n.loai === "phan_loai") return [...(n.cai_dat.nhan || []), "khac"];
  return (META[n.loai] || {}).cong || null;
}
function nodeById(id) { return flow.nodes.find(n => n.id === id); }
function laLui(d) { return d.lap_toi_da !== undefined && d.lap_toi_da !== null; }
function toi(tu, den) { // den đi tới được tu qua dây tiến?
  const seen = new Set([den]), q = [den];
  while (q.length) {
    const x = q.pop(); if (x === tu) return true;
    for (const d of flow.day) if (!laLui(d) && d.tu === x && !seen.has(d.den)) { seen.add(d.den); q.push(d.den); }
  }
  return false;
}
function tuDongXep() {
  const sau = {}; flow.nodes.forEach(n => sau[n.id] = 0);
  for (let k = 0; k < flow.nodes.length; k++)
    for (const d of flow.day) if (!laLui(d) && sau[d.den] < sau[d.tu] + 1) sau[d.den] = sau[d.tu] + 1;
  const dem = {};
  flow.nodes.forEach(n => {
    if (n.vi_tri) return;
    const c = sau[n.id]; dem[c] = (dem[c] || 0) + 1;
    n.vi_tri = [40 + c * 240, 40 + (dem[c] - 1) * 150];
  });
}
function chieuCao(n) { const c = congRa(n); return Math.max(96, 58 + (c ? c.length : 1) * PORT_DY); }
function diemRa(n, cong) {
  const c = congRa(n); const i = c ? Math.max(0, c.indexOf(cong)) : 0;
  return {x: n.vi_tri[0] + NODE_W, y: n.vi_tri[1] + PORT_Y0 + i * PORT_DY};
}
function diemVao(n) { return {x: n.vi_tri[0], y: n.vi_tri[1] + PORT_Y0}; }
function duongCong(a, b, lui) {
  if (lui) {
    const yd = Math.max(a.y, b.y) + 110;
    return `M${a.x},${a.y} C${a.x + 90},${a.y} ${a.x + 90},${yd} ${(a.x + b.x) / 2},${yd} S${b.x - 90},${b.y} ${b.x},${b.y}`;
  }
  const dx = Math.max(50, Math.abs(b.x - a.x) / 2);
  return `M${a.x},${a.y} C${a.x + dx},${a.y} ${b.x - dx},${b.y} ${b.x},${b.y}`;
}
function mauNhom(loai) { const m = META[loai]; return m ? `var(--g-${NHOM[m.nhom].mau})` : "var(--g-xam)"; }

function htmlNode(n) {
  const m = META[n.loai] || {ten: n.loai, nhom: "tien_ich"};
  const r = rt[n.id] || {};
  const tt = r.trang_thai || "cho";
  const c = congRa(n);
  let ports = KHONG_VAO.has(n.loai) ? "" : `<span class="port in" data-in="${esc(n.id)}" title="vào"></span>`;
  (c || [null]).forEach((p, i) => {
    const y = PORT_Y0 - 6.5 + i * PORT_DY;
    ports += `<span class="port out" style="top:${y}px" data-out="${esc(n.id)}" data-cong="${esc(p ?? "")}" title="${esc(p ?? "ra")}"></span>`;
    if (p) ports += `<span class="plabel" style="top:${y}px">${esc(p)}</span>`;
  });
  const items = r.items ? Object.values(r.items) : null;
  const itemTxt = items ? ` · ${items.filter(x => x === "xong").length}/${items.length}` : "";
  const ghiChu = r.loi || r.ghi_chu || (r.cong ? "→ " + r.cong : "");
  return `<div class="nhead"><span class="ico">${esc((NHOM[m.nhom] || {ten: "?"}).ten[0])}</span><span class="tt">${esc(m.ten)}</span></div>
    <div class="nbody"><span class="nid">${esc(n.id)}${m.gia_lap ? '<span class="tag">giả lập</span>' : ""}</span>
    <span class="nst">${TT[tt] || tt}${itemTxt}${r.tu_cache ? " · cache" : ""}</span>
    ${ghiChu ? `<span class="ngc">${esc(String(ghiChu).slice(0, 90))}</span>` : ""}
    <div class="pin"><i></i></div></div>${ports}`;
}
function veNodes() {
  const cv = $("#cv");
  $$(".node", cv).forEach(e => e.remove());
  if (!flow) return;
  for (const n of flow.nodes) {
    const el = document.createElement("div");
    const tt = (rt[n.id] || {}).trang_thai || "cho";
    el.className = `node ${tt}${sel && sel.kind === "node" && sel.id === n.id ? " sel" : ""}`;
    el.dataset.id = n.id;
    el.style.cssText = `left:${n.vi_tri[0]}px;top:${n.vi_tri[1]}px;min-height:${chieuCao(n)}px;--c:${mauNhom(n.loai)}`;
    el.innerHTML = htmlNode(n);
    cv.appendChild(el);
  }
}
function capNhatNode(id) {
  const el = $(`.node[data-id="${CSS.escape(id)}"]`); const n = nodeById(id);
  if (!el || !n) return;
  const tt = (rt[id] || {}).trang_thai || "cho";
  el.className = `node ${tt}${sel && sel.kind === "node" && sel.id === id ? " sel" : ""}`;
  el.innerHTML = htmlNode(n);
}
function trangThaiDay(d) {
  const u = rt[d.tu], v = rt[d.den];
  if (!u) return "";
  if (u.trang_thai === "xong") {
    if (d.cong && u.cong && d.cong !== u.cong) return "chet";
    if (laLui(d)) return "";
    if (v && v.trang_thai === "dang_chay") return "sac";
    return "song";
  }
  if (u.trang_thai === "bo_qua") return "chet";
  if (u.trang_thai === "loi") return "chan";
  return "";
}
function veDay(tam) {
  if (!flow) { $("#wires").innerHTML = ""; return; }
  let h = "";
  const demLap = (run && run.st && run.st.dem_lap) || {};
  flow.day.forEach((d, i) => {
    const u = nodeById(d.tu), v = nodeById(d.den); if (!u || !v) return;
    const a = diemRa(u, d.cong), b = diemVao(v), lui = laLui(d);
    const p = duongCong(a, b, lui), st = trangThaiDay(d), wc = mauNhom(u.loai);
    const chon = sel && sel.kind === "wire" && sel.i === i ? " sel" : "";
    h += `<path class="hit" d="${p}" data-wire="${i}"/><path class="vis ${lui ? "lui" : ""} ${st}${chon}" style="--wc:${wc}" d="${p}"/>`;
    if (st === "sac") {
      h += `<path class="dien" style="--wc:${wc}" d="${p}"/><circle class="tia" r="4" style="--wc:${wc}"><animateMotion dur="0.9s" repeatCount="indefinite" path="${p}"/></circle>`;
    }
    if (lui) {
      const k = `${d.tu}:${d.cong || ""}>${d.den}`;
      const yd = Math.max(a.y, b.y) + 92;
      h += `<text x="${(a.x + b.x) / 2 - 24}" y="${yd}">↺ ${demLap[k] || 0}/${d.lap_toi_da}</text>`;
    }
  });
  if (tam) h += `<path class="tmp" d="${duongCong(tam.a, tam.b)}"/>`;
  $("#wires").innerHTML = h;
}
function veTatCa() { veNodes(); veDay(); veInspector(); capNhatZoom(); }

/* ---- toạ độ, kéo thả, nối dây ---- */
function toaDo(e) { const r = $("#cv").getBoundingClientRect(); return {x: (e.clientX - r.left) / z, y: (e.clientY - r.top) / z}; }
let keo = null;
$("#cv").addEventListener("pointerdown", e => {
  const out = e.target.closest(".port.out");
  if (out) {
    keo = {kind: "day", tu: out.dataset.out, cong: out.dataset.cong || null};
    out.setPointerCapture(e.pointerId); e.preventDefault(); return;
  }
  const head = e.target.closest(".nhead");
  const nodeEl = e.target.closest(".node");
  if (nodeEl) {
    const n = nodeById(nodeEl.dataset.id);
    if (!sel || sel.kind !== "node" || sel.id !== n.id) { sel = {kind: "node", id: n.id}; $$(".node.sel").forEach(x => x.classList.remove("sel")); nodeEl.classList.add("sel"); veInspector(); veDay(); }
    if (head) { const p = toaDo(e); keo = {kind: "node", n, el: nodeEl, dx: p.x - n.vi_tri[0], dy: p.y - n.vi_tri[1]}; head.setPointerCapture(e.pointerId); }
    return;
  }
  const w = e.target.closest("[data-wire]");
  if (w) { sel = {kind: "wire", i: +w.dataset.wire}; veDay(); veNodes(); veInspector(); return; }
  if (sel) { sel = null; veNodes(); veDay(); veInspector(); }
});
$("#cv").addEventListener("pointermove", e => {
  if (!keo) return;
  const p = toaDo(e);
  if (keo.kind === "node") {
    keo.n.vi_tri = [Math.max(0, Math.round(p.x - keo.dx)), Math.max(0, Math.round(p.y - keo.dy))];
    keo.el.style.left = keo.n.vi_tri[0] + "px"; keo.el.style.top = keo.n.vi_tri[1] + "px"; veDay();
  } else veDay({a: diemRa(nodeById(keo.tu), keo.cong), b: p});
});
$("#cv").addEventListener("pointerup", e => {
  if (!keo) return;
  if (keo.kind === "day") {
    const t = document.elementFromPoint(e.clientX, e.clientY);
    const vao = t && t.closest && (t.closest(".port.in") || t.closest(".node"));
    const den = vao && (vao.dataset.in || vao.dataset.id);
    if (den && !KHONG_VAO.has(nodeById(den).loai)) noiDay(keo.tu, keo.cong, den);
    veDay();
  }
  keo = null;
});
function noiDay(tu, cong, den) {
  if (flow.day.some(d => d.tu === tu && d.den === den && (d.cong || null) === cong)) return;
  const d = {tu, den}; if (cong) d.cong = cong;
  if (tu === den || toi(tu, den)) { d.lap_toi_da = 3; toast("Dây quay ngược = vòng lặp, tối đa 3 lần (sửa ở khung bên phải)."); }
  flow.day.push(d);
  sel = {kind: "wire", i: flow.day.length - 1};
  veDay(); veInspector();
}
document.addEventListener("keydown", e => {
  if (e.key !== "Delete" || !sel || ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) return;
  xoaDangChon();
});
function xoaDangChon() {
  if (!sel) return;
  if (sel.kind === "node") { flow.nodes = flow.nodes.filter(n => n.id !== sel.id); flow.day = flow.day.filter(d => d.tu !== sel.id && d.den !== sel.id); }
  else flow.day.splice(sel.i, 1);
  sel = null; veTatCa();
}

/* ---- zoom ---- */
function capNhatZoom() { $("#cv").style.transform = `scale(${z})`; $("#cv").style.marginBottom = `${-1800 * (1 - z)}px`; $("#cv").style.marginRight = `${-3200 * (1 - z)}px`; veDay(); }
$("#zoom-to").onclick = () => { z = Math.min(1.5, z + 0.1); capNhatZoom(); };
$("#zoom-nho").onclick = () => { z = Math.max(0.35, z - 0.1); capNhatZoom(); };
$("#zoom-vua").onclick = vuaKhung;
function vuaKhung() {
  if (!flow || !flow.nodes.length) return;
  const xs = flow.nodes.map(n => n.vi_tri[0]), ys = flow.nodes.map(n => n.vi_tri[1]);
  const w = Math.max(...xs) - Math.min(...xs) + NODE_W + 80, h = Math.max(...ys) - Math.min(...ys) + 260;
  const wr = $("#cv-wrap");
  z = Math.max(0.75, Math.min(1.1, Math.min(wr.clientWidth / w, wr.clientHeight / h)));
  capNhatZoom();
  wr.scrollLeft = (Math.min(...xs) - 40) * z; wr.scrollTop = (Math.min(...ys) - 40) * z;
}

/* ================= khung bên phải ================= */
const CAI_DAT_AI = ["ai", "che_do", "du_phong", "vai"];
const TRUONG_DAI = new Set(["lenh", "he_thong", "noi_dung", "cau_hoi"]);
function laNodeAI(n) { const m = META[n.loai]; return m && ["chu", "phan_tich"].includes(m.nhom) || ["kiem_duyet", "dieu_kien"].includes(n.loai); }
function hienGiaTri(v) { return typeof v === "string" ? v : JSON.stringify(v, null, 2); }

function veInspector() {
  const el = $("#inspector");
  if (!flow) { el.innerHTML = ""; return; }
  if (sel && sel.kind === "node" && nodeById(sel.id)) return veInspNode(el, nodeById(sel.id));
  if (sel && sel.kind === "wire" && flow.day[sel.i]) return veInspDay(el, flow.day[sel.i]);
  veInspSoDo(el);
}
function veInspSoDo(el) {
  let h = `<h3>Sơ đồ</h3><label>Tên</label><input type="text" id="sd-ten" value="${esc(flow.ten || "")}">
    <label>Mô tả</label><textarea id="sd-mo-ta">${esc(flow.mo_ta || "")}</textarea>
    <div class="muted">${flow.nodes.length} node · ${flow.day.length} dây · ${flow.day.filter(laLui).length} vòng lặp${flowSrc ? ` · ${flowSrc.nhom === "mau" ? "mẫu" : "của anh"}: ${esc(flowSrc.file)}` : ""}</div>`;
  if (run && run.st) {
    const st = run.st, tt = run.dang_chay ? "dang_chay" : st.trang_thai;
    h += `<h3 style="margin-top:8px">Lần chạy</h3><div class="kv"><b>Mã</b><span>${esc(st.id)}</span><b>Trạng thái</b><span>${esc(TT_LAN[tt] || tt)}</span>
      <b>Đầu vào</b><span>${esc(st.dau_vao || "—")}</span><b>Chi phí</b><span>$${(st.chi_phi || 0).toFixed(4)}</span><b>Bắt đầu</b><span>${esc(st.bat_dau)}</span></div>`;
    if ((st.canh_bao || []).length) h += `<div class="box warn"><b>Cảnh báo</b><div class="out">${esc(st.canh_bao.slice(-8).join("\n"))}</div></div>`;
    let cho = 0;
    for (const [k, v] of Object.entries(rt)) {
      const n = nodeById(k); if (!n || n.loai !== "cho_duyet") continue;
      cho += v.items ? Object.values(v.items).filter(x => x === "cho_duyet").length : (v.trang_thai === "cho_duyet" ? 1 : 0);
    }
    if (cho) h += `<button class="primary" onclick="moTab('duyet')">Có ${cho} chỗ chờ anh duyệt →</button>`;
    if (!run.dang_chay && ["loi", "dung_chi_phi", "dang_chay"].includes(st.trang_thai)) h += `<button id="nut-tiep">Chạy tiếp</button>`;
  } else {
    h += `<div class="box vi-du"><b>Mẹo:</b> bấm 1 node để xem <b>ví dụ</b> và cài đặt. Node mới: <b>AI báo cáo</b>, <b>Kiểm duyệt nội dung</b>, Tóm tắt, Phân loại, Phân tích đối thủ, Trả lời bình luận (nhãn “mới” ở cột trái). Mẫu có sẵn: “Báo cáo 9h sáng”, “Kiểm duyệt nội dung có sẵn”.</div>`;
  }
  el.innerHTML = h;
  $("#sd-ten").onchange = e => { flow.ten = e.target.value; };
  $("#sd-mo-ta").onchange = e => { flow.mo_ta = e.target.value; };
  const t = $("#nut-tiep"); if (t) t.onclick = async () => { await api("/api/tiep", {lan: run.id}); run.dang_chay = true; capNhatChip("dang_chay"); };
}
function oNhap(k, v, mau) {
  const id = "f-" + k;
  if (typeof (v ?? mau) === "boolean") return `<label style="display:flex;gap:6px;align-items:center;color:var(--fg)"><input type="checkbox" data-k="${k}" data-kieu="bool" ${v ? "checked" : ""}> ${esc(k)}</label>`;
  if (typeof (v ?? mau) === "number") return `<label for="${id}">${esc(k)}</label><input type="number" step="any" id="${id}" data-k="${k}" data-kieu="so" value="${esc(v ?? "")}">`;
  if (v !== undefined && typeof v === "object" || mau !== undefined && typeof mau === "object" && v === undefined)
    return `<label for="${id}">${esc(k)} <span class="muted">(JSON)</span></label><textarea id="${id}" data-k="${k}" data-kieu="json" rows="3">${esc(v === undefined ? "" : JSON.stringify(v, null, 1))}</textarea>`;
  if (TRUONG_DAI.has(k) || String(v ?? "").length > 60) return `<label for="${id}">${esc(k)}</label><textarea id="${id}" data-k="${k}" data-kieu="chu" rows="4">${esc(v ?? "")}</textarea>`;
  const dl = k === "kenh" ? ` list="dl-kenh"` : "";
  return `<label for="${id}">${esc(k)}</label><input type="text" id="${id}" data-k="${k}" data-kieu="chu" value="${esc(v ?? "")}"${dl}>`;
}
function veInspNode(el, n) {
  const m = META[n.loai] || {};
  const r = rt[n.id];
  const cd = n.cai_dat || (n.cai_dat = {});
  let h = `<div class="row"><span class="pal-dot" style="background:${mauNhom(n.loai)}"></span><h3 style="margin:0">${esc(m.ten || n.loai)}</h3><span class="grow"></span><span class="tag">GĐ ${m.giai_doan}</span>${m.gia_lap ? '<span class="tag">giả lập</span>' : ""}</div>
    <label>Mã node (dùng làm biến {{${esc(n.id)}}})</label><input type="text" id="n-id" value="${esc(n.id)}">
    <div class="muted">${esc(m.mo_ta || "")}</div>
    <div class="box vi-du"><b>Ví dụ:</b> ${esc(m.vi_du || "")}</div>`;
  if (laNodeAI(n)) {
    const ais = Object.entries(DOI).filter(([k]) => k !== "am_thanh");
    h += `<label>AI thực hiện</label><select data-k="ai" data-kieu="chu"><option value="tu_chon">Tự chọn theo vai (Claude quyết)</option>${ais.map(([k, a]) => `<option value="${k}" ${cd.ai === k ? "selected" : ""}>${esc(a.ten_hien || k)}${a.co_key ? " ✓ key" : ""}</option>`).join("")}</select>
      <label>Cách gọi</label><select data-k="che_do" data-kieu="chu"><option value="">Theo Đội AI</option>${[["tu_dong", "Tự động: API trước, lỗi/thiếu key → Chrome"], ["chi_api", "Chỉ API"], ["chi_chrome", "Chỉ Chrome"]].map(([k, t]) => `<option value="${k}" ${cd.che_do === k ? "selected" : ""}>${t}</option>`).join("")}</select>
      <label>AI dự phòng (theo thứ tự, cách nhau dấu phẩy)</label><input type="text" data-k="du_phong" data-kieu="ds" value="${esc((cd.du_phong || []).join(", "))}">`;
  }
  const keys = [...new Set([...Object.keys(m.cai_dat_mau || {}), ...Object.keys(cd)])].filter(k => !CAI_DAT_AI.includes(k) && k !== "khong_cache");
  if (laNodeAI(n) && !keys.includes("lenh") && !["kiem_duyet", "dieu_kien", "kiem_tra_chat_luong", "phan_loai", "bao_cao_ai", "tra_loi_binh_luan", "tieu_de_mo_ta", "tach_loi"].includes(n.loai)) keys.push("lenh");
  if (keys.length) h += `<h3 style="margin-top:6px">Cài đặt</h3>` + keys.map(k => oNhap(k, cd[k], (m.cai_dat_mau || {})[k])).join("");
  h += `<label style="display:flex;gap:6px;align-items:center;color:var(--fg)"><input type="checkbox" data-k="khong_cache" data-kieu="bool" ${cd.khong_cache ? "checked" : ""}> Không dùng kết quả lưu sẵn (cache)</label>`;
  h += `<datalist id="dl-kenh">${KENH.map(k => `<option value="${esc(k.ma)}">${esc(k.ten)}</option>`).join("")}<option value="{{phan_tu}}"></datalist>`;
  if (r) {
    h += `<h3 style="margin-top:8px">Lần chạy này</h3><div class="kv"><b>Trạng thái</b><span>${esc(TT[r.trang_thai] || r.trang_thai)}${r.cong ? " → " + esc(r.cong) : ""}</span>`;
    if (r.ai) h += `<b>AI</b><span>${esc(r.ai)} (${esc(r.tay)})</span>`;
    if (r.token_vao || r.token_ra) h += `<b>Token</b><span>${r.token_vao} vào / ${r.token_ra} ra · $${(r.chi_phi || 0).toFixed(4)}</span>`;
    if (r.giay != null) h += `<b>Thời gian</b><span>${r.giay}s${r.tu_cache ? " (cache)" : ""}</span>`;
    if (r.lan_lap) h += `<b>Lần sửa</b><span>${r.lan_lap}</span>`;
    if (r.items) h += `<b>Phần tử</b><span>${Object.entries(r.items).map(([i, t]) => `#${i}: ${TT[t] || t}`).join(", ")}</span>`;
    h += `</div>`;
    if (r.ghi_chu) h += `<div class="box">${esc(r.ghi_chu)}</div>`;
    if (r.loi) h += `<div class="box bad"><b>Lỗi:</b> ${esc(r.loi)}</div>`;
    if ((r.canh_bao || []).length) h += `<div class="box warn">${esc([...new Set(r.canh_bao)].join("\n"))}</div>`;
    if (r.ra !== undefined && r.ra !== null) h += `<details open><summary>Kết quả</summary><div class="box out">${esc(hienGiaTri(r.ra))}</div></details>`;
    if ((r.lenh || []).length) h += `<details><summary>Lệnh đã gửi AI (${r.lenh.length})</summary>${r.lenh.map(l => `<div class="box out">[${esc(l.ai)}/${esc(l.tay)}]\n${l.he_thong ? "HỆ THỐNG:\n" + esc(l.he_thong) + "\n\n" : ""}${esc(l.lenh)}</div>`).join("")}</details>`;
    if ((r.nhat_ky || []).length) h += `<details><summary>Nhật ký</summary><div class="box out">${esc(r.nhat_ky.join("\n"))}</div></details>`;
    if (r.trang_thai === "cho_duyet" && !r.items) h += `<div class="row"><button class="ok" data-qd="duyet">Duyệt</button><button data-qd="sua">Sửa…</button><button class="bad" data-qd="bo">Bỏ</button></div>`;
    if (run && !run.dang_chay && !r.items && run.st && run.st.nodes[n.id]) h += `<button id="nut-chay-lai">↻ Chạy lại từ node này</button>`;
  }
  h += `<button class="bad" id="nut-xoa-node" style="margin-top:6px">Xoá node</button>`;
  el.innerHTML = h;
  el.querySelectorAll("[data-k]").forEach(i => i.onchange = () => {
    const k = i.dataset.k, kieu = i.dataset.kieu;
    try {
      let v = kieu === "bool" ? i.checked : kieu === "so" ? (i.value === "" ? undefined : Number(i.value)) : kieu === "json" ? (i.value.trim() ? JSON.parse(i.value) : undefined)
        : kieu === "ds" ? i.value.split(",").map(s => s.trim()).filter(Boolean) : i.value;
      if (v === undefined || v === "" || (kieu === "bool" && v === false)) delete cd[k]; else cd[k] = v;
      if (k === "nhan") veTatCa(); else capNhatNode(n.id);
    } catch (e) { toast(`Ô ${k}: JSON chưa đúng (${e.message})`, "loi"); }
  });
  $("#n-id").onchange = e => doiId(n, e.target.value.trim());
  $("#nut-xoa-node").onclick = xoaDangChon;
  const cl = $("#nut-chay-lai");
  if (cl) cl.onclick = async () => { const r2 = await api("/api/chay_lai", {lan: run.id, node: n.id}); if (r2.ok === false) return toast(r2.loi, "loi"); run.dang_chay = true; capNhatChip("dang_chay"); };
  el.querySelectorAll("[data-qd]").forEach(b => b.onclick = () => quyetDinh(run.id, n.id, b.dataset.qd));
}
function doiId(n, moi) {
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(moi) || flow.nodes.some(x => x.id === moi)) { toast("Mã node chỉ gồm chữ không dấu, số, gạch dưới, và không trùng.", "loi"); return veInspector(); }
  const cu = n.id; n.id = moi;
  flow.day.forEach(d => { if (d.tu === cu) d.tu = moi; if (d.den === cu) d.den = moi; });
  const re = new RegExp(`\\{\\{\\s*${cu}([.\\s}])`, "g");
  flow.nodes.forEach(x => { const s = JSON.stringify(x.cai_dat).replace(re, `{{${moi}$1`); x.cai_dat = JSON.parse(s); if (x.cai_dat.ket_thuc === cu) x.cai_dat.ket_thuc = moi; });
  if (rt[cu]) { rt[moi] = rt[cu]; delete rt[cu]; }
  sel = {kind: "node", id: moi}; veTatCa();
}
function veInspDay(el, d) {
  const lui = laLui(d);
  el.innerHTML = `<h3>${lui ? "Dây quay ngược (vòng lặp)" : "Dây"}</h3>
    <div class="kv"><b>Từ</b><span>${esc(d.tu)}${d.cong ? " · cổng " + esc(d.cong) : ""}</span><b>Đến</b><span>${esc(d.den)}</span></div>
    ${lui ? `<label>Số lần quay lại tối đa (1–20)</label><input type="number" min="1" max="20" id="d-lap" value="${d.lap_toi_da}">
      <div class="muted">Hết lượt mà vẫn chưa đạt thì dừng nhánh và báo anh. Node đích nhận {{phan_hoi}} (nhận xét cần sửa) và {{lan_lap}}.</div>` : `<div class="muted">Dữ liệu node trước chảy sang node sau. Nối ngược về node phía trước để tạo vòng lặp có giới hạn.</div>`}
    <button class="bad" id="nut-xoa-day">Xoá dây</button>`;
  const l = $("#d-lap"); if (l) l.onchange = () => { d.lap_toi_da = Math.max(1, Math.min(20, +l.value || 3)); veDay(); };
  $("#nut-xoa-day").onclick = xoaDangChon;
}

/* ================= mở / lưu / chạy ================= */
function veChonSoDo() {
  const s = $("#chon-so-do");
  const nhom = (k, t) => { const ds = DS_SO_DO.filter(x => x.nhom === k); return ds.length ? `<optgroup label="${t}">${ds.map(x => `<option value="${k}|${esc(x.file)}">${esc(x.ten)}</option>`).join("")}</optgroup>` : ""; };
  s.innerHTML = `<option value="">— Mở sơ đồ —</option>` + nhom("cua_anh", "Của anh") + nhom("mau", "Mẫu");
  if (flowSrc) s.value = flowSrc.nhom + "|" + flowSrc.file;
}
$("#chon-so-do").onchange = async e => {
  const v = e.target.value; if (!v) return;
  const [nhom, file] = v.split("|");
  const data = await api(`/api/so_do?nhom=${nhom}&file=${encodeURIComponent(file)}`);
  moSoDo(data, {nhom, file});
};
function moSoDo(data, src) {
  flow = data; flow.nodes = flow.nodes || []; flow.day = flow.day || [];
  flow.nodes.forEach(n => n.cai_dat = n.cai_dat || {});
  flowSrc = src; run = null; rt = {}; sel = null; capNhatChip(null);
  tuDongXep(); veChonSoDo(); veTatCa(); setTimeout(vuaKhung, 30);
  const bd = flow.nodes.find(n => n.loai === "bat_dau");
  $("#dau-vao").placeholder = (bd && bd.cai_dat.goi_y_nhap) || "Đầu vào: chủ đề, link, ý tưởng…";
}
$("#nut-moi").onclick = () => moSoDo({phien_ban: 1, ten: "Sơ đồ mới", mo_ta: "", nodes: [{id: "bat_dau", loai: "bat_dau", cai_dat: {}, vi_tri: [60, 160]}], day: []}, null);
$("#nut-kiem").onclick = async () => {
  const r = await api("/api/kiem", {data: flow});
  r.ok ? toast(`Sơ đồ hợp lệ: ${r.so_node} node.`, "ok") : toast(["Sơ đồ còn lỗi:", ...r.loi], "loi");
};
$("#nut-luu").onclick = async () => {
  const file = flowSrc && flowSrc.nhom === "cua_anh" ? flowSrc.file : null;
  const r = await api("/api/luu_so_do", {data: flow, file});
  if (!r.ok) return toast(["Chưa lưu được:", ...r.loi], "loi");
  flowSrc = {nhom: "cua_anh", file: r.file};
  DS_SO_DO = await api("/api/so_do_ds"); veChonSoDo();
  toast(`Đã lưu: ${r.file}`, "ok");
};
$("#nut-chay").onclick = async () => {
  if (!flow) return;
  const r = await api("/api/chay", {data: flow, dau_vao: $("#dau-vao").value, kenh: $("#chon-kenh").value || null, nguon: flowSrc ? flowSrc.file : ""});
  if (!r.ok) return toast(["Chưa chạy được:", ...r.loi], "loi");
  run = {id: r.id, st: null, dang_chay: true}; rt = {};
  capNhatChip("dang_chay"); veTatCa();
};
function capNhatChip(tt) {
  const c = $("#run-chip");
  if (!tt) { c.hidden = true; return; }
  c.hidden = false; c.className = "run-chip " + tt; c.textContent = TT_LAN[tt] || tt;
  $("#nut-chay").disabled = tt === "dang_chay";
}
function veChonKenh() {
  $("#chon-kenh").innerHTML = `<option value="">— Kênh —</option>` + KENH.map(k => `<option value="${esc(k.ma)}">${esc(k.ten)} (${esc(k.thi_truong || "")})</option>`).join("");
}

/* ---- dựng trạng thái từ dữ liệu lần chạy ---- */
function dungRt(st) {
  const kq = {};
  const gom = (nodes) => {
    for (const [id, s] of Object.entries(nodes)) {
      const con = s.rieng && s.rieng.con;
      if (!kq[id] || s.trang_thai !== "cho") kq[id] = Object.assign(kq[id] || {}, s);
      if (con) for (const [i, c] of Object.entries(con)) {
        for (const [cid, cs] of Object.entries(c.nodes || {})) {
          if (cid === id) continue;
          kq[cid] = kq[cid] || {...cs};
          kq[cid].items = kq[cid].items || {};
          kq[cid].items[i] = cs.trang_thai;
          if (cs.trang_thai !== "cho") Object.assign(kq[cid], {...cs, items: kq[cid].items});
        }
      }
    }
  };
  gom(st.nodes);
  for (const r of Object.values(kq)) if (r.items) r.trang_thai = tongItems(r.items);
  return kq;
}
function tongItems(items) {
  const v = Object.values(items);
  if (v.includes("dang_chay")) return "dang_chay";
  if (v.includes("cho_duyet")) return "cho_duyet";
  if (v.includes("loi")) return "loi";
  if (v.length && v.every(x => x === "xong" || x === "bo_qua")) return v.includes("xong") ? "xong" : "bo_qua";
  return "cho";
}
let _taiHen = null;
function taiLanSau(ms = 400) { clearTimeout(_taiHen); _taiHen = setTimeout(taiLan, ms); }
async function taiLan() {
  if (!run) return;
  const st = await api(`/api/lan?id=${encodeURIComponent(run.id)}`);
  if (!st || st.loi) return;
  run.st = st; run.dang_chay = st.dang_chay;
  const items = {}; for (const [k, v] of Object.entries(rt)) if (v.items) items[k] = v.items;
  rt = dungRt(st);
  capNhatChip(st.dang_chay ? "dang_chay" : st.trang_thai);
  if (flow) { veNodes(); veDay(); veInspector(); }
}

/* ---- sự kiện thời gian thực ---- */
function noiSuKien() {
  const es = new EventSource("/api/su_kien");
  es.onmessage = m => {
    const ev = JSON.parse(m.data);
    if (ev.loai === "thong_bao") return toast(ev.noi_dung, ev.muc);
    if (ev.loai === "node" && ev.trang_thai === "cho_duyet") capNhatBadge();
    if (!run || ev.lan !== run.id) { if (ev.loai === "lan" && ev.trang_thai === "cho_duyet") capNhatBadge(); return; }
    if (ev.loai === "node") {
      const parts = ev.duong_dan.split("/");
      const id = parts[parts.length - 1];
      const r = rt[id] = rt[id] || {};
      if (parts.length >= 3) {
        r.items = r.items || {}; r.items[parts[parts.length - 2]] = ev.trang_thai;
        r.trang_thai = tongItems(r.items);
      } else Object.assign(r, {trang_thai: ev.trang_thai, cong: ev.cong, ghi_chu: ev.ghi_chu, loi: ev.loi});
      if (ev.trang_thai === "dang_chay") r.t0 = performance.now();
      capNhatNode(id); veDay();
      if (["xong", "loi", "cho_duyet"].includes(ev.trang_thai)) taiLanSau(600);
    } else if (ev.loai === "vong_lap") {
      toast(`↺ Vòng lặp: ${ev.tu} → ${ev.den} (lần ${ev.lan_thu})`);
    } else if (ev.loai === "lan" && !ev.pham_vi) {
      run.dang_chay = ev.trang_thai === "dang_chay";
      capNhatChip(ev.trang_thai);
      if (ev.trang_thai !== "dang_chay") { taiLanSau(50); capNhatBadge(); if (ev.trang_thai === "cho_duyet") toast("Có bài chờ anh duyệt (tab Duyệt).", "ok"); }
    }
  };
  es.onerror = () => { es.close(); setTimeout(noiSuKien, 2000); };
}
setInterval(() => { // thanh pin chạy theo thời gian ước tính
  const now = performance.now();
  for (const [id, r] of Object.entries(rt)) {
    if (r.trang_thai !== "dang_chay" || !r.t0) continue;
    const n = flow && nodeById(id); if (!n) continue;
    const est = laNodeAI(n) ? 6000 : 1500;
    const w = 95 * (1 - Math.exp(-(now - r.t0) / est));
    const i = $(`.node[data-id="${CSS.escape(id)}"] .pin i`); if (i) i.style.width = w.toFixed(1) + "%";
  }
}, 250);

/* ================= DUYỆT ================= */
function gomXemTruoc(x, out = {chu: [], anh: [], tep: [], tieu_de: null, mo_ta: null, hashtag: null, kiem_duyet: []}, sau = 0) {
  if (sau > 6 || x == null) return out;
  if (typeof x === "string") { if (x.length > 30 && !/^(Kiểm duyệt|Điểm \d)/.test(x)) out.chu.push(x); return out; }
  if (Array.isArray(x)) { x.forEach(v => gomXemTruoc(v, out, sau + 1)); return out; }
  if (typeof x === "object") {
    if (x.tieu_de && typeof x.tieu_de === "string" && !out.tieu_de) out.tieu_de = x.tieu_de;
    if (x.mo_ta && typeof x.mo_ta === "string" && !out.mo_ta) out.mo_ta = x.mo_ta;
    if (Array.isArray(x.hashtag) && !out.hashtag) out.hashtag = x.hashtag;
    if (x.ket_luan) out.kiem_duyet.push(x);
    if (typeof x.file === "string") (/\.(svg|png|jpe?g|webp)$/i.test(x.file) ? out.anh : out.tep).push(x.file);
    for (const [k, v] of Object.entries(x)) if (!(["tieu_de", "mo_ta", "file"].includes(k) && typeof v === "string") && !["hashtag", "vi_pham"].includes(k)) gomXemTruoc(v, out, sau + 1);
  }
  return out;
}
async function taiDuyet() {
  const ds = await api("/api/cho_duyet");
  capNhatBadge(ds.length);
  if (!ds.length) { $("#ds-duyet").innerHTML = `<div class="panel card"><b>Không có bài nào chờ duyệt.</b><span class="muted">Chạy một sơ đồ có node “Chờ anh duyệt”, bài sẽ hiện ở đây.</span></div>`; return; }
  $("#ds-duyet").innerHTML = ds.map((d, i) => {
    const x = d.xem_truoc || {}, g = gomXemTruoc(x.dau_vao);
    const kd = g.kiem_duyet[0];
    return `<div class="panel card" data-i="${i}">
      <div class="row" style="display:flex;gap:8px;align-items:center"><h3 style="margin:0">${esc(g.tieu_de || d.ten)}</h3><span class="grow"></span>${kd ? `<span class="chip ${kd.ket_luan === "dat" ? "ok" : "warn"}">Kiểm duyệt: ${esc(kd.ket_luan)}</span>` : ""}</div>
      <div class="meta">${esc(d.ten)} · ${esc(x.kenh || "chưa chọn kênh")} · ${esc(d.duong_dan)} · ${esc(d.bat_dau)}</div>
      ${(x.canh_bao || []).length ? `<div class="box bad">${esc(x.canh_bao.join("\n"))}</div>` : ""}
      ${kd && kd.vi_pham && kd.vi_pham.length ? `<div class="box warn">${esc(kd.vi_pham.map(v => `• ${v.loai} (${v.muc_do}): ${v.goi_y || ""}`).join("\n"))}</div>` : ""}
      ${g.anh.length ? `<div class="prev-img">${g.anh.slice(0, 4).map(a => `<img alt="ảnh xem trước" src="/api/tep?p=${encodeURIComponent(a)}">`).join("")}</div>` : ""}
      ${g.mo_ta ? `<div><b>Mô tả:</b> ${esc(g.mo_ta)}</div>` : ""}
      ${g.hashtag ? `<div class="chips">${g.hashtag.map(t => `<span class="chip">${esc(t)}</span>`).join("")}</div>` : ""}
      ${g.chu.length ? `<details open><summary>Nội dung</summary><div class="box out">${esc(g.chu.sort((a, b) => b.length - a.length)[0])}</div></details>` : ""}
      ${g.tep.length ? `<div class="meta">Tệp: ${g.tep.map(t => esc(t.split(/[\\/]/).pop())).join(", ")}</div>` : ""}
      <details><summary>Toàn bộ dữ liệu</summary><div class="box out">${esc(JSON.stringify(x.dau_vao, null, 2))}</div></details>
      <textarea placeholder="Yêu cầu sửa (khi bấm Sửa): ví dụ câu móc cần có con số" data-ghi-chu></textarea>
      <div style="display:flex;gap:6px"><button class="ok" data-qd="duyet">Duyệt</button><button data-qd="sua">Sửa</button><button class="bad" data-qd="bo">Bỏ</button></div>
    </div>`;
  }).join("");
  $$("#ds-duyet [data-qd]").forEach(b => b.onclick = async () => {
    const card = b.closest(".card"), d = ds[+card.dataset.i], gc = $("[data-ghi-chu]", card).value.trim();
    if (b.dataset.qd === "sua" && !gc) return toast("Anh ghi yêu cầu sửa vào ô trên rồi bấm Sửa.", "loi");
    await quyetDinh(d.lan, d.duong_dan, b.dataset.qd, gc);
    card.remove();
  });
}
async function quyetDinh(lan, duong, qd, ghiChu = "") {
  if (qd === "sua" && !ghiChu) { ghiChu = (window.prompt && window.prompt("Yêu cầu sửa:")) || ""; if (!ghiChu) return; }
  const r = await api("/api/duyet", {lan, duong_dan: duong, quyet_dinh: qd, ghi_chu: ghiChu});
  if (r.ok === false) return toast(r.loi, "loi");
  toast({duyet: "Đã duyệt.", sua: "Đã gửi yêu cầu sửa, AI đang làm lại.", bo: "Đã bỏ."}[qd] + (r.tt === "xep_hang" ? " (sẽ áp dụng khi các nhánh khác chạy xong)" : ""), "ok");
  if (run && run.id === lan) { run.dang_chay = true; capNhatChip("dang_chay"); }
  setTimeout(capNhatBadge, 800);
}
async function capNhatBadge(n) {
  if (n === undefined) { const ds = await api("/api/cho_duyet"); n = ds.length; }
  const b = $("#badge-duyet"); b.hidden = !n; b.textContent = n;
}
$("#nut-tai-duyet").onclick = taiDuyet;

/* ================= KÊNH ================= */
const TRUONG_KENH = [["ma", "Mã kênh (không dấu)"], ["ten", "Tên kênh"], ["nen_tang", "Nền tảng (phẩy)", "ds"], ["thi_truong", "Thị trường (VN, US, JP…)"],
  ["ngon_ngu", "Ngôn ngữ"], ["mui_gio", "Múi giờ"], ["ngach", "Ngách"], ["khan_gia", "Khán giả"], ["giong_van", "Giọng văn"],
  ["dieu_cam", "Điều cấm (phẩy) — Kiểm duyệt chặn", "ds"], ["loai_video", "Loại video, nhịp đăng"], ["chrome_dang_bai", "Chrome đăng bài"],
  ["muc_tieu", "Mục tiêu"], ["giong_doc", "Giọng đọc mặc định theo ngôn ngữ (JSON)", "json"]];
let kenhChon = null;
function veKenh() {
  $("#ds-kenh").innerHTML = KENH.map((k, i) => `<div class="panel item ${kenhChon === i ? "sel" : ""}" data-i="${i}"><b>${esc(k.ten)}</b><div class="muted">${esc(k.thi_truong || "")} · ${esc(k.ngach || "")}</div>${k.ghi_chu ? `<div class="muted" style="font-size:11px">${esc(k.ghi_chu)}</div>` : ""}</div>`).join("");
  $$("#ds-kenh .item").forEach(it => it.onclick = () => { kenhChon = +it.dataset.i; veKenh(); veFormKenh(KENH[kenhChon]); });
}
function veFormKenh(k) {
  const f = $("#form-kenh"); f.hidden = false;
  f.innerHTML = TRUONG_KENH.map(([t, nhan, kieu]) => {
    const v = k[t];
    if (kieu === "json") return `<label class="full">${nhan}<textarea data-t="${t}" data-kieu="json">${esc(v ? JSON.stringify(v, null, 1) : "{}")}</textarea></label>`;
    return `<label>${nhan}<input type="text" data-t="${t}" data-kieu="${kieu || ""}" value="${esc(Array.isArray(v) ? v.join(", ") : v ?? "")}"></label>`;
  }).join("") + `<div class="full" style="display:flex;gap:8px;align-items:center"><button class="primary" type="submit">Lưu kênh</button><span class="muted">Lưu vào thư mục kenh trong ${esc(CAI_DAT._home || "")}. Kênh mẫu chỉ minh hoạ.</span></div>`;
  f.onsubmit = async e => {
    e.preventDefault();
    const moi = {};
    try {
      $$("[data-t]", f).forEach(i => { const t = i.dataset.t, kieu = i.dataset.kieu; moi[t] = kieu === "ds" ? i.value.split(",").map(s => s.trim()).filter(Boolean) : kieu === "json" ? JSON.parse(i.value || "{}") : i.value.trim(); });
    } catch (er) { return toast("Giọng đọc: JSON chưa đúng", "loi"); }
    const r = await api("/api/kenh", {kenh: moi});
    if (!r.ok) return toast(r.loi, "loi");
    KENH = await api("/api/kenh"); veChonKenh(); veKenh(); toast("Đã lưu kênh.", "ok");
  };
}
$("#nut-kenh-moi").onclick = () => { kenhChon = null; veKenh(); veFormKenh({ma: "", ten: "", nen_tang: ["youtube", "facebook"], thi_truong: "VN", ngon_ngu: "tiếng Việt", mui_gio: "Asia/Ho_Chi_Minh", giong_doc: {}}); };

/* ================= LỊCH SỬ ================= */
async function taiLichSu() {
  const ds = await api("/api/lan?toi_da=100");
  $("#bang-ls").innerHTML = `<tr><th>Bắt đầu</th><th>Sơ đồ</th><th>Đầu vào</th><th>Trạng thái</th><th>Chi phí</th></tr>` +
    (ds.length ? ds.map(x => `<tr class="click" data-id="${esc(x.id)}"><td>${esc(x.bat_dau)}</td><td>${esc(x.ten)}</td><td>${esc((x.dau_vao || "").slice(0, 60))}</td><td>${esc(TT_LAN[x.trang_thai] || x.trang_thai)}</td><td>$${(x.chi_phi || 0).toFixed(4)}</td></tr>`).join("")
      : `<tr><td colspan="5" class="muted">Chưa có lần chạy nào.</td></tr>`);
  $$("#bang-ls tr.click").forEach(tr => tr.onclick = () => moLan(tr.dataset.id));
}
async function moLan(id) {
  const st = await api(`/api/lan?id=${encodeURIComponent(id)}`);
  moSoDo(clone(st.so_do), null);
  run = {id, st, dang_chay: st.dang_chay}; rt = dungRt(st);
  capNhatChip(st.dang_chay ? "dang_chay" : st.trang_thai);
  $("#dau-vao").value = st.dau_vao || "";
  moTab("so_do");
}
$("#nut-tai-ls").onclick = taiLichSu;

/* ================= ĐỘI AI ================= */
function veDoiAI() {
  $("#ds-ai").innerHTML = Object.entries(DOI).map(([k, a]) => `<div class="panel card">
    <div style="display:flex;gap:8px;align-items:center"><h3 style="margin:0">${esc(a.ten_hien || k)}</h3><span class="grow"></span><span class="chip">${esc({tu_dong: "Tự động", chi_api: "Chỉ API", chi_chrome: "Chỉ Chrome"}[a.che_do] || a.che_do)}</span></div>
    <div class="chips">${(a.vai || []).map(v => `<span class="chip">${esc(v)}</span>`).join("")}</div>
    <div class="kv"><b>Tay API</b><span>${a.api_kieu ? esc(a.api_kieu + (a.model ? " · " + a.model : "")) : "không có"}${a.api_kieu && !["gia_lap", "mock"].includes(a.api_kieu) ? (a.co_key ? ` <span class="chip ok">key ${esc(a.key_an)}</span>` : ` <span class="chip warn">chưa có key → giả lập</span>`) : ""}</span>
      <b>Tay Chrome</b><span>${a.chrome ? esc(a.chrome.ho_so + " · " + a.chrome.url) + ' <span class="chip">giai đoạn 4</span>' : "không có"}</span>
      <b>Chạy cùng lúc</b><span>${a.gioi_han || 1}</span></div></div>`).join("");
}

/* ================= CÀI ĐẶT ================= */
function veCaiDat() {
  const c = CAI_DAT;
  $("#form-cai-dat").innerHTML = `
    <label>Thư mục dữ liệu<input type="text" value="${esc(c._home)}" disabled></label>
    <label>Số node chạy cùng lúc<input type="number" min="1" max="16" data-k="song_song" value="${c.song_song}"></label>
    <label>Trần chi phí mỗi ngày (USD)<input type="number" step="0.5" min="0" data-k="tran_chi_phi_ngay_usd" value="${c.tran_chi_phi_ngay_usd}"></label>
    <label>Trần chi phí mỗi tháng (USD)<input type="number" step="1" min="0" data-k="tran_chi_phi_thang_usd" value="${c.tran_chi_phi_thang_usd}"></label>
    <label>Số lần thử lại khi AI lỗi<input type="number" min="0" max="5" data-k="thu_lai" value="${c.thu_lai}"></label>
    <label>Giữ file trung gian (ngày)<input type="number" min="1" data-k="giu_file_trung_gian_ngay" value="${c.giu_file_trung_gian_ngay}"></label>
    <label>Duyệt chính qua<input type="text" value="Telegram (giai đoạn 5)" disabled></label>
    <label>Báo tin thêm qua<input type="text" value="Zalo (giai đoạn 5)" disabled></label>
    <div><button class="primary" type="submit">Lưu cài đặt</button></div>`;
  $("#form-cai-dat").onsubmit = async e => {
    e.preventDefault();
    const b = {}; $$("#form-cai-dat [data-k]").forEach(i => b[i.dataset.k] = Number(i.value));
    await api("/api/cai_dat", b); Object.assign(CAI_DAT, b); toast("Đã lưu cài đặt.", "ok");
  };
}

/* ================= khởi động ================= */
(async function khoiDong() {
  let cd = null; try { cd = localStorage.getItem("ailink_chu_de"); } catch (e) {}
  const kd = await api("/api/khoi_dong");
  META = Object.fromEntries(kd.node.map(n => [n.loai, n])); NHOM = kd.nhom; KENH = kd.kenh.filter(Boolean);
  DOI = kd.doi_ai; CAI_DAT = kd.cai_dat; CAI_DAT._home = kd.home; DS_SO_DO = kd.so_do;
  $("#chu-de").value = cd || kd.cai_dat.chu_de || "tu_dong"; apDungChuDe();
  veBangNode(); veChonKenh(); veChonSoDo();
  const dau = DS_SO_DO.find(x => x.file === "short_youtube.ailink.json") || DS_SO_DO[0];
  if (dau) { const data = await api(`/api/so_do?nhom=${dau.nhom}&file=${encodeURIComponent(dau.file)}`); moSoDo(data, {nhom: dau.nhom, file: dau.file}); }
  noiSuKien(); capNhatBadge();
  window.addEventListener("resize", () => veDay());
})();

"""Dòng lệnh AiLink (dùng khi chưa có giao diện, hoặc để kiểm tra nhanh).

  python -m ailink node                         danh sách 40 loại node + ví dụ
  python -m ailink kiem mau/short_youtube.ailink.json
  python -m ailink chay mau/short_youtube.ailink.json "Chủ đề" [--kenh vn_chuyen_la]
  python -m ailink duyet <id_lan> <node|cho_moi/2/node> duyet|sua|bo ["ghi chú"]
  python -m ailink tiep <id_lan>                chạy tiếp lần chạy dở / sau khi duyệt
  python -m ailink chay_lai <id_lan> <node>     chạy lại từ node
  python -m ailink lich_su
"""
import json, sys
from . import config, engine, so_do
from .nodes import danh_sach_node, NHOM

KY = {"cho": "·", "dang_chay": "⚡", "xong": "✔", "loi": "✖", "bo_qua": "–", "cho_duyet": "⏸"}


def in_su_kien(ev):
    if ev["loai"] == "node" and ev["trang_thai"] in ("xong", "loi", "cho_duyet", "dang_chay"):
        them = f" → {ev['cong']}" if ev.get("cong") else ""
        loi = f"  {ev['loi']}" if ev.get("loi") else ""
        print(f"  {KY[ev['trang_thai']]} {ev['duong_dan']}{them}{loi}", flush=True)
    elif ev["loai"] == "vong_lap":
        print(f"  ↺ {ev['tu']} → {ev['den']} (lần {ev['lan_thu']})", flush=True)


def ket(lan, tt):
    print(f"\nKết quả: {tt}  |  chi phí ${lan.goc.chi_phi:.4f}  |  lần chạy {lan.st['id']}")
    for p, x in lan.cho_duyet_list():
        print(f"  ⏸ chờ duyệt: {p}" + (f"  (cảnh báo: {'; '.join(x.get('canh_bao', []))})" if x and x.get("canh_bao") else ""))
    for c in lan.st.get("canh_bao", [])[-5:]:
        print(f"  ! {c}")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    lenh, a = argv[0], argv[1:]
    if lenh == "node":
        for nhom in NHOM:
            ds = [n for n in danh_sach_node() if n["nhom"] == nhom]
            print(f"\n== {NHOM[nhom]['ten']} ({NHOM[nhom]['mau']}) ==")
            for n in ds:
                gl = " [giả lập]" if n["gia_lap"] else ""
                print(f"- {n['loai']}: {n['ten']}{gl} (GĐ {n['giai_doan']})\n    {n['mo_ta']}\n    Ví dụ: {n['vi_du']}")
        return 0
    if lenh == "kiem":
        sd = so_do.doc_file(a[0])
        print(f"OK: '{sd.ten}' — {len(sd.nodes)} node, {len(sd.day)} dây ({len(sd.lui)} dây quay ngược)")
        return 0
    if lenh == "chay":
        kenh = None
        if "--kenh" in a:
            i = a.index("--kenh")
            kenh = a[i + 1]
            a = a[:i] + a[i + 2:]
        lan = engine.LanChay(so_do.doc_file(a[0]), a[1] if len(a) > 1 else "", kenh=kenh, on_event=in_su_kien)
        ket(lan, lan.chay())
        return 0
    if lenh == "duyet":
        lan = engine.mo_lan(a[0], on_event=in_su_kien)
        lan.duyet(a[1], a[2], a[3] if len(a) > 3 else "")
        ket(lan, lan.chay())
        return 0
    if lenh == "tiep":
        lan = engine.mo_lan(a[0], on_event=in_su_kien)
        ket(lan, lan.chay())
        return 0
    if lenh == "chay_lai":
        lan = engine.mo_lan(a[0], on_event=in_su_kien)
        ket(lan, lan.chay_lai_tu(a[1]))
        return 0
    if lenh == "lich_su":
        for x in engine.danh_sach_lan():
            print(f"{x['id']}  {x['trang_thai']:<12} {x['ten']}")
        return 0
    print(f"Không có lệnh '{lenh}'.\n{__doc__}")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except so_do.LoiSoDo as e:
        print(e)
        sys.exit(2)

"""Nhóm AI phân tích (xanh dương): AI báo cáo, tóm tắt, phân loại, phân tích đối thủ, trả lời bình luận."""
import os, time
from .base import NodeType, KetQua, LoiNode, dang_ky, chu
from .van_ban import NodeAI

MUC_BAO_CAO = {
    "sang_9h": ["Tóm tắt 3 dòng", "View, sub, giờ xem 24h theo kênh", "Kênh tăng / giảm mạnh và lý do",
                "Chủ đề ngách đang lên", "Tin AI / YouTube đáng chú ý", "Việc nên làm hôm nay (tối đa 5)"],
    "kenh": ["Hiệu suất kênh", "Video tốt nhất / kém nhất và lý do", "Khán giả",
             "Tiến độ bật kiếm tiền (1.000 sub, 4.000 giờ xem)", "Đề xuất 3 video tiếp theo"],
    "tuan": ["Tổng kết tuần", "So với tuần trước", "Bài học", "Kế hoạch tuần tới"],
    "chi_phi": ["Tổng chi phí", "Theo AI", "Theo kênh", "Cảnh báo trần chi phí"],
    "lan_chay": ["Lần chạy nào xong / lỗi / chờ duyệt", "Lỗi lặp lại và cách sửa", "Việc cần anh xử lý"],
}
DO_DAI = {"ngan": "dưới 150 chữ", "vua": "150–400 chữ", "dai": "400–900 chữ"}


@dang_ky
class BaoCaoAI(NodeType):
    loai, ten, nhom, giai_doan = "bao_cao_ai", "AI báo cáo", "phan_tich", 1
    mo_ta = ("Gom dữ liệu từ các node nối vào (view, nghiên cứu ngách, tin tức, chi phí, lịch sử chạy) "
             "rồi AI viết báo cáo theo mẫu: sáng 9h, theo kênh, tuần, chi phí, lần chạy, hoặc tự đặt mục. "
             "Định dạng Telegram (ngắn, có biểu tượng) hoặc Markdown; tuỳ chọn lưu file .md.")
    vi_du = ("9h sáng: Đọc view 10 kênh + Nghiên cứu ngách + Hỏi AI tin AI/YouTube → AI báo cáo (sang_9h) "
             "→ Nhắn tin Telegram + lưu G:\\claude\\AiLink\\xuat\\bao_cao\\.")
    cai_dat_mau = {"loai": "sang_9h", "dinh_dang": "telegram", "do_dai": "vua", "luu_file": True,
                   "muc": [], "ai": "tu_chon"}

    def chay(self, nx):
        loai = nx.cd("loai", "sang_9h")
        muc = [nx.render(m) for m in (nx.cai_dat.get("muc") or MUC_BAO_CAO.get(loai) or MUC_BAO_CAO["sang_9h"])]
        dinh_dang = nx.cd("dinh_dang", "telegram")
        do_dai = DO_DAI.get(nx.cd("do_dai", "vua"), DO_DAI["vua"])
        du_lieu = "\n\n".join(f"### {k}\n{chu(v)[:4000]}" for k, v in nx.dau_vao.items()) or chu(nx.prev)
        lenh = (f"Viết báo cáo '{loai}' ngày {nx.bien['ngay']} cho anh Hoà, bằng tiếng Việt, {do_dai}. "
                f"Định dạng: {'tin nhắn Telegram, gạch đầu dòng, không bảng' if dinh_dang == 'telegram' else 'Markdown có tiêu đề'}. "
                "Chỉ dùng số liệu có trong dữ liệu; thiếu thì ghi 'chưa có số liệu', không bịa. "
                "Các mục:\n- " + "\n- ".join(muc) + f"\n\nDỮ LIỆU:\n{du_lieu}")

        def gia_lap(p):
            du = {}
            for k, v in nx.dau_vao.items():  # mở 1 lớp node Gộp
                du.update(v if isinstance(v, dict) and k not in v and not any(x in v for x in ("van_ban", "noi_dung")) else {k: v})
            dong = [f"📊 BÁO CÁO {loai.upper()} — {nx.bien['ngay']} (giả lập, AI thật sẽ viết lại)"]
            for i, m in enumerate(muc, 1):
                dong.append(f"\n{i}. {m}")
                if i == 1:
                    dong.append(f"  • Có {len(du)} nguồn dữ liệu: {', '.join(du) or 'không có'}")
                elif "view" in m.lower() or "hiệu suất" in m.lower():
                    rows = [r for v in du.values() if isinstance(v, list) for r in v if isinstance(r, dict) and "kenh" in r]
                    for r in rows or []:
                        dong.append(f"  • {r['kenh']}: {r.get('view_24h', '?')} view, +{r.get('sub_moi', '?')} sub, "
                                    f"{r.get('gio_xem', '?')} giờ xem")
                    if not rows:
                        dong.append("  • chưa có số liệu")
                else:
                    tu_khoa = {"ngách": "ngach", "tin": "tin", "chi phí": "chi_phi", "ý tưởng": "y_tuong"}
                    k = next((v for t, v in tu_khoa.items() if t in m.lower()), None)
                    khop = [chu(v) for kk, v in du.items() if k and k in kk]
                    dong.append("  • " + (khop[0][:300].replace("\n", "\n    ") if khop else "(giả lập) chưa có số liệu thật"))
            return "\n".join(dong)

        van_ban = nx.ai(lenh, vai="bao_cao", gia_lap=gia_lap)
        ra = {"van_ban": van_ban, "loai": loai, "ngay": nx.bien["ngay"], "tom_tat": van_ban.strip().split("\n")[0][:200]}
        if nx.cd("luu_file", False):
            ten = nx.render(nx.cai_dat.get("ten_file") or "{{ngay}}_" + loai + ".md")
            p = nx.ghi_xuat(os.path.join("bao_cao", ten), van_ban)
            ra["file"] = p
        return KetQua(ra)


@dang_ky
class TomTat(NodeAI):
    loai, ten, nhom, giai_doan = "tom_tat", "Tóm tắt", "phan_tich", 1
    vai = "bao_cao"
    mo_ta = "Rút gọn nội dung dài (bài báo, kịch bản, bình luận) thành N ý."
    vi_du = "Tóm tắt 20 tin AI trong ngày thành 5 ý cho báo cáo sáng."
    cai_dat_mau = {"so_y": 5}
    lenh_mac_dinh = "Tóm tắt thành {{cai_dat.so_y}} ý ngắn, giữ số liệu quan trọng:\n{{prev}}"

    def mau_gia_lap(self, nx):
        n = int(nx.cd("so_y", 5))
        return lambda p: "\n".join(f"- Ý {i} (giả lập) từ: {chu(nx.prev)[:50]}" for i in range(1, n + 1))


@dang_ky
class PhanLoai(NodeType):
    loai, ten, nhom, giai_doan = "phan_loai", "Phân loại", "phan_tich", 1
    mo_ta = ("AI xếp nội dung vào 1 nhãn; mỗi nhãn là 1 cổng ra riêng (thêm cổng 'khac'). "
             "Đầu vào đi thẳng qua cổng được chọn.")
    vi_du = "Ý tưởng → nhãn short / dai / ca_hai → mỗi nhãn đi dây chuyền riêng."
    cai_dat_mau = {"nhan": ["short", "dai", "ca_hai"], "cau_hoi": "Ý tưởng này hợp làm Short, video dài hay cả hai?"}
    bat_buoc = ("nhan",)

    def cong_ra(self, cd):
        return list(cd.get("nhan") or []) + ["khac"]

    def chay(self, nx):
        nhan = list(nx.cai_dat["nhan"])
        lenh = (f"{nx.cd('cau_hoi', 'Phân loại nội dung sau')}\nChỉ chọn 1 trong: {', '.join(nhan)}.\n"
                f"Nội dung:\n{chu(nx.prev)}\nTrả JSON: {{\"nhan\": \"...\", \"ly_do\": \"...\"}}")
        kq = nx.ai(lenh, vai="kiem_tra", json=True,
                   gia_lap=lambda p: {"nhan": nx.cd("nhan_gia_lap", nhan[0]), "ly_do": "Giả lập"})
        n = kq.get("nhan")
        nx.ghi_chu(f"{n}: {kq.get('ly_do', '')}")
        return KetQua(nx.prev, n if n in nhan else "khac")


@dang_ky
class PhanTichDoiThu(NodeAI):
    loai, ten, nhom, giai_doan = "phan_tich_doi_thu", "Phân tích đối thủ", "phan_tich", 3
    vai = "nghien_cuu"
    mo_ta = "Từ danh sách kênh đối thủ: nhịp đăng, kiểu tiêu đề, thumbnail, video nổi, khoảng trống để mình chen vào."
    vi_du = "Mỗi thứ Hai: phân tích 3 kênh đối thủ ngách bí ẩn JP → gợi ý 5 video lấp khoảng trống."
    cai_dat_mau = {"doi_thu": ["@kenh_doi_thu_1", "@kenh_doi_thu_2"]}
    lenh_mac_dinh = ("Phân tích các kênh đối thủ {{cai_dat.doi_thu}} trong ngách {{kenh.ngach}}, thị trường "
                     "{{kenh.thi_truong}}: nhịp đăng, mẫu tiêu đề, thumbnail, video nổi nhất, khoảng trống. "
                     "Đề xuất 5 video lấp khoảng trống. Thông tin không chắc thì ghi rõ 'chưa chắc'.")

    def mau_gia_lap(self, nx):
        return lambda p: ("(giả lập) Đối thủ đăng 1 video/ngày, tiêu đề dạng câu hỏi, thumbnail mặt người + chữ đỏ.\n"
                          "Khoảng trống: chưa ai làm series theo vùng miền.")


@dang_ky
class TraLoiBinhLuan(NodeType):
    loai, ten, nhom, giai_doan = "tra_loi_binh_luan", "Trả lời bình luận", "phan_tich", 6
    mo_ta = ("AI soạn câu trả lời cho bình luận theo giọng kênh, đánh dấu bình luận cần anh xem "
             "(chửi bới, hỏi hợp tác, phàn nàn). Chỉ soạn nháp, muốn đăng phải qua Chờ duyệt.")
    vi_du = "Đọc 50 bình luận mới → soạn trả lời → Chờ duyệt → (giai đoạn 6) đăng trả lời."
    cai_dat_mau = {"toi_da": 50}

    def chay(self, nx):
        bl = nx.prev if isinstance(nx.prev, list) else [x for x in chu(nx.prev).splitlines() if x.strip()]
        bl = bl[: int(nx.cd("toi_da", 50))]
        lenh = ("Soạn trả lời ngắn, thân thiện theo giọng kênh {{kenh.ten}} cho từng bình luận. Đánh dấu "
                "can_anh_xem=true nếu chửi bới, hỏi hợp tác, phàn nàn, hoặc nhạy cảm.\n"
                + "\n".join(f"{i}. {chu(b)}" for i, b in enumerate(bl, 1)) +
                '\nTrả JSON: {"tra_loi": [{"binh_luan": "...", "tra_loi": "...", "can_anh_xem": false}]}')
        kq = nx.ai(nx.render(lenh), vai="kich_ban", json=True, gia_lap=lambda p: {"tra_loi": [
            {"binh_luan": chu(b), "tra_loi": "Cảm ơn bạn đã xem! (giả lập)", "can_anh_xem": False} for b in bl]})
        return KetQua(kq)

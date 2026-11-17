import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import assistant as tl  # noqa: E402

st.set_page_config(page_title="Trợ lý hỏi đáp", layout="wide")
st.title("8 · Trợ lý hỏi đáp trên tầng Gold")
st.caption("Hỏi bằng tiếng Việt. Trợ lý tự viết câu SELECT, kho kiểm tra rồi mới chạy, và câu trả lời luôn kèm câu SQL đã dùng. "
           "Trợ lý chỉ đọc được tầng Gold và tầng mô hình. Đây là công cụ phục vụ học tập, không phải khuyến nghị đầu tư.")

GOI_Y = [
    "5 mã nào được dự báo biến động mạnh nhất phiên tới?",
    "Nếu giữ 1 tỉ đồng HPG thì mức lỗ một phiên ở độ tin cậy 95% là bao nhiêu?",
    "Tháng nào mô hình HAR-X sai nhiều nhất và sai gấp mấy lần bình thường?",
    "So sánh lợi nhuận sau thuế quý 3/2026 của FPT, HPG và MWG.",
    "Mã nào bị nguồn viết lại lịch sử giá nhiều nhất?",
    "Ngày nào có nhiều mã biến động bất thường nhất?",
]

if not tl.tai_khoa():
    st.warning("Chưa có khoá Claude API. Tạo file `.env` ở thư mục gốc của dự án với một dòng "
               "`ANTHROPIC_API_KEY=...` rồi khởi động lại dashboard. File `.env` đã nằm trong `.gitignore`.")
    st.markdown("**Các câu trợ lý trả lời được, ví dụ:**\n" + "\n".join(f"- {g}" for g in GOI_Y))
    st.stop()

if "tl_luot" not in st.session_state:
    st.session_state.tl_luot = []          # [(câu hỏi, TraLoi)]


def ve(tr: tl.TraLoi) -> None:
    st.markdown(tr.van_ban or "_(không có câu trả lời)_")
    for i, b in enumerate(tr.cac_buoc, 1):
        nhan = f"Truy vấn {i}: {b.muc_dich}" + (" (bị từ chối hoặc lỗi)" if b.loi else f" · quét {b.byte_quet / 1e6:.1f} MB")
        with st.expander(nhan, expanded=False):
            st.code(b.sql, language="sql")
            if b.loi:
                st.error(b.loi)
    if tr.bang_cuoi is not None and not tr.bang_cuoi.empty:
        st.dataframe(tr.bang_cuoi, use_container_width=True, hide_index=True)
    st.caption(f"{tr.so_lan_goi} lần gọi mô hình · {tr.token_vao + tr.token_doc_dem + tr.token_ghi_dem:,} token vào "
               f"(trong đó {tr.token_doc_dem:,} đọc từ bộ nhớ đệm) · {tr.token_ra:,} token ra".replace(",", "."))


with st.sidebar:
    st.subheader("Câu hỏi gợi ý")
    chon = None
    for g in GOI_Y:
        if st.button(g, use_container_width=True):
            chon = g
    if st.button("Xoá cuộc trò chuyện"):
        st.session_state.tl_luot = []
        st.rerun()

for cau, tr in st.session_state.tl_luot:
    with st.chat_message("user"):
        st.markdown(cau)
    with st.chat_message("assistant"):
        ve(tr)

cau_hoi = st.chat_input("Hỏi về giá, biến động, rủi ro, báo cáo tài chính, chất lượng dữ liệu…") or chon
if cau_hoi:
    with st.chat_message("user"):
        st.markdown(cau_hoi)
    lich_su = []
    for cau, tr in st.session_state.tl_luot[-4:]:      # giữ 4 lượt gần nhất làm ngữ cảnh
        lich_su += [{"role": "user", "content": cau}, {"role": "assistant", "content": tr.van_ban or "(không có)"}]
    with st.chat_message("assistant"):
        with st.spinner("Đang viết truy vấn và hỏi kho…"):
            try:
                tr = tl.hoi(cau_hoi, lich_su)
            except Exception as e:
                tr = tl.TraLoi(van_ban=f"Không gọi được mô hình: {type(e).__name__}: {str(e)[:300]}")
        ve(tr)
    st.session_state.tl_luot.append((cau_hoi, tr))

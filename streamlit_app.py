"""Entry page — Vietnam Stock Market Medallion Warehouse (Nhóm 10)."""
import streamlit as st

st.set_page_config(page_title="Vnstock Medallion DW", page_icon="📊", layout="wide")

st.title("Kho dữ liệu chứng khoán Việt Nam — Medallion / BigQuery")
st.markdown(
    """
**Đồ án Nhà kho dữ liệu và tích hợp — Nhóm 10.**
Dashboard đọc trực tiếp tầng **Gold** trên BigQuery (không gọi Vnstock khi mở trang).

| Trang | Nội dung |
|---|---|
| 1 — Market Overview | VN-Index, độ rộng thị trường, thanh khoản |
| 2 — Stock Analysis | Nến + SMA20/50, RSI14, khối lượng theo mã |
| 3 — Financials & Alerts | Chỉ tiêu tài chính theo quý và tín hiệu theo quy tắc |
| 4 — Pipeline Health | Trạng thái ingestion, đối soát, độ tươi dữ liệu |

> ⚠️ Các tín hiệu/cảnh báo là minh họa dựa trên quy tắc, **không phải khuyến nghị đầu tư**.
"""
)
st.caption("Pipeline: Vnstock → Bronze → dbt Silver → dbt Gold → Streamlit · điều phối bởi Dagster.")

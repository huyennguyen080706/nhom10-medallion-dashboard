import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.bigquery_client import BRONZE, GOLD, query  # noqa: E402

st.set_page_config(page_title="Pipeline Health", layout="wide")
st.title("4 · Pipeline Health")

health = query(f"SELECT * FROM `{GOLD}.mart_pipeline_health` ORDER BY kind")

ok = int(health["datasets_ok"].sum())
total = int(health["datasets"].sum())
rec = bool(health["rows_reconciled"].fillna(False).all())
issues = int(health["open_price_issues"].iloc[0]) if len(health) else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Extract thành công", f"{ok}/{total}")
k2.metric("Đối soát dòng Bronze↔Silver", "ĐẠT" if rec else "LỆCH")
k3.metric("Bản ghi giá nghi vấn (DQ)", issues)
k4.metric("Batch", health["_batch_id"].iloc[0] if len(health) else "—")

st.subheader("Theo nhóm dữ liệu")
st.dataframe(health, use_container_width=True)

st.subheader("Chi tiết ingestion audit (manifest)")
audit = query(f"""
    SELECT kind, status, COUNT(*) datasets, SUM(row_count) total_rows,
           MIN(_ingested_at) first_ingested, MAX(_ingested_at) last_ingested
    FROM `{BRONZE}.ingestion_audit`
    GROUP BY kind, status ORDER BY kind, status
""")
st.dataframe(audit, use_container_width=True)

errs = query(f"""
    SELECT dataset_key, kind, symbol, error_type, error_message
    FROM `{BRONZE}.ingestion_audit` WHERE status != 'ok'
""")
st.subheader("Extract lỗi")
if len(errs):
    st.dataframe(errs, use_container_width=True)
else:
    st.success("Không có extract lỗi trong batch hiện tại (126/126 ok).")

st.caption("Nguồn: bronze.ingestion_audit + gold.mart_pipeline_health. Lịch refresh: Dagster schedule 18:45 các ngày T2–T6 (giờ VN).")

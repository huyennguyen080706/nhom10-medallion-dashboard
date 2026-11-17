# Dashboard kho dữ liệu chứng khoán Việt Nam — Nhóm 10

Bản triển khai online của dashboard Streamlit (8 trang) trong đồ án *Nhà kho dữ liệu và tích hợp* (UEL).
Dashboard đọc tầng Gold và tầng mô hình trên Google BigQuery qua một service account chỉ có quyền đọc.

Chạy trên máy: `pip install -r requirements.txt && streamlit run streamlit_app.py`
(cần `.streamlit/secrets.toml` có mục `[gcp_service_account]`, hoặc đã `gcloud auth application-default login`).

Dashboard phục vụ học tập, không phải khuyến nghị đầu tư.

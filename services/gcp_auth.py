"""Tạo BigQuery client cho cả máy cá nhân và Streamlit Community Cloud.

- Trên Streamlit Cloud: đọc service account từ secrets, mục [gcp_service_account].
- Trên máy cá nhân: không có secrets thì dùng Application Default Credentials (gcloud auth).
"""
from __future__ import annotations

from google.cloud import bigquery


def _service_account_info() -> dict | None:
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            return dict(st.secrets["gcp_service_account"])
    except Exception:
        # Chưa có file secrets.toml hoặc không chạy trong Streamlit: dùng ADC.
        pass
    return None


def make_client(project: str) -> bigquery.Client:
    info = _service_account_info()
    if info:
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_info(info)
        return bigquery.Client(project=project, credentials=creds)
    return bigquery.Client(project=project)

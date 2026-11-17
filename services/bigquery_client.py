"""Cached BigQuery access for the Streamlit app.

The app reads GOLD only (never calls Vnstock directly) and caches every query
for 10 minutes, so page switching does not re-bill the sandbox quota.
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from google.cloud import bigquery

from services.gcp_auth import make_client

PROJECT = "project-k244161774"
SUFFIX = os.environ.get("DW_SUFFIX", "_v2")   # v2 đọc gold_v2 / silver_v2 / bronze_v2; đặt DW_SUFFIX="" để xem kho cũ
GOLD = f"{PROJECT}.gold{SUFFIX}"
SILVER = f"{PROJECT}.silver{SUFFIX}"
BRONZE = f"{PROJECT}.bronze{SUFFIX}"
ML = f"{PROJECT}.ml{SUFFIX}"


@st.cache_resource
def _client() -> bigquery.Client:
    return make_client(PROJECT)


@st.cache_data(ttl=600, show_spinner="Đang truy vấn BigQuery…")
def query(sql: str) -> pd.DataFrame:
    return _client().query(sql).to_dataframe()

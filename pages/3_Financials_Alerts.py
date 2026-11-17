import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from components.charts import LAYOUT  # noqa: E402
from services.bigquery_client import GOLD, query  # noqa: E402

st.set_page_config(page_title="Financials & Alerts", layout="wide")
st.title("3 · Financials & Alerts")

st.subheader("Chỉ tiêu tài chính theo quý")
fin_symbols = query(
    f"SELECT DISTINCT symbol FROM `{GOLD}.mart_financial_summary` ORDER BY symbol"
)["symbol"].tolist()
symbol = st.selectbox("Mã (15 mã có BCTC)", fin_symbols)

fs = query(f"""
    SELECT period, net_revenue, net_profit_after_tax, total_assets, equity,
           operating_cash_flow, roe_quarterly, roa_quarterly, debt_to_assets
    FROM `{GOLD}.mart_financial_summary`
    WHERE symbol = '{symbol}' ORDER BY period
""")

import plotly.graph_objects as go  # noqa: E402

c1, c2 = st.columns(2)
fig = go.Figure()
fig.add_trace(go.Bar(x=fs["period"], y=fs["net_profit_after_tax"], name="LNST", marker_color="#1f3a5f"))
if fs["net_revenue"].notna().any():
    fig.add_trace(go.Bar(x=fs["period"], y=fs["net_revenue"], name="Doanh thu thuần", marker_color="#98a2b3"))
fig.update_layout(title=f"{symbol} — Doanh thu & LNST theo quý (VNĐ)", barmode="group", **LAYOUT)
c1.plotly_chart(fig, use_container_width=True)

fig2 = go.Figure(go.Scatter(x=fs["period"], y=fs["roe_quarterly"], mode="lines+markers",
                            line=dict(color="#f2695c")))
fig2.update_layout(title=f"{symbol} — ROE theo quý (LNST quý / VCSH)", yaxis_tickformat=".1%", **LAYOUT)
c2.plotly_chart(fig2, use_container_width=True)

st.dataframe(fs, use_container_width=True)
st.caption("Ô trống = nguồn không công bố chỉ tiêu cho kỳ đó (ngân hàng không có Doanh thu thuần…). Không thay NULL bằng 0.")

st.divider()
st.subheader("Tín hiệu theo quy tắc (minh họa — không phải khuyến nghị đầu tư)")
rules = query(f"SELECT DISTINCT rule FROM `{GOLD}.mart_stock_alerts` ORDER BY rule")["rule"].tolist()
c3, c4, c5 = st.columns(3)
sel_rules = c3.multiselect("Loại tín hiệu", rules, default=rules)
days = c4.slider("Số ngày gần nhất", 5, 365, 30)
sym_filter = c5.text_input("Lọc mã (bỏ trống = tất cả)", "")

where = f"rule IN UNNEST({sel_rules})" if sel_rules else "TRUE"
if sym_filter.strip():
    where += f" AND symbol = '{sym_filter.strip().upper()}'"
alerts = query(f"""
    SELECT trade_date, symbol, rule, threshold, observed, reason
    FROM `{GOLD}.mart_stock_alerts`
    WHERE {where}
      AND trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM `{GOLD}.mart_stock_alerts`), INTERVAL {days} DAY)
    ORDER BY trade_date DESC, symbol
""")
st.metric("Số tín hiệu", len(alerts))
st.dataframe(alerts, use_container_width=True, height=420)

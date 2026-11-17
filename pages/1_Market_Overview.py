import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from components.charts import LAYOUT, NAVY, line  # noqa: E402
from services.bigquery_client import GOLD, query  # noqa: E402

st.set_page_config(page_title="Market Overview", layout="wide")
st.title("1 · Market Overview")

idx = query(f"SELECT trade_date, close, volume FROM `{GOLD}.fact_index_daily` ORDER BY trade_date")
d_min, d_max = idx["trade_date"].min(), idx["trade_date"].max()
c1, c2 = st.columns(2)
start = c1.date_input("Từ ngày", d_min, min_value=d_min, max_value=d_max)
end = c2.date_input("Đến ngày", d_max, min_value=d_min, max_value=d_max)
win = idx[(idx["trade_date"] >= start) & (idx["trade_date"] <= end)]

k1, k2, k3, k4 = st.columns(4)
if len(win) >= 2:
    chg = win["close"].iloc[-1] / win["close"].iloc[0] - 1
    k1.metric("VN-Index mới nhất", f"{win['close'].iloc[-1]:,.2f}", f"{chg:+.2%} trong kỳ")
k2.metric("Số phiên trong kỳ", f"{len(win):,}")
k3.metric("KLGD bình quân/phiên", f"{win['volume'].mean():,.0f}")
k4.metric("Khoảng dữ liệu Index", f"{d_min} → {d_max}")

st.plotly_chart(line(win, "trade_date", "close", "VN-Index (close)"), use_container_width=True)

st.subheader("Độ rộng thị trường — phiên gần nhất")
breadth = query(f"""
    WITH last_day AS (SELECT MAX(trade_date) d FROM `{GOLD}.mart_technical_indicators`)
    SELECT symbol, daily_return, close, volume
    FROM `{GOLD}.mart_technical_indicators`, last_day
    WHERE trade_date = last_day.d
    ORDER BY daily_return DESC
""")
up = int((breadth["daily_return"] > 0).sum())
down = int((breadth["daily_return"] < 0).sum())
flat = len(breadth) - up - down
b1, b2, b3 = st.columns(3)
b1.metric("Tăng", up)
b2.metric("Giảm", down)
b3.metric("Đứng giá", flat)

import plotly.graph_objects as go  # noqa: E402

fig = go.Figure(go.Bar(
    x=breadth["symbol"], y=breadth["daily_return"],
    marker_color=["#12805c" if v > 0 else "#f2695c" for v in breadth["daily_return"]],
))
fig.update_layout(title="Lợi suất ngày theo mã (phiên gần nhất)", yaxis_tickformat=".1%", **LAYOUT)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Top thanh khoản (giá trị ≈ close × volume, 20 phiên gần nhất)")
liq = query(f"""
    SELECT symbol, AVG(turnover_approx) avg_turnover
    FROM `{GOLD}.fact_price_daily`
    WHERE trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM `{GOLD}.fact_price_daily`), INTERVAL 28 DAY)
    GROUP BY symbol ORDER BY avg_turnover DESC LIMIT 15
""")
fig2 = go.Figure(go.Bar(x=liq["symbol"], y=liq["avg_turnover"], marker_color=NAVY))
fig2.update_layout(title="Giá trị giao dịch bình quân/phiên", **LAYOUT)
st.plotly_chart(fig2, use_container_width=True)

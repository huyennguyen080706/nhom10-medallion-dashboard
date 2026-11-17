import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from components.charts import LAYOUT, candlestick_with_indicators, line  # noqa: E402
from services.bigquery_client import GOLD, query  # noqa: E402

st.set_page_config(page_title="Stock Analysis", layout="wide")
st.title("2 · Stock Analysis")

symbols = query(f"SELECT symbol FROM `{GOLD}.dim_ticker` ORDER BY symbol")["symbol"].tolist()
c1, c2 = st.columns([1, 2])
symbol = c1.selectbox("Mã cổ phiếu", symbols, index=symbols.index("FPT") if "FPT" in symbols else 0)
months = c2.slider("Số tháng gần nhất", 3, 72, 18)

px = query(f"""
    SELECT trade_date, open, high, low, close, volume
    FROM `{GOLD}.fact_price_daily`
    WHERE symbol = '{symbol}'
      AND trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM `{GOLD}.fact_price_daily`), INTERVAL {months} MONTH)
    ORDER BY trade_date
""")
ind = query(f"""
    SELECT trade_date, close, sma20, sma50, rsi14, daily_return, volatility20, drawdown
    FROM `{GOLD}.mart_technical_indicators`
    WHERE symbol = '{symbol}'
      AND trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM `{GOLD}.mart_technical_indicators`), INTERVAL {months} MONTH)
    ORDER BY trade_date
""")

last = ind.dropna(subset=["rsi14"]).iloc[-1] if len(ind) else None
if last is not None:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Close", f"{last['close']:,.2f}")
    k2.metric("RSI14", f"{last['rsi14']:.1f}")
    k3.metric("Volatility20", f"{last['volatility20']:.2%}" if last["volatility20"] else "—")
    k4.metric("Drawdown từ đỉnh", f"{last['drawdown']:.1%}")

st.plotly_chart(candlestick_with_indicators(px, ind, symbol), use_container_width=True)

st.subheader("So với VN-Index (khoảng ngày giao nhau)")
rel = query(f"""
    SELECT trade_date, stock_cum_return, index_cum_return, excess_return
    FROM `{GOLD}.mart_stock_vs_index`
    WHERE symbol = '{symbol}' ORDER BY trade_date
""")
import plotly.graph_objects as go  # noqa: E402

fig = go.Figure()
fig.add_trace(go.Scatter(x=rel["trade_date"], y=rel["stock_cum_return"], name=symbol,
                         line=dict(color="#1f3a5f", width=1.6)))
fig.add_trace(go.Scatter(x=rel["trade_date"], y=rel["index_cum_return"], name="VN-Index",
                         line=dict(color="#98a2b3", width=1.6)))
fig.update_layout(title="Lợi suất tích lũy", yaxis_tickformat=".0%", **LAYOUT)
st.plotly_chart(fig, use_container_width=True)

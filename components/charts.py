"""Shared Plotly chart builders (white background, minimal style)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

NAVY = "#1f3a5f"
CORAL = "#f2695c"
GREY = "#98a2b3"

LAYOUT = dict(
    template="plotly_white",
    margin=dict(l=40, r=20, t=40, b=30),
    font=dict(family="Inter, Arial, sans-serif", size=13),
    hovermode="x unified",
)


def line(df: pd.DataFrame, x: str, y: str, title: str, color: str = NAVY) -> go.Figure:
    fig = go.Figure(go.Scatter(x=df[x], y=df[y], mode="lines", line=dict(color=color, width=1.6)))
    fig.update_layout(title=title, **LAYOUT)
    return fig


def candlestick_with_indicators(px: pd.DataFrame, ind: pd.DataFrame, symbol: str) -> go.Figure:
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.03, subplot_titles=(f"{symbol} — giá & SMA", "Khối lượng", "RSI14"),
    )
    fig.add_trace(go.Candlestick(
        x=px["trade_date"], open=px["open"], high=px["high"], low=px["low"], close=px["close"],
        name="OHLC", increasing_line_color="#12805c", decreasing_line_color=CORAL,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=ind["trade_date"], y=ind["sma20"], name="SMA20",
                             line=dict(color=NAVY, width=1.2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=ind["trade_date"], y=ind["sma50"], name="SMA50",
                             line=dict(color=GREY, width=1.2)), row=1, col=1)
    fig.add_trace(go.Bar(x=px["trade_date"], y=px["volume"], name="Volume",
                         marker_color=NAVY, opacity=0.6), row=2, col=1)
    fig.add_trace(go.Scatter(x=ind["trade_date"], y=ind["rsi14"], name="RSI14",
                             line=dict(color=CORAL, width=1.2)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color=GREY, row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color=GREY, row=3, col=1)
    fig.update_layout(height=760, xaxis_rangeslider_visible=False, **LAYOUT)
    return fig

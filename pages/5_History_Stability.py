import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from components.charts import CORAL, GREY, LAYOUT, NAVY  # noqa: E402
from services.bigquery_client import GOLD, query  # noqa: E402

st.set_page_config(page_title="Độ ổn định lịch sử", layout="wide")
st.title("5 · Độ ổn định lịch sử")
st.caption("Tầng Bronze có thật sự bất biến không? Nguồn giá đã điều chỉnh viết lại toàn bộ quá khứ của một mã sau mỗi lần "
           "chia cổ tức hoặc chia tách. Trang này cho thấy mức viết lại giữa các lần tải và hậu quả lên chỉ báo.")

batches = query(f"SELECT * FROM `{GOLD}.dim_batch` ORDER BY extracted_at")
stab = query(f"SELECT * FROM `{GOLD}.mart_history_stability` ORDER BY share_days_rewritten DESC, symbol")
audit = query(f"SELECT * FROM `{GOLD}.mart_indicator_audit` ORDER BY symbol")
dq = query(f"SELECT * FROM `{GOLD}.mart_dq_exchange_rules` ORDER BY rule, share_violations DESC")

multi = stab[stab["n_batches"] > 1]
off = dq[dq["rule"] == "OFF_TICK_GRID"]
k1, k2, k3, k4 = st.columns(4)
k1.metric("Số lần tải trong Bronze", len(batches), help="Gồm lần tải thật và các lần dựng lại bằng công thức (xem bảng dưới).")
k2.metric("Mã có lịch sử bị viết lại", f"{int((multi['n_days_rewritten'] > 0).sum())}/{len(multi)}")
k3.metric("Lần đổi thang giá đã phát hiện", int(stab["n_rescale_events"].sum()))
k4.metric("Mã có giá lệch lưới bước giá", f"{len(off)}/{len(stab)}")

st.subheader("Các lần tải")
b = batches.copy()
b["loại"] = b["is_reconstructed"].map({True: "dựng lại bằng công thức", False: "tải thật"})
st.dataframe(b[["batch_id", "loại", "extracted_date", "n_symbols", "n_rows", "min_trade_date", "max_trade_date"]],
             use_container_width=True, hide_index=True)

st.subheader("Xem một mã qua các lần tải")
c1, c2 = st.columns([1, 3])
sym = c1.selectbox("Mã", sorted(multi["symbol"]) or sorted(stab["symbol"]))
px = query(f"""
    SELECT trade_date, batch_id, extracted_at, close
    FROM `{GOLD}.fact_price_asof` WHERE symbol = '{sym}' ORDER BY trade_date
""")
order = px.groupby("batch_id")["extracted_at"].min().sort_values().index.tolist()
fig = go.Figure()
for i, bid in enumerate(order):
    d = px[px["batch_id"] == bid]
    last = i == len(order) - 1
    fig.add_trace(go.Scatter(x=d["trade_date"], y=d["close"], mode="lines", name=bid,
                             line=dict(color=NAVY if last else GREY, width=2 if last else 1)))
fig.update_layout(title=f"{sym}: cùng một ngày, mỗi lần tải cho một giá khác (nghìn đồng)", height=420, **LAYOUT)
c2.plotly_chart(fig, use_container_width=True)
row = stab[stab["symbol"] == sym].iloc[0]
c1.metric("Số ngày bị viết lại", f"{int(row['n_days_rewritten'])}/{int(row['n_days_multi_batch'])}")
c1.metric("Lần đổi thang giá", int(row["n_rescale_events"]))
if row["max_spread"] == row["max_spread"]:
    c1.metric("Chênh lớn nhất giữa các lần tải", f"{row['max_spread'] * 100:.1f}%")

adj = query(f"SELECT first_batch_after, detected_at, factor, cumulative_factor_to_latest FROM `{GOLD}.dim_price_adjustment` "
            f"WHERE symbol = '{sym}' ORDER BY detected_at")
if len(adj):
    st.caption("Hệ số điều chỉnh suy ra từ phép kiểm vùng chồng giữa hai lần tải liên tiếp")
    st.dataframe(adj, use_container_width=True, hide_index=True)

st.subheader("Chỉ báo nào đổi khi nguồn đổi thang giá")
st.caption("So lần tải cũ nhất với lần mới nhất của từng mã, trên các ngày chung. Chỉ báo dạng mức (giá, SMA, giá trị giao dịch) "
           "đổi theo hệ số; chỉ báo dạng tỉ lệ (lợi suất, sụt giảm từ đỉnh) gần như giữ nguyên.")
cols = ["share_close_changed", "share_sma20_changed", "share_traded_value_changed", "share_return_changed", "share_drawdown_changed"]
names = ["Giá đóng cửa", "SMA20", "Giá trị giao dịch", "Lợi suất ngày", "Sụt giảm từ đỉnh"]
avg = audit[audit["scale_factor"].sub(1).abs() > 1e-4][cols].mean() * 100
fig2 = go.Figure(go.Bar(x=avg.values, y=names, orientation="h", marker_color=[CORAL, CORAL, CORAL, NAVY, NAVY],
                        text=[f"{v:.1f}%" for v in avg.values], textposition="outside"))
fig2.update_layout(title="% số dòng đổi giá trị (trung bình các mã có đổi thang giá)", height=300, xaxis_range=[0, 115],
                   yaxis=dict(autorange="reversed"), **{**LAYOUT, "hovermode": "closest"})
st.plotly_chart(fig2, use_container_width=True)
st.dataframe(audit, use_container_width=True, hide_index=True)

st.subheader("Vi phạm luật sàn")
st.caption("OFF_TICK_GRID: giá không phải bội số bước giá, tức không phải giá từng khớp lệnh. ODD_LOT_VOLUME: khối lượng không chia hết lô 100.")
st.dataframe(dq, use_container_width=True, hide_index=True)

st.caption("Nguồn: gold.dim_batch, fact_price_asof, dim_price_adjustment, mart_history_stability, mart_indicator_audit, "
           "mart_dq_exchange_rules. Các batch recon_* được dựng lại bằng công thức từ snapshot 03/11/2026, không phải lần tải thật.")

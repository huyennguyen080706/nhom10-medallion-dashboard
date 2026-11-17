import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from components.charts import CORAL, GREY, LAYOUT, NAVY  # noqa: E402
from services.bigquery_client import GOLD, ML, query  # noqa: E402

st.set_page_config(page_title="Dự báo và giám sát mô hình", layout="wide")
st.title("6 · Dự báo biến động và giám sát mô hình")
st.caption("Mô hình huấn luyện ngay trong kho bằng BigQuery ML. Đích: log độ biến động (Garman–Klass) của phiên kế tiếp. "
           "Đây là công cụ theo dõi rủi ro phục vụ học tập, không phải khuyến nghị đầu tư.")

models = query(f"SELECT * FROM `{ML}.eval_models`")
pol = query(f"SELECT * FROM `{ML}.eval_retrain_policies` ORDER BY so_lan_huan_luyen")
mon = query(f"SELECT * FROM `{ML}.monitoring_monthly` ORDER BY month")
age = query(f"SELECT * FROM `{ML}.eval_model_age` ORDER BY tuoi")
reg = query(f"SELECT model_version, spec, train_cutoff, n_train_rows, train_mae, train_seconds, bytes_processed FROM `{ML}.model_registry` ORDER BY spec, train_cutoff")

best = models.sort_values("mae").iloc[0]
k1, k2, k3, k4 = st.columns(4)
k1.metric("Mô hình tốt nhất ngoài mẫu", best["mo_hinh"])
k2.metric("MAE ngoài mẫu", f"{best['mae']:.4f}")
k3.metric("Giảm so với mốc tốt nhất", f"{best['giam_mae_so_moc_tot_nhat'] * 100:.1f}%")
k4.metric("Phiên bản trong sổ đăng ký", len(reg))

dep = query(f"SELECT deployed_month, model_version, reason, ratio, is_production FROM `{ML}.model_deployments` ORDER BY deployed_month")
nxt = query(f"SELECT risk_rank, symbol, as_of_date, vol_today_pct, vol_pred_pct, model_version FROM `{ML}.forecast_next_session` ORDER BY risk_rank")
prod = dep[dep["is_production"]].iloc[-1]

st.subheader("Triển khai: bản đang chạy và dự báo cho phiên kế tiếp")
d1, d2, d3 = st.columns(3)
d1.metric("Bản đang chạy", prod["model_version"])
d2.metric("Triển khai từ", str(prod["deployed_month"]))
d3.metric("Số lần triển khai", len(dep))
c_a, c_b = st.columns([3, 2])
top = nxt.head(15).iloc[::-1]
figd = go.Figure()
figd.add_trace(go.Bar(y=top["symbol"], x=top["vol_pred_pct"], orientation="h", marker_color=CORAL, name="Dự báo phiên kế tiếp"))
figd.add_trace(go.Scatter(y=top["symbol"], x=top["vol_today_pct"], mode="markers", marker=dict(color=NAVY, size=8), name="Phiên gần nhất"))
figd.update_layout(title=f"15 mã có độ biến động dự báo cao nhất (%, tính tới {nxt['as_of_date'].iloc[0]})", height=460, **{**LAYOUT, "hovermode": "closest"})
c_a.plotly_chart(figd, use_container_width=True)
c_b.caption("Lịch sử triển khai (luật: sai số tháng trước vượt 5% sai số trong mẫu)")
c_b.dataframe(dep, use_container_width=True, hide_index=True)

st.subheader("Mô hình so với mốc đơn giản")
st.dataframe(models, use_container_width=True, hide_index=True)

st.subheader("Sai số theo tháng của mô hình đang chạy")
fig = go.Figure()
fig.add_trace(go.Scatter(x=mon["month"], y=mon["mae_ewma"], name="Mốc: trung bình mũ", line=dict(color=GREY, width=1.4)))
fig.add_trace(go.Scatter(x=mon["month"], y=mon["mae_har"], name="HAR", line=dict(color=NAVY, width=1.6)))
fig.add_trace(go.Scatter(x=mon["month"], y=mon["mae_harx"], name="HAR-X", line=dict(color=CORAL, width=1.8)))
fig.update_layout(title="MAE ngoài mẫu theo tháng (huấn luyện lại đầu mỗi tháng)", height=380, **LAYOUT)
st.plotly_chart(fig, use_container_width=True)

c1, c2 = st.columns(2)
c1.subheader("Chính sách huấn luyện lại")
c1.dataframe(pol, use_container_width=True, hide_index=True)
c2.subheader("Sai số theo tuổi mô hình")
fig2 = go.Figure(go.Scatter(x=age["tuoi"], y=age["ti_so"], mode="lines", line=dict(color=NAVY, width=2)))
fig2.add_hline(y=1.0, line_dash="dot", line_color=GREY)
fig2.update_layout(title="MAE của phiên bản cũ / MAE của phiên bản vừa huấn luyện", xaxis_title="Tuổi mô hình (tháng)", height=340, **LAYOUT)
c2.plotly_chart(fig2, use_container_width=True)

st.subheader("Dự báo cho một mã")
syms = query(f"SELECT DISTINCT symbol FROM `{GOLD}.feat_volatility_daily` ORDER BY symbol")["symbol"].tolist()
sym = st.selectbox("Mã", syms, index=syms.index("FPT") if "FPT" in syms else 0)
d = query(f"""
    SELECT p.trade_date, p.y1 AS thuc_te, p.y_pred AS du_bao
    FROM `{ML}.pred_harx` p
    WHERE p.symbol = '{sym}' AND DATE_TRUNC(p.trade_date, MONTH) = p.train_cutoff
    ORDER BY p.trade_date
""")
fig3 = go.Figure()
fig3.add_trace(go.Scatter(x=d["trade_date"], y=d["thuc_te"], name="Thực tế", line=dict(color=GREY, width=1)))
fig3.add_trace(go.Scatter(x=d["trade_date"], y=d["du_bao"], name="Dự báo HAR-X", line=dict(color=CORAL, width=1.8)))
fig3.update_layout(title=f"{sym}: log độ biến động phiên kế tiếp, thực tế và dự báo", height=380, **LAYOUT)
st.plotly_chart(fig3, use_container_width=True)

st.subheader("Hồ sơ rủi ro: phân cụm cổ phiếu")
clu = query(f"SELECT * FROM `{ML}.stock_clusters` ORDER BY cluster_id, symbol")
st.dataframe(clu, use_container_width=True, hide_index=True)

st.subheader("Sổ đăng ký mô hình")
st.dataframe(reg, use_container_width=True, hide_index=True)
st.caption("Nguồn: ml.model_registry, pred_harx, eval_models, eval_retrain_policies, eval_model_age, monitoring_monthly, stock_clusters.")

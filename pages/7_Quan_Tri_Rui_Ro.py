import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from components.charts import CORAL, GREY, LAYOUT, NAVY  # noqa: E402
from services.bigquery_client import ML, query  # noqa: E402



def vn(x: float, n: int = 1) -> str:
    return f"{x:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.set_page_config(page_title="Quản trị rủi ro", layout="wide")
st.title("7 · Hạn mức rủi ro từ dự báo biến động")
st.caption("Value-at-Risk (VaR) một phiên = phân vị của lợi suất chuẩn hoá trên 250 phiên trước × độ biến động do mô hình trong kho dự báo. "
           "Hạn mức được kiểm định ngược từ 01/2024. Đây là công cụ theo dõi rủi ro phục vụ học tập, không phải khuyến nghị đầu tư.")

tong = query(f"SELECT * FROM `{ML}.risk_var_summary` ORDER BY muc, phuong_an")
dm = query(f"SELECT * FROM `{ML}.risk_var_portfolio` ORDER BY muc, phuong_an")
nx = query(f"SELECT * FROM `{ML}.risk_var_next_session` ORDER BY var95_pct DESC")
chuoi = query(f"SELECT * FROM `{ML}.risk_var_portfolio_daily` ORDER BY trade_date")

a95 = tong[(tong["muc"] == "95") & tong["phuong_an"].str.startswith("HAR-X")].iloc[0]
d95 = dm[(dm["muc"] == "95") & dm["phuong_an"].str.startswith("HAR-X")].iloc[0]
k1, k2, k3, k4 = st.columns(4)
k1.metric("Tỉ lệ vượt VaR 95% (từng mã)", vn(a95['ti_le_vuot'] * 100, 2) + "%", help="Danh nghĩa 5%")
k2.metric("Số mã không bị kiểm định Kupiec bác", f"{int(a95['so_ma_khong_bi_bac'])}/40")
k3.metric("Danh mục: số phiên vượt VaR 95%", f"{int(d95['so_lan_vuot'])}/{int(d95['n'])}")
k4.metric("Danh mục: p của kiểm định Kupiec", vn(d95['kupiec_p'], 2))

st.subheader("Hạn mức cho phiên kế tiếp")
c1, c2 = st.columns([2, 3])
ma = c1.selectbox("Mã", sorted(nx["symbol"]), index=sorted(nx["symbol"]).index("HPG") if "HPG" in set(nx["symbol"]) else 0)
tien = c1.number_input("Giá trị nắm giữ (triệu đồng)", min_value=1.0, value=1000.0, step=100.0)
r = nx[nx["symbol"] == ma].iloc[0]
c1.metric("Mức lỗ một phiên, tin cậy 95%", vn(tien * r['var95_pct'] / 100) + " triệu", help=f"{r['var95_pct']:.2f}% giá trị nắm giữ")
c1.metric("Mức lỗ một phiên, tin cậy 99%", vn(tien * r['var99_pct'] / 100) + " triệu", help=f"{r['var99_pct']:.2f}% giá trị nắm giữ")
if bool(r["cham_bien_do"]):
    c1.info("Mã này hay chạm sàn nên hạn mức tính ra vượt biên độ; số hiển thị đã được chặn ở biên độ sàn.")
top = nx.head(15).iloc[::-1]
f1 = go.Figure()
f1.add_trace(go.Bar(y=top["symbol"], x=top["var99_pct"], orientation="h", marker_color=GREY, name="VaR 99%"))
f1.add_trace(go.Bar(y=top["symbol"], x=top["var95_pct"], orientation="h", marker_color=CORAL, name="VaR 95%"))
f1.update_layout(title=f"15 mã có hạn mức lỗ lớn nhất (% giá trị nắm giữ, tính tới {nx['as_of_date'].iloc[0]})", barmode="overlay", height=460, **{**LAYOUT, "hovermode": "closest"})
c2.plotly_chart(f1, use_container_width=True)

st.subheader("Kiểm định ngược trên danh mục 40 mã chia đều")
vuot = chuoi[chuoi["r"] < chuoi["var95_A"]]
f2 = go.Figure()
f2.add_trace(go.Bar(x=chuoi["trade_date"], y=chuoi["r"] * 100, marker_color=GREY, name="Lợi suất danh mục (%)"))
f2.add_trace(go.Scatter(x=chuoi["trade_date"], y=chuoi["var95_A"] * 100, line=dict(color=NAVY, width=1.6), name="VaR 95% theo HAR-X"))
f2.add_trace(go.Scatter(x=vuot["trade_date"], y=vuot["r"] * 100, mode="markers", marker=dict(color=CORAL, size=8), name=f"Phiên vượt hạn mức ({len(vuot)})"))
f2.update_layout(height=400, yaxis_title="%", **LAYOUT)
st.plotly_chart(f2, use_container_width=True)

c3, c4 = st.columns(2)
c3.caption("Từng mã (28.080 quan sát)")
c3.dataframe(tong, use_container_width=True, hide_index=True)
c4.caption("Danh mục chia đều (702 phiên)")
c4.dataframe(dm, use_container_width=True, hide_index=True)

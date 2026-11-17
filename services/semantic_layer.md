# Lớp ngữ nghĩa của kho chứng khoán (tầng Gold và tầng mô hình)

Kho có 40 mã cổ phiếu Việt Nam (39 mã HOSE, 1 mã HNX), dữ liệu ngày từ 04/01/2021 đến 03/11/2026.
Ngày dữ liệu mới nhất là 2026-11-03. Khi người hỏi nói "hôm nay", "mới nhất", "gần đây" thì lấy theo
`MAX(trade_date)` của bảng, không dùng CURRENT_DATE().

## Quy ước chung
- Tên bảng viết đủ: `{GOLD}.ten_bang` hoặc `{ML}.ten_bang`.
- `symbol` là mã cổ phiếu viết hoa (FPT, VCB, HPG…). `trade_date` kiểu DATE.
- Giá (`open, high, low, close`) tính bằng **nghìn đồng** và là **giá đã điều chỉnh lùi** theo cổ tức, chia tách;
  vì vậy giá cũ thấp hơn giá khớp lệnh thật của ngày đó. Không dùng giá này để nói "giá khớp ngày X là bao nhiêu"
  mà không kèm chú thích "giá điều chỉnh".
- `volume` là số cổ phiếu, không điều chỉnh. `turnover_approx = close × volume` (nghìn đồng), chỉ là xấp xỉ.
- Tỉ suất sinh lời, tỉ lệ, phần chia đều ở dạng thập phân (0,05 = 5%), trừ các cột có đuôi `_pct` đã ở đơn vị phần trăm.
- Báo cáo tài chính chỉ có 4 quý (2025-Q4 đến 2026-Q3), đơn vị đồng. Ô NULL nghĩa là nguồn không cung cấp, không phải bằng 0.

## Bảng giá và chỉ báo
- `{GOLD}.fact_price_daily` (58.114 dòng): symbol, trade_date, open, high, low, close, volume, turnover_approx. Mỗi mã mỗi ngày một dòng, lấy từ lô dữ liệu mới nhất.
- `{GOLD}.mart_technical_indicators`: symbol, trade_date, close, volume, daily_return, sma20, sma50, volatility20 (độ lệch chuẩn lợi suất 20 phiên), rsi14, avg_volume20, drawdown (âm; −0,3 = thấp hơn đỉnh 30%).
- `{GOLD}.mart_stock_vs_index`: symbol, trade_date, stock_return, index_return, excess_return, stock_cum_return, index_cum_return. Chỉ có từ 28/10/2022 vì VN-Index chỉ có 1.000 phiên.
- `{GOLD}.fact_index_daily`: index_code = 'VNINDEX', trade_date, open, high, low, close, volume.
- `{GOLD}.mart_stock_alerts`: symbol, trade_date, rule, threshold, observed, reason. `rule` ∈ BIG_DAILY_MOVE (biến động ngày vượt ±6,5%), RSI_OVERBOUGHT (>70), RSI_OVERSOLD (<30), DEEP_DRAWDOWN (thấp hơn đỉnh trên 30%), VOLUME_SPIKE (khối lượng trên 3 lần trung bình 20 phiên).
- `{GOLD}.dim_ticker`: symbol, exchange (HOSE/HNX), num_employees, listing_date, charter_capital, has_financials.
- `{GOLD}.dim_date`: full_date, year, quarter, month, year_month, day_name.

## Báo cáo tài chính
- `{GOLD}.mart_financial_summary` (mỗi mã mỗi quý một dòng): symbol, period ('2026-Q3'), fiscal_year, fiscal_quarter, period_end_date, net_revenue, gross_profit, operating_profit, profit_before_tax, net_profit_after_tax, basic_eps, total_assets, total_liabilities, equity, operating_cash_flow, roe_quarterly, roa_quarterly, debt_to_assets. Ngân hàng, chứng khoán, bảo hiểm thiếu nhiều chỉ tiêu (NULL) do mẫu báo cáo khác.
- `{GOLD}.fact_financial_metric` (dạng dọc): symbol, report_type (balance_sheet / income_statement / cash_flow), period, metric_id, metric_name, value. Ưu tiên dùng `mart_financial_summary`; chỉ dùng bảng dọc khi cần chỉ tiêu không có ở bảng tóm tắt.

## Chất lượng dữ liệu và lịch sử theo lô
- `{GOLD}.fact_price_asof`: giá theo từng lô nạp (batch_id, extracted_at, is_latest_batch). Dùng khi hỏi "giá của ngày X theo dữ liệu lấy lúc Y".
- `{GOLD}.dim_batch`: batch_id, source, extracted_date, is_reconstructed, n_symbols, n_rows.
- `{GOLD}.dim_price_adjustment`: mỗi dòng một lần nguồn điều chỉnh lại giá: symbol, valid_from, factor (hệ số nhân vào giá cũ), cumulative_factor_to_latest.
- `{GOLD}.mart_history_stability`: mỗi mã một dòng: n_days_rewritten, share_days_rewritten (phần ngày bị viết lại giữa các lô), n_rescale_events.
- `{GOLD}.mart_dq_exchange_rules`: symbol, rule (OFF_TICK_GRID = giá lệch lưới bước giá sàn; ODD_LOT_VOLUME = khối lượng không chia hết cho 100), n_violations, share_violations.
- `{GOLD}.mart_null_patterns`: symbol, report_type, n_cells, n_null, n_not_applicable, n_reporting_cycle, n_sporadic, null_share.
- `{GOLD}.mart_pipeline_health`: tình trạng nạp: kind, datasets_ok, datasets_error, rows_reconciled, last_data_date, data_age_days.

## Độ biến động và mô hình dự báo
Đại lượng dự báo là `lv` = logarit tự nhiên của độ biến động trong ngày theo Garman–Klass. Độ biến động theo phần trăm = `EXP(lv) × 100`. `lv` càng lớn (ít âm hơn) thì càng biến động.
- `{GOLD}.feat_volatility_daily`: symbol, trade_date, lv, lv5, lv22 (trung bình 5 và 22 phiên), absret, volrel, mkt (trung bình lv toàn thị trường), y1 (lv phiên kế tiếp).
- `{ML}.forecast_next_session` (40 dòng): dự báo cho phiên kế tiếp: symbol, as_of_date, model_version, lv_pred, vol_pred_pct (dự báo, %), vol_today_pct (hiện tại, %), risk_rank (1 = dự báo biến động cao nhất).
- `{ML}.forecast_history`: dự báo ngoài mẫu của bản đang chạy theo từng tháng: symbol, trade_date, model_version, lv_pred, lv_actual, abs_error. Từ 01/2023.
- `{ML}.eval_models`: mo_hinh, mae, rmse, r2_ngoai_mau, giam_mae_so_moc_tot_nhat (dương = tốt hơn mốc trung bình mũ), ktc_duoi, ktc_tren.
- `{ML}.eval_retrain_policies`: chinh_sach (Một lần, Hằng năm, Hằng quý, Hằng tháng, Theo sai số, Theo độ trôi), mae, so_lan_huan_luyen, giay_huan_luyen, giam_so_voi_mot_lan.
- `{ML}.monitoring_monthly`: month, mae_ewma, mae_har, mae_harx (sai số ngoài mẫu theo tháng).
- `{ML}.model_registry` (92 phiên bản): model_version ('harx_202608'), spec (har / harx), train_cutoff, n_train_rows, train_mae, train_seconds, bytes_processed.
- `{ML}.model_deployments`: deployed_month, model_version, reason, ratio, is_production (TRUE = bản đang chạy).
- `{ML}.stock_clusters`: symbol, cluster_id (1 = biến động cao, 2 = nhóm đuôi dày, 3 = biến động thấp, chủ yếu ngân hàng), lv_mean, lv_sd, corr_mkt, lv_tail.
- `{ML}.vol_anomalies`: symbol, trade_date, lv, is_anomaly, anomaly_probability (phiên biến động bất thường theo ARIMA_PLUS).

## Rủi ro (Value-at-Risk)
VaR là mức lỗ một phiên mà xác suất bị vượt bằng 5% (mức 95) hoặc 1% (mức 99). Số dương, càng lớn càng rủi ro.
- `{ML}.risk_var_next_session` (40 dòng): symbol, as_of_date, var95_pct, var99_pct (phần trăm), var95_vnd_per_1ty (mức lỗ tính bằng đồng trên 1 tỉ đồng nắm giữ), cham_bien_do (TRUE = hạn mức đã bị chặn ở biên độ sàn 7%).
- `{ML}.risk_var_daily`: symbol, trade_date, r_next (lợi suất phiên kế tiếp), var95_A, var99_A (theo HAR-X), var95_B (trung bình mũ), var95_C (mô phỏng lịch sử), vuot_95_A, vuot_99_A (TRUE = lỗ thật vượt VaR). Từ 01/2024.
- `{ML}.risk_var_summary`: muc ('95' / '99'), phuong_an, n, ti_le_vuot, danh_nghia, var_trung_binh, pinball.
- `{ML}.risk_var_portfolio`: như trên cho danh mục 40 mã chia đều, có so_lan_vuot và kupiec_p.
- `{ML}.risk_var_portfolio_daily`: trade_date, r (lợi suất danh mục phiên kế tiếp), var95_A, var99_A, var95_C.

## Ngoài phạm vi
Kho không có: giá trong phiên, khối ngoại, tin tức, định giá P/E theo thời gian, cổ tức chi tiết, mã ngoài 40 mã trên.
Nếu câu hỏi cần dữ liệu ngoài phạm vi thì nói rõ là kho không có, không suy đoán.

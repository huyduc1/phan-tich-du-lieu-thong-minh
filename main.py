# python -m streamlit run main.py
import streamlit as st
import pandas as pd
import os
from data_crawler import scrape_data
from data_processor import load_data, preprocess_data, FILE_LOCAL
import visualizations as viz

st.set_page_config(page_title="Hệ thống Giám sát BA", layout="wide")
st.title("British Airways Data Monitoring System")

# 1. LOAD & PREPROCESS
df = load_data()
if df is not None:
    df = preprocess_data(df)

# 2. SIDEBAR MANAGEMENT
with st.sidebar:
    st.header("⚙️ Quản lý hệ thống")
    if not os.path.exists(FILE_LOCAL):
        if st.button("🚀 Khởi tạo dữ liệu"):
            new_df = scrape_data(max_pages=10)
            if not new_df.empty:
                new_df.to_csv(FILE_LOCAL, index=False, encoding="utf-8-sig")
                st.rerun()
    else:
        if st.button("🔄 Cập nhật dữ liệu mới"):
            df_hist = pd.read_csv(FILE_LOCAL)
            last_date = pd.to_datetime(df_hist["Date"]).max()
            new_df = scrape_data(max_pages=40, checkpoint_date=last_date)
            if not new_df.empty:
                pd.concat([new_df, df_hist]).drop_duplicates(subset=["Header", "Date"]).to_csv(FILE_LOCAL, index=False)
                st.cache_data.clear()
                st.rerun()

    # 3. FILTERS
    st.markdown("---")
    st.header("🔍 Bộ lọc")
    if df is not None:
        sel_seats = st.pills("💺 Hạng ghế", options=sorted(df["Seat Type"].dropna().unique()), default=list(df["Seat Type"].dropna().unique()), selection_mode="multi")
        sel_rec = st.pills("👍 Đề xuất", options=["yes", "no"], default=["yes", "no"], selection_mode="multi")
        sel_aircraft = st.selectbox("✈️ Máy bay", ["Tất cả"] + sorted(df["Aircraft"].dropna().unique().tolist()))

# 4. MAIN DISPLAY
if df is not None:
    # Áp dụng lọc
    df_filt = df[df["Seat Type"].isin(sel_seats) & df["Recommended"].isin(sel_rec)]
    if sel_aircraft != "Tất cả":
        df_filt = df_filt[df_filt["Aircraft"] == sel_aircraft]

    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Số lượng đánh giá", len(df_filt))
    c2.metric("Rating trung bình", f"{df_filt['Overall_Rating'].mean():.2f}/10")
    c3.metric("Cập nhật cuối", str(df["Date"].max().date()))

    # Dashboard
    tab1, tab2 = st.tabs(["📊 Biểu đồ phân tích", "📋 Dữ liệu chi tiết"])
    with tab1:
        viz.plot_combined_trend(df_filt)
        viz.plot_service_comparison(df_filt)
    with tab2:
        st.dataframe(df_filt.sort_values("Date", ascending=False), use_container_width=True)
        st.download_button("⬇️ Tải CSV", df_filt.to_csv(index=False).encode("utf-8-sig"), "ba_filt.csv")
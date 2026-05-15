import streamlit as st
import pandas as pd
from data_processor import load_data, preprocess_data, apply_advanced_analytics
import sidebar
import visualizations as viz

st.set_page_config(page_title="BA Monitoring", layout="wide")
st.title("✈️ British Airways Data Monitoring System")

df = load_data()
if df is not None:
    df = preprocess_data(df)
    
    with st.sidebar:
        sidebar.render_management_panel()
        filters = sidebar.render_filters(df)

    # Áp dụng ML trên dữ liệu sạch ban đầu
    df_with_ml = apply_advanced_analytics(df)
    df_filt = df_with_ml.copy()

    # Logic lọc dữ liệu
    # Dùng trực tiếp .isin() - khi list rỗng sẽ trả về 0 hàng (đúng hành vi)
    df_filt = df_filt[df_filt["Seat Type"].isin(filters["seats"])] if filters["seats"] is not None else df_filt.iloc[0:0]
    df_filt = df_filt[df_filt["Type Of Traveller"].isin(filters["travellers"])] if filters["travellers"] is not None else df_filt.iloc[0:0]

    # Lọc Rating
    df_filt = df_filt[(df_filt["Overall_Rating"] >= filters["rating_range"][0]) &
                      (df_filt["Overall_Rating"] <= filters["rating_range"][1])]

    # Lọc Recommended (pills - list rỗng = không chọn gì = 0 kết quả)
    df_filt = df_filt[df_filt["Recommended"].isin(filters["recommended"])] if filters["recommended"] is not None else df_filt.iloc[0:0]

    # Lọc Loại máy bay
    if filters["aircraft"] != "Tất cả":
        df_filt = df_filt[df_filt["Aircraft"] == filters["aircraft"]]

    # Lọc Thành phố đi (Origin)
    if filters["origin"] != "Tất cả" and "Origin" in df_filt.columns:
        df_filt = df_filt[df_filt["Origin"] == filters["origin"]]

    # Lọc Thành phố đến (Destination)
    if filters["destination"] != "Tất cả" and "Destination" in df_filt.columns:
        df_filt = df_filt[df_filt["Destination"] == filters["destination"]]

    # Lọc Khoảng thời gian
    if len(filters["date_range"]) == 2:
        start_date, end_date = filters["date_range"]
        df_filt = df_filt[
            (df_filt["Date"].dt.date >= start_date) &
            (df_filt["Date"].dt.date <= end_date)
        ]

    # Hiển thị Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Tổng mẫu", len(df))
    m2.metric("Sau khi lọc", len(df_filt))
    m3.metric("Rating TB", f"{df_filt['Overall_Rating'].mean():.1f}" if not df_filt.empty else "N/A")

    if df_filt.empty:
        st.warning("Không tìm thấy dữ liệu phù hợp bộ lọc.")
    else:
        tab1, tab2 = st.tabs(["📊 Phân tích", "📋 Dữ liệu"])
        with tab1:
            viz.plot_combined_trend(df_filt)
            c1, c2 = st.columns(2)
            with c1: viz.plot_seat_rating(df_filt)
            with c2: viz.plot_traveller_pie(df_filt)
            viz.plot_service_comparison(df_filt)
            viz.plot_pca_clusters(df_filt)
            viz.plot_heatmap(df_filt)
        with tab2:
            st.dataframe(df_filt.head(50), use_container_width=True)
else:
    st.error("Không thể tải dữ liệu.")
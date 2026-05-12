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

    # Logic lọc dữ liệu (Rút gọn)
    if filters["seats"]:
        df_filt = df_filt[df_filt["Seat Type"].isin(filters["seats"])]
    if filters["travellers"]:
        df_filt = df_filt[df_filt["Type Of Traveller"].isin(filters["travellers"])]
    
    # Lọc Rating
    df_filt = df_filt[(df_filt["Overall_Rating"] >= filters["rating_range"][0]) & 
                      (df_filt["Overall_Rating"] <= filters["rating_range"][1])]

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
        with tab2:
            st.dataframe(df_filt.head(50), use_container_width=True)
else:
    st.error("Không thể tải dữ liệu.")
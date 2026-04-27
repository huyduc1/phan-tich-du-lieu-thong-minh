import streamlit as st
import pandas as pd
import plotly.express as px

# Cấu hình trang
st.set_page_config(page_title="Airline Monitor", layout="wide")

# 1. Hàm load dữ liệu
@st.cache_data
def load_data():
    df = pd.read_csv("ba_detailed_reviews.csv")
    df['Date'] = pd.to_datetime(df['Date'])
    return df

try:
    df = load_data()

    # --- SIDEBAR: Bộ lọc (Filters) ---
    st.sidebar.header("Bộ lọc dữ liệu")
    seat_type = st.sidebar.multiselect("Hạng ghế:", options=df["Seat Type"].unique(), default=df["Seat Type"].unique())
    df_selection = df[df["Seat Type"].isin(seat_type)]

    # --- MAIN PAGE: Các chỉ số chính (KPIs) ---
    st.title("✈️ British Airways Real-time Monitoring")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tổng số đánh giá", len(df_selection))
    with col2:
        avg_rating = df_selection["Overall_Rating"].mean()
        st.metric("Điểm trung bình", f"{avg_rating:.2f}/10")
    with col3:
        rec_rate = (df_selection["Recommended"] == "Yes").mean() * 100
        st.metric("Tỷ lệ đề xuất", f"{rec_rate:.1f}%")

    # --- BIỂU ĐỒ THEO DÕI (Monitoring Charts) ---
    st.markdown("---")
    st.subheader("📈 Xu hướng hài lòng theo thời gian")
    
    # Tính trung bình động (MA) để theo dõi xu hướng
    df_trend = df_selection.resample('M', on='Date')['Overall_Rating'].mean().reset_index()
    fig_trend = px.line(df_trend, x='Date', y='Overall_Rating', title="Biến động Overall Rating (Theo tháng)")
    st.plotly_chart(fig_trend, use_container_width=True)

    # --- PHÂN TÍCH CHI TIẾT (Service Breakdown) ---
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📊 Điểm số theo dịch vụ")
        service_cols = ['Seat Comfort', 'Cabin Staff Service', 'Food & Beverages', 'Inflight Entertainment', 'Ground Service']
        avg_services = df_selection[service_cols].mean().sort_values()
        fig_service = px.bar(avg_services, orientation='h', labels={'value':'Điểm (1-5)', 'index':'Dịch vụ'})
        st.plotly_chart(fig_service)

    with col_right:
        st.subheader("💬 Danh sách đánh giá mới nhất")
        st.dataframe(df_selection[['Date', 'Header', 'Overall_Rating']].head(10))

except FileNotFoundError:
    st.error("Không tìm thấy file dữ liệu. Hãy chạy script cào dữ liệu trước!")

import streamlit as st
import pandas as pd
import plotly.express as px

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Airline Monitor", layout="wide")

# --- KẾT NỐI DỮ LIỆU (Google Sheets) ---
# Lưu ý: Thay ID chính xác của bạn vào đây
SHEET_URL = "https://docs.google.com/spreadsheets/d/1d2JeOC7r50ISTu-9LoM9DPF6PAbQ207FtiG8y5G7vH0/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        # Đọc trực tiếp từ Google Sheets
        df = pd.read_csv(SHEET_URL)
        # Ép kiểu dữ liệu
        df['Date'] = pd.to_datetime(df['Date'])
        # Đảm bảo các cột điểm số là kiểu số (numeric)
        numeric_cols = ['Overall_Rating', 'Seat Comfort', 'Cabin Staff Service', 
                        'Food & Beverages', 'Inflight Entertainment', 'Ground Service']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Lỗi kết nối dữ liệu: {e}")
        return None

# --- THỰC THI APP ---
df = load_data()

if df is not None:
    # --- SIDEBAR: Bộ lọc (Filters) ---
    st.sidebar.header("Bộ lọc dữ liệu")
    
    # Lọc theo Hạng ghế
    all_seats = df["Seat Type"].dropna().unique()
    seat_type = st.sidebar.multiselect("Hạng ghế:", options=all_seats, default=all_seats)
    
    # Lọc theo Khuyên dùng (Yes/No)
    rec_filter = st.sidebar.radio("Khách hàng khuyên dùng:", ["Tất cả", "Yes", "No"])

    # Áp dụng bộ lọc
    df_selection = df[df["Seat Type"].isin(seat_type)]
    if rec_filter != "Tất cả":
        df_selection = df_selection[df_selection["Recommended"] == rec_filter]

    # --- MAIN PAGE: KPIs ---
    st.title("✈️ British Airways Real-time Monitoring")
    st.markdown(f"**Nguồn dữ liệu:** Google Sheets (Cập nhật mỗi 10 phút)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tổng số đánh giá", len(df_selection))
    with col2:
        avg_rating = df_selection["Overall_Rating"].mean()
        st.metric("Điểm trung bình", f"{avg_rating:.2f}/10" if not pd.isna(avg_rating) else "N/A")
    with col3:
        rec_rate = (df_selection["Recommended"] == "Yes").mean() * 100
        st.metric("Tỷ lệ đề xuất", f"{rec_rate:.1f}%" if not pd.isna(rec_rate) else "0%")

    # --- BIỂU ĐỒ MONITORING ---
    st.markdown("---")
    
    # 1. Biểu đồ xu hướng
    st.subheader("📈 Xu hướng hài lòng theo thời gian")
    df_trend = df_selection.resample('M', on='Date')['Overall_Rating'].mean().reset_index()
    fig_trend = px.line(df_trend, x='Date', y='Overall_Rating', 
                        title="Biến động Overall Rating (Trung bình theo tháng)",
                        markers=True)
    st.plotly_chart(fig_trend, use_container_width=True)

    # 2. Phân tích chi tiết dịch vụ
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📊 Điểm số theo dịch vụ")
        service_cols = ['Seat Comfort', 'Cabin Staff Service', 'Food & Beverages', 
                        'Inflight Entertainment', 'Ground Service']
        # Kiểm tra xem các cột có tồn tại không trước khi tính mean
        existing_cols = [c for c in service_cols if c in df_selection.columns]
        avg_services = df_selection[existing_cols].mean().sort_values()
        fig_service = px.bar(avg_services, orientation='h', 
                             labels={'value':'Điểm (1-5)', 'index':'Dịch vụ'},
                             color=avg_services.values, color_continuous_scale='RdYlGn')
        st.plotly_chart(fig_service)

    with col_right:
        st.subheader("💬 Danh sách đánh giá mới nhất")
        st.dataframe(df_selection[['Date', 'Header', 'Overall_Rating']].sort_values(by='Date', ascending=False).head(10), 
                     use_container_width=True)
else:
    st.warning("Vui lòng kiểm tra lại quyền chia sẻ (Share) của file Google Sheets. Đảm bảo chế độ: 'Anyone with the link can view'.")

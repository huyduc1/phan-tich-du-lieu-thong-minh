# cd "C:\Users\Admin\OneDrive - VNU-HCMUS\phân tích dữ liệu thông minh"
#  python -m streamlit run app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
import time
import os

# --- CẤU HÌNH ---
GSHEET_ID = "1F19cUq04OUQOs9nz097pCJ1uZ0Kbx1HD648dvmmixdg"
CLOUD_URL = f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}/export?format=csv"

# File lưu tại máy (Đảm bảo tên file thống nhất)
FILE_LOCAL = "ba_data.csv"
BASE_URL = "https://www.airlinequality.com/airline-reviews/british-airways/page/"

st.set_page_config(page_title="Hệ thống Giám sát Dữ liệu Airline", layout="wide")

# --- 1. HÀM LOAD DỮ LIỆU ---
@st.cache_data(ttl=300)
def load_data():
    # Kiểm tra file local trước
    if os.path.exists(FILE_LOCAL):
        try:
            return pd.read_csv(FILE_LOCAL)
        except:
            return None
    # Nếu không có file local (trên Web), đọc từ GSheet
    else:
        try:
            return pd.read_csv(CLOUD_URL)
        except Exception as e:
            st.error(f" Không thể kết nối Cloud. Lỗi: {e}")
            return None

# --- 2. HÀM CÀO DỮ LIỆU (TÍCH HỢP LOGIC CODE A) ---
def scrape_data(max_pages=40, checkpoint_date=None):
    all_reviews = []
    found_stop_point = False
    progress_bar = st.progress(0)
    status_text = st.empty()

    headers = {"User-Agent": "Mozilla/5.0"}

    for page in range(1, max_pages + 1):
        if found_stop_point:
            break

        status_text.text(f" Đang quét trang {page}...")
        url = f"{BASE_URL}{page}/?sortby=post_date%3ADesc&pagesize=100"

        try:
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.content, "html.parser")
            articles = soup.find_all("article", {"itemprop": "review"})

            if not articles:
                break

            for item in articles:
                # Lấy ngày để kiểm tra checkpoint
                date_tag = item.find("time", {"itemprop": "datePublished"})
                if not date_tag:
                    continue

                date_str = date_tag["datetime"]
                current_date = pd.to_datetime(date_str)

                # DỪNG KHI GẶP DATA ĐÃ CÓ TRONG MÁY
                if checkpoint_date and current_date <= checkpoint_date:
                    found_stop_point = True
                    break

                # 1. Thông tin cơ bản (Từ Code A)
                review_dict = {
                    "Date": date_str,
                    "Overall_Rating": item.find("span", {"itemprop": "ratingValue"}).text if item.find("span", {"itemprop": "ratingValue"}) else None,
                    "Header": item.find("h2", {"class": "text_header"}).text.strip() if item.find("h2", {"class": "text_header"}) else None,
                    "Review_Body": item.find("div", {"class": "text_content"}).text.strip() if item.find("div", {"class": "text_content"}) else None
                }

                # 2. Bóc tách bảng chi tiết (Logic mạnh mẽ từ Code A)
                review_stats = item.find("table", {"class": "review-ratings"})
                if review_stats:
                    rows = review_stats.find_all("tr")
                    for row in rows:
                        header_node = row.find("td", {"class": "review-rating-header"})
                        if header_node:
                            key = header_node.text.strip()

                            # Kiểm tra giá trị text (Value) hoặc sao (Stars)
                            value_cell = row.find("td", {"class": "review-value"})
                            stars_cell = row.find("td", {"class": "review-rating-stars"})

                            if value_cell:
                                review_dict[key] = value_cell.text.strip()
                            elif stars_cell:
                                filled_stars = stars_cell.find_all("span", {"class": "star fill"})
                                review_dict[key] = len(filled_stars)

                all_reviews.append(review_dict)

            progress_bar.progress(page / max_pages if not found_stop_point else 1.0)
            time.sleep(2)

        except Exception as e:
            st.error(f"Lỗi tại trang {page}: {e}")
            break

    return pd.DataFrame(all_reviews)

# --- 3. GIAO DIỆN ---
st.title("British Airways Data Monitoring System")

# Load dữ liệu ban đầu
df = load_data()

with st.sidebar:
    st.header(" Quản lý hệ thống")

    # KIỂM TRA MÔI TRƯỜNG ĐỂ HIỆN NÚT
    # Nếu file không tồn tại, ta cho phép tạo mới
    if not os.path.exists(FILE_LOCAL):
        st.warning("Chưa tìm thấy file dữ liệu cục bộ.")
        if st.button(" Khởi tạo & Cào 10 trang đầu"):
            with st.spinner("Đang khởi tạo dữ liệu..."):
                new_df = scrape_data(max_pages=10)
                if not new_df.empty:
                    new_df.to_csv(FILE_LOCAL, index=False, encoding="utf-8-sig")
                    st.success("Đã tạo file! Hãy chạy lại App.")
                    st.rerun()
    else:
        st.success(" Chế độ: Máy trạm (Local)")
        if st.button(" Cập nhật dữ liệu mới"):
            df_history = pd.read_csv(FILE_LOCAL)
            df_history["Date"] = pd.to_datetime(df_history["Date"], format='mixed')
            last_checkpoint = df_history["Date"].max()

            with st.spinner("Đang kiểm tra dữ liệu mới trên Skytrax..."):
                new_df = scrape_data(max_pages=40, checkpoint_date=last_checkpoint)
                if not new_df.empty:
                    # Gộp dữ liệu theo logic Code B
                    final_df = pd.concat([new_df, df_history]).drop_duplicates(subset=["Header", "Date"])
                    final_df.to_csv(FILE_LOCAL, index=False, encoding="utf-8-sig")
                    st.success(f" Đã thêm {len(new_df)} dòng mới!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.info("Dữ liệu đã là mới nhất.")

# --- 4. HIỂN THỊ DỮ LIỆU ---
if df is not None:
    df["Date"] = pd.to_datetime(df["Date"], format='mixed')
    df["Overall_Rating"] = pd.to_numeric(df["Overall_Rating"], errors="coerce")

    # === TÁCH CỘT ROUTE THÀNH ORIGIN / DESTINATION ===
    if 'Route' in df.columns:
        route_split = df['Route'].str.split(r'\s+to\s+', n=1, expand=True, regex=True)
        df['Origin'] = route_split[0].str.strip()
        df['Destination'] = route_split[1].str.strip() if route_split.shape[1] > 1 else None

    # Chuẩn hóa Recommended về chữ thường
    if 'Recommended' in df.columns:
        df['Recommended'] = df['Recommended'].str.strip().str.lower()

    # === BỘ LỌC TRONG SIDEBAR ===
    with st.sidebar:
        st.markdown("### Bộ lọc")

        # Lọc theo khoảng thời gian
        min_date = df["Date"].min().date()
        max_date = df["Date"].max().date()
        date_range = st.date_input(
            "Thời gian",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        # Lọc theo Loại ghế - dùng pills luôn hiển thị
        all_seats = sorted(df["Seat Type"].dropna().unique().tolist())
        selected_seat = st.pills(
            "💺 Hạng ghế",
            options=all_seats,
            default=all_seats,
            selection_mode="multi"
        )

        # Lọc theo Loại hành khách - dùng pills luôn hiển thị
        all_travellers = sorted(df["Type Of Traveller"].dropna().unique().tolist())
        selected_traveller = st.pills(
            "👤 Loại hành khách",
            options=all_travellers,
            default=all_travellers,
            selection_mode="multi"
        )

        # Lọc theo khoảng điểm số
        rating_range = st.slider(
            "⭐ Điểm đánh giá",
            min_value=1, max_value=10,
            value=(1, 10)
        )

        # Lọc theo Recommended (Yes / No) - pills
        selected_recommended = st.pills(
            " Đề xuất ",
            options=["yes", "no"],
            default=["yes", "no"],
            selection_mode="multi"
        )

        # Lọc theo Aircraft - searchable selectbox
        all_aircraft = ["Tất cả"] + sorted(df["Aircraft"].dropna().unique().tolist())
        selected_aircraft = st.selectbox(
            "Loại máy bay",
            options=all_aircraft,
            index=0
        )

        # Lọc theo Thành phố đi (Origin) - searchable selectbox
        all_origins = ["Tất cả"] + sorted(df["Origin"].dropna().unique().tolist()) if "Origin" in df.columns else ["Tất cả"]
        selected_origin = st.selectbox(
            " Thành phố đi ",
            options=all_origins,
            index=0
        )

        # Lọc theo Thành phố đến (Destination) - searchable selectbox
        all_destinations = ["Tất cả"] + sorted(df["Destination"].dropna().unique().tolist()) if "Destination" in df.columns else ["Tất cả"]
        selected_destination = st.selectbox(
            " Thành phố đến ",
            options=all_destinations,
            index=0
        )

    # --- Áp dụng bộ lọc -> tạo df_filtered ---
    df_filtered = df.copy()

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date = pd.Timestamp(date_range[0])
        end_date = pd.Timestamp(date_range[1])
        df_filtered = df_filtered[
            (df_filtered["Date"] >= start_date) & (df_filtered["Date"] <= end_date)
        ]

    # lọc seat type
    df_filtered = df_filtered[df_filtered["Seat Type"].isin(selected_seat)] if selected_seat is not None else df_filtered.iloc[0:0]

    # lọc traveller type
    df_filtered = df_filtered[df_filtered["Type Of Traveller"].isin(selected_traveller)] if selected_traveller is not None else df_filtered.iloc[0:0]

    # lọc rating
    df_filtered = df_filtered[
        (df_filtered["Overall_Rating"] >= rating_range[0]) &
        (df_filtered["Overall_Rating"] <= rating_range[1])
    ]

    # Lọc Recommended
    if selected_recommended is not None:
        df_filtered = df_filtered[df_filtered["Recommended"].isin(selected_recommended)]
    else:
        df_filtered = df_filtered.iloc[0:0]

    # Lọc Aircraft
    if selected_aircraft != "Tất cả":
        df_filtered = df_filtered[df_filtered["Aircraft"] == selected_aircraft]

    # Lọc Origin
    if selected_origin != "Tất cả" and "Origin" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Origin"] == selected_origin]

    # Lọc Destination
    if selected_destination != "Tất cả" and "Destination" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Destination"] == selected_destination]

    # Hiển thị Metric (dùng df_filtered)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng dữ liệu gốc", f"{len(df)} dòng")
    c2.metric("Số dữ liệu lọc ", f"{len(df_filtered)} dòng")
    c3.metric("Rating trung bình", f"{df_filtered['Overall_Rating'].mean():.2f} /10.00" if len(df_filtered) > 0 else "N/A")
    c4.metric("Ngày cập nhật cuối", str(df["Date"].max().date()))

    st.markdown("---")

    # --- DASHBOARD PHÂN TÍCH ---
    st.header("📊 Dashboard phân tích đánh giá")

    if len(df_filtered) == 0:
        st.warning("⚠️ Không có dữ liệu phù hợp với bộ lọc hiện tại. Hãy điều chỉnh điều kiện lọc ở thanh bên trái.")
    else:
        # === BIỂU ĐỒ: XU HƯỚNG THỜI GIAN ===
        import plotly.graph_objects as go
        st.subheader("📈 Xu hướng điểm đánh giá theo thời gian")
        df_trend_base = df_filtered.copy()
        df_trend_base['YearMonth'] = df_trend_base['Date'].dt.to_period('M').astype(str)

        # Tính avg rating và số lượng review theo tháng
        trend_agg = df_trend_base.groupby('YearMonth').agg(
            Avg_Rating=('Overall_Rating', 'mean'),
            Review_Count=('Overall_Rating', 'count')
        ).reset_index()

        # Tính rolling average 3 tháng
        trend_agg['Rolling_Avg'] = trend_agg['Avg_Rating'].rolling(window=3, min_periods=1).mean()

        # Tìm điểm min/max
        idx_max = trend_agg['Avg_Rating'].idxmax()
        idx_min = trend_agg['Avg_Rating'].idxmin()

        fig_trend = go.Figure()

        # Cột: Số lượng review (trục Y phụ bên phải)
        fig_trend.add_trace(go.Bar(
            x=trend_agg['YearMonth'],
            y=trend_agg['Review_Count'],
            name='Số lượng reviews',
            marker_color='rgba(100,160,220,0.35)',
            yaxis='y2'
        ))

        # Đường: Avg Rating
        fig_trend.add_trace(go.Scatter(
            x=trend_agg['YearMonth'],
            y=trend_agg['Avg_Rating'],
            mode='lines+markers',
            name='Rating trung bình',
            line=dict(color='#1e8c4e', width=2.5),
            marker=dict(size=6)
        ))

        # Đường: Rolling avg 3 tháng
        fig_trend.add_trace(go.Scatter(
            x=trend_agg['YearMonth'],
            y=trend_agg['Rolling_Avg'],
            mode='lines',
            name='Rolling avg (3 tháng)',
            line=dict(color='#f4a261', width=2, dash='dash')
        ))

        # Annotation điểm cao nhất
        fig_trend.add_annotation(
            x=trend_agg.loc[idx_max, 'YearMonth'],
            y=trend_agg.loc[idx_max, 'Avg_Rating'],
            text=f"⬆ Cao nhất: {trend_agg.loc[idx_max, 'Avg_Rating']:.2f}",
            showarrow=True, arrowhead=2,
            bgcolor='#1e8c4e', font=dict(color='white', size=11), arrowcolor='#1e8c4e'
        )

        # Annotation điểm thấp nhất
        fig_trend.add_annotation(
            x=trend_agg.loc[idx_min, 'YearMonth'],
            y=trend_agg.loc[idx_min, 'Avg_Rating'],
            text=f"⬇ Thấp nhất: {trend_agg.loc[idx_min, 'Avg_Rating']:.2f}",
            showarrow=True, arrowhead=2, ay=40,
            bgcolor='#e63946', font=dict(color='white', size=11), arrowcolor='#e63946'
        )

        fig_trend.update_layout(
            title='Xu hướng Rating trung bình & Số lượng reviews theo tháng',
            yaxis=dict(title='Rating trung bình (1-10)', range=[0, 10.5]),
            yaxis2=dict(title='Số lượng reviews', overlaying='y', side='right', showgrid=False),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            hovermode='x unified',
            xaxis=dict(
                type='category',
                tickangle=-45,
                tickmode='auto',
                dtick=1
            )
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        st.info("💡 **Insight:** Đường **xanh lá** = Rating trung bình thực tế; Đường **cam đứt** = xu hướng làm mượt 3 tháng (loại bỏ nhiễu); Cột **xanh nhạt** = số lượng reviews. Chú ý các tháng có ít reviews → dữ liệu kém đại diện hơn.")

        # === BIỂU ĐỒ SO SÁNH ===
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Average Rating by Seat Type")

            seat_rating = (
                df_filtered.dropna(subset=["Seat Type", "Overall_Rating"])
                .groupby("Seat Type")["Overall_Rating"]
                .mean()
                .reset_index()
                .sort_values("Overall_Rating", ascending=False)
            )

            fig1 = px.bar(
                seat_rating,
                x="Seat Type",
                y="Overall_Rating",
                text="Overall_Rating",
                title="Average Rating by Seat Type"
            )
            fig1.update_traces(texttemplate="%{text:.2f}", textposition="outside")
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            st.subheader("Reviews by Traveller Type")

            traveller_count = (
                df_filtered["Type Of Traveller"]
                .dropna()
                .value_counts()
                .reset_index()
            )
            traveller_count.columns = ["Type Of Traveller", "Count"]

            fig2 = px.pie(
                traveller_count,
                names="Type Of Traveller",
                values="Count",
                title="Distribution of Traveller Types"
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.info(
            "💡 **Insight:** Các biểu đồ này so sánh mức độ hài lòng tổng quan theo loại ghế và nhóm hành khách, "
            "giúp nhận diện tệp khách hàng nào đang có trải nghiệm tiêu cực nhất để hãng tập trung cải thiện."
        )

        # === BIỂU ĐỒ: ĐÁNH GIÁ CHI TIẾT THEO LOẠI GHẾ ===
        st.markdown("---")
        st.subheader("⚖️ Detailed service evaluation by seat class.")

        # Các cột dịch vụ cần phân tích
        service_cols = ['Seat Comfort', 'Cabin Staff Service', 'Food & Beverages',
                        'Inflight Entertainment', 'Ground Service', 'Value For Money']

        # Chuyển dữ liệu dạng text (sao) sang số, áp dụng trên df_filtered
        df_services = df_filtered.copy()
        for col in service_cols:
            if col in df_services.columns:
                df_services[col] = pd.to_numeric(df_services[col], errors='coerce')

        # Tính trung bình các dịch vụ theo loại ghế
        service_avg = df_services.groupby('Seat Type')[service_cols].mean().reset_index()

        # Melt dataframe để vẽ grouped bar chart bằng Plotly
        service_melted = pd.melt(service_avg, id_vars=['Seat Type'], value_vars=service_cols,
                                 var_name='Dịch vụ', value_name='Điểm trung bình')

        fig_service = px.bar(
            service_melted,
            x='Dịch vụ',
            y='Điểm trung bình',
            color='Seat Type',
            barmode='group',
            title="Comparison of service scores (1-5 stars) between seat classes"
        )
        fig_service.update_traces(texttemplate="%{y:.1f}", textposition="outside")
        fig_service.update_layout(xaxis_title="Service criteria", yaxis_title="Average rating (1-5 stars)")
        st.plotly_chart(fig_service, use_container_width=True)

        st.info("💡 **Insight:** Biểu đồ này đi sâu vào từng tiêu chí dịch vụ thay vì điểm tổng quan. Nó cho thấy liệu khách Hạng Thương gia (Business) có thực sự hài lòng với Đồ ăn (Food & Beverages) hơn Hạng Phổ thông không, hay họ còn khắt khe hơn. Từ đó hãng có chiến lược nâng cấp dịch vụ cụ thể.")

        st.markdown("---")
        st.subheader("📋 Top 20 đánh giá mới nhất")
        st.dataframe(df_filtered.sort_values("Date", ascending=False).head(20), use_container_width=True)

        # Nút Download (xuất dữ liệu đã lọc)
        csv = df_filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Tải dữ liệu CSV (đã lọc)", data=csv, file_name="ba_filtered_data.csv", mime="text/csv")

else:
    st.info("Đang chờ dữ liệu từ Cloud hoặc Local...")
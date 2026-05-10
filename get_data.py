# cd "C:\Users\Admin\OneDrive - VNU-HCMUS\phân tích dữ liệu thông minh"
#  python -m streamlit run app.py
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import numpy as np
import plotly.express as px
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
        if found_stop_point: break
        status_text.text(f" Đang quét trang {page}...")
        url = f"{BASE_URL}{page}/?sortby=post_date%3ADesc&pagesize=100"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all("article", {"itemprop": "review"})
            
            if not articles: break

            for item in articles:
                # Lấy ngày để kiểm tra checkpoint
                date_tag = item.find("time", {"itemprop": "datePublished"})
                if not date_tag: continue
                
                date_str = date_tag['datetime']
                current_timestamp = pd.to_datetime(date_str, errors='coerce')
                if pd.isna(current_timestamp):
                    continue
                current_date = current_timestamp.date()

                # DỪNG KHI GẶP DATA ĐÃ CÓ TRONG MÁY
                if checkpoint_date:
                    
                    safe_checkpoint = pd.to_datetime(checkpoint_date).date()
                    
                    if current_date <= safe_checkpoint:
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
            time.sleep(2) # Giảm xuống 2s để cào nhanh hơn nhưng vẫn an toàn
        except Exception as e:
            st.error(f"Lỗi tại trang {page}: {e}")
            break
            
    return pd.DataFrame(all_reviews)





def preprocess_data(df):
    if df is None or df.empty:
        return df

    # --- 1. LÀM SẠCH CƠ BẢN ---
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    df['Date'] = df['Date'].dt.date
    df['Overall_Rating'] = pd.to_numeric(df['Overall_Rating'], errors='coerce')

    # Fill missing với -1 cho các cột Rating dịch vụ
    cols = ['Wifi & Connectivity', 'Inflight Entertainment', 'Food & Beverages', 
            'Cabin Staff Service', 'Seat Comfort', 'Ground Service']
    existing_cols = [col for col in cols if col in df.columns]
    if existing_cols:
        for col in existing_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df[existing_cols] = df[existing_cols].fillna(-1)

    # Fill 'Unknown' cho cột Aircraft
    if 'Aircraft' in df.columns:
        if pd.api.types.is_categorical_dtype(df['Aircraft']):
            if 'Unknown' not in df['Aircraft'].cat.categories:
                df['Aircraft'] = df['Aircraft'].cat.add_categories(['Unknown'])
        df['Aircraft'] = df['Aircraft'].fillna('Unknown')

    # --- 2. TÁCH CỘT ROUTE (LOGIC CỦA BẠN) ---
    if 'Route' in df.columns:
        df['Route'] = df['Route'].astype(object).fillna('MISSING_ROUTE')
        
        # Tách 'Departure' và 'Arrival_and_Transit'
        route_parts = df['Route'].str.split(r'\s+to\s+', expand=True, n=1)
        
        # Lớp phòng thủ: Đảm bảo split thành công ra 2 cột trước khi gán tên
        if route_parts.shape[1] == 2:
            route_parts.columns = ['Departure', 'Arrival_and_Transit']
            TRANSIT_PATTERN = r'\s+via\s+(.+)'
            
            df['Departure_city'] = route_parts['Departure'].str.strip()
            df['Transit_city'] = route_parts['Arrival_and_Transit'].str.extract(TRANSIT_PATTERN).iloc[:, 0].str.strip()
            df['Arrival_city'] = route_parts['Arrival_and_Transit'].str.replace(TRANSIT_PATTERN, '', regex=True).str.strip()

            for col in ['Departure_city', 'Arrival_city', 'Transit_city']:
                df[col] = df[col].replace('MISSING_ROUTE', np.nan).astype(object)

            condition = (df['Transit_city'].isna() & df['Departure_city'].notna() & df['Arrival_city'].notna())
            df.loc[condition, 'Transit_city'] = "No transition"

    # --- 3. CHUẨN HÓA TÊN THÀNH PHỐ (LOGIC CỦA BẠN) ---
    try:
        airport_df = pd.read_csv('airport_codes_cleaned.csv')
        iata_to_city_map = airport_df.set_index('iata_code')['city'].to_dict()
        airport_to_city_map = airport_df.drop_duplicates(subset=['airport_name']).set_index('airport_name')['city'].to_dict()
        
        # Lấy list cities và loại bỏ các giá trị NaN trong từ điển để tránh lỗi khi lower()
        cities = airport_df['city'].dropna().str.lower().tolist()
        
        columns_to_standardize = ['Departure_city', 'Arrival_city', 'Transit_city']
        existing_city_cols = [col for col in columns_to_standardize if col in df.columns]

        # Hàm map fuzzy của bạn
        def replace_with_city(city_val, city_list):
            if pd.isna(city_val): return city_val
            lower_val = str(city_val).lower()
            for city in city_list:
                if city in lower_val:
                    return city.title()
            return city_val

        for col in existing_city_cols:
            df[col + '_mapped'] = df[col].copy()
            df[col + '_mapped'] = df[col + '_mapped'].replace(iata_to_city_map)
            unmapped_mask = (df[col + '_mapped'] == df[col])
            df.loc[unmapped_mask, col + '_mapped'] = df.loc[unmapped_mask, col].replace(airport_to_city_map)
            df[col] = df[col + '_mapped']
            del df[col + '_mapped']

            # Áp dụng fuzzy map
            df[col] = df[col].apply(lambda x: replace_with_city(x, cities))

    except FileNotFoundError:
        # Nếu app không tìm thấy file csv phụ trợ, nó sẽ bỏ qua để không làm sập luồng chạy
        pass

    # --- 4. XÓA CÁC DÒNG THIẾU DỮ LIỆU QUAN TRỌNG ---
    drop_cols = ['Type Of Traveller', 'Transit_city', 'Departure_city', 'Arrival_city']
    valid_drop_cols = [c for c in drop_cols if c in df.columns]
    
    if valid_drop_cols:
        df = df.dropna(subset=valid_drop_cols).reset_index(drop=True)

    return df
# --- 3. GIAO DIỆN ---

st.title("✈️ SkyHigh Insights: BA Passenger Analytics")

# Load dữ liệu lịch sử và tự động làm sạch nếu có
df = load_data()
if df is not None:
    df = preprocess_data(df)

with st.sidebar:
    st.header("⚙️ Quản lý hệ thống")
    
    if not os.path.exists(FILE_LOCAL):
        st.warning("Chưa tìm thấy file dữ liệu cục bộ.")
        if st.button("🚀 Khởi tạo & Cào 10 trang đầu"):
            with st.spinner("Đang khởi tạo dữ liệu và làm sạch..."):
                new_df = scrape_data(max_pages=10)
                if not new_df.empty:
                    # GỌI HÀM LÀM SẠCH NGAY TẠI ĐÂY
                    clean_df = preprocess_data(new_df) 
                    clean_df.to_csv(FILE_LOCAL, index=False, encoding='utf-8-sig')
                    st.success("Đã tạo và làm sạch file! Hãy tải lại trang.")
                    st.rerun()
    else:
        st.success("🟢 Chế độ: Hoạt động (Local)")
        if st.button("🔄 Cập nhật dữ liệu mới"):
            # Đọc file lịch sử an toàn để tìm ngày dừng
            df_history = pd.read_csv(FILE_LOCAL)
            df_history['Date'] = pd.to_datetime(df_history['Date'], errors='coerce')
            last_checkpoint = df_history['Date'].dropna().max().date()
            
            with st.spinner("Đang cào dữ liệu mới và áp dụng bộ lọc EDA..."):
                new_df = scrape_data(max_pages=40, checkpoint_date=last_checkpoint)
                
                if not new_df.empty:
                    # 1. LÀM SẠCH DỮ LIỆU VỪA CÀO
                    clean_new_df = preprocess_data(new_df)
                    
                    # 2. ĐỌC LẠI LỊCH SỬ VÀ LÀM SẠCH (đề phòng)
                    clean_history_df = preprocess_data(pd.read_csv(FILE_LOCAL))
                    
                    # 3. GỘP LẠI VÀ LƯU
                    final_df = pd.concat([clean_new_df, clean_history_df]).drop_duplicates(subset=['Header', 'Date'])
                    final_df.to_csv(FILE_LOCAL, index=False, encoding='utf-8-sig')
                    
                    st.success(f"🎉 Đã thêm và xử lý {len(clean_new_df)} dòng mới!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.info("Dữ liệu đã là mới nhất.")

# --- 4. HIỂN THỊ DỮ LIỆU & PHÂN TÍCH ---
# Vì dữ liệu df đã được làm sạch ngay từ lúc load (dòng 5), phần hiển thị trở nên rất gọn gàng!
if df is not None and not df.empty:
    
    # --- TẠO TABS ---
    tab1, tab2 = st.tabs(["📊 Bảng Dữ Liệu Sạch", "📈 Phân Tích (Analytics)"])

    with tab1:
        st.subheader("Dữ liệu trực tiếp (Đã qua EDA)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng quy mô", f"{len(df)} đánh giá")
        
        
        if 'Overall_Rating' in df.columns:
            c2.metric("Rating trung bình", f"{df['Overall_Rating'].mean():.2f} / 10")
        
        if 'Date' in df.columns:
            c3.metric("Ngày cập nhật cuối", str(df['Date'].dropna().max()))

        
        st.dataframe(df.sort_values('Date', ascending=False).head(10), use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("⬇️ Tải dữ liệu CSV (Đã làm sạch)", data=csv, file_name="ba_clean_data.csv", mime="text/csv")

    with tab2:
        st.subheader("📈 Phân Tích Chuyên Sâu (Analytics)")
        
        if 'Date' in df.columns and 'Overall_Rating' in df.columns:
            # --- BIỂU ĐỒ 1: XU HƯỚNG ĐIỂM TỔNG THỂ ---
            st.markdown("##### 1. Xu hướng Điểm đánh giá trung bình theo tháng")
            
            # Nhóm dữ liệu theo Tháng/Năm
            df['Month_Year'] = pd.to_datetime(df['Date']).dt.to_period('M').astype(str)
            trend_df = df.groupby('Month_Year')['Overall_Rating'].mean().reset_index()
            
            # Vẽ Line Chart
            fig_trend = px.line(trend_df, x='Month_Year', y='Overall_Rating', 
                                markers=True,
                                labels={"Month_Year": "Thời gian", "Overall_Rating": "Điểm tổng thể (1-10)"})
            fig_trend.update_yaxes(range=[1, 10]) # Chốt trục Y từ 1-10
            fig_trend.update_traces(line_color='#1f77b4', line_width=3, marker=dict(size=8))
            st.plotly_chart(fig_trend, use_container_width=True)

            st.markdown("---")

            # --- BIỂU ĐỒ 2: ĐÁNH GIÁ TỪNG DỊCH VỤ ---
            st.markdown("##### 2. Khách hàng đang phàn nàn/hài lòng về dịch vụ nào nhất?")
            
            # Danh sách các cột dịch vụ (thang điểm 5)
            service_cols = ['Seat Comfort', 'Cabin Staff Service', 'Food & Beverages', 
                            'Inflight Entertainment', 'Ground Service', 'Wifi & Connectivity']
            
            # Chỉ lấy những cột thực sự tồn tại trong data
            valid_services = [c for c in service_cols if c in df.columns]
            
            if valid_services:
                service_means = {}
                for col in valid_services:
                    # RẤT QUAN TRỌNG: Chỉ tính điểm trung bình cho những khách có sử dụng dịch vụ (> 0)
                    # Loại bỏ các giá trị -1 (chưa dùng) hoặc NaN mà chúng ta đã xử lý ở bước EDA
                    valid_data = df[df[col] > 0][col]
                    if not valid_data.empty:
                        service_means[col] = valid_data.mean()
                
                if service_means:
                    # Chuyển Dictionary thành DataFrame để vẽ biểu đồ
                    service_df = pd.DataFrame(list(service_means.items()), columns=['Dịch vụ', 'Điểm trung bình'])
                    # Sắp xếp từ cao xuống thấp
                    service_df = service_df.sort_values('Điểm trung bình', ascending=True)
                    
                    # Vẽ Bar Chart ngang
                    fig_bar = px.bar(service_df, x='Điểm trung bình', y='Dịch vụ', orientation='h',
                                     color='Điểm trung bình', color_continuous_scale='Blues',
                                     labels={"Điểm trung bình": "Điểm (1 - 5)", "Dịch vụ": ""})
                    
                    fig_bar.update_xaxes(range=[1, 5]) # Chốt trục X từ 1-5 sao
                    st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Chưa có đủ dữ liệu chi tiết về các dịch vụ để hiển thị biểu đồ này.")
                
        else:
            st.warning("Không đủ dữ liệu Date hoặc Rating để vẽ biểu đồ.")

else:
    st.info("👈 Bấm 'Khởi tạo & Cào 10 trang đầu' ")
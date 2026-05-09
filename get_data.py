# cd "C:\Users\Admin\OneDrive - VNU-HCMUS\phân tích dữ liệu thông minh"
#  python -m streamlit run app.py
import streamlit as st
import pandas as pd
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
            time.sleep(2) # Giảm xuống 2s để cào nhanh hơn nhưng vẫn an toàn
        except Exception as e:
            st.error(f"Lỗi tại trang {page}: {e}")
            break
            
    return pd.DataFrame(all_reviews)

# --- 3. GIAO DIỆN ---
st.title("✈️ British Airways Data Monitoring System")

# Load dữ liệu ban đầu
df = load_data()

with st.sidebar:
    st.header(" Quản lý hệ thống")
    
    # KIỂM TRA MÔ TRƯỜNG ĐỂ HIỆN NÚT
    # Nếu file không tồn tại, ta cho phép tạo mới
    if not os.path.exists(FILE_LOCAL):
        st.warning("Chưa tìm thấy file dữ liệu cục bộ.")
        if st.button(" Khởi tạo & Cào 10 trang đầu"):
            with st.spinner("Đang khởi tạo dữ liệu..."):
                new_df = scrape_data(max_pages=10)
                if not new_df.empty:
                    new_df.to_csv(FILE_LOCAL, index=False, encoding='utf-8-sig')
                    st.success("Đã tạo file! Hãy chạy lại App.")
                    st.rerun()
    else:
        st.success(" Chế độ: Máy trạm (Local)")
        if st.button(" Cập nhật dữ liệu mới"):
            df_history = pd.read_csv(FILE_LOCAL)
            df_history['Date'] = pd.to_datetime(df_history['Date'])
            last_checkpoint = df_history['Date'].max()
            
            with st.spinner("Đang kiểm tra dữ liệu mới trên Skytrax..."):
                new_df = scrape_data(max_pages=40, checkpoint_date=last_checkpoint)
                if not new_df.empty:
                    # Gộp dữ liệu theo logic Code B
                    final_df = pd.concat([new_df, df_history]).drop_duplicates(subset=['Header', 'Date'])
                    final_df.to_csv(FILE_LOCAL, index=False, encoding='utf-8-sig')
                    st.success(f" Đã thêm {len(new_df)} dòng mới!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.info("Dữ hiệu đã là mới nhất.")

# --- 4. HIỂN THỊ DỮ LIỆU ---
if df is not None:
    df['Date'] = pd.to_datetime(df['Date'])
    df['Overall_Rating'] = pd.to_numeric(df['Overall_Rating'], errors='coerce')
    
    # Hiển thị Metric
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng quy mô", f"{len(df)} dòng")
    c2.metric("Rating trung bình", f"{df['Overall_Rating'].mean():.2f}")
    c3.metric("Ngày cập nhật cuối", str(df['Date'].max().date()))

    st.markdown("---")
    st.subheader(" Top 20 đánh giá mới nhất")
    st.dataframe(df.sort_values('Date', ascending=False).head(20), use_container_width=True)

    # Nút Download
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(" Tải dữ liệu CSV", data=csv, file_name="ba_monitor_data.csv", mime="text/csv")
else:
    st.info("Đang chờ dữ liệu từ Cloud hoặc Local...")
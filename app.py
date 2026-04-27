import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import plotly.express as px

# --- CẤU HÌNH ---
FILE_NAME = "ba_detailed_reviews.csv"
BASE_URL = "https://www.airlinequality.com/airline-reviews/british-airways/page/"

st.set_page_config(page_title="Data Monitoring System", layout="wide")

# --- HÀM THU THẬP DỮ LIỆU (SCRAPER) ---
def scrape_data(max_pages=2):
    all_reviews = []
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}{page}/?sortby=post_date%3ADesc&pagesize=100"
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all("article", {"itemprop": "review"})

            for item in articles:
                # Thông tin cơ bản
                review_dict = {
                    "Date": item.find("time", {"itemprop": "datePublished"})['datetime'],
                    "Overall_Rating": item.find("span", {"itemprop": "ratingValue"}).text if item.find("span", {"itemprop": "ratingValue"}) else "0",
                    "Header": item.find("h2", {"class": "text_header"}).text.strip(),
                }
                
                # Bóc tách bảng chỉ số chi tiết
                review_stats = item.find("table", {"class": "review-ratings"})
                if review_stats:
                    rows = review_stats.find_all("tr")
                    for row in rows:
                        header = row.find("td", {"class": "review-rating-header"}).text.strip()
                        # Dạng text
                        val = row.find("td", {"class": "review-value"})
                        if val: review_dict[header] = val.text.strip()
                        # Dạng sao
                        stars = row.find("td", {"class": "review-rating-stars"})
                        if stars: review_dict[header] = len(stars.find_all("span", {"class": "star fill"}))
                
                all_reviews.append(review_dict)
            time.sleep(2) # Nghỉ ngắn để tránh bị chặn
        except:
            break
    return pd.DataFrame(all_reviews)

# --- GIAO DIỆN CHÍNH ---
st.title("🛡️ Hệ thống Thu thập & Giám sát dữ liệu hàng không")
st.markdown(f"**Trạng thái lưu trữ:** Lập nhật vào file `{FILE_NAME}`")

# --- CHỨC NĂNG CẬP NHẬT (MONITORING LOGIC) ---
if st.button("🔄 Cập nhật nhận xét mới nhất từ Skytrax"):
    with st.spinner("Đang kiểm tra và thu thập dữ liệu mới..."):
        new_df = scrape_data(max_pages=2) # Lấy 2 trang mới nhất để kiểm tra
        
        if os.path.exists(FILE_NAME):
            old_df = pd.read_csv(FILE_NAME)
            # Gộp và xóa trùng lặp dựa trên Tiêu đề và Ngày
            combined_df = pd.concat([new_df, old_df]).drop_duplicates(subset=['Header', 'Date'], keep='last')
            added_count = len(combined_df) - len(old_df)
            combined_df.to_csv(FILE_NAME, index=False, encoding='utf-8-sig')
            st.success(f"Hoàn thành! Đã tìm thấy và thêm {added_count} nhận xét mới.")
        else:
            new_df.to_csv(FILE_NAME, index=False, encoding='utf-8-sig')
            st.success(f"Đã tạo file mới với {len(new_df)} nhận xét.")

# --- HIỂN THỊ DỮ LIỆU ---
if os.path.exists(FILE_NAME):
    df = pd.read_csv(FILE_NAME)
    df['Date'] = pd.to_datetime(df['Date'])
    
    # KPIs đơn giản
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng dữ liệu hiện có", len(df))
    c2.metric("Đánh giá trung bình", round(df['Overall_Rating'].mean(), 2))
    c3.metric("Lần cập nhật cuối", str(df['Date'].max().date()))

    # Biểu đồ giám sát xu hướng
    st.subheader("📈 Biểu đồ giám sát phong độ hãng bay")
    df_trend = df.set_index('Date').resample('ME')['Overall_Rating'].mean().reset_index()
    fig = px.area(df_trend, x='Date', y='Overall_Rating', title="Xu hướng hài lòng tích lũy")
    st.plotly_chart(fig, use_container_width=True)

    # Bảng dữ liệu thô
    st.subheader("📄 Dữ liệu chi tiết trong file CSV")
    st.dataframe(df, use_container_width=True)
    
    # Nút tải file CSV về máy
    with open(FILE_NAME, "rb") as file:
        st.download_button(label="📥 Tải file CSV về máy", data=file, file_name=FILE_NAME, mime="text/csv")
else:
    st.warning("Hiện chưa có dữ liệu. Vui lòng nhấn nút 'Cập nhật' ở trên để bắt đầu thu thập.")

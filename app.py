import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import plotly.express as px

# --- CẤU HÌNH HỆ THỐNG ---
FILE_NAME = "ba_detailed_reviews.csv"
BASE_URL = "https://www.airlinequality.com/airline-reviews/british-airways/page/"

st.set_page_config(page_title="Hệ thống Thu thập & Lưu trữ Dữ liệu", layout="wide")

# --- HÀM THU THẬP DỮ LIỆU (Cào chuyên sâu) ---
def scrape_latest_reviews(max_pages=2):
    all_reviews = []
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}{page}/?sortby=post_date%3ADesc&pagesize=100"
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all("article", {"itemprop": "review"})

            for item in articles:
                # 1. Thông tin cơ bản
                review_dict = {
                    "Date": item.find("time", {"itemprop": "datePublished"})['datetime'],
                    "Overall_Rating": item.find("span", {"itemprop": "ratingValue"}).text if item.find("span", {"itemprop": "ratingValue"}) else "0",
                    "Header": item.find("h2", {"class": "text_header"}).text.strip(),
                    "Review_Body": item.find("div", {"class": "text_content"}).text.strip()
                }
                
                # 2. Thông tin chi tiết từ bảng (Giống form khai báo)
                review_stats = item.find("table", {"class": "review-ratings"})
                if review_stats:
                    rows = review_stats.find_all("tr")
                    for row in rows:
                        header = row.find("td", {"class": "review-rating-header"}).text.strip()
                        # Dạng text (Type of Traveller, Seat Type, v.v.)
                        val = row.find("td", {"class": "review-value"})
                        if val: review_dict[header] = val.text.strip()
                        # Dạng điểm sao (1-5)
                        stars = row.find("td", {"class": "review-rating-stars"})
                        if stars: review_dict[header] = len(stars.find_all("span", {"class": "star fill"}))
                
                all_reviews.append(review_dict)
            time.sleep(5) # Nghỉ 1 giây để đảm bảo an toàn cho server
        except Exception as e:
            st.error(f"Lỗi tại trang {page}: {e}")
            break
    return pd.DataFrame(all_reviews)

# --- GIAO DIỆN APP ---
st.title("📂 Hệ thống Cập nhật Dữ liệu Đánh giá Hàng không")
st.info(f"Dữ liệu hiện tại được lưu trữ tại file: **{FILE_NAME}**")

# --- KHỐI XỬ LÝ CẬP NHẬT ---
if st.button("🚀 Bắt đầu Cập nhật Dữ liệu Mới"):
    with st.spinner("Đang kết nối Skytrax và tìm kiếm nhận xét mới..."):
        # Bước 1: Cào dữ liệu mới nhất (lấy 2-3 trang đầu để đảm bảo có review mới nhất)
        new_data_df = scrape_latest_reviews(max_pages=3)
        
        if not new_data_df.empty:
            if os.path.exists(FILE_NAME):
                # Bước 2: Đọc dữ liệu cũ từ file CSV
                old_data_df = pd.read_csv(FILE_NAME)
                
                # Bước 3: Gộp dữ liệu và loại bỏ trùng lặp
                # Dựa trên Header và Date để xác định một review duy nhất
                combined_df = pd.concat([new_data_df, old_data_df])
                combined_df = combined_df.drop_duplicates(subset=['Header', 'Date'], keep='first')
                
                # Tính toán số lượng bản ghi mới thêm vào
                new_records_count = len(combined_df) - len(old_data_df)
                
                # Bước 4: Lưu lại vào file .csv
                combined_df.to_csv(FILE_NAME, index=False, encoding='utf-8-sig')
                
                if new_records_count > 0:
                    st.success(f"Thành công! Đã thêm {new_records_count} nhận xét mới vào file CSV.")
                else:
                    st.info("Không có nhận xét nào mới hơn dữ liệu hiện tại.")
            else:
                # Nếu chưa có file, tạo file mới hoàn toàn
                new_data_df.to_csv(FILE_NAME, index=False, encoding='utf-8-sig')
                st.success(f"Đã tạo file mới và lưu {len(new_data_df)} nhận xét.")
        else:
            st.error("Không thể lấy dữ liệu từ website. Vui lòng kiểm tra kết nối mạng.")

# --- HIỂN THỊ THỐNG KÊ VÀ DỮ LIỆU ---
if os.path.exists(FILE_NAME):
    df = pd.read_csv(FILE_NAME)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Overall_Rating'] = pd.to_numeric(df['Overall_Rating'], errors='coerce')

    # Thống kê nhanh
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Tổng số dòng trong CSV", len(df))
    with c2:
        st.metric("Điểm Overall TB", f"{df['Overall_Rating'].mean():.2f}")
    with c3:
        st.metric("Ngày cập nhật cuối", str(df['Date'].max().date()))

    # Xem trước dữ liệu
    st.subheader("📊 Xem trước 10 dòng dữ liệu mới nhất trong CSV")
    st.dataframe(df.sort_values(by='Date', ascending=False).head(10), use_container_width=True)

    # Nút Download cho người dùng
    with open(FILE_NAME, "rb") as f:
        st.download_button(
            label="📥 Tải file CSV hiện tại về máy",
            data=f,
            file_name=FILE_NAME,
            mime="text/csv"
        )
else:
    st.warning("Hiện chưa có file CSV dữ liệu. Hãy nhấn nút 'Bắt đầu Cập nhật' để tạo dữ liệu.")

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os

# --- CẤU HÌNH ---
FILE_NAME = "ba_detailed_reviews.csv"
BASE_URL = "https://www.airlinequality.com/airline-reviews/british-airways/page/"

st.set_page_config(page_title="Hệ thống Thu thập Dữ liệu", layout="wide")

# --- HÀM THU THẬP DỮ LIỆU (CRAWLER) ---
def scrape_data(max_pages=40, checkpoint_date=None):
    all_reviews = []
    found_stop_point = False
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for page in range(1, max_pages + 1):
        if found_stop_point:
            break
            
        status_text.text(f"🔎 Đang quét trang {page}...")
        url = f"{BASE_URL}{page}/?sortby=post_date%3ADesc&pagesize=100"
        
        try:
            response = requests.get(url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all("article", {"itemprop": "review"})

            if not articles:
                break

            for item in articles:
                date_str = item.find("time", {"itemprop": "datePublished"})['datetime']
                current_date = pd.to_datetime(date_str)

                # KIỂM TRA ĐIỂM DỪNG (CHECKPOINT)
                if checkpoint_date and current_date <= checkpoint_date:
                    found_stop_point = True
                    break

                # Thu thập thông tin cơ bản
                review_dict = {
                    "Date": date_str,
                    "Overall_Rating": item.find("span", {"itemprop": "ratingValue"}).text if item.find("span", {"itemprop": "ratingValue"}) else "0",
                    "Header": item.find("h2", {"class": "text_header"}).text.strip(),
                    "Review_Body": item.find("div", {"class": "text_content"}).text.strip()
                }
                
                # Thu thập các chỉ số đánh giá chi tiết trong bảng
                stats = item.find("table", {"class": "review-ratings"})
                if stats:
                    for row in stats.find_all("tr"):
                        header = row.find("td", {"class": "review-rating-header"}).text.strip()
                        # Giá trị dạng văn bản
                        val = row.find("td", {"class": "review-value"})
                        if val: review_dict[header] = val.text.strip()
                        # Giá trị dạng sao
                        stars = row.find("td", {"class": "review-rating-stars"})
                        if stars: review_dict[header] = len(stars.find_all("span", {"class": "star fill"}))
                
                all_reviews.append(review_dict)

            progress_bar.progress(page / max_pages if not found_stop_point else 1.0)
            time.sleep(2) # Tránh bị chặn (Crawl-delay)
            
        except Exception as e:
            st.error(f"Lỗi kết nối tại trang {page}: {e}")
            break
            
    return pd.DataFrame(all_reviews)

# --- GIAO DIỆN CHÍNH ---
st.title("🛡️ Data Collection System")

# Kiểm tra file CSV cũ để lấy mốc Checkpoint
if os.path.exists(FILE_NAME):
    df_history = pd.read_csv(FILE_NAME)
    df_history['Date'] = pd.to_datetime(df_history['Date'])
    last_checkpoint = df_history['Date'].max()
    st.info(f"📍 Checkpoint: Dữ liệu mới nhất trong máy là ngày **{last_checkpoint.date()}**")
else:
    df_history = pd.DataFrame()
    last_checkpoint = None
    st.warning("🆕 Chưa có dữ liệu. Hệ thống sẽ cào tối đa 40 trang trong lần đầu.")

# NÚT ĐIỀU KHIỂN
if st.button("🔄 Cập nhật dữ liệu (Từ checkpoint)"):
    with st.spinner("Đang thực hiện thu thập..."):
        # Cào tối đa 40 trang, nhưng sẽ dừng ngay khi gặp checkpoint
        new_df = scrape_data(max_pages=40, checkpoint_date=last_checkpoint)
        
        if not new_df.empty:
            # Gộp dữ liệu mới vào dữ liệu cũ
            final_df = pd.concat([new_df, df_history]).drop_duplicates(subset=['Header', 'Date'])
            final_df.to_csv(FILE_NAME, index=False, encoding='utf-8-sig')
            st.success(f"✅ Đã thêm {len(new_df)} nhận xét mới vào file CSV.")
            st.rerun()
        else:
            st.info("Dữ liệu của bạn đã là mới nhất so với website.")

# --- HIỂN THỊ THÔNG SỐ CƠ BẢN ---
if not df_history.empty:
    df_history['Overall_Rating'] = pd.to_numeric(df_history['Overall_Rating'], errors='coerce')
    
    st.markdown("---")
    # 1. Các chỉ số cơ bản
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng quy mô dữ liệu", f"{len(df_history)} dòng")
    c2.metric("Đánh giá tổng (Trung bình)", f"{df_history['Overall_Rating'].mean():.2f}")
    
    # Đánh giá tổng gần nhất (lấy 100 dòng mới nhất làm mẫu)
    recent_avg = df_history.sort_values('Date', ascending=False).head(100)['Overall_Rating'].mean()
    c3.metric("Đánh giá gần nhất (100 bài)", f"{recent_avg:.2f}")

    # 2. Hiển thị 10 dòng đầu trong CSV
    st.subheader("📄 10 dòng dữ liệu mới nhất")
    st.dataframe(df_history.sort_values('Date', ascending=False).head(10), use_container_width=True)

    # 3. Nút tải file CSV
    with open(FILE_NAME, "rb") as file:
        st.download_button(
            label="📥 Tải file dữ liệu (.CSV)",
            data=file,
            file_name=FILE_NAME,
            mime="text/csv"
        )

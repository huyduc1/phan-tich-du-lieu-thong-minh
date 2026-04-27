import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import plotly.express as px
from textblob import TextBlob

# --- CẤU HÌNH ---
FILE_NAME = "ba_detailed_reviews.csv"
BASE_URL = "https://www.airlinequality.com/airline-reviews/british-airways/page/"

st.set_page_config(page_title="Air-Monitor Pro", layout="wide")

# --- HÀM XỬ LÝ NLP ĐƠN GIẢN (MONITORING ELEMENT) ---
def get_sentiment(text):
    if not text: return 0
    return TextBlob(text).sentiment.polarity

# --- BỘ CÀO DỮ LIỆU THÔNG MINH (DATA INGESTION) ---
def smart_scraper(max_pages=40, last_checkpoint=None):
    all_reviews = []
    found_stop = False
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for page in range(1, max_pages + 1):
        if found_stop: break
        
        status_text.text(f"📡 Đang quét trang {page}...")
        url = f"{BASE_URL}{page}/?sortby=post_date%3ADesc&pagesize=100"
        
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all("article", {"itemprop": "review"})

            for item in articles:
                date_str = item.find("time", {"itemprop": "datePublished"})['datetime']
                curr_date = pd.to_datetime(date_str)

                # KIỂM TRA ĐIỂM DỪNG (CHECKPOINT)
                if last_checkpoint and curr_date <= last_checkpoint:
                    found_stop = True
                    break

                # Bóc tách dữ liệu
                content = item.find("div", {"class": "text_content"}).text.strip()
                review_dict = {
                    "Date": date_str,
                    "Overall_Rating": int(item.find("span", {"itemprop": "ratingValue"}).text) if item.find("span", {"itemprop": "ratingValue"}) else 0,
                    "Header": item.find("h2", {"class": "text_header"}).text.strip(),
                    "Review_Body": content,
                    "Sentiment": get_sentiment(content) # Phân tích cảm xúc ngay khi cào
                }
                
                # Chi tiết dịch vụ
                stats = item.find("table", {"class": "review-ratings"})
                if stats:
                    for row in stats.find_all("tr"):
                        h = row.find("td", {"class": "review-rating-header"}).text.strip()
                        v = row.find("td", {"class": "review-value"})
                        if v: review_dict[h] = v.text.strip()
                        s = row.find("td", {"class": "review-rating-stars"})
                        if s: review_dict[h] = len(s.find_all("span", {"class": "star fill"}))
                
                all_reviews.append(review_dict)

            progress_bar.progress(page / max_pages if not found_stop else 1.0)
            time.sleep(1)
        except Exception as e:
            st.error(f"Lỗi: {e}")
            break
            
    return pd.DataFrame(all_reviews)

# --- GIAO DIỆN GIÁM SÁT (DASHBOARD) ---
st.title("✈️ Airline Quality Data Monitoring System")

# Kiểm tra dữ liệu lịch sử
if os.path.exists(FILE_NAME):
    df_history = pd.read_csv(FILE_NAME)
    df_history['Date'] = pd.to_datetime(df_history['Date'])
    last_date = df_history['Date'].max()
else:
    df_history = pd.DataFrame()
    last_date = None

# Sidebar cho chức năng thu thập
with st.sidebar:
    st.header("⚙️ Cấu hình thu thập")
    pages_limit = st.slider("Giới hạn quét (Trang):", 1, 50, 40)
    if st.button("🚀 Kích hoạt Cập nhật"):
        new_data = smart_scraper(max_pages=pages_limit, last_checkpoint=last_date)
        if not new_data.empty:
            df_final = pd.concat([new_data, df_history]).drop_duplicates(subset=['Header', 'Date'])
            df_final.to_csv(FILE_NAME, index=False, encoding='utf-8-sig')
            st.success(f"Đã cập nhật {len(new_data)} bản ghi mới!")
            st.rerun()
        else:
            st.info("Dữ liệu đã là mới nhất!")

# --- TẦNG GIÁM SÁT (MONITORING OUTPUT) ---
if not df_history.empty:
    # 1. KPIs & Alerts
    avg_now = df_history.head(50)['Overall_Rating'].mean() # 50 bản ghi gần nhất
    avg_total = df_history['Overall_Rating'].mean()
    diff = avg_now - avg_total

    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng quy mô dữ liệu", len(df_history))
    c2.metric("Rating trung bình (All)", f"{avg_total:.2f}")
    c3.metric("Rating gần đây (Cửa sổ 50)", f"{avg_now:.2f}", delta=f"{diff:.2f}")

    # Cảnh báo bất thường (Anomaly Detection)
    if diff < -1.0:
        st.error(f"⚠️ CẢNH BÁO GIÁM SÁT: Chất lượng dịch vụ đang sụt giảm nghiêm trọng ({diff:.2f} điểm)!")

    # 2. Biểu đồ xu hướng (Moving Average)
    st.subheader("📈 Phân tích xu hướng chất lượng (MA30)")
    df_daily = df_history.groupby('Date')['Overall_Rating'].mean().reset_index()
    df_daily['MA30'] = df_daily['Overall_Rating'].rolling(window=30).mean()
    
    fig = px.line(df_daily, x='Date', y=['Overall_Rating', 'MA30'], 
                  title="Biến động điểm số và Đường trung bình động 30 ngày")
    st.plotly_chart(fig, use_container_width=True)

    # 3. Phân tích cảm xúc
    st.subheader("🎭 Giám sát trạng thái khách hàng")
    fig_sent = px.histogram(df_history, x='Sentiment', nbins=50, title="Phân phối cảm xúc (Tiêu cực < 0 < Tích cực)")
    st.plotly_chart(fig_sent, use_container_width=True)

    # 4. Bảng dữ liệu thô
    with st.expander("🔍 Xem chi tiết kho dữ liệu CSV"):
        st.dataframe(df_history)
else:
    st.warning("Hệ thống trống. Hãy nhấn 'Kích hoạt Cập nhật' ở Sidebar để bắt đầu.")
